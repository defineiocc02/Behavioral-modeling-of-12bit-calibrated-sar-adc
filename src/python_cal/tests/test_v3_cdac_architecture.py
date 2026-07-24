"""Release invariants for the locked v3.0 integer CDAC."""

import inspect

from python_cal import config as cfg
from python_cal.decode.sar_decoder import SARDecoder
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.topology.switch_state import Rail, SideSwitchState
from python_cal.topology.switching_policy import DifferentialSwitchingPolicy


def test_integer_capacitance_budget_is_138_cu_per_side():
    assert all(
        isinstance(value, int) and value >= 1
        for value in cfg.CAP_NOMINAL_CU.values()
    )
    assert sum(cfg.CAP_NOMINAL_CU.values()) == 138
    assert cfg.C_HIGH_NOMINAL == 71
    assert cfg.C_B_NOMINAL == 2
    assert cfg.C_LOW_NOMINAL == 65


def test_ideal_bridge_weights_match_locked_vector():
    expected = [
        2144, 1072, 536, 536, 268, 134, 67,
        64, 32, 16, 8, 4, 4, 2, 1,
    ]
    wp, wn = DifferentialCDAC.ideal().get_physical_weights_per_side_q0()
    assert wp == expected
    assert wn == expected
    assert list(cfg.NOMINAL_WEIGHTS_Q0) == expected


def test_every_physical_capacitor_samples_input():
    state = DifferentialSwitchingPolicy().sampling_state(1.0, 0.8)
    assert set(SideSwitchState.CAP_NAMES) == {
        name for name in cfg.ALL_CAP_NAMES if name != "bridge"
    }
    for name in SideSwitchState.CAP_NAMES:
        assert state.p_side.get_rail(name) is Rail.VINP
        assert state.n_side.get_rail(name) is Rail.VINN


def test_high_segment_calibration_has_at_least_64_q0_backend_margin():
    weights = cfg.NOMINAL_WEIGHTS_Q0
    for target in cfg.SHEN_CAL_TARGETS:
        lower = cfg.SHEN_LOWER_STAGES[target["stage"]]
        margin = sum(weights[stage] for stage in lower) - target["nominal_q0"]
        assert margin >= 64


def test_active_decoder_contains_no_lut_or_dp_remap():
    source = inspect.getsource(SARDecoder).lower()
    assert "lookup" not in source
    assert "centroid" not in source
    assert "dynamic programming" not in source
    assert "exception table" not in source
