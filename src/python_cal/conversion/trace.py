"""
trace.py — 转换 trace 数据结构

需求文档 §13: 完整转换 trace。
每个转换必须产生事件级 trace。
"""

from dataclasses import dataclass

from python_cal.topology.switch_state import DifferentialSwitchState


@dataclass(frozen=True)
class AsyncSARStepTrace:
    """单个 SAR 阶段的完整 trace

    需求文档 §13: 事件级 trace。
    """
    stage: int
    stage_name: str

    trial_start_time_s:    float
    dac_settled_time_s:    float
    comparator_done_time_s: float
    commit_time_s:         float

    committed_before: DifferentialSwitchState
    trial_state:      DifferentialSwitchState
    committed_after:  DifferentialSwitchState

    # commit-state voltages (residual after bit decision)
    vtop_p:    float
    vtop_n:    float
    vbridge_p: float
    vbridge_n: float
    differential_v: float

    comparator_output:    int
    comparator_metastable: bool
    decision: int

    # fields with defaults must come last
    cmp_request_time_s:    float = 0.0
    vtop_p_trial:    float = 0.0
    vtop_n_trial:    float = 0.0
    vdiff_trial:     float = 0.0
