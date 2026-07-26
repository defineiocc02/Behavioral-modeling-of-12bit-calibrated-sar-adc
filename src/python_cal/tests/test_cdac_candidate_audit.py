from python_cal.validation import cdac_candidate_audit as audit


ACTIVE_CANDIDATE = {
    "high": [32, 16, 8, 8, 4, 2, 1],
    "low": [32, 16, 8, 4, 2, 2, 1],
    "bridge": 2,
    "terminal": 1.0,
}


def test_matched_candidate_is_order_preserving(monkeypatch):
    monkeypatch.setattr(audit, "SIGMA", 0.0)
    result = audit._audit_seed(**ACTIVE_CANDIDATE, seed=70000)
    assert result["integer_backsteps"] == 0
    assert result["float_backsteps"] == 0
    assert result["max_float_rollback_lsb"] == 0.0
    assert result["integer_nonmonotonic_input_fraction"] == 0.0


def test_mismatch_severity_metrics_expose_order_violation(monkeypatch):
    monkeypatch.setattr(audit, "SIGMA", 0.005)
    result = audit._audit_seed(**ACTIVE_CANDIDATE, seed=70000)
    assert result["float_backsteps"] > 0
    assert result["worst_float_step_lsb"] < 0.0
    assert result["worst_float_backstep_magnitude_lsb"] > 0.0
    assert result["max_float_rollback_lsb"] > 0.0
    assert result["float_nonmonotonic_input_fraction"] > 0.0
