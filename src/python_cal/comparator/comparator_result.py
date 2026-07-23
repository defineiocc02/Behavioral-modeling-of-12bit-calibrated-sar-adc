"""
comparator_result.py — 比较器结果

需求文档 §9: 比较器是异步事件源。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ComparatorResult:
    """一次比较操作的结果

    属性:
        output: 比较器输出 (0 或 1)
                1 ⇔ VTOP_P > VTOP_N (需求文档 §9, 固定极性)
        differential_v: 差分输入电压 (V)
        decision_time_s: 决策时间 (s)
        metastable: 是否处于亚稳态
    """
    output: int
    differential_v: float
    decision_time_s: float
    metastable: bool = False
