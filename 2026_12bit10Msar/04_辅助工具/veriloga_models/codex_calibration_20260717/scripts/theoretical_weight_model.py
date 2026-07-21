from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np


def greedy_sar(inputs: np.ndarray, analog_weights: np.ndarray) -> np.ndarray:
    residual = np.asarray(inputs, dtype=float).copy()
    decisions = np.zeros((residual.size, analog_weights.size), dtype=int)
    for index, weight in enumerate(analog_weights):
        keep = residual >= weight
        decisions[:, index] = keep
        residual[keep] -= weight
    return decisions


def decode(
    decisions: np.ndarray,
    weights: np.ndarray,
    *,
    normalize_range: bool,
) -> np.ndarray:
    raw = decisions @ weights
    if normalize_range:
        raw = raw * 4095.0 / np.sum(weights)
    else:
        raw = raw - (np.sum(weights) - 4095.0) / 2.0
    return np.clip(np.rint(raw), 0, 4095).astype(int)


def fft_metrics(codes: np.ndarray, fundamental_bin: int) -> dict[str, float]:
    spectrum = np.fft.rfft(codes - np.mean(codes))
    power = np.abs(spectrum) ** 2
    power[0] = 0.0
    signal = power[fundamental_bin]
    noise_distortion = np.sum(power) - signal
    spur = np.max(np.delete(power[1:], fundamental_bin - 1))
    sndr = 10.0 * math.log10(signal / noise_distortion)
    return {
        "sndr_dbc": sndr,
        "sfdr_dbc": 10.0 * math.log10(signal / spur),
        "enob": (sndr - 1.76) / 6.02,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analytical non-binary SAR weight-reconstruction model.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--va", type=float, default=0.8, help="Differential input half-amplitude in volts.")
    parser.add_argument("--cal-c12", type=float, default=2049.875)
    parser.add_argument("--cal-c11", type=float, default=1025.875)
    parser.add_argument("--cal-c10", type=float, default=512.0)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    low_caps = np.asarray([24.0, 16.0, 10.0, 6.0, 4.0, 2.0, 1.0])
    bridge_attenuation = 1.0 / (1.0 + np.sum(low_caps))
    low_weights = 128.0 * bridge_attenuation * low_caps
    c12 = 128.0 * (16.054213 + 16.0365) / 2.0
    c11 = 128.0 * (8.054243 + 8.00545) / 2.0
    c10 = 128.0 * (4.01754 + 4.0) / 2.0
    analog_weights = np.asarray(
        [c12, c11, c10, 256.0, 256.0, 128.0, *low_weights, 1.0]
    )
    nominal_weights = np.asarray(
        [2048.0, 1024.0, 512.0, 256.0, 256.0, 128.0, 48.0, 32.0,
         20.0, 12.0, 8.0, 4.0, 2.0, 1.0]
    )
    calibrated_weights = nominal_weights.copy()
    # Defaults predict the split-deadband reconstruction.  Final report
    # generation overrides these values with the closed-loop log when needed.
    calibrated_weights[0] = args.cal_c12
    calibrated_weights[1] = args.cal_c11
    calibrated_weights[2] = args.cal_c10

    phase = 2.0 * np.pi * 59.0 * np.arange(128) / 128.0
    analog_range = float(np.sum(analog_weights))
    input_codes = analog_range / 2.0 * (
        1.0 + (args.va / 0.9) * np.sin(phase)
    )
    sine_decisions = greedy_sar(input_codes, analog_weights)
    nominal_codes = decode(sine_decisions, nominal_weights, normalize_range=True)
    calibrated_codes = decode(sine_decisions, calibrated_weights, normalize_range=True)
    nominal_offset_only_codes = decode(
        sine_decisions, nominal_weights, normalize_range=False
    )
    calibrated_offset_only_codes = decode(
        sine_decisions, calibrated_weights, normalize_range=False
    )

    dense_input = np.linspace(0.0, analog_range, 4096 * 16, endpoint=True)
    dense_decisions = greedy_sar(dense_input, analog_weights)
    dense_nominal = decode(dense_decisions, nominal_weights, normalize_range=True)
    dense_calibrated = decode(
        dense_decisions, calibrated_weights, normalize_range=True
    )
    dense_nominal_offset_only = decode(
        dense_decisions, nominal_weights, normalize_range=False
    )
    dense_calibrated_offset_only = decode(
        dense_decisions, calibrated_weights, normalize_range=False
    )
    nominal_diff = np.diff(dense_nominal)
    calibrated_diff = np.diff(dense_calibrated)

    # Omran et al. (TCSI 2016) report K_C=0.20%*sqrt(fF) for their
    # lateral-field set B and 0.14%*sqrt(fF) for vertical-field set A.
    # These values are process/geometry-specific context, not a TSMC18 model.
    unit_cap_ff = 4.0
    paper_sigma_unit_lateral = 0.0020 / math.sqrt(unit_cap_ff)
    paper_sigma_unit_vertical = 0.0014 / math.sqrt(unit_cap_ff)

    def array_weight_sigma(weight_lsb: float, units: int, sigma_unit: float) -> float:
        return weight_lsb * sigma_unit / math.sqrt(units)

    c12_sigma_lateral = array_weight_sigma(2048.0, 16, paper_sigma_unit_lateral)
    c11_sigma_lateral = array_weight_sigma(1024.0, 8, paper_sigma_unit_lateral)
    c10_sigma_lateral = array_weight_sigma(512.0, 4, paper_sigma_unit_lateral)
    c12_sigma_vertical = array_weight_sigma(2048.0, 16, paper_sigma_unit_vertical)
    c11_sigma_vertical = array_weight_sigma(1024.0, 8, paper_sigma_unit_vertical)
    c10_sigma_vertical = array_weight_sigma(512.0, 4, paper_sigma_unit_vertical)

    result = {
        "bridge_attenuation": bridge_attenuation,
        "input_half_amplitude_v": args.va,
        "analog_raw_range_lsb": analog_range,
        "analog_weights": analog_weights.tolist(),
        "nominal_weights": nominal_weights.tolist(),
        "calibrated_weights_q4_split_deadband": calibrated_weights.tolist(),
        "c12_nominal_error_lsb": float(analog_weights[0] - nominal_weights[0]),
        "c11_nominal_error_lsb": float(analog_weights[1] - nominal_weights[1]),
        "c10_nominal_error_lsb": float(analog_weights[2] - nominal_weights[2]),
        "omran_2016_context": {
            "scope_note": "0.18um measured MOM context; extrapolated to 4fF and not a foundry signoff model",
            "unit_cap_ff": unit_cap_ff,
            "kc_lateral_fraction_sqrt_ff": 0.0020,
            "kc_vertical_fraction_sqrt_ff": 0.0014,
            "unit_sigma_lateral_fraction": paper_sigma_unit_lateral,
            "unit_sigma_vertical_fraction": paper_sigma_unit_vertical,
            "c12_sigma_lsb_lateral": c12_sigma_lateral,
            "c11_sigma_lsb_lateral": c11_sigma_lateral,
            "c10_sigma_lsb_lateral": c10_sigma_lateral,
            "c12_sigma_lsb_vertical": c12_sigma_vertical,
            "c11_sigma_lsb_vertical": c11_sigma_vertical,
            "c10_sigma_lsb_vertical": c10_sigma_vertical,
            "c12_actual_error_sigma_lateral": float(
                (analog_weights[0] - nominal_weights[0]) / c12_sigma_lateral
            ),
            "c11_actual_error_sigma_lateral": float(
                (analog_weights[1] - nominal_weights[1]) / c11_sigma_lateral
            ),
            "c10_actual_error_sigma_lateral": float(
                (analog_weights[2] - nominal_weights[2]) / c10_sigma_lateral
            ),
        },
        "nominal_sine": fft_metrics(nominal_codes, 59),
        "calibrated_sine": fft_metrics(calibrated_codes, 59),
        "nominal_offset_only_sine": fft_metrics(nominal_offset_only_codes, 59),
        "calibrated_offset_only_sine": fft_metrics(
            calibrated_offset_only_codes, 59
        ),
        "nominal_nonmonotonic_steps": int(np.sum(nominal_diff < 0)),
        "calibrated_nonmonotonic_steps": int(np.sum(calibrated_diff < 0)),
        "nominal_largest_output_drop_codes": int(np.min(nominal_diff)),
        "calibrated_largest_output_drop_codes": int(np.min(calibrated_diff)),
    }
    (output_dir / "theory_metrics.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    with (output_dir / "theory_transfer.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            (
                "input_code",
                "nominal_output",
                "calibrated_output",
                "nominal_offset_only_output",
                "calibrated_offset_only_output",
            )
        )
        for values in zip(
            dense_input,
            dense_nominal,
            dense_calibrated,
            dense_nominal_offset_only,
            dense_calibrated_offset_only,
        ):
            writer.writerow(
                (
                    f"{values[0]:.9f}",
                    int(values[1]),
                    int(values[2]),
                    int(values[3]),
                    int(values[4]),
                )
            )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
