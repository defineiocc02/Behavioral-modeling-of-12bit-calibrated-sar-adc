"""
test_async_conversion.py — 异步转换端到端测试

需求文档 §15: 完整转换行为验证。
"""

import pytest
import numpy as np

from python_cal.topology.cdac_topology import VCM, VREF
from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
from python_cal.comparator.dynamic_comparator import DynamicComparator


@pytest.fixture
def adc_ideal():
    adc = AsyncBehavioralSARADC()
    adc.enable_nominal_decode()
    return adc


def test_vin_zero_converges(adc_ideal):
    """Vin=0 时 Vdiff 收敛到零"""
    result = adc_ideal.convert_diff(0.0)
    final_step = result.steps[-1]
    assert abs(final_step.differential_v) < 0.01, \
        f"Vdiff={final_step.differential_v} should be near zero"


def test_vin_positive_vs_negative_symmetry(adc_ideal):
    """+Vin 和 -Vin 的 decisions 互补"""
    for vd in [0.1, 0.25, 0.5]:
        r_pos = adc_ideal.convert_diff(vd * VREF)
        r_neg = adc_ideal.convert_diff(-vd * VREF)
        for s in range(14):
            assert r_pos.decisions[s] == 1 - r_neg.decisions[s], \
                f"vd=±{vd}*VREF, stage={s}: pos={r_pos.decisions[s]}, neg={r_neg.decisions[s]}"


def test_initial_vdiff_matches_full_array_sampling(adc_ideal):
    """All high/low bottom plates sample VIN, so differential gain is unity."""
    for vd in [0.0, 0.1, -0.1, 0.25, -0.25]:
        vd_v = vd * VREF
        result = adc_ideal.convert_diff(vd_v)
        expected = -vd_v
        assert result.initial_vdiff == pytest.approx(expected, abs=1e-9), \
            f"vd={vd_v}: initial_vdiff={result.initial_vdiff}, expected={expected}"


def test_conversion_time_nonzero(adc_ideal):
    """转换时间 > 0"""
    result = adc_ideal.convert_diff(0.1 * VREF)
    assert result.total_time_s > 0


def test_batch_conversion(adc_ideal):
    """批量转换返回正确数量"""
    vins = np.array([0.0, 0.1 * VREF, -0.1 * VREF])
    results = adc_ideal.convert_batch(vins)
    assert len(results) == 3
    for r in results:
        assert len(r.decisions) == 15


def test_noise_does_not_crash(adc_ideal):
    """带噪声比较器不崩溃"""
    rng = np.random.default_rng(42)
    adc_ideal.comparator = DynamicComparator(noise_sigma_v=0.001)
    result = adc_ideal.convert_diff(0.1 * VREF, rng=rng)
    assert len(result.decisions) == 15


def test_terminal_is_comparator_only_decision(adc_ideal):
    result = adc_ideal.convert_diff(0.137 * VREF)
    terminal = result.steps[14]
    assert terminal.trial_state == terminal.committed_before
    assert terminal.committed_after == terminal.committed_before
    assert result.decisions[14] == terminal.comparator_output
