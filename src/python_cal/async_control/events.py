"""
events.py — 异步事件定义

需求文档 §10: 转换必须由事件驱动。
"""

from dataclasses import dataclass
from enum import Enum


class AsyncEventType(Enum):
    """异步事件类型"""
    SAMPLE_START     = "sample_start"
    SAMPLE_DONE      = "sample_done"
    DAC_TRIAL_START  = "dac_trial_start"
    DAC_SETTLED      = "dac_settled"
    CMP_REQUEST      = "cmp_request"
    CMP_DONE         = "cmp_done"
    BIT_COMMIT       = "bit_commit"
    CONVERSION_DONE  = "conversion_done"
    RESET_DONE       = "reset_done"


@dataclass(frozen=True)
class AsyncEvent:
    """一次异步事件

    属性:
        time_s: 事件发生时间 (s)
        event_type: 事件类型
        stage: 对应的 SAR 阶段 (None 表示不属于特定阶段)
    """
    time_s: float
    event_type: AsyncEventType
    stage: int | None = None
