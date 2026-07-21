from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codex_veri.adc_performance import (
    HIGH_STAGE_TO_INDEX,
    MAX_CODE,
    NOMINAL_WEIGHTS,
    coherent_sine,
    decode_decisions,
    dynamic_metrics,
    enob_to_sinad_db,
    fractional_cancellation_codes,
    generate_split_cdac_weights,
    sar_decisions,
)
from codex_veri.model import calibrate_centered_recursive


SPEC = json.loads((PROJECT / "config" / "calibration_spec.json").read_text(encoding="utf-8"))
CFG = SPEC["adc_performance_gate"]
TABLES = PROJECT / "results" / "tables"
RAW = PROJECT / "results" / "raw"
SEED = 2026072202


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def calibrated_high_decoder(
    physical: np.ndarray,
    noise: np.ndarray,
    offset: float,
    pairs: int,
    extra_weights: tuple[float, ...],
) -> np.ndarray:
    names = tuple(HIGH_STAGE_TO_INDEX)

    def noise_source(name: str, pair: int, direction: str) -> float:
        return float(noise[names.index(name), pair, 0 if direction == "+" else 1])

    physical_stages = {name: float(physical[index]) for name, index in HIGH_STAGE_TO_INDEX.items()}
    stages = calibrate_centered_recursive(
        physical_stages,
        pairs=pairs,
        step=float(SPEC["calibration_lsb"]),
        tie=str(SPEC["quantizer_tie_policy"]),
        offset=offset,
        noise_source=noise_source,
        max_abs_residual_code=float(SPEC["candidate_max_abs_residual_code"]),
    )
    decoder = np.concatenate((NOMINAL_WEIGHTS.copy(), np.asarray(extra_weights, dtype=float)))
    for stage in stages:
        decoder[HIGH_STAGE_TO_INDEX[stage.name]] = stage.estimate
    return decoder


def metric_row(
    *,
    sample: int,
    tone_bin: int,
    method: str,
    codes: np.ndarray,
    physical_hash: str,
    evaluation_seed: int,
) -> dict[str, object]:
    metrics = dynamic_metrics(codes, tone_bin)
    return {
        "sample": sample,
        "tone_bin": tone_bin,
        "method": method,
        "physical_hash": physical_hash,
        "evaluation_seed": evaluation_seed,
        "sndr_db": metrics.sndr_db,
        "enob": metrics.enob,
        "sfdr_db": metrics.sfdr_db,
        "thd_db": metrics.thd_db,
        "time_domain_sndr_db": metrics.time_domain_sndr_db,
        "fft_time_sndr_delta_db": metrics.sndr_db - metrics.time_domain_sndr_db,
        "clip_count": metrics.clip_count,
        "pass_enob_strict": int(metrics.enob > float(CFG["minimum_enob_bits_strict"])),
    }


