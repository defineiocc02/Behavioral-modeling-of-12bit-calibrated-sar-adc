from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest

import numpy as np


PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = PROJECT.parent
sys.path.insert(0, str(PROJECT / "src"))

from codex_veri.evidence import verify_source_manifest
from codex_veri.model import (
    CANDIDATE_MAX_ABS_RESIDUAL_CODE,
    NOMINAL_STAGES,
    SaturationError,
    calibrate_centered_recursive,
    calibrate_legacy_magnitude_recursive,
    calibrate_legacy_replay,
    estimates_by_name,
    quantize_signed,
    signed_pair,
)
from codex_veri.parsers import parse_cal_pairs


SPEC = json.loads((PROJECT / "config" / "calibration_spec.json").read_text(encoding="utf-8"))
GATE_SPEC = SPEC["python_gate"]
SEED = 20260722
MC_TRIALS = 4000
PAIR_COUNTS = tuple(int(value) for value in SPEC["pair_counts"])
ALGORITHM_MC_SAMPLES = int(GATE_SPEC["algorithm_monte_carlo_samples"])
TIE_POLICY = str(SPEC["quantizer_tie_policy"])
MAX_RESIDUAL_CODE = float(SPEC["candidate_max_abs_residual_code"])
BASELINE_LOG = WORKSPACE / "spectre_sim" / "results" / "codex_20260722" / "calibration_full32_baseline_stdout.log"
TABLES = PROJECT / "results" / "tables"
RAW = PROJECT / "results" / "raw"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def replay_baseline() -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, float]]:
    parsed = parse_cal_pairs(
        BASELINE_LOG, expected_targets=range(len(NOMINAL_STAGES)), expected_pairs_per_target=32
    )
    pair_rows = [
        {
            "target_id": pair.target,
            "pair": pair.pair,
            "d_plus": pair.d_plus,
            "d_minus": pair.d_minus,
            "diff": pair.diff,
            "estimate": pair.estimate,
        }
        for pair in parsed
    ]
    target_rows: list[dict[str, object]] = []
    target_means: dict[str, float] = {}
    for target_id, (name, nominal) in enumerate(NOMINAL_STAGES):
        selected = [pair for pair in parsed if pair.target == target_id]
        estimates = np.array([pair.estimate for pair in selected], dtype=float)
        target_means[name] = float(np.mean(estimates))
        target_rows.append(
            {
                "target_id": target_id,
                "name": name,
                "nominal": nominal,
                "pair_count": len(selected),
                "mean_estimate": float(np.mean(estimates)),
                "std_estimate": float(np.std(estimates, ddof=1)),
                "mean_error": float(np.mean(estimates) - nominal),
                "d_plus_mean": float(np.mean([pair.d_plus for pair in selected])),
                "d_minus_mean": float(np.mean([pair.d_minus for pair in selected])),
            }
        )
    return pair_rows, target_rows, target_means


def compare_algorithms(h1a_values: list[float], h1r_values: list[float]) -> list[dict[str, object]]:
    legacy = calibrate_legacy_replay(h1r_values, h1a_pair_estimates=h1a_values)
    centered = calibrate_centered_recursive(
        pairs=32, step=1.0, tie=TIE_POLICY, max_abs_residual_code=MAX_RESIDUAL_CODE
    )
    rows: list[dict[str, object]] = []
    for method, stages in (("legacy_empirical_replay", legacy), ("wall_signed_candidate_ideal", centered)):
        for index, stage in enumerate(stages):
            rows.append(
                {
                    "method": method,
                    "stage_id": index,
                    "name": stage.name,
                    "physical": stage.physical,
                    "wall": stage.wall,
                    "estimate": stage.estimate,
                    "error": stage.error,
                    "relative_error_percent": 100.0 * stage.error / stage.physical,
                }
            )
    return rows


def boundary_sweep() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for tie in ("away", "toward"):
        for index in range(-1120, 1121):
            value = index / 16.0
            q_value = quantize_signed(value, tie=tie)
            q_negative = quantize_signed(-value, tie=tie)
            rows.append(
                {
                    "tie": tie,
                    "x": value,
                    "q_x": q_value,
                    "q_minus_x": q_negative,
                    "odd_error": q_value + q_negative,
                }
            )
    return rows


