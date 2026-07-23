"""
capacitor.py — 物理电容定义

需求文档 §4: 物理电容必须显式建模。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Capacitor:
    """单个物理电容

    属性:
        name: 电容名称 (如 'H32C', 'L1C', 'CB')
        capacitance_f: 电容值 (F)
        top_node: 顶板连接节点 ('VTOP_P', 'VTOP_N', 'VBRIDGE_P', 'VBRIDGE_N')
        bottom_node: 底板连接节点 (由开关状态决定, 此处仅记录标识)
        stage: SAR 阶段索引 (0..12) 或 None (bridge)
        is_physical: 是否对应物理电容
    """
    name: str
    capacitance_f: float
    top_node: str
    bottom_node: str
    stage: int | None

    @property
    def is_physical(self) -> bool:
        return self.stage is not None