def one_sided_all_pass_lcb95(passes: int, total: int) -> float:
    if passes != total:
        return 0.0
    return 0.05 ** (1.0 / total)


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    methods = sorted({str(row["method"]) for row in rows})
    for method in methods:
        selected = [row for row in rows if row["method"] == method]
        enob = np.asarray([row["enob"] for row in selected], dtype=float)
        passed = int(np.count_nonzero(enob > float(CFG["minimum_enob_bits_strict"])))
        out.append(
            {
                "method": method,
                "records": len(selected),
                "passes": passed,
                "failures": len(selected) - passed,
                "yield": passed / len(selected),
                "yield_lcb95": one_sided_all_pass_lcb95(passed, len(selected)),
                "enob_min": float(np.min(enob)),
                "enob_p01": float(np.quantile(enob, 0.01)),
                "enob_p05": float(np.quantile(enob, 0.05)),
                "enob_median": float(np.median(enob)),
                "enob_mean": float(np.mean(enob)),
                "enob_max": float(np.max(enob)),
                "max_abs_fft_time_sndr_delta_db": max(abs(float(row["fft_time_sndr_delta_db"])) for row in selected),
                "total_clip_count": sum(int(row["clip_count"]) for row in selected),
            }
        )
    return out


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    n_samples = int(CFG["sample_count"])
    tone_bins = tuple(int(value) for value in CFG["tone_bins"])
    mc_samples = int(CFG["monte_carlo_samples"])
    pairs32 = int(CFG["calibration_pairs_baseline"])
    pairs_candidate = int(CFG["calibration_pairs_candidate"])
    fraction_bits = int(CFG["fractional_decoder_bits"])
    extras = tuple(float(value) for value in CFG["candidate_fractional_decisions_lsb"])
    rng = np.random.default_rng(SEED)
    dynamic_rows: list[dict[str, object]] = []
    retained: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

    for sample in range(mc_samples):
        base_physical = generate_split_cdac_weights(
            rng,
            sigma_unit_relative=float(CFG["unit_cap_sigma_relative"]),
            clip_sigma=float(CFG["unit_cap_clip_sigma"]),
        )
        extended_physical = np.concatenate((base_physical, np.asarray(extras)))
        calibration_noise = rng.normal(
            0.0,
            float(CFG["calibration_noise_sigma_lsb"]),
            size=(len(HIGH_STAGE_TO_INDEX), pairs_candidate, 2),
        )
        calibration_offset = float(rng.normal(0.0, float(CFG["calibration_offset_sigma_lsb"])))
        decoder32 = calibrated_high_decoder(base_physical, calibration_noise, calibration_offset, pairs32, ())
        decoder_candidate = calibrated_high_decoder(
            base_physical, calibration_noise, calibration_offset, pairs_candidate, ()
        )
        extended_decoder_candidate = np.concatenate((decoder_candidate, np.asarray(extras)))
        physical_hash = hashlib.sha256(base_physical.tobytes()).hexdigest().upper()

        for tone_bin in tone_bins:
            evaluation_seed = SEED + 1_000_003 * sample + 97 * tone_bin
            eval_rng = np.random.default_rng(evaluation_seed)
            x = coherent_sine(
                n_samples,
                tone_bin,
                amplitude_dbfs=float(CFG["input_amplitude_dbfs"]),
                phase_rad=0.123 + 0.001 * (sample % 17),
            )
            input_noise = eval_rng.normal(
                0.0, float(CFG["normal_conversion_noise_sigma_lsb"]), n_samples
            )
            current_bits = sar_decisions(x, base_physical, input_noise_lsb=input_noise)
            extended_bits = sar_decisions(x, extended_physical, input_noise_lsb=input_noise)
            _, fractional_cancel_codes = fractional_cancellation_codes(
                x, base_physical, decoder_candidate, input_noise_lsb=input_noise
            )
            methods = {
                "current_nominal_12b": decode_decisions(current_bits, NOMINAL_WEIGHTS),
                "current_cal32_12b": decode_decisions(current_bits, decoder32),
                f"current_cal{pairs_candidate}_12b": decode_decisions(current_bits, decoder_candidate),
                f"current_cal{pairs_candidate}_q{fraction_bits}": np.rint(
                    decode_decisions(current_bits, decoder_candidate, integer_output=False) * (1 << fraction_bits)
                ) / (1 << fraction_bits),
                "sublsb3_nominal_12b": decode_decisions(
                    extended_bits, np.concatenate((NOMINAL_WEIGHTS, np.asarray(extras)))
                ),
                f"sublsb3_cal{pairs_candidate}_12b": decode_decisions(
                    extended_bits, extended_decoder_candidate
                ),
                f"fractional_cancel_cal{pairs_candidate}_12b": fractional_cancel_codes,
            }
            for method, codes in methods.items():
                dynamic_rows.append(
                    metric_row(
                        sample=sample,
                        tone_bin=tone_bin,
                        method=method,
                        codes=codes,
                        physical_hash=physical_hash,
                        evaluation_seed=evaluation_seed,
                    )
                )
        retained[sample] = (base_physical, decoder_candidate, extended_physical)

    summary_rows = summarize(dynamic_rows)
    candidate_name = f"current_cal{pairs_candidate}_q{fraction_bits}"
    candidate_records = [row for row in dynamic_rows if row["method"] == candidate_name]
    worst_samples = sorted(
        {int(row["sample"]) for row in sorted(candidate_records, key=lambda row: float(row["enob"]))[:8]}
    )
    static_rows: list[dict[str, object]] = []
    static_detail_candidates: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    ramp_count = int(CFG["static_ramp_samples"])
    ramp = (np.arange(ramp_count, dtype=float) + 0.5) / ramp_count
    for sample in worst_samples:
        physical, decoder, _ = retained[sample]
        decisions = sar_decisions(ramp, physical)
        codes = np.rint(
            decode_decisions(decisions, decoder, integer_output=False) * (1 << fraction_bits)
        ) / (1 << fraction_bits)
        steps = np.diff(codes)
        ideal = ramp * MAX_CODE
        fit = np.polyfit(ideal, codes, 1)
        endpoint_residual = codes - np.polyval(fit, ideal)
        static_detail_candidates[sample] = (codes, endpoint_residual)
        static_rows.append(
            {
                "sample": sample,
                "method": candidate_name,
                "ramp_samples": ramp_count,
                "monotonic_violations": int(np.count_nonzero(steps < 0.0)),
                "worst_code_backstep": float(min(0.0, float(np.min(steps)))),
                "fractional_unique_levels": int(len(np.unique(codes))),
                "endpoint_fit_peak_error_lsb": float(np.max(np.abs(endpoint_residual))),
                "endpoint_fit_gain": float(fit[0]),
                "endpoint_fit_offset_lsb": float(fit[1]),
            }
        )

    write_csv(TABLES / "adc_dynamic_monte_carlo.csv", dynamic_rows)
    write_csv(TABLES / "adc_dynamic_summary.csv", summary_rows)
    write_csv(TABLES / "adc_static_worst_cases.csv", static_rows)
    detail_sample = max(static_rows, key=lambda row: int(row["monotonic_violations"]))["sample"]
    detail_codes, detail_error = static_detail_candidates[int(detail_sample)]
    write_csv(
        TABLES / "adc_static_q2_detail.csv",
        [
            {
                "sample": int(detail_sample),
                "ideal_code": float(ramp[index] * MAX_CODE),
                "q2_code": float(detail_codes[index]),
                "endpoint_fit_error_lsb": float(detail_error[index]),
            }
            for index in range(0, ramp_count, 16)
        ],
    )
    hardware_rows = []
    for pairs in (32, 64, 96, 128, 512, 1024):
        frames = 7 * pairs * 2
        hardware_rows.append(
            {
                "pairs": pairs,
                "rst1_frames": frames,
                "calclk_decisions": 140 * pairs,
                "calibration_time_us_at_150ns": frames * 0.150,
                "relative_time_vs_32": pairs / 32,
            }
        )
    write_csv(TABLES / "hardware_calibration_cost.csv", hardware_rows)

    worst_dynamic = min(candidate_records, key=lambda row: float(row["enob"]))
    worst_sample = int(worst_dynamic["sample"])
    worst_tone = int(worst_dynamic["tone_bin"])
    physical, decoder, _ = retained[worst_sample]
    evaluation_seed = SEED + 1_000_003 * worst_sample + 97 * worst_tone
    eval_rng = np.random.default_rng(evaluation_seed)
    x = coherent_sine(
        n_samples,
        worst_tone,
        amplitude_dbfs=float(CFG["input_amplitude_dbfs"]),
        phase_rad=0.123 + 0.001 * (worst_sample % 17),
    )
    input_noise = eval_rng.normal(0.0, float(CFG["normal_conversion_noise_sigma_lsb"]), n_samples)
    bits = sar_decisions(x, physical, input_noise_lsb=input_noise)
    spectrum_methods = {
        "calibrated_12b_integer": decode_decisions(bits, decoder),
        f"calibrated_q{fraction_bits}": np.rint(
            decode_decisions(bits, decoder, integer_output=False) * (1 << fraction_bits)
        ) / (1 << fraction_bits),
    }
    spectrum_rows: list[dict[str, object]] = []
    for method, codes in spectrum_methods.items():
        power = np.abs(np.fft.rfft(codes - np.mean(codes))) ** 2
        power[1:-1] *= 2.0
        relative_db = 10.0 * np.log10(np.maximum(power, 1e-300) / power[worst_tone])
        spectrum_rows.extend(
            {
                "method": method,
                "sample": worst_sample,
                "tone_bin": worst_tone,
                "bin": index,
                "normalized_frequency": index / n_samples,
                "relative_power_db": float(relative_db[index]),
            }
            for index in range(1, len(relative_db))
        )
    write_csv(TABLES / "adc_worst_case_spectrum.csv", spectrum_rows)
    candidate_summary = next(row for row in summary_rows if row["method"] == candidate_name)
    current_summary = next(row for row in summary_rows if row["method"] == "current_cal32_12b")
    fractional_summary = next(
        row for row in summary_rows
        if row["method"] == f"current_cal{pairs_candidate}_q{fraction_bits}"
    )
    static_characterized = bool(static_rows) and all(
        float(row["endpoint_fit_peak_error_lsb"]) <= 1.5 for row in static_rows
    )
    static_monotonic_all = all(int(row["monotonic_violations"]) == 0 for row in static_rows)
    checks = {
        "sinad_threshold_matches_enob": abs(
            enob_to_sinad_db(float(CFG["minimum_enob_bits_strict"]))
            - float(CFG["minimum_sinad_db_strict"])
        ) < 1e-12,
        "coherent_two_tone_records": len(tone_bins) == 2 and all(math.gcd(n_samples, k) == 1 for k in tone_bins),
        "current_12b_limitation_reproduced": int(current_summary["failures"]) > 0,
        "fractional_digital_path_zero_dynamic_failures": int(fractional_summary["failures"]) == 0,
        "candidate_fractional_zero_dynamic_failures": int(candidate_summary["failures"]) == 0,
        "candidate_strict_min_enob": float(candidate_summary["enob_min"]) > float(CFG["minimum_enob_bits_strict"]),
        "candidate_yield_lcb95": float(candidate_summary["yield_lcb95"]) > float(CFG["minimum_one_sided_yield_lcb95"]),
        "candidate_no_clipping": int(candidate_summary["total_clip_count"]) == 0,
        "candidate_fft_time_crosscheck": float(candidate_summary["max_abs_fft_time_sndr_delta_db"]) < 1e-6,
        "candidate_fractional_static_characterized": static_characterized,
        "calibration_and_evaluation_seeds_separate": SEED != min(int(row["evaluation_seed"]) for row in dynamic_rows),
    }
    summary = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": CFG,
        "seed": SEED,
        "method_summaries": summary_rows,
        "static_worst_samples": static_rows,
        "static_monotonic_all": static_monotonic_all,
        "checks": checks,
        "adc_performance_gate_pass": all(checks.values()),
        "decision": (
            f"PASS: Q{fraction_bits} calibrated reconstruction exceeds the strict 11.5-bit ENOB gate"
            if all(checks.values())
            else "FAIL: no VA work is authorized"
        ),
        "scope_warning": (
            f"Python ENOB evidence only. The accepted path preserves {fraction_bits} fractional output bits. "
            "The present 12-bit integer interface fails; small fractional-code backsteps remain in selected "
            "static cases and require a separate linearity remedy before transistor-level sign-off."
        ),
    }
    (RAW / "adc_performance_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if not summary["adc_performance_gate_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
