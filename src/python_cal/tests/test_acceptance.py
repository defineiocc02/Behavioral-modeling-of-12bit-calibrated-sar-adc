from python_cal.validation.acceptance import evaluate_acceptance


def _passing_inputs():
    return {
        "n_valid": 2,
        "n_seeds": 2,
        "calibrated_enob": [12.0, 12.1],
        "calibrated_sndr_db": [74.0, 74.5],
        "min_enob_bits": 11.5,
        "min_sndr_db": 70.99,
        "total_missing_codes": 0,
        "max_integer_jumps": [1, 1],
        "dnl_peaks_lsb": [0.8, 0.9],
        "inl_peaks_lsb": [0.8, 0.9],
        "total_integer_backsteps": 0,
    }


def test_all_mismatch_acceptance_gates_pass_together():
    verdicts = evaluate_acceptance(**_passing_inputs())
    assert verdicts == {
        "absolute_dynamic_verdict": "PASS",
        "code_density_static_verdict": "PASS",
        "mismatch_transfer_integrity_verdict": "PASS",
        "strict_monotonicity_required": "NO",
        "acceptance_verdict": "PASS",
    }


def test_integer_backsteps_are_reported_without_changing_existing_contract():
    inputs = _passing_inputs()
    inputs["total_integer_backsteps"] = 1
    verdicts = evaluate_acceptance(**inputs)
    assert verdicts["code_density_static_verdict"] == "PASS"
    assert verdicts["mismatch_transfer_integrity_verdict"] == "FAIL"
    assert verdicts["acceptance_verdict"] == "PASS"


def test_application_can_require_strict_monotonicity():
    inputs = _passing_inputs()
    inputs["total_integer_backsteps"] = 1
    inputs["require_strict_monotonicity"] = True
    verdicts = evaluate_acceptance(**inputs)
    assert verdicts["strict_monotonicity_required"] == "YES"
    assert verdicts["acceptance_verdict"] == "FAIL"


def test_missing_codes_fail_histogram_and_overall_gates():
    inputs = _passing_inputs()
    inputs["total_missing_codes"] = 1
    verdicts = evaluate_acceptance(**inputs)
    assert verdicts["code_density_static_verdict"] == "FAIL"
    assert verdicts["acceptance_verdict"] == "FAIL"
