"""
charge_solver.py — 节点电荷守恒求解器

需求文档 §7: 使用节点电荷守恒求解。
求解 VTOP_P, VBRIDGE_P, VTOP_N, VBRIDGE_N 四个浮动节点电压。

每次底板开关改变后, 都必须重新求解浮动节点电压。

对于桥接 CDAC (每侧):
  VTOP 节点: 高段电容 + 桥接电容
  VBRIDGE 节点: 桥接电容 + 低段电容

两侧独立 (无耦合电容), 可分别求解。
"""

from dataclasses import dataclass
import numpy as np

from python_cal.topology.cdac_topology import CDACTopology
from python_cal.topology.switch_state import SideSwitchState, Rail
from .charge_state import SampledChargeState


@dataclass(frozen=True)
class CDACNodeSolution:
    """一次求解后的四个浮动节点电压"""
    vtop_p:    float
    vbridge_p: float
    vtop_n:    float
    vbridge_n: float

    @property
    def differential_input(self) -> float:
        """比较器看到的差分电压 Vdiff = VTOP_P - VTOP_N"""
        return self.vtop_p - self.vtop_n


class SideChargeSolver:
    """单侧 CDAC 电荷守恒求解器

    求解两个浮动节点: VTOP, VBRIDGE。

    电荷守恒方程:
      Q_top    = Σ C_high_i * (VTOP - Vbot_high_i) + C_bridge * (VTOP - VBRIDGE)
      Q_bridge = C_bridge * (VBRIDGE - VTOP) + Σ C_low_j * (VBRIDGE - Vbot_low_j)

    写成矩阵:
      [C_high_total+C_bridge,      -C_bridge         ] [VTOP]    = [Q_top + Σ C_high_i*Vbot_hi ]
      [-C_bridge,                   C_low_total+C_bridge] [VBRIDGE]   [Q_bridge + Σ C_low_j*Vbot_lo]
    """

    def __init__(self, topology: CDACTopology):
        self.top = topology

        # 预计算系数矩阵 (常数, 不随开关变化)
        ct = topology.c_high_total
        cb = topology.c_bridge
        cl = topology.c_low_total

        a11 = ct + cb
        a12 = -cb
        a21 = -cb
        a22 = cl + cb

        self.A = np.array([[a11, a12], [a21, a22]], dtype=np.float64)
        self.det = a11 * a22 - a12 * a21  # > 0

        # 预计算 A 的逆
        self.A_inv = np.array([[a22, -a12], [-a21, a11]], dtype=np.float64) / self.det

    def solve(self, q_top: float, q_bridge: float,
              switch_state: SideSwitchState,
              vin_at_sample: float, vcm: float, vrefp: float, vrefn: float
              ) -> tuple[float, float]:
        """求解 VTOP, VBRIDGE

        参数:
            q_top: 顶板节点保存电荷 (C)
            q_bridge: bridge 节点保存电荷 (C)
            switch_state: 当前开关状态
            vin_at_sample: 采样时的顶板电压 (for Rail.VINP/VINN)
            vcm, vrefp, vrefn: 电压值

        返回:
            (vtop, vbridge) 单位 V
        """
        # 构建 RHS
        # b_top = q_top + Σ C_high_i * Vbot_high_i
        # b_bridge = q_bridge + Σ C_low_j * Vbot_low_j

        b_top = q_top
        b_bridge = q_bridge

        for cap in self.top.high_capacitors:
            rail = switch_state.get_rail(cap.name)
            vbot = _rail_to_voltage(rail, vin_at_sample, vin_at_sample,
                                    vcm, vrefp, vrefn)
            b_top += cap.capacitance_f * vbot

        for cap in self.top.low_capacitors:
            rail = switch_state.get_rail(cap.name)
            vbot = _rail_to_voltage(rail, vin_at_sample, vin_at_sample,
                                    vcm, vrefp, vrefn)
            b_bridge += cap.capacitance_f * vbot

        b = np.array([b_top, b_bridge], dtype=np.float64)
        x = self.A_inv @ b
        return float(x[0]), float(x[1])


