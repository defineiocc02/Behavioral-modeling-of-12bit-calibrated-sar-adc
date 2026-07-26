from python_cal import config as cfg
from python_cal.calibration.calibration_fsm import ADCOperatingMode
from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
from python_cal.decode.sar_decoder import SARDecoder
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.topology.cdac_topology import VCM
from python_cal.validation.reachable_codebook import (
    audit_reachable_codebook,
    enumerate_reachable_leaves,
)


def test_reachable_tree_covers_input_interval_without_gaps():
    leaves = enumerate_reachable_leaves(
        DifferentialCDAC.ideal(),
        v_lo=-2.0,
        v_hi=2.0,
    )
    assert leaves
    assert leaves[0].v_lo == -2.0
    assert leaves[-1].v_hi == 2.0
    for left, right in zip(leaves, leaves[1:]):
        assert left.v_hi == right.v_lo
        assert left.width_v > 0.0


def test_ideal_reachable_codebook_is_monotonic_and_complete():
    result = audit_reachable_codebook(
        DifferentialCDAC.ideal(),
        SARDecoder(),
    )
    assert result["n_reachable_leaves"] > 4096
    assert result["n_unique_integer_codes"] == 4096
    assert result["n_float_backsteps"] == 0
    assert result["n_integer_backsteps"] == 0
    assert result["max_float_rollback_lsb"] == 0.0
    assert result["max_integer_rollback_lsb"] == 0
    assert result["float_nonmonotonic_input_fraction"] == 0.0
    assert result["integer_nonmonotonic_input_fraction"] == 0.0
    assert result["n_missing_codes"] == 0


def test_reachable_leaf_midpoints_match_real_converter():
    cdac = DifferentialCDAC.ideal()
    leaves = enumerate_reachable_leaves(cdac, v_lo=-2.0, v_hi=2.0)
    adc = AsyncBehavioralSARADC(cdac=cdac)
    adc._nominal_decode_enabled = True
    object.__setattr__(adc, "mode", ADCOperatingMode.READY)

    # Check every leaf, not a sampled subset.  This validates the independent
    # tree partition against the production conversion controller.
    for leaf in leaves:
        vin_diff = 0.5 * (leaf.v_lo + leaf.v_hi)
        result = adc.convert(
            VCM + vin_diff / 2.0,
            VCM - vin_diff / 2.0,
        )
        assert tuple(result.decisions) == leaf.decisions
