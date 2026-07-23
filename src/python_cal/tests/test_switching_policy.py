"""
test_switching_policy.py — 开关策略测试

需求文档 §15: 单电容开关 + trial/commit 正确性。
"""

import pytest

from python_cal.topology.switch_state import Rail, SideSwitchState, DifferentialSwitchState
from python_cal.topology.switching_policy import DifferentialSwitchingPolicy


@pytest.fixture
def policy():
    return DifferentialSwitchingPolicy()


def test_sampling_state_all_caps_to_input():
    """采样阶段: 所有电容底板接 VINP 或 VINN"""
    p = DifferentialSwitchingPolicy()
    state = p.sampling_state(1.0, 0.8)

    for name in SideSwitchState.CAP_NAMES:
        assert state.p_side.get_rail(name) == Rail.VINP, \
            f"P-side {name} should be VINP"
        assert state.n_side.get_rail(name) == Rail.VINN, \
            f"N-side {name} should be VINN"


def test_reset_state_all_vcm(policy):
    """复位: 全部 VCM"""
    state = policy.reset_state()
    for name in SideSwitchState.CAP_NAMES:
        assert state.p_side.get_rail(name) == Rail.VCM
        assert state.n_side.get_rail(name) == Rail.VCM


def test_trial_state_puts_both_to_vrefp(policy):
    """trial: P 和 N 当前电容都接 VREFP"""
    committed = DifferentialSwitchState.all_vcm()

    trial_0 = policy.trial_state(0, committed)
    assert trial_0.p_side.high_32c == Rail.VREFP
    assert trial_0.n_side.high_32c == Rail.VREFP
    # 其他不变
    assert trial_0.p_side.high_16c == Rail.VCM

    trial_7 = policy.trial_state(7, committed)
    assert trial_7.p_side.low_32c == Rail.VREFP
    assert trial_7.n_side.low_32c == Rail.VREFP


def test_commit_cmp1_keeps_n_side(policy):
    """比较器 output=1 (P>N): N 侧保留 VREFP, P 侧回 VCM"""
    committed = DifferentialSwitchState.all_vcm()
    trial = policy.trial_state(0, committed)

    result = policy.commit_state(0, committed, trial, comparator_output=1)

    assert result.n_side.high_32c == Rail.VREFP  # N 保留
    assert result.p_side.high_32c == Rail.VCM     # P 回 VCM


def test_commit_cmp0_keeps_p_side(policy):
    """比较器 output=0 (P<N): P 侧保留 VREFP, N 侧回 VCM"""
    committed = DifferentialSwitchState.all_vcm()
    trial = policy.trial_state(0, committed)

    result = policy.commit_state(0, committed, trial, comparator_output=0)

    assert result.p_side.high_32c == Rail.VREFP  # P 保留
    assert result.n_side.high_32c == Rail.VCM     # N 回 VCM


def test_terminal_stage_no_switch_change(policy):
    """stage 13 (terminal): 开关状态不变"""
    committed = DifferentialSwitchState.all_vcm()
    trial = policy.trial_state(13, committed)
    assert trial == committed

    result = policy.commit_state(13, committed, trial, 1)
    assert result == committed


def test_derive_decisions(policy):
    """从最终开关状态派生 decisions"""
    # 构造已知状态: stage 0 BITN=1 (N侧 VREFP), stage 1 BITP=1 (P侧 VREFP)
    state = DifferentialSwitchState(
        p_side=SideSwitchState(high_16c=Rail.VREFP),
        n_side=SideSwitchState(high_32c=Rail.VREFP),
    )
    decisions = policy.derive_decisions(state)
    assert decisions[0] == 1  # N侧 VREFP → BITN=1
    assert decisions[1] == 0  # P侧 VREFP → BITP=1
    assert decisions[2] == 0  # 未切换 → 默认 0
