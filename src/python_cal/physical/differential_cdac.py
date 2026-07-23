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
        """通过电荷求解器测量每个物理阶段的差分权重 (Q0)

        方法: 测量每个电容的 complementary ΔVdiff (P→VREFP, N→VREFN),
        按信号阶段总 ΔVdiff 归一化使 signal_weight = 4095 Q0,
        确保理想 CDAC 下 physical == nominal。

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

        # 所有物理阶段 (0..12)，每个测量 complementary ΔVdiff
        all_physical = list(range(13))  # 0..12
        complementary_delta = {}

        for stage in all_physical:
            cap_name = policy.STAGE_TO_CAP[stage]

            # Baseline: all VCM
            self.apply_switch_state(DifferentialSwitchState.all_vcm())
            sol_base = self.solve_current()

            # Complementary: P→VREFP, N→VREFN
            p_comp = DifferentialSwitchState.all_vcm().p_side.with_rail(cap_name, Rail.VREFP)
            n_comp = DifferentialSwitchState.all_vcm().n_side.with_rail(cap_name, Rail.VREFN)
            comp_sw = DifferentialSwitchState(p_side=p_comp, n_side=n_comp)
            self.apply_switch_state(comp_sw)
            sol_comp = self.solve_current()

            complementary_delta[stage] = sol_comp.differential_input - sol_base.differential_input

        # 信号阶段 (0..4, 6): sum=4095 for ideal CDAC
        signal_stages = [0, 1, 2, 3, 4, 6]
        total_signal_delta = sum(complementary_delta[s] for s in signal_stages)

        # 所有权重按比例归一化: signal_weight 恒为 4095
        weights = [0.0] * 14
        for stage in all_physical:
            weights[stage] = complementary_delta[stage] / total_signal_delta * 4095.0

        # Terminal 权重 = 1 Q0 (标称值, 无物理电容, 不会参与失配)
        weights[13] = 1.0

        weights = [round(float(w), 6) for w in weights]

        # Restore
        self.sampled_charge = saved_charge
        self.current_switch_state = saved_sw

        return weights
