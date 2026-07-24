"""Decoder isolation and ordinary weighted-sum reconstruction tests."""

import random

import pytest

from python_cal import config as cfg
from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
from python_cal.decode.sar_decoder import SARDecoder
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.topology.cdac_topology import VREF


@pytest.fixture
def adc():
    model = AsyncBehavioralSARADC()
    model.enable_nominal_decode()
    return model


def test_weight_update_does_not_change_physical_decisions(adc):
    before = adc.convert(1.0, 0.8).decisions
    decoder = SARDecoder()
    decoder.update_weights([weight * 1.1 for weight in decoder.weights])
    after = adc.convert(1.0, 0.8).decisions
    assert before == after


def test_decoder_is_deterministic(adc):
    assert adc.convert(1.0, 0.8).decisions == adc.convert(1.0, 0.8).decisions


@pytest.mark.parametrize(
    ("vin_diff", "relation"),
    [(0.0, "mid"), (0.25 * VREF, "high"), (-0.25 * VREF, "low")],
)
def test_nominal_polarity(adc, vin_diff, relation):
    code = SARDecoder().decode(adc.convert_diff(vin_diff).decisions)
    if relation == "mid":
        assert abs(code - 2048) < 100
    elif relation == "high":
        assert code > 2048
    else:
        assert code < 2048


def test_signed_decoder_covers_all_output_codes():
    decoder = SARDecoder()
    codes = {
        decoder.decode(
            [(combo >> stage) & 1 for stage in range(cfg.N_STAGES)]
        )
        for combo in range(1 << cfg.N_STAGES)
    }
    assert codes == set(range(1 << cfg.N_BITS))


def test_terminal_completes_all_odd_internal_levels():
    physical = list(cfg.NOMINAL_WEIGHTS_Q0[:-1])
    sums = {
        sum(
            (1 - 2 * ((combo >> stage) & 1)) * physical[stage]
            for stage in range(cfg.N_PHYSICAL)
        )
        for combo in range(1 << cfg.N_PHYSICAL)
    }
    with_terminal = {value + sign for value in sums for sign in (-1, 1)}
    total = int(sum(physical))
    required = set(range(-total + 1, total, 2))
    assert required.issubset(with_terminal)


def test_signed_sum_parity_is_stable():
    decoder = SARDecoder()
    rng = random.Random(42)
    for _ in range(1000):
        decisions = [
            rng.randint(0, 1) for _ in range(cfg.N_STAGES)
        ]
        signed_sum = sum(
            (1 - 2 * decision) * weight
            for decision, weight in zip(decisions, decoder.weights)
        )
        assert signed_sum % 2 == 0


def test_q2_preserves_fractional_reconstruction():
    nominal = SARDecoder().weights
    decoder = SARDecoder(
        weights_p=[weight * 1.003 for weight in nominal],
        weights_n=[weight * 0.997 for weight in nominal],
    )
    decisions = [0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0]
    code_float = decoder.decode_float(decisions)
    assert abs(
        decoder.decode_fixed(decisions, fractional_bits=2) - code_float
    ) <= 0.125 + 1e-12
    assert isinstance(decoder.decode(decisions), int)


def test_physical_oracle_is_per_side_and_terminal_is_digital():
    cdac = DifferentialCDAC.from_mismatch(
        md=[1.02] * 7,
        mu=[0.98] * 7,
    )
    wp, wn = cdac.get_physical_weights_per_side_q0()
    assert wp[:7] != wn[:7]
    assert wp[-1] == 1.0 and wn[-1] == 1.0
    assert cdac.p_topology.get_cap_by_stage(cfg.N_STAGES - 1) is None