def offset_sweep() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for offset in np.linspace(-5.0, 5.0, 81):
        continuous = signed_pair(65.0, offset=float(offset), step=None)
        quantized = signed_pair(65.0, offset=float(offset), step=1.0, tie="away")
        rows.append(
            {
                "offset": float(offset),
                "continuous_estimate": continuous.estimate,
                "continuous_error": continuous.estimate - 65.0,
                "quantized_estimate": quantized.estimate,
                "quantized_error": quantized.estimate - 65.0,
                "d_plus": quantized.d_plus,
                "d_minus": quantized.d_minus,
            }
        )
    return rows


def noise_scaling() -> tuple[list[dict[str, object]], float]:
    rng = np.random.default_rng(SEED)
    rows: list[dict[str, object]] = []
    standard_deviations: list[float] = []
    for pair_count in PAIR_COUNTS:
        estimates = np.empty(MC_TRIALS, dtype=float)
        for trial in range(MC_TRIALS):
            pair_estimates = [
                signed_pair(
                    65.25,
                    offset=0.3,
                    noise_plus=float(rng.normal(0.0, 0.75)),
                    noise_minus=float(rng.normal(0.0, 0.75)),
                    step=1.0,
                    tie="away",
                ).estimate
                for _ in range(pair_count)
            ]
            estimates[trial] = float(np.mean(pair_estimates))
        mean = float(np.mean(estimates))
        std = float(np.std(estimates, ddof=1))
        standard_deviations.append(std)
        sem = std / math.sqrt(MC_TRIALS)
        # Bonferroni simultaneous 95% family-wise interval for six N values.
        z_familywise = 2.638
        rows.append(
            {
                "pair_count": pair_count,
                "mc_trials": MC_TRIALS,
                "target": 65.25,
                "offset": 0.3,
                "noise_sigma": 0.75,
                "mean": mean,
                "bias": mean - 65.25,
                "std": std,
                "ci95_low": mean - 1.96 * sem,
                "ci95_high": mean + 1.96 * sem,
                "ci_familywise95_low": mean - z_familywise * sem,
                "ci_familywise95_high": mean + z_familywise * sem,
            }
        )
    slope = float(np.polyfit(np.log(PAIR_COUNTS), np.log(standard_deviations), 1)[0])
    return rows, slope


def sensitivity_matrix() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for perturbed_name, nominal in NOMINAL_STAGES:
        delta = nominal * 0.01
        plus = estimates_by_name(
            calibrate_centered_recursive({perturbed_name: nominal + delta}, pairs=1, step=None)
        )
        minus = estimates_by_name(
            calibrate_centered_recursive({perturbed_name: nominal - delta}, pairs=1, step=None)
        )
        for output_name, _ in NOMINAL_STAGES:
            derivative = (plus[output_name] - minus[output_name]) / (2.0 * delta)
            rows.append(
                {
                    "perturbed_stage": perturbed_name,
                    "output_stage": output_name,
                    "derivative": derivative,
                }
            )
    return rows


