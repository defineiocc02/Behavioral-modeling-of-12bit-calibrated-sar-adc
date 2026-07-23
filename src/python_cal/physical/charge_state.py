"""
charge_state.py — 采样电荷状态

需求文档 §6: 必须真实模拟采样阶段。
采样阶段建立顶板和 bridge 节点的初始电荷。
"""

from dataclasses import dataclass
from python_cal.topology.switch_state import DifferentialSwitchState, Rail


@dataclass(frozen=True)
class SampledChargeState:
    """采样后 CDAC 各节点的保存电荷 (C)

    采样完成后, 这四个浮动节点的总电荷被保存,
    后续所有转换阶段的电荷守恒以此为基础。
    """
    p_top_charge_c:    float
    p_bridge_charge_c: float
    n_top_charge_c:    float
    n_bridge_charge_c: float
    sampled_switch_state: DifferentialSwitchState
    vinp: float
    vinn: float