class DifferentialChargeSolver:
    """全差分电荷守恒求解器

    需求文档 §7: 求解 VTOP_P, VBRIDGE_P, VTOP_N, VBRIDGE_N。
    """

    def __init__(self, p_topology: CDACTopology, n_topology: CDACTopology):
        self.p_solver = SideChargeSolver(p_topology)
        self.n_solver = SideChargeSolver(n_topology)
        self.p_top = p_topology
        self.n_top = n_topology

    def solve(self, sampled_charge: SampledChargeState,
              switch_state,
              vcm: float = 0.9, vrefp: float = 1.8, vrefn: float = 0.0
              ) -> CDACNodeSolution:
        """根据采样电荷和当前开关状态求解四个节点电压

        参数:
            sampled_charge: 采样阶段保存的电荷
            switch_state: 当前全差分开关状态 (DifferentialSwitchState)
            vcm, vrefp, vrefn: 电压基准

        返回:
            CDACNodeSolution
        """
        vtop_p, vbridge_p = self.p_solver.solve(
            sampled_charge.p_top_charge_c,
            sampled_charge.p_bridge_charge_c,
            switch_state.p_side,
            vin_at_sample=sampled_charge.vinp,
            vcm=vcm, vrefp=vrefp, vrefn=vrefn,
        )

        vtop_n, vbridge_n = self.n_solver.solve(
            sampled_charge.n_top_charge_c,
            sampled_charge.n_bridge_charge_c,
            switch_state.n_side,
            vin_at_sample=sampled_charge.vinn,
            vcm=vcm, vrefp=vrefp, vrefn=vrefn,
        )

        return CDACNodeSolution(
            vtop_p=vtop_p, vbridge_p=vbridge_p,
            vtop_n=vtop_n, vbridge_n=vbridge_n,
        )

    def compute_sampled_charge(self, switch_state,
                                vinp: float, vinn: float,
                                vcm: float = 0.9
                                ) -> SampledChargeState:
        """从采样开关状态计算保存的电荷

        采样时 (bottom-plate sampling):
          - VTOP_P 和 VTOP_N 被强制到 VCM (通过采样开关)
          - 底板按 switch_state 连接输入信号
          - BRIDGE 节点电压由 DC 求解确定
        """
        # Bridge 节点 DC 电压 (采样时 VTOP=VCM)
        vbridge_p_sampled = _compute_bridge_dc(
            self.p_top, switch_state.p_side, vcm, vcm,
            vinp=vinp, vinn=vinn,
        )
        vbridge_n_sampled = _compute_bridge_dc(
            self.n_top, switch_state.n_side, vcm, vcm,
            vinp=vinp, vinn=vinn,
        )

        # 顶板电荷 (采样时 VTOP=VCM, 底板接输入)
        q_top_p = _compute_top_charge(self.p_top, switch_state.p_side,
                                       vcm, vbridge_p_sampled,
                                       vinp=vinp, vinn=vinn)
        q_top_n = _compute_top_charge(self.n_top, switch_state.n_side,
                                       vcm, vbridge_n_sampled,
                                       vinp=vinp, vinn=vinn)

        # Bridge 节点电荷
        q_bridge_p = _compute_bridge_charge(self.p_top, switch_state.p_side,
                                             vbridge_p_sampled, vcm,
                                             vinp=vinp, vinn=vinn)
        q_bridge_n = _compute_bridge_charge(self.n_top, switch_state.n_side,
                                             vbridge_n_sampled, vcm,
                                             vinp=vinp, vinn=vinn)

        return SampledChargeState(
            p_top_charge_c=q_top_p,
            p_bridge_charge_c=q_bridge_p,
            n_top_charge_c=q_top_n,
            n_bridge_charge_c=q_bridge_n,
            sampled_switch_state=switch_state,
            vinp=vinp,
            vinn=vinn,
        )


def _rail_to_voltage(rail: Rail, vinp, vinn, vcm, vrefp, vrefn):
    """Rail → 电压值 (vinp/vinn 为 P/N 侧实际输入电压)"""
    return rail.voltage(vrefp=vrefp, vrefn=vrefn, vcm=vcm,
                        vinp=vinp, vinn=vinn)


def _compute_bridge_dc(topology: CDACTopology, switch_state: SideSwitchState,
                       vtop, vcm, vinp=0.9, vinn=0.9):
    """计算 Bridge 节点 DC 电压 (采样时)

    Bridge 节点通过低段电容和桥接电容形成的电阻分压网络确定 DC 电压。
    由于节点没有 DC 路径, 采样时 VBRIDGE 由低段电容底板电压和 VTOP 共同确定。

    VBRIDGE * (C_bridge + C_low_total) = C_bridge * VTOP + Σ C_low_j * Vbot_low_j
    """
    num = topology.c_bridge * vtop
    for cap in topology.low_capacitors:
        rail = switch_state.get_rail(cap.name)
        vbot = _rail_to_voltage(rail, vinp, vinn, vcm, 1.8, 0.0)
        num += cap.capacitance_f * vbot
    den = topology.c_bridge + topology.c_low_total
    return num / den if den > 0 else vtop


def _compute_top_charge(topology: CDACTopology, switch_state: SideSwitchState,
                        vtop, vbridge, vinp=0.9, vinn=0.9):
    """计算顶板节点电荷 Q_top"""
    q = 0.0
    for cap in topology.high_capacitors:
        rail = switch_state.get_rail(cap.name)
        vbot = _rail_to_voltage(rail, vinp, vinn, 0.9, 1.8, 0.0)
        q += cap.capacitance_f * (vtop - vbot)
    q += topology.c_bridge * (vtop - vbridge)
    return q


def _compute_bridge_charge(topology: CDACTopology, switch_state: SideSwitchState,
                           vbridge, vtop, vinp=0.9, vinn=0.9):
    """计算 Bridge 节点电荷 Q_bridge"""
    q = topology.c_bridge * (vbridge - vtop)
    for cap in topology.low_capacitors:
        rail = switch_state.get_rail(cap.name)
        vbot = _rail_to_voltage(rail, vinp, vinn, 0.9, 1.8, 0.0)
        q += cap.capacitance_f * (vbridge - vbot)
    return q
