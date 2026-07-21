from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


FIGURA_SCRIPTS = Path(r"C:\Users\Administrator\.agents\skills\figura\scripts")
sys.path.insert(0, str(FIGURA_SCRIPTS))
import colors  # noqa: E402
import export  # noqa: E402
import pubstyle  # noqa: E402


TARGET_NAMES = ["C12", "C11", "C10", "C9", "CR", "C8"]
NOMINAL = np.asarray([2048.0, 1024.0, 512.0, 256.0, 256.0, 128.0])
ANALOG = np.asarray([2053.805632, 1027.820352, 513.12256, 256.0, 256.0, 128.0])


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        key: np.asarray([float(row[key]) for row in rows])
        for key in rows[0]
    }


def metric(path: Path, key: str) -> float:
    data = json.loads(path.read_text(encoding="utf-8"))
    return float(data["manual_crosscheck"][key])


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the publication result figure for CDAC calibration.")
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    project = args.project.resolve()

    theory = load_csv(project / "results" / "theory_latest_890m_norm" / "theory_transfer.csv")
    bypass_dir = project / "results" / "full_adc_latest_bypass_890m_norm_nf100k_matched_cx" / "analysis"
    calibrated_dir = project / "results" / "full_adc_latest_frame_cal_890m_norm_nf100k_matched_cx" / "analysis"
    bypass_spectrum = load_csv(bypass_dir / "spectrum.csv")
    calibrated_spectrum = load_csv(calibrated_dir / "spectrum.csv")
    cal_log = json.loads(
        (
            project
            / "results"
            / "full_adc_latest_frame_cal_890m_norm_nf100k_matched_cx"
            / "calibration_summary.json"
        ).read_text(encoding="utf-8")
    )
    weights = np.asarray(cal_log["weights"]["values_lsb"][:6])

    pubstyle.apply(venue="ieee")
    colors.apply_cycle()
    palette = colors.categorical()
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.2), constrained_layout=True)

    ax = axes[0, 0]
    x = theory["input_code"]
    calibrated = theory["calibrated_output"]
    offset_only = theory["calibrated_offset_only_output"]
    ideal = x * 4095.0 / x[-1]
    stride = 64
    ax.plot(x[::stride], ideal[::stride], color="0.45", linewidth=0.8, label="Ideal 12-bit map")
    ax.plot(x[::stride], offset_only[::stride], color=palette[1], label="Offset only")
    ax.plot(
        x[::stride],
        calibrated[::stride],
        color=palette[0],
        linestyle="--",
        label="Range normalized",
    )
    ax.set(
        xlabel="Physical non-binary input (raw LSB)",
        ylabel="Output code",
        xlim=(0, x[-1]),
        ylim=(-100, 4195),
        title="(a) Full-scale output mapping",
    )
    ax.legend(frameon=False, loc="upper left")

    ax = axes[0, 1]
    for spectrum, label, color, linestyle in (
        (bypass_spectrum, "Calibration bypassed", palette[1], "-"),
        (calibrated_spectrum, "Foreground calibrated", palette[0], "--"),
    ):
        ax.plot(spectrum["frequency_hz"] / 1e6, spectrum["magnitude_dbc"], label=label, color=color, linestyle=linestyle)
    ax.set(xlabel="Frequency (MHz)", ylabel="Magnitude (dBc)", ylim=(-120, 5), title="(b) 128-point coherent FFT")
    ax.legend(frameon=False, loc="lower left")

    ax = axes[1, 0]
    index = np.arange(len(TARGET_NAMES))
    width = 0.25
    ax.bar(index - width, ANALOG - NOMINAL, width, color=palette[2], label="Netlist physical")
    ax.bar(index, weights - NOMINAL, width, color=palette[0], label="Measured decoder")
    ax.bar(index + width, weights - ANALOG, width, color=palette[1], label="Residual")
    ax.axhline(0, color="0.35", linewidth=0.7)
    ax.set_xticks(index, TARGET_NAMES)
    ax.set(ylabel="Weight error (LSB)", title="(c) High-weight reconstruction")
    ax.legend(frameon=False, loc="best")

    ax = axes[1, 1]
    keys = ["sndr_dbc", "sfdr_dbc"]
    bypass_values = [metric(bypass_dir / "metrics.json", key) for key in keys]
    calibrated_values = [metric(calibrated_dir / "metrics.json", key) for key in keys]
    xbar = np.arange(2)
    ax.bar(xbar - 0.18, bypass_values, 0.36, color=palette[1], label="Bypassed")
    bars = ax.bar(xbar + 0.18, calibrated_values, 0.36, color=palette[0], label="Calibrated")
    for bars_set in (ax.containers[-2], bars):
        ax.bar_label(bars_set, fmt="%.1f", padding=2, fontsize=7)
    ax.set_xticks(xbar, ["SNDR", "SFDR"])
    ax.set(ylabel="Dynamic metric (dB)", ylim=(0, max(calibrated_values + bypass_values) + 12), title="(d) Full transistor-level result")
    ax.legend(frameon=False, loc="upper left")

    export.save(
        fig,
        "fig_fullscale_calibration_results",
        formats=("pdf", "svg", "png"),
        outdir=str(project / "figures"),
    )


if __name__ == "__main__":
    main()
