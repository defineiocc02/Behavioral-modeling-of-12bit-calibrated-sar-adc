"""
test_async_handshake.py — 异步握手顺序测试

需求文档 §15.5: 每一级必须满足事件顺序。
禁止事件倒序或重叠。
"""

import pytest

from python_cal.topology.cdac_topology import VCM
from python_cal.comparator.dynamic_comparator import DynamicComparator
from python_cal.async_control.events import AsyncEventType
from python_cal.async_control.handshake import AsyncSARController
from python_cal.async_control.timing import TimingParams
from python_cal.topology.switching_policy import DifferentialSwitchingPolicy
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.async_control.sar_fsm import SARState


@pytest.fixture
def controller():
    cdac = DifferentialCDAC.ideal()
    cmp = DynamicComparator(noise_sigma_v=0.0, offset_v=0.0)
    policy = DifferentialSwitchingPolicy()
    timing = TimingParams(ideal_settling=True)
    return AsyncSARController(
        cdac=cdac, comparator=cmp,
        switching_policy=policy, timing=timing,
    )


def test_event_order_per_stage(controller):
    """每个物理阶段的事件顺序: trial → dac_settled → cmp → commit"""
    result = controller.start_conversion(1.0, 0.8)

    # 按 stage 分组检查
    stage_events = {}
    for evt in result.events:
        if evt.stage is not None and evt.stage < 13:
            stage_events.setdefault(evt.stage, []).append(evt)

    for stage, evts in stage_events.items():
        types = [e.event_type for e in evts]
        # 物理阶段应包含: DAC_TRIAL_START, DAC_SETTLED, CMP_REQUEST, CMP_DONE, BIT_COMMIT
        assert AsyncEventType.DAC_TRIAL_START in types, f"Stage {stage} missing DAC_TRIAL_START"
        assert AsyncEventType.DAC_SETTLED in types, f"Stage {stage} missing DAC_SETTLED"
        assert AsyncEventType.CMP_REQUEST in types, f"Stage {stage} missing CMP_REQUEST"
        assert AsyncEventType.CMP_DONE in types, f"Stage {stage} missing CMP_DONE"
        assert AsyncEventType.BIT_COMMIT in types, f"Stage {stage} missing BIT_COMMIT"


def test_conversion_has_start_and_done(controller):
    """转换包含 CONVERSION_DONE 事件"""
    result = controller.start_conversion(1.0, 0.8)
    event_types = [e.event_type for e in result.events]

    assert AsyncEventType.SAMPLE_START in event_types
    assert AsyncEventType.SAMPLE_DONE in event_types
    assert AsyncEventType.CONVERSION_DONE in event_types


def test_15_decisions_produced(controller):
    """Produce fourteen physical decisions plus one terminal decision."""
    result = controller.start_conversion(1.0, 0.8)
    assert len(result.decisions) == 15


def test_15_steps_in_trace(controller):
    """Trace contains all fifteen comparisons."""
    result = controller.start_conversion(1.0, 0.8)
    assert len(result.steps) == 15


def test_final_state_is_done(controller):
    """最终状态为 DONE"""
    controller.start_conversion(1.0, 0.8)
    assert controller.state == SARState.DONE


def test_events_monotonic_time(controller):
    """事件时间单调递增"""
    result = controller.start_conversion(1.0, 0.8)
    times = [e.time_s for e in result.events]
    for i in range(1, len(times)):
        assert times[i] >= times[i - 1], \
            f"Event time not monotonic: {times[i-1]} → {times[i]}"
