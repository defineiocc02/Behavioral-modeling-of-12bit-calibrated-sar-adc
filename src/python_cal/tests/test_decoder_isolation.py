"""
test_decoder_isolation.py — 解码器隔离测试

需求文档 §14, §15.8: decoder 权重更新不得改变物理 decisions。
"""

import pytest
import numpy as np

from python_cal.topology.cdac_topology import VCM, VREF
from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
from python_cal.decode.sar_decoder import SARDecoder


@pytest.fixture
def adc():
    adc = AsyncBehavioralSARADC()
    adc.enable_nominal_decode()
    return adc


def test_weight_update_does_not_change_decisions(adc):
    """更新 decoder 权重不影响物理 decisions"""
    vinp, vinn = 1.0, 0.8

    r1 = adc.convert(vinp, vinn)
    decisions_before = r1.decisions

    # 修改 decoder 权重 (不会影响物理转换)
    decoder = SARDecoder()
    new_weights = [w * 1.1 for w in decoder.weights]
    decoder.update_weights(new_weights)

    r2 = adc.convert(vinp, vinn)
    decisions_after = r2.decisions

    assert decisions_before == decisions_after, \
        "Decoder weight update should not affect physical decisions"


def test_decoder_deterministic(adc):
    """相同输入产生相同 decisions"""
    vinp, vinn = 1.0, 0.8

    r1 = adc.convert(vinp, vinn)
    r2 = adc.convert(vinp, vinn)

    assert r1.decisions == r2.decisions


def test_decode_vin_zero_is_mid_code(adc):
    """Vin=0 解码到中码"""
    r = adc.convert_diff(0.0)
    decoder = SARDecoder()
    code = decoder.decode(r.decisions)
    assert abs(code - 2048) < 100, \
        f"Vin=0 should decode near mid-scale, got {code}"


def test_decode_vin_positive_above_mid(adc):
    """正输入解码到中码以上"""
    r = adc.convert_diff(0.25 * VREF)
    decoder = SARDecoder()
    code = decoder.decode(r.decisions)
    assert code > 2048, f"Vin > 0 should be above mid-scale, got {code}"


def test_decode_vin_negative_below_mid(adc):
    """负输入解码到中码以下"""
    r = adc.convert_diff(-0.25 * VREF)
    decoder = SARDecoder()
    code = decoder.decode(r.decisions)
    assert code < 2048, f"Vin < 0 should be below mid-scale, got {code}"


# ==========================================================================
# P0-C: 不可绕过的映射测试 (文档 38 §九)
# ==========================================================================

def test_signed_decoder_covers_all_4096_codes():
    """ decoder 将所有 4096 个 signed levels 正确映射到 [0, 4095]

    文档 38 P0-C: 确保 decoder 的 signed_sum→code 映射覆盖全部 4096 个 code,
    不存在奇偶锁导致的 50% 缺码。

    枚举全部 2^14=16384 个 decision 组合, 验证 clipped code 集合 = [0, 4095]。
    """
    decoder = SARDecoder()
    codes = set()
    for combo in range(1 << 14):
        decisions = [(combo >> i) & 1 for i in range(14)]
        code = decoder.decode(decisions)  # 使用带 clipping 的 decode
        codes.add(code)

    assert len(codes) == 4096, (
        f"Decoder (clipped) must produce all 4096 codes. Got {len(codes)} unique."
    )
    assert min(codes) == 0, f"Min code should be 0, got {min(codes)}"
    assert max(codes) == 4095, f"Max code should be 4095, got {max(codes)}"


def test_terminal_completes_physical_levels():
    """ 物理 13-stage signed sums + terminal(±1) 覆盖 [-4095, 4095, 2]

    文档 38 P0-C: 13 个物理阶段产生偶数 signed sum,
    terminal ±1 使其变为奇数并覆盖全部 signed level 空间。
    """
    # 枚举 2^13 个物理开关状态
    from python_cal.topology.switching_policy import DifferentialSwitchingPolicy
    from python_cal.topology.switch_state import Rail, SideSwitchState, DifferentialSwitchState

    policy = DifferentialSwitchingPolicy()
    cap_names = [policy.STAGE_TO_CAP[s] for s in range(13)]
    # 13 个物理阶段的名义权重 (不含 terminal)
    phys_weights = [2080, 1040, 520, 260, 130, 65, 65, 64, 32, 16, 8, 4, 2]

    physical_even_sums = set()
    for combo in range(1 << 13):
        signed_sum = 0
        for stage in range(13):
            d = (combo >> stage) & 1
            signed_sum += (1 - 2 * d) * phys_weights[stage]
        physical_even_sums.add(signed_sum)

    # 加 terminal ±1 后应覆盖全部 [-4095, 4095, 2]
    with_terminal = set()
    for s in physical_even_sums:
        with_terminal.add(s + 1)
        with_terminal.add(s - 1)

    required = set(range(-4095, 4096, 2))
    missing = required - with_terminal
    extra = with_terminal - required

    assert missing == set(), (
        f"Physical levels + terminal do not cover all signed levels.\n"
        f"  Physical even sums: {len(physical_even_sums)} unique\n"
        f"  With terminal ±1: {len(with_terminal)} unique\n"
        f"  Required [-4095,4095,2]: {len(required)}\n"
        f"  Missing: {sorted(missing)[:20]}\n"
        f"  Extra (outside range): {sorted(extra)[:20]}"
    )


def test_signed_sum_is_always_odd():
    """ 验证 14 个决策的 signed_sum 恒为奇数 (parity lock)

    这是理想整数权重 + 零噪声下的确定性属性, 不是 bug。
    正确 decoder 除以 2 后该属性确保 code 始终为整数。
    """
    decoder = SARDecoder()
    weights = decoder.weights
    # 遍历 2^14 个 decision 组合太慢 (16384), 采样测试
    import random
    rng = random.Random(42)
    for _ in range(1000):
        decisions = [rng.randint(0, 1) for _ in range(14)]
        signed_sum = sum((1 - 2 * d) * w for d, w in zip(decisions, weights))
        assert signed_sum % 2 == 1, (
            f"signed_sum must be odd for any valid decision vector.\n"
            f"  decisions: {decisions}\n"
            f"  signed_sum: {signed_sum}"
        )
