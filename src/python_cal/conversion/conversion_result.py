"""
conversion_result.py — 转换结果

需求文档 §13: 完整结果数据结构。
"""

from dataclasses import dataclass

from python_cal.physical.charge_state import SampledChargeState
from python_cal.topology.switch_state import DifferentialSwitchState
from python_cal.async_control.events import AsyncEvent
from .trace import AsyncSARStepTrace


@dataclass(frozen=True)
class AsyncSARConversionResult:
    """一次完整异步 SAR 转换的结果

    需求文档 §13: 包含所有转换信息。
    """
    sampled_charge: SampledChargeState
    final_switch_state: DifferentialSwitchState
    decisions: tuple[int, ...]
    steps: tuple[AsyncSARStepTrace, ...]
    events: tuple[AsyncEvent, ...]
    start_time_s: float
    done_time_s: float
    initial_vtop_p: float = 0.0
    initial_vtop_n: float = 0.0

    @property
    def total_time_s(self) -> float:
        return self.done_time_s - self.start_time_s

    @property
    def initial_vdiff(self) -> float:
        """复位后、首次 trial 前的差分电压"""
        return self.initial_vtop_p - self.initial_vtop_n

    @property
    def final_vdiff(self) -> float:
        """最终残差"""
        return self.steps[-1].differential_v if self.steps else 0.0

    @property
    def decision_bits(self) -> str:
        """decisions 的位字符串表示"""
        return ''.join(str(d) for d in self.decisions)
