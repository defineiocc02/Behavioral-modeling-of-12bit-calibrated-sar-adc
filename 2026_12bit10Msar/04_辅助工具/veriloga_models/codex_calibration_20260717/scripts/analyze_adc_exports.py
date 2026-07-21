from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path

import adctoolbox
import numpy as np


NUMBER_LINE = re.compile(
    r"^\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\s+"
    r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\s*$"
)


def load_ocean_wave(path: Path) -> tuple[np.ndarray, np.ndarray]:
    time: list[float] = []
    value: list[float] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = NUMBER_LINE.match(line)
        if match:
            time.append(float(match.group(1)))
            value.append(float(match.group(2)))
    if not time:
        raise ValueError(f"No waveform samples parsed from {path}")
    return np.asarray(time), np.asarray(value)


def rising_edges(time: np.ndarray, value: np.ndarray, threshold: float) -> np.ndarray:
    indices = np.flatnonzero((value[:-1] < threshold) & (value[1:] >= threshold))
    fraction = (threshold - value[indices]) / (value[indices + 1] - value[indices])
    return time[indices] + fraction * (time[indices + 1] - time[indices])


def manual_fft_metrics(data: np.ndarray, fs: float, fundamental_bin: int) -> dict[str, float | int]:
    centered = np.asarray(data, dtype=float) - np.mean(data)
    spectrum = np.fft.rfft(centered)
    power = np.abs(spectrum) ** 2
    power[0] = 0.0
    signal_power = power[fundamental_bin]
    noise_dist_power = np.sum(power) - signal_power

    harmonic_bins: set[int] = set()
    n = len(centered)
    for order in range(2, 6):
        raw_bin = (order * fundamental_bin) % n
        folded_bin = raw_bin if raw_bin <= n // 2 else n - raw_bin
        if folded_bin not in (0, fundamental_bin):
            harmonic_bins.add(folded_bin)
    harmonic_power = sum(power[index] for index in harmonic_bins)
    noise_power = max(noise_dist_power - harmonic_power, np.finfo(float).tiny)

    spur_power = np.max(np.delete(power[1:], fundamental_bin - 1))
    return {
        "fundamental_bin": fundamental_bin,
        "sndr_dbc": 10.0 * math.log10(signal_power / noise_dist_power),
        "snr_dbc": 10.0 * math.log10(signal_power / noise_power),
        "sfdr_dbc": 10.0 * math.log10(signal_power / spur_power),
        "thd_dbc": 10.0 * math.log10(max(harmonic_power, np.finfo(float).tiny) / signal_power),
        "enob": (10.0 * math.log10(signal_power / noise_dist_power) - 1.76) / 6.02,
    }


def normalized_spectrum(data: np.ndarray, fs: float, fundamental_bin: int) -> tuple[np.ndarray, np.ndarray]:
    centered = np.asarray(data, dtype=float) - np.mean(data)
    spectrum = np.fft.rfft(centered)
    magnitude = np.abs(spectrum)
    reference = max(magnitude[fundamental_bin], np.finfo(float).tiny)
    dbc = 20.0 * np.log10(np.maximum(magnitude / reference, np.finfo(float).tiny))
    frequency = np.fft.rfftfreq(centered.size, d=1.0 / fs)
    return frequency, dbc


def scalar_metrics(metrics: dict) -> dict[str, float | int | str]:
    result: dict[str, float | int | str] = {}
    for key, value in metrics.items():
        if isinstance(value, (str, int, float, np.integer, np.floating)):
            result[key] = value.item() if isinstance(value, (np.integer, np.floating)) else value
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Sample ADC OCEAN exports and calculate coherent FFT metrics.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sout", type=Path)
    parser.add_argument(
        "--sampled-out",
        action="store_true",
        help="Treat OUT input as values already resampled at the desired SOUT+delay times.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--nfft", type=int, default=128)
    parser.add_argument("--fs", type=float, default=10e6)
    parser.add_argument("--fin", type=float, default=59 / 128 * 10e6)
    parser.add_argument("--sample-delay", type=float, default=0.5e-9)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    out_t, out_v = load_ocean_wave(args.out.resolve())
    if args.sampled_out:
        sample_times = out_t
        sample_values = out_v
    else:
        if args.sout is None:
            parser.error("--sout is required unless --sampled-out is used")
        sout_t, sout_v = load_ocean_wave(args.sout.resolve())
        edges = rising_edges(sout_t, sout_v, 0.9)
        sample_times = edges + args.sample_delay
        sample_values = np.interp(sample_times, out_t, out_v)
    if sample_values.size < args.nfft:
        raise ValueError(f"Need {args.nfft} conversion samples, found {sample_values.size}")

    sample_times = sample_times[-args.nfft :]
    sample_values = sample_values[-args.nfft :]
    codes = np.rint(sample_values * 2048.0 / 1.8).astype(int)
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
    manual = manual_fft_metrics(codes, args.fs, coherent_bin)
    spectrum_frequency, spectrum_dbc = normalized_spectrum(codes, args.fs, coherent_bin)
    result = {
        "nfft": args.nfft,
        "fs_hz": args.fs,
        "fin_hz": args.fin,
        "coherent_bin": coherent_bin,
        "sample_time_start_s": float(sample_times[0]),
        "sample_time_stop_s": float(sample_times[-1]),
        "code_min": int(np.min(codes)),
        "code_max": int(np.max(codes)),
        "adctoolbox": scalar_metrics(toolbox),
        "manual_crosscheck": manual,
    }

    with (output_dir / "samples.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("index", "time_s", "out_v", "code"))
        for index, (time_value, out_value, code) in enumerate(zip(sample_times, sample_values, codes)):
            writer.writerow((index, f"{time_value:.12e}", f"{out_value:.12e}", int(code)))
    with (output_dir / "spectrum.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("bin", "frequency_hz", "magnitude_dbc"))
        for index, (frequency, magnitude) in enumerate(zip(spectrum_frequency, spectrum_dbc)):
            writer.writerow((index, f"{frequency:.12e}", f"{magnitude:.9f}"))
    (output_dir / "metrics.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