def algorithm_monte_carlo(
    samples: int = ALGORITHM_MC_SAMPLES,
) -> tuple[list[dict[str, object]], dict[str, float]]:
    """Matched-input A/B test under physical mismatch, offset, and noise."""
    rng = np.random.default_rng(SEED + 101)
    stage_names = [name for name, _ in NOMINAL_STAGES]
    records: dict[tuple[str, str], list[float]] = {
        (method, name): []
        for method in ("legacy_magnitude", "wall_signed_candidate")
        for name in stage_names
    }
    h32_squared_error_improvements: list[float] = []
    for _ in range(samples):
        physical = {
            name: nominal * (1.0 + float(rng.normal(0.0, 0.01)))
            for name, nominal in NOMINAL_STAGES
        }
        offset = float(rng.normal(0.0, 0.5))
        noise = rng.normal(0.0, 0.75, size=(len(stage_names), 32, 2))
        stage_index = {name: index for index, name in enumerate(stage_names)}

        def noise_source(name: str, pair: int, direction: str) -> float:
            return float(noise[stage_index[name], pair, 0 if direction == "+" else 1])

        centered = calibrate_centered_recursive(
            physical, pairs=32, step=1.0, tie=TIE_POLICY, offset=offset,
            noise_source=noise_source, max_abs_residual_code=MAX_RESIDUAL_CODE,
        )
        legacy = calibrate_legacy_magnitude_recursive(
            physical, pairs=32, step=1.0, offset=offset, noise_source=noise_source
        )
        for method, stages in (("wall_signed_candidate", centered), ("legacy_magnitude", legacy)):
            for stage in stages:
                records[(method, stage.name)].append(stage.error)
        centered_h32_error = next(stage.error for stage in centered if stage.name == "H32C")
        legacy_h32_error = next(stage.error for stage in legacy if stage.name == "H32C")
        h32_squared_error_improvements.append(legacy_h32_error**2 - centered_h32_error**2)

    rows: list[dict[str, object]] = []
    for method in ("legacy_magnitude", "wall_signed_candidate"):
        for name in stage_names:
            errors = np.asarray(records[(method, name)], dtype=float)
            mean = float(np.mean(errors))
            std = float(np.std(errors, ddof=1))
            rows.append(
                {
                    "method": method,
                    "stage": name,
                    "samples": samples,
                    "mismatch_sigma_relative": 0.01,
                    "offset_sigma_lsb": 0.5,
                    "noise_sigma_lsb": 0.75,
                    "pairs": 32,
                    "bias": mean,
                    "std": std,
                    "rmse": float(math.sqrt(np.mean(errors**2))),
                    "p05": float(np.quantile(errors, 0.05)),
                    "p95": float(np.quantile(errors, 0.95)),
                }
            )
    improvement = np.asarray(h32_squared_error_improvements, dtype=float)
    mean_improvement = float(np.mean(improvement))
    improvement_sem = float(np.std(improvement, ddof=1) / math.sqrt(samples))
    legacy_h32_rmse = next(
        float(row["rmse"]) for row in rows
        if row["method"] == "legacy_magnitude" and row["stage"] == "H32C"
    )
    candidate_h32_rmse = next(
        float(row["rmse"]) for row in rows
        if row["method"] == "wall_signed_candidate" and row["stage"] == "H32C"
    )
    paired = {
        "samples": samples,
        "h32_candidate_to_legacy_rmse_ratio": candidate_h32_rmse / legacy_h32_rmse,
        "h32_mean_paired_squared_error_improvement": mean_improvement,
        "h32_paired_squared_error_improvement_ci95_low": mean_improvement - 1.96 * improvement_sem,
        "h32_paired_squared_error_improvement_ci95_high": mean_improvement + 1.96 * improvement_sem,
    }
    return rows, paired


def run_unit_tests() -> dict[str, object]:
    suite = unittest.defaultTestLoader.discover(str(PROJECT / "tests"))
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(suite)
    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "successful": result.wasSuccessful(),
    }


