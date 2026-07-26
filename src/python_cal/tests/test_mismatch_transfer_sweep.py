from python_cal.validation.mismatch_transfer_sweep import run_sweep


def test_zero_mismatch_point_is_strictly_monotonic():
    result = run_sweep(seed_start=1, seed_count=2)
    point = result["points"][0]
    assert point["unit_cap_sigma"] == 0.0
    assert point["strict_integer_monotonic_yield"] == 2
    assert point["zero_missing_code_yield"] == 2
    assert point["metrics"]["integer_backsteps"]["max"] == 0.0


def test_sweep_explicitly_isolates_calibration_and_noise():
    result = run_sweep(seed_start=1, seed_count=1)
    assert "physical-oracle" in result["isolation"]
    assert "zero comparator/calibration noise" in result["isolation"]
