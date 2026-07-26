"""Collect mismatch-matrix runs into one machine-readable comparison."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


CASE_ORDER = (
    "ideal_zero_noise",
    "mismatch_0p5_zero_noise",
    "mismatch_0p5_calnoise_0p3mV",
    "mismatch_1p0_zero_noise",
    "mismatch_1p0_calnoise_0p3mV",
)


def _percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q))


def _latest(path: Path, pattern: str) -> Path:
    matches = sorted(path.glob(pattern), key=lambda item: item.stat().st_mtime)
    if not matches:
        raise FileNotFoundError(f"no {pattern} under {path}")
    return matches[-1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_case(path: Path) -> dict:
    summary_path = _latest(path, "final_summary_*.json")
    csv_path = _latest(path, "final_pipeline_*.csv")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    valid = [row for row in rows if row["valid"].lower() == "true"]
    if not valid:
        raise RuntimeError(f"no valid rows in {csv_path}")
    expected_total = int(summary["n_total"])
    expected_valid = int(summary["n_valid"])
    if len(rows) != expected_total or len(valid) != expected_valid:
        raise RuntimeError(
            "CSV/summary count mismatch under "
            f"{path}: rows={len(rows)}/{expected_total}, "
            f"valid={len(valid)}/{expected_valid}"
        )
    if expected_total != int(summary["mc_seeds"]):
        raise RuntimeError(
            f"summary seed count mismatch under {path}: "
            f"n_total={expected_total}, mc_seeds={summary['mc_seeds']}"
        )

    def values(field: str) -> list[float]:
        return [float(row[field]) for row in valid]

    def optional_values(field: str) -> list[float]:
        return [float(row[field]) for row in valid if row[field] != ""]

    dnl = optional_values("dnl_peak")
    inl = optional_values("inl_peak")
    nominal_sndr = values("nominal_sndr")
    calibrated_sndr = values("calibrated_sndr")
    physical_sndr = values("physical_sndr")
    calibrated_enob = values("calibrated_enob")
    gains = values("cal_gain_db")
    integer_backsteps = values("n_non_monotonic")
    float_backsteps = values("n_float_backsteps")
    integer_rollbacks = values("max_integer_rollback_lsb")
    float_rollbacks = values("max_float_rollback_lsb")
    integer_affected_fractions = values(
        "integer_nonmonotonic_input_fraction"
    )
    float_affected_fractions = values(
        "float_nonmonotonic_input_fraction"
    )
    min_sndr = float(summary["min_cal_sndr_db"])
    min_enob = float(summary["min_cal_enob_bits"])
    dynamic_pass = [
        float(row["calibrated_sndr"]) > min_sndr
        and float(row["calibrated_enob"]) > min_enob
        for row in valid
    ]
    code_density_pass = [
        int(row["n_missing"]) == 0
        and int(row["max_integer_jump"]) <= 1
        and row["dnl_peak"] != ""
        and float(row["dnl_peak"]) <= 1.0
        and row["inl_peak"] != ""
        and float(row["inl_peak"]) <= 1.0
        for row in valid
    ]
    combined_pass = [
        dyn and static
        for dyn, static in zip(dynamic_pass, code_density_pass)
    ]
    return {
        "case_dir": path.name,
        "summary_file": summary_path.name,
        "csv_file": csv_path.name,
        "summary_sha256": _sha256(summary_path),
        "csv_sha256": _sha256(csv_path),
        "run_id": summary["run_id"],
        "mc_sigma": summary["mc_sigma"],
        "cal_noise_sigma_v": summary["cal_noise_sigma_v"],
        "avg_pairs": summary["avg_pairs"],
        "mismatch_mode": summary.get("mismatch_mode", "unrecorded"),
        "mismatch_scope": summary.get("mismatch_scope", "unrecorded"),
        "cal_weight_fractional_bits": summary.get(
            "cal_weight_fractional_bits"
        ),
        "output_fractional_bits": summary.get(
            "output_fractional_bits"
        ),
        "n_total": len(rows),
        "n_valid": len(valid),
        "yield": {
            "dynamic_pass": int(sum(dynamic_pass)),
            "code_density_pass": int(sum(code_density_pass)),
            "combined_pass": int(sum(combined_pass)),
            "denominator": len(valid),
        },
        "nominal_sndr_db": {
            "p50": _percentile(nominal_sndr, 50),
            "min": min(nominal_sndr),
        },
        "calibrated_sndr_db": {
            "p50": _percentile(calibrated_sndr, 50),
            "min": min(calibrated_sndr),
        },
        "physical_oracle_sndr_db": {
            "p50": _percentile(physical_sndr, 50),
            "min": min(physical_sndr),
        },
        "calibrated_enob_bits": {
            "p50": _percentile(calibrated_enob, 50),
            "min": min(calibrated_enob),
        },
        "calibration_gain_db": {
            "p50": _percentile(gains, 50),
            "min": min(gains),
        },
        "oracle_gap_db": {
            "p50": summary["gap_p50_db"],
            "p95": summary["gap_p95_db"],
        },
        "missing_codes_total": int(summary["total_missing_codes"]),
        "dnl_peak_lsb": {
            "defined_seeds": len(dnl),
            "p95": _percentile(dnl, 95) if dnl else None,
            "max": max(dnl) if dnl else None,
        },
        "inl_peak_lsb": {
            "defined_seeds": len(inl),
            "p95": _percentile(inl, 95) if inl else None,
            "max": max(inl) if inl else None,
        },
        "missing_code_seed_count": sum(
            int(row["n_missing"]) > 0 for row in valid
        ),
        "negative_gain_seed_count": sum(value < 0.0 for value in gains),
        "integer_backsteps_total": int(
            sum(int(row["n_non_monotonic"]) for row in valid)
        ),
        "transfer_integrity": {
            "integer_monotonic_seed_count": int(
                sum(value == 0 for value in integer_backsteps)
            ),
            "integer_backstep_seed_count": int(
                sum(value > 0 for value in integer_backsteps)
            ),
            "integer_backsteps_per_seed": {
                "p50": _percentile(integer_backsteps, 50),
                "p95": _percentile(integer_backsteps, 95),
                "max": max(integer_backsteps),
            },
            "float_backsteps_per_seed": {
                "p50": _percentile(float_backsteps, 50),
                "p95": _percentile(float_backsteps, 95),
                "max": max(float_backsteps),
            },
            "max_integer_rollback_lsb": max(integer_rollbacks),
            "max_float_rollback_lsb": max(float_rollbacks),
            "integer_nonmonotonic_input_fraction": {
                "p50": _percentile(integer_affected_fractions, 50),
                "p95": _percentile(integer_affected_fractions, 95),
                "max": max(integer_affected_fractions),
            },
            "float_nonmonotonic_input_fraction": {
                "p50": _percentile(float_affected_fractions, 50),
                "p95": _percentile(float_affected_fractions, 95),
                "max": max(float_affected_fractions),
            },
        },
        "acceptance_verdict": summary["acceptance_verdict"],
    }


def summarize(root: Path) -> dict:
    cases = {}
    for label in CASE_ORDER:
        case_path = root / label
        if (
            case_path.exists()
            and any(case_path.glob("final_summary_*.json"))
            and any(case_path.glob("final_pipeline_*.csv"))
        ):
            cases[label] = _collect_case(case_path)
    required = set(CASE_ORDER)
    missing = sorted(required.difference(cases))
    result = {
        "method": (
            "same production pipeline and seeds; mismatch is the primary "
            "variable; calibration noise is secondary"
        ),
        "provenance": {
            "pipeline_sha256": _sha256(
                Path(__file__).resolve().parents[1]
                / "run_final_calibration_pipeline.py"
            ),
            "config_sha256": _sha256(
                Path(__file__).resolve().parents[1] / "config.py"
            ),
            "calibrator_sha256": _sha256(
                Path(__file__).resolve().parents[1]
                / "calibration"
                / "shen_calibrator.py"
            ),
            "decoder_sha256": _sha256(
                Path(__file__).resolve().parents[1]
                / "decode"
                / "sar_decoder.py"
            ),
            "acceptance_sha256": _sha256(
                Path(__file__).resolve().with_name("acceptance.py")
            ),
            "manifest_generator_sha256": _sha256(
                Path(__file__).resolve().parents[1] / "provenance.py"
            ),
            "summarizer_sha256": _sha256(Path(__file__).resolve()),
        },
        "cases": cases,
        "missing_cases": missing,
    }
    if (
        "mismatch_0p5_zero_noise" in cases
        and "mismatch_0p5_calnoise_0p3mV" in cases
    ):
        zero = cases["mismatch_0p5_zero_noise"]
        noisy = cases["mismatch_0p5_calnoise_0p3mV"]
        result["calibration_noise_effect_at_0p5pct"] = {
            "calibrated_sndr_p50_delta_db": (
                noisy["calibrated_sndr_db"]["p50"]
                - zero["calibrated_sndr_db"]["p50"]
            ),
            "calibrated_sndr_min_delta_db": (
                noisy["calibrated_sndr_db"]["min"]
                - zero["calibrated_sndr_db"]["min"]
            ),
            "oracle_gap_p95_delta_db": (
                noisy["oracle_gap_db"]["p95"]
                - zero["oracle_gap_db"]["p95"]
            ),
        }
    if (
        "mismatch_1p0_zero_noise" in cases
        and "mismatch_1p0_calnoise_0p3mV" in cases
    ):
        zero = cases["mismatch_1p0_zero_noise"]
        noisy = cases["mismatch_1p0_calnoise_0p3mV"]
        result["calibration_noise_effect_at_1pct"] = {
            "calibrated_sndr_p50_delta_db": (
                noisy["calibrated_sndr_db"]["p50"]
                - zero["calibrated_sndr_db"]["p50"]
            ),
            "calibrated_sndr_min_delta_db": (
                noisy["calibrated_sndr_db"]["min"]
                - zero["calibrated_sndr_db"]["min"]
            ),
            "oracle_gap_p95_delta_db": (
                noisy["oracle_gap_db"]["p95"]
                - zero["oracle_gap_db"]["p95"]
            ),
        }
    return result


def main() -> None:
    default_root = (
        Path(__file__).resolve().parents[1]
        / "validation_results"
        / "mismatch_matrix"
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    result = summarize(root)
    output = (
        args.output.resolve()
        if args.output is not None
        else root / "mismatch_matrix_summary.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(output)
    print(json.dumps(result, indent=2))
    if result["missing_cases"]:
        raise SystemExit(
            f"matrix incomplete: {', '.join(result['missing_cases'])}"
        )


if __name__ == "__main__":
    main()