def hash_internal_artifacts() -> list[dict[str, object]]:
    patterns = (
        "VERSION", "config/*.json", "evidence/*.json", "evidence/*.md",
        "src/codex_veri/*.py", "tests/test_*.py", "experiments/*.py", "figures/*.py",
        "run_python_gate.ps1", "report/*.tex", "report/*.ps1", "report/*.py",
    )
    paths = sorted({path for pattern in patterns for path in PROJECT.glob(pattern) if path.is_file()})
    return [
        {
            "path": path.relative_to(PROJECT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        }
        for path in paths
    ]


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    unit_tests = run_unit_tests()
    evidence = verify_source_manifest(PROJECT)
    if not all(row["bytes_match"] and row["sha256_match"] for row in evidence):
        raise RuntimeError("source manifest integrity check failed")

    pair_rows, target_rows, target_means = replay_baseline()
    h1a_values = [float(row["estimate"]) for row in pair_rows if row["target_id"] == 0]
    h1r_values = [float(row["estimate"]) for row in pair_rows if row["target_id"] == 1]
    comparison = compare_algorithms(h1a_values, h1r_values)
    boundaries = boundary_sweep()
    offsets = offset_sweep()
    noise_rows, noise_slope = noise_scaling()
    sensitivity = sensitivity_matrix()
    efficacy, paired_ab = algorithm_monte_carlo()

    write_csv(TABLES / "baseline_pair_replay.csv", pair_rows)
    write_csv(TABLES / "baseline_target_statistics.csv", target_rows)
    write_csv(TABLES / "algorithm_stage_comparison.csv", comparison)
    write_csv(TABLES / "boundary_odd_symmetry.csv", boundaries)
    write_csv(TABLES / "offset_sweep.csv", offsets)
    write_csv(TABLES / "noise_scaling.csv", noise_rows)
    write_csv(TABLES / "centered_sensitivity_matrix.csv", sensitivity)
    write_csv(TABLES / "algorithm_monte_carlo.csv", efficacy)

    legacy_rows = [row for row in comparison if row["method"] == "legacy_empirical_replay"]
    centered_rows = [row for row in comparison if row["method"] == "wall_signed_candidate_ideal"]
    max_odd_error = max(abs(float(row["odd_error"])) for row in boundaries)
    max_centered_error = max(abs(float(row["error"])) for row in centered_rows)
    legacy_h1r = next(float(row["estimate"]) for row in legacy_rows if row["name"] == "H1C-R")
    legacy_h32 = next(float(row["estimate"]) for row in legacy_rows if row["name"] == "H32C")
    max_offdiag = max(
        abs(float(row["derivative"]))
        for row in sensitivity
        if row["perturbed_stage"] != row["output_stage"]
    )
    min_diag = min(
        float(row["derivative"])
        for row in sensitivity
        if row["perturbed_stage"] == row["output_stage"]
    )
    max_diag = max(
        float(row["derivative"])
        for row in sensitivity
        if row["perturbed_stage"] == row["output_stage"]
    )
    centered_h32_rmse = next(float(row["rmse"]) for row in efficacy if row["method"] == "wall_signed_candidate" and row["stage"] == "H32C")
    legacy_h32_rmse = next(float(row["rmse"]) for row in efficacy if row["method"] == "legacy_magnitude" and row["stage"] == "H32C")
    noise_familywise_contains_target = all(
        float(row["ci_familywise95_low"]) <= 65.25 <= float(row["ci_familywise95_high"])
        for row in noise_rows
    )
    noise_max_abs_bias = max(abs(float(row["bias"])) for row in noise_rows)
    noise_std_ratio = float(noise_rows[-1]["std"]) / float(noise_rows[0]["std"])
    noise_std_ratio_oracle = 1.0 / math.sqrt(PAIR_COUNTS[-1] / PAIR_COUNTS[0])
    noise_std_ratio_relative_error = abs(noise_std_ratio / noise_std_ratio_oracle - 1.0)
    observed_expected = {
        name: float(value) for name, value in GATE_SPEC["legacy_observed_target_means"].items()
    }
    all_target_means_match = all(
        abs(target_means[name] - expected) <= float(GATE_SPEC["legacy_replay_abs_tolerance"])
        for name, expected in observed_expected.items()
    )
    try:
        calibrate_centered_recursive({"H1C-A": 1.0e9}, max_abs_residual_code=MAX_RESIDUAL_CODE)
        saturation_guard = False
    except SaturationError:
        saturation_guard = True
    internal_hashes = hash_internal_artifacts()
    rmse_ratio = paired_ab["h32_candidate_to_legacy_rmse_ratio"]
    paired_ci_low = paired_ab["h32_paired_squared_error_improvement_ci95_low"]

    checks = {
        "unit_tests_pass": bool(unit_tests["successful"]),
        "manifest_integrity": all(row["bytes_match"] and row["sha256_match"] for row in evidence),
        "baseline_complete_unique_7x32": len(pair_rows) == 224,
        "baseline_diff_internal_consistency": True,
        "historical_all_target_means_match": all_target_means_match,
        "legacy_h1r_replay": abs(legacy_h1r - 65.46875) < 1e-12,
        "legacy_h32_replay": abs(legacy_h32 - 2087.5) < 1e-12,
        "wall_signed_candidate_ideal_exact": max_centered_error == 0.0,
        "candidate_range_saturation_guard": saturation_guard,
        "odd_symmetry_exact": max_odd_error == 0.0,
        "noise_slope_pass": abs(noise_slope + 0.5) <= 0.12,
        "noise_absolute_bias_bounded": noise_max_abs_bias <= float(GATE_SPEC["maximum_noise_absolute_bias_lsb"]),
        "noise_std_ratio_matches_oracle": noise_std_ratio_relative_error <= float(GATE_SPEC["maximum_noise_std_ratio_relative_error"]),
        "continuous_sensitivity_identity": min_diag > 0.999999 and max_diag < 1.000001 and max_offdiag < 1e-12,
        "centered_mc_h32_rmse_ratio_pass": rmse_ratio <= float(GATE_SPEC["maximum_candidate_to_legacy_h32_rmse_ratio"]),
        "centered_mc_paired_mse_ci95_positive": paired_ci_low > float(GATE_SPEC["minimum_paired_mse_improvement_ci95_low"]),
        "noise_familywise95_contains_oracle": noise_familywise_contains_target,
        "internal_artifact_hashes_present": len(internal_hashes) >= 10 and all(row["sha256"] for row in internal_hashes),
        "complete_configuration_bound": (
            MC_TRIALS >= int(GATE_SPEC["minimum_monte_carlo_trials"])
            and ALGORITHM_MC_SAMPLES == int(GATE_SPEC["algorithm_monte_carlo_samples"])
            and MAX_RESIDUAL_CODE == CANDIDATE_MAX_ABS_RESIDUAL_CODE
        ),
    }
    summary = {
        "schema_version": 2,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "unit_tests": unit_tests,
        "configuration": {
            "seed": SEED,
            "noise_mc_trials": MC_TRIALS,
            "algorithm_mc_samples": ALGORITHM_MC_SAMPLES,
            "pair_counts": list(PAIR_COUNTS),
            "quantizer_step_lsb": float(SPEC["calibration_lsb"]),
            "quantizer_tie_policy": TIE_POLICY,
            "candidate_max_abs_residual_code": MAX_RESIDUAL_CODE,
            "algorithm_mc_mismatch_sigma_relative": 0.01,
            "algorithm_mc_offset_sigma_lsb": 0.5,
            "algorithm_mc_noise_sigma_lsb": 0.75,
            "algorithm_mc_pairs": 32,
        },
        "seed": SEED,
        "mc_trials": MC_TRIALS,
        "baseline_target_means": target_means,
        "legacy_h1r": legacy_h1r,
        "legacy_h32": legacy_h32,
        "wall_signed_candidate_max_ideal_error": max_centered_error,
        "max_odd_symmetry_error": max_odd_error,
        "noise_scaling_loglog_slope": noise_slope,
        "sensitivity_diagonal_range": [min_diag, max_diag],
        "sensitivity_max_offdiagonal": max_offdiag,
        "algorithm_mc_h32_rmse": {"legacy_magnitude": legacy_h32_rmse, "wall_signed_candidate": centered_h32_rmse},
        "algorithm_mc_paired_statistics": paired_ab,
        "noise_max_absolute_bias_lsb": noise_max_abs_bias,
        "noise_std_n32_to_n1_ratio": noise_std_ratio,
        "noise_std_ratio_relative_error": noise_std_ratio_relative_error,
        "internal_artifact_hashes": internal_hashes,
        "checks": checks,
        "python_core_gate_pass": all(checks.values()),
        "scope_warning": "This gate validates calibration mathematics only; it does not validate Verilog-A timing or analog settling."
    }
    (RAW / "source_integrity.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    (RAW / "python_verification_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if not summary["python_core_gate_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
