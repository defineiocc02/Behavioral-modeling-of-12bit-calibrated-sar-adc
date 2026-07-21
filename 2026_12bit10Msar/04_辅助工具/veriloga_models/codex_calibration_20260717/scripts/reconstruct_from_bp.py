from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import adctoolbox
import numpy as np

from analyze_adc_exports import load_ocean_wave, manual_fft_metrics, scalar_metrics


def load_weights(args: argparse.Namespace) -> tuple[int, np.ndarray]:
    if args.calibration_summary is not None:
        summary = json.loads(args.calibration_summary.read_text(encoding="utf-8"))
        weights = summary["weights"]
        return int(weights["frac_bits"]), np.asarray(weights["values_q"], dtype=np.int64)

    values = np.asarray([float(value) for value in args.weights_lsb.split(",")])
    if values.size != 14:
        raise ValueError(f"Expected 14 comma-separated weights, found {values.size}")
    q_scale = 1 << args.frac_bits
    return args.frac_bits, np.rint(values * q_scale).astype(np.int64)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruct DEC_CAL_PHY output from sampled BP nodes.")
    parser.add_argument("--bp-dir", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--calibration-summary", type=Path)
    source.add_argument("--weights-lsb")
    parser.add_argument("--frac-bits", type=int, default=6)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--nfft", type=int, default=128)
    parser.add_argument("--fs", type=float, default=10e6)
    parser.add_argument("--fin", type=float, default=59 / 128 * 10e6)
    args = parser.parse_args()

    times: np.ndarray | None = None
    bp_columns: list[np.ndarray] = []
    for index in range(14):
        time, value = load_ocean_wave(args.bp_dir / f"BP_{index}_.txt")
        if times is None:
            times = time
        elif time.size != times.size or not np.allclose(time, times, rtol=0.0, atol=1e-15):
            raise ValueError(f"BP<{index}> sampling grid does not match BP<0>")
        bp_columns.append((value > 0.9).astype(np.int64))

    assert times is not None
    if times.size < args.nfft:
        raise ValueError(f"Need {args.nfft} samples, found {times.size}")
    times = times[-args.nfft :]
    bp = np.column_stack(bp_columns)[-args.nfft :, :]
    frac_bits, weights_q = load_weights(args)
    if weights_q.size != 14:
        raise ValueError(f"Expected 14 Q weights, found {weights_q.size}")

    q_scale = 1 << frac_bits
    raw_bits = bp[:, ::-1]
    raw_sum_q = raw_bits @ weights_q
    redundancy_q = int(np.sum(weights_q) - 4095 * q_scale)
    if redundancy_q >= 0:
        offset_q = (redundancy_q + 1) // 2
    else:
        offset_q = math.trunc((redundancy_q - 1) / 2)
    scaled_code = (raw_sum_q - offset_q) / q_scale
    codes = np.trunc(scaled_code + 0.5).astype(int)
    codes = np.clip(codes, 0, 4095)

    coherent_fin, coherent_bin = adctoolbox.find_coherent_frequency(
        args.fs, args.fin, args.nfft, force_odd=True
    )
    if abs(coherent_fin - args.fin) > 1e-6:
        raise ValueError(f"Input tone is not coherent: requested {args.fin}, nearest {coherent_fin}")
    toolbox = adctoolbox.analyze_spectrum(
        codes,
        fs=args.fs,
        osr=1,
        max_scale_range=(0, 4095),
        win_type="boxcar",
        side_bin=0,
        max_harmonic=5,
        create_plot=False,
    )
    result = {
        "nfft": args.nfft,
        "fs_hz": args.fs,
        "fin_hz": args.fin,
        "coherent_bin": coherent_bin,
        "frac_bits": frac_bits,
        "weights_q": weights_q.tolist(),
        "weights_lsb": (weights_q / q_scale).tolist(),
        "redundancy_offset_lsb": offset_q / q_scale,
        "code_min": int(np.min(codes)),
        "code_max": int(np.max(codes)),
        "adctoolbox": scalar_metrics(toolbox),
        "manual_crosscheck": manual_fft_metrics(codes, args.fs, coherent_bin),
    }

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "samples.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("index", "time_s", "code", "raw_sum_q"))
        for index, (time, code, raw_sum) in enumerate(zip(times, codes, raw_sum_q)):
            writer.writerow((index, f"{time:.12e}", int(code), int(raw_sum)))
    (output_dir / "metrics.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
