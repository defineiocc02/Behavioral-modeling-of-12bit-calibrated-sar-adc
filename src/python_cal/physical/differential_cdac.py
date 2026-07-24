"""
differential_cdac.py — 差分 CDAC 物理模型

需求文档 §4: 差分网络包含 P/N 顶板节点和 bridge 节点。
"""

from dataclasses import dataclass

from python_cal.topology.cdac_topology import (
    CDACTopology,
    build_differential_topology,
    CU, VREF, VCM,
)
from python_cal.physical.charge_state import SampledChargeState
from python_cal.physical.charge_solver import DifferentialChargeSolver, CDACNodeSolution
from python_cal.topology.switch_state import DifferentialSwitchState


@dataclass
class DifferentialCDAC:
    """全差分 CDAC 物理模型

    组合:
      - P/N 两侧拓扑
      - 电荷守恒求解器
      - 当前采样电荷状态 (None 表示未采样)
    """
    p_topology: CDACTopology
    n_topology: CDACTopology
    charge_solver: DifferentialChargeSolver

    # 运行时状态
    sampled_charge: SampledChargeState | None = None
    current_switch_state: DifferentialSwitchState = DifferentialSwitchState.all_vcm()

    @classmethod
    def from_mismatch(cls, md=None, mu=None, p_caps=None, n_caps=None):
        """从失配参数构建"""
        p_top, n_top = build_differential_topology(
            md=md, mu=mu, p_caps=p_caps, n_caps=n_caps
        )
        solver = DifferentialChargeSolver(p_top, n_top)
        return cls(p_topology=p_top, n_topology=n_top, charge_solver=solver)

    @classmethod
    def ideal(cls):
        """构建理想 CDAC (无失配)"""
        return cls.from_mismatch()

    def sample(self, vinp: float, vinn: float,
               sampling_state: DifferentialSwitchState,
               vcm: float = VCM) -> SampledChargeState:
        """执行采样并保存电荷状态

        需求文档 §6: 输入只能通过采样阶段产生的初始电荷影响转换。
        """
        charge = self.charge_solver.compute_sampled_charge(
            sampling_state, vinp, vinn, vcm
        )
        self.sampled_charge = charge
        self.current_switch_state = DifferentialSwitchState.all_vcm()
        return charge

    def reset(self):
        """复位: 清除采样电荷并设置底板为 VCM"""
        self.sampled_charge = None
        self.current_switch_state = DifferentialSwitchState.all_vcm()

    def solve_current(self, vcm: float = VCM, vrefp: float = VREF, vrefn: float = 0.0
                      ) -> CDACNodeSolution:
        """求解当前开关状态下的节点电压

        Raises:
            RuntimeError: 未采样时调用
        """
        if self.sampled_charge is None:
            raise RuntimeError("CDAC not sampled: call sample() first")
        return self.charge_solver.solve(
            self.sampled_charge, self.current_switch_state,
            vcm=vcm, vrefp=vrefp, vrefn=vrefn,
        )

    def apply_switch_state(self, state: DifferentialSwitchState):
        """应用新的开关状态"""
        self.current_switch_state = state

    def get_physical_weights_q0(self) -> list[float]:
        """返回 P/N 物理权重的逐阶段均值 (Q0)。

        兼容旧分析接口。需要真实分侧 oracle 时使用
        :meth:`get_physical_weights_per_side_q0`，不能把本方法的均值同时
        填入 P/N 解码器。
        """
        weights_p, weights_n = self.get_physical_weights_per_side_q0()
        return [
            round(float((wp + wn) / 2.0), 6)
            for wp, wn in zip(weights_p, weights_n)
        ]

    def get_physical_weights_per_side_q0(self) -> tuple[list[float], list[float]]:
        """通过电荷求解器独立测量 P/N 两侧物理权重 (Q0)。

        每侧从 VCM 向 VREFP 切换，测得正常转换实际使用的半参考步进。
        P/N 共用一个比例因子，使两侧 signal-weight 的均值为 4095；
        因而不会抹掉真实的 P/N 总电容/增益不对称。

        stage 13 是数字 terminal 判决，不是电容，权重固定为 1 Q0。

        这是测试 oracle — 校准控制器不得调用此方法。
        """
        from python_cal.topology.switch_state import Rail, DifferentialSwitchState
        from python_cal.topology.switching_policy import DifferentialSwitchingPolicy

        policy = DifferentialSwitchingPolicy()
        saved_charge = self.sampled_charge
        saved_sw = self.current_switch_state

        # 零输入采样
        sampling_sw = policy.sampling_state(VCM, VCM)
        self.sample(VCM, VCM, sampling_sw, VCM)

        # 13 个物理阶段；stage 13 是 comparator-only terminal。
        all_physical = list(range(13))
        delta_p = {}
        delta_n = {}

        for stage in all_physical:
            cap_name = policy.STAGE_TO_CAP[stage]

            # Baseline: all VCM.
            self.apply_switch_state(DifferentialSwitchState.all_vcm())
            sol_base = self.solve_current()

            p_active = DifferentialSwitchState(
                p_side=DifferentialSwitchState.all_vcm().p_side.with_rail(
                    cap_name, Rail.VREFP
                ),
                n_side=DifferentialSwitchState.all_vcm().n_side,
            )
            self.apply_switch_state(p_active)
            sol_p = self.solve_current()
            delta_p[stage] = sol_p.differential_input - sol_base.differential_input

            n_active = DifferentialSwitchState(
                p_side=DifferentialSwitchState.all_vcm().p_side,
                n_side=DifferentialSwitchState.all_vcm().n_side.with_rail(
                    cap_name, Rail.VREFP
                ),
            )
            self.apply_switch_state(n_active)
            sol_n = self.solve_current()
            delta_n[stage] = sol_base.differential_input - sol_n.differential_input

        # 信号阶段 (0..4, 6): P/N 总量的均值归一到 4095 Q0。
        signal_stages = [0, 1, 2, 3, 4, 6]
        total_p = sum(delta_p[s] for s in signal_stages)
        total_n = sum(delta_n[s] for s in signal_stages)
        common_scale = 4095.0 / ((total_p + total_n) / 2.0)

        weights_p = [0.0] * 14
        weights_n = [0.0] * 14
        for stage in all_physical:
            weights_p[stage] = delta_p[stage] * common_scale
            weights_n[stage] = delta_n[stage] * common_scale
        weights_p[13] = 1.0
        weights_n[13] = 1.0

        weights_p = [round(float(w), 6) for w in weights_p]
        weights_n = [round(float(w), 6) for w in weights_n]

        # Restore
        self.sampled_charge = saved_charge
        self.current_switch_state = saved_sw

        return weights_p, weights_n
