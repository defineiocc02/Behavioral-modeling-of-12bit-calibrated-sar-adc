"""
test_comparator.py — 比较器测试

需求文档 §15.6-7: 决策时间依赖输入 + metastability。
"""

import pytest
import numpy as np

from python_cal.comparator.dynamic_comparator import DynamicComparator


@pytest.fixture
def cmp_ideal():
    return DynamicComparator(noise_sigma_v=0.0, offset_v=0.0)


@pytest.fixture
def cmp_noisy():
    rng = np.random.default_rng(42)
    return DynamicComparator(noise_sigma_v=0.001, offset_v=0.0, rng_seed=42)


def test_polarity_positive(cmp_ideal):
    """VTOP_P > VTOP_N → output=1"""
    r = cmp_ideal.request(1.0, 0.9)
    assert r.output == 1


def test_polarity_negative(cmp_ideal):
    """VTOP_P < VTOP_N → output=0"""
    r = cmp_ideal.request(0.9, 1.0)
    assert r.output == 0


def test_decision_time_smaller_diff_slower(cmp_ideal):
    """差分越小, 决策时间越长"""
    r_large = cmp_ideal.request(1.0, 0.5)   # diff=0.5V
    r_small = cmp_ideal.request(0.901, 0.9) # diff=0.001V
    assert r_small.decision_time_s > r_large.decision_time_s


def test_metastability_flag(cmp_ideal):
    """极小差分触发 metastable"""
    v_min_cmp = DynamicComparator(v_min=1e-3)
    r = v_min_cmp.request(0.9, 0.9)  # diff=0
    assert r.metastable


def test_max_wait_timeout(cmp_ideal):
    """超时强制输出"""
    cmp_timeout = DynamicComparator(max_wait_s=1e-9, v_min=1e-3)
    r = cmp_timeout.request(0.9, 0.9)  # diff=0, metastable
    assert r.decision_time_s <= 1e-9


def test_offset(cmp_ideal):
    """失调电压正确偏移"""
    cmp_offset = DynamicComparator(offset_v=0.01)
    # VTOP_P - VTOP_N = -0.005, 加 offset=0.01 → 有效=0.005 > 0
    r = cmp_offset.request(0.895, 0.9)
    assert r.output == 1


def test_noise_affects_output(cmp_noisy):
    """噪声在一定概率下翻转输出"""
    n_on = 0
    n_off = 0
    for _ in range(100):
        # 非常接近 0 的差分, 噪声主导
        r = cmp_noisy.request(0.9, 0.9 + 0.0001)
        if r.output == 1:
            n_on += 1
        else:
            n_off += 1
    # 两个方向都应出现
    assert n_on > 0 and n_off > 0, \
        f"Noise should cause both outputs: on={n_on}, off={n_off}"
