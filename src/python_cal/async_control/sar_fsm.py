"""
sar_fsm.py — 异步 SAR 状态机

需求文档 §11: 实现异步状态机。
转换必须由事件驱动, 下一 bit 的开始时间由上一 bit 的完成事件决定。
"""

from dataclasses import dataclass
from enum import Enum



class SARState(Enum):
    """异步 SAR 状态"""
    IDLE             = "idle"
    SAMPLING         = "sampling"
    HOLD             = "hold"
    APPLY_TRIAL      = "apply_trial"
    WAIT_DAC         = "wait_dac"
    REQUEST_COMPARE  = "request_compare"
    WAIT_COMPARE     = "wait_compare"
    COMMIT_BIT       = "commit_bit"
    NEXT_BIT         = "next_bit"
    DONE             = "done"
    RESET            = "reset"
