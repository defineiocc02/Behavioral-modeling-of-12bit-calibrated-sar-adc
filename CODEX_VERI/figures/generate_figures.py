from __future__ import annotations

import csv
from pathlib import Path
import sys

import numpy as np


PROJECT = Path(__file__).resolve().parents[1]
TABLES = PROJECT / "results" / "tables"
OUT = PROJECT / "results" / "figures"
FIGURA = Path(r"C:\Users\Administrator\.agents\skills\figura")
sys.path.insert(0, str(FIGURA / "scripts"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import pubstyle
import colors
import export


pubstyle.apply(venue="ieee")
LEGACY = "#D55E00"
CANDIDATE = "#0072B2"
PAPER = "#009E73"
NEUTRAL = "#1A1A1A"
GRID = "#D9D9D9"


def read_csv(name: str) -> list[dict[str, str]]:
    with (TABLES / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def panel_labels(axes: list[plt.Axes]) -> None:
    for ax, label in zip(axes, "abcdefghijklmnopqrstuvwxyz"):
        ax.text(-0.16, 1.04, f"({label})", transform=ax.transAxes,
                fontsize=9, fontweight="bold", ha="left", va="bottom")


def save(fig: plt.Figure, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    export.save(fig, stem, formats=("pdf", "svg", "png"), outdir=str(OUT))
    plt.close(fig)


def figure_legacy_replay() -> None:
    pairs = [row for row in read_csv("baseline_pair_replay.csv") if int(row["target_id"]) == 1]
    comparison = read_csv("algorithm_stage_comparison.csv")
    x = np.array([int(row["pair"]) for row in pairs])
    d_plus = np.array([float(row["d_plus"]) for row in pairs])
    d_minus_mag = -np.array([float(row["d_minus"]) for row in pairs])
    stages = [name for name, _ in (
        ("H1A", 65), ("H1R", 65), ("H2", 130), ("H4", 260),
        ("H8", 520), ("H16", 1040), ("H32", 2080)
    )]
    legacy = [float(row["error"]) for row in comparison if row["method"] == "legacy_empirical_replay"]
    candidate = [float(row["error"]) for row in comparison if row["method"] == "wall_signed_candidate_ideal"]

    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.55), constrained_layout=True,
                             gridspec_kw={"wspace": 0.32})
    axes[0].step(x, d_plus, where="mid", color=CANDIDATE, lw=1.25, label=r"$D_+$")
    axes[0].step(x, d_minus_mag, where="mid", color=LEGACY, lw=1.25, ls="--", label=r"$-D_-$")
    axes[0].scatter(x, d_plus, color=CANDIDATE, s=10, marker="o", zorder=3)
    axes[0].scatter(x, d_minus_mag, color=LEGACY, s=12, marker="x", zorder=3)
    axes[0].axhline(65, color=NEUTRAL, lw=0.8, ls=":")
    axes[0].set(xlabel="Pair index", ylabel="Directional magnitude (LSB)",
                xlim=(-0.8, 31.8), ylim=(64.75, 66.25))
    axes[0].set_yticks([65, 65.5, 66])
    axes[0].legend(loc="upper left", ncol=2)
    axes[0].grid(axis="y", color=GRID, lw=0.5, alpha=0.7)

    xi = np.arange(len(stages))
    axes[1].plot(xi, legacy, color=LEGACY, marker="s", ms=4, lw=1.4,
                 label="Historical legacy replay")
    axes[1].plot(xi, candidate, color=CANDIDATE, marker="o", ms=4, lw=1.4,
                 ls="--", label="Wall + signed candidate")
    axes[1].set_xticks(xi)
    axes[1].set_xticklabels(stages, rotation=25, ha="right")
    axes[1].set(xlabel="Calibration stage", ylabel="Weight error (LSB)", ylim=(-0.35, 8.0))
    axes[1].grid(axis="y", color=GRID, lw=0.5, alpha=0.7)
    axes[1].legend(loc="upper left")
    panel_labels(list(axes))
    save(fig, "fig01_legacy_bias_replay")


def figure_noise_scaling() -> None:
    rows = read_csv("noise_scaling.csv")
    n = np.array([int(row["pair_count"]) for row in rows], dtype=float)
    std = np.array([float(row["std"]) for row in rows])
    bias = np.array([float(row["bias"]) for row in rows])
    lo = np.array([float(row["ci_familywise95_low"]) for row in rows]) - 65.25
    hi = np.array([float(row["ci_familywise95_high"]) for row in rows]) - 65.25
    reference = std[0] / np.sqrt(n)
    slope = np.polyfit(np.log(n), np.log(std), 1)[0]

    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.55), constrained_layout=True,
                             gridspec_kw={"wspace": 0.34})
    axes[0].loglog(n, std, color=CANDIDATE, marker="o", ms=4, lw=1.4,
                   label=f"Monte Carlo (slope {slope:.3f})")
    axes[0].loglog(n, reference, color=NEUTRAL, ls="--", lw=1.0,
                   label=r"$N^{-1/2}$ reference")
    axes[0].set_xticks(n)
    axes[0].set_xticklabels([str(int(v)) for v in n])
    axes[0].set(xlabel="Directional pairs, $N$", ylabel="Estimator standard deviation (LSB)")
    axes[0].legend(loc="upper right")
    axes[0].grid(which="both", color=GRID, lw=0.45, alpha=0.65)

    axes[1].errorbar(n, bias, yerr=np.vstack((bias - lo, hi - bias)), color=PAPER,
                     marker="D", ms=4, lw=1.2, capsize=3, elinewidth=0.9)
    axes[1].axhline(0, color=NEUTRAL, lw=0.8, ls="--")
    axes[1].set_xscale("log", base=2)
    axes[1].set_xticks(n)
    axes[1].set_xticklabels([str(int(v)) for v in n])
    axes[1].set(xlabel="Directional pairs, $N$", ylabel="Bias, simultaneous 95% CI (LSB)")
    axes[1].grid(axis="y", color=GRID, lw=0.45, alpha=0.65)
    panel_labels(list(axes))
    save(fig, "fig02_noise_averaging")


def figure_algorithm_efficacy() -> None:
    rows = read_csv("algorithm_monte_carlo.csv")
    stage_order = ["H1C-A", "H1C-R", "H2C", "H4C", "H8C", "H16C", "H32C"]
    x = np.arange(len(stage_order))
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.55), constrained_layout=True,
                             gridspec_kw={"wspace": 0.33})
    styles = {
        "legacy_magnitude": (LEGACY, "s", "-", "Legacy magnitude"),
        "wall_signed_candidate": (CANDIDATE, "o", "--", "Wall + signed candidate"),
    }
    for method, (color, marker, ls, label) in styles.items():
        selected = {row["stage"]: row for row in rows if row["method"] == method}
        rmse = [float(selected[name]["rmse"]) for name in stage_order]
        bias = [float(selected[name]["bias"]) for name in stage_order]
        axes[0].semilogy(x, rmse, color=color, marker=marker, ls=ls, ms=4, lw=1.4, label=label)
        axes[1].plot(x, bias, color=color, marker=marker, ls=ls, ms=4, lw=1.4, label=label)
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels([s.replace("C-", "-") for s in stage_order], rotation=25, ha="right")
        ax.grid(axis="y", color=GRID, lw=0.45, alpha=0.65)
    axes[0].set(xlabel="Calibration stage", ylabel="RMSE (LSB)")
    axes[1].set(xlabel="Calibration stage", ylabel="Mean error (LSB)")
    axes[1].axhline(0, color=NEUTRAL, lw=0.8, ls=":")
    axes[0].legend(loc="upper left")
    axes[1].legend(loc="upper left")
    panel_labels(list(axes))
    save(fig, "fig03_algorithm_efficacy_mc")


def figure_offset_and_sensitivity() -> None:
    offset_rows = read_csv("offset_sweep.csv")
    sensitivity_rows = read_csv("centered_sensitivity_matrix.csv")
    offset = np.array([float(row["offset"]) for row in offset_rows])
    continuous = np.array([float(row["continuous_error"]) for row in offset_rows])
    quantized = np.array([float(row["quantized_error"]) for row in offset_rows])
    names = ["H1A", "H1R", "H2", "H4", "H8", "H16", "H32"]
    full_names = ["H1C-A", "H1C-R", "H2C", "H4C", "H8C", "H16C", "H32C"]
    matrix = np.zeros((7, 7))
    for row in sensitivity_rows:
        i = full_names.index(row["output_stage"])
        j = full_names.index(row["perturbed_stage"])
        matrix[i, j] = float(row["derivative"])

    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.75), constrained_layout=True,
                             gridspec_kw={"wspace": 0.32})
    axes[0].plot(offset, continuous, color=PAPER, lw=1.3, label="Continuous equation oracle")
    axes[0].step(offset, quantized, where="mid", color=CANDIDATE, lw=1.3, ls="--",
                 label="1-LSB signed quantizer")
    axes[0].axhline(0, color=NEUTRAL, lw=0.8, ls=":")
    axes[0].set(xlabel="Comparator offset (LSB)", ylabel="Single-pair estimation error (LSB)",
                ylim=(-0.62, 0.62))
    axes[0].legend(loc="lower right")
    axes[0].grid(axis="y", color=GRID, lw=0.45, alpha=0.65)

    norm = TwoSlopeNorm(vmin=-1.0, vcenter=0.0, vmax=1.0)
    im = axes[1].imshow(matrix, cmap="RdBu_r", norm=norm, aspect="equal")
    axes[1].set_xticks(range(7)); axes[1].set_yticks(range(7))
    axes[1].set_xticklabels(names, rotation=35, ha="right"); axes[1].set_yticklabels(names)
    axes[1].set(xlabel="Perturbed physical stage", ylabel="Estimated output stage")
    for i in range(7):
        for j in range(7):
            axes[1].text(j, i, f"{matrix[i,j]:.0f}", ha="center", va="center",
                         fontsize=6.5, color="white" if abs(matrix[i,j]) > 0.55 else "black")
    cbar = fig.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04)
    cbar.set_label(r"Sensitivity $\partial\hat W_i/\partial W_j$")
    cbar.outline.set_linewidth(0.5)
    panel_labels(list(axes))
    save(fig, "fig04_offset_and_sensitivity")


def figure_provenance_flow() -> None:
    fig, ax = plt.subplots(figsize=(6.8, 2.2), constrained_layout=True)
    ax.set_xlim(0, 12); ax.set_ylim(0, 3.2); ax.axis("off")

    def box(x: float, y: float, w: float, h: float, text: str, color: str) -> None:
        patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                               facecolor=color, edgecolor="none", alpha=0.95)
        ax.add_patch(patch)
        ax.text(x + w/2, y + h/2, text, ha="center", va="center", color="white", fontsize=7.5)

    def arrow(x1: float, y1: float, x2: float, y2: float, label: str = "") -> None:
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10,
                                     lw=1.0, color=NEUTRAL))
        if label:
            ax.text((x1+x2)/2, (y1+y2)/2 + 0.18, label, ha="center", fontsize=6.5)

    box(0.2, 1.75, 2.25, 0.9, "Huang paper\nEq. (4.17)-(4.19)", PAPER)
    box(0.2, 0.35, 2.25, 0.9, "Historical legacy log\n224 measured pairs", LEGACY)
    box(3.25, 1.05, 2.5, 1.0, "Python evidence layers\nkept strictly separate", "#6A5ACD")
    box(6.55, 1.05, 2.4, 1.0, "Wall + signed candidate\nboundary and MC tests", CANDIDATE)
    box(9.75, 1.05, 2.0, 1.0, "VA conformance\nfuture gate", "#777777")
    arrow(2.45, 2.2, 3.25, 1.75, "formula")
    arrow(2.45, 0.8, 3.25, 1.35, "replay")
    arrow(5.75, 1.55, 6.55, 1.55, "A/B")
    arrow(8.95, 1.55, 9.75, 1.55, "only after pass")
    ax.text(6.0, 2.85, "Evidence provenance and hard stage gate", ha="center",
            fontsize=9.5, fontweight="bold")
    save(fig, "fig05_evidence_provenance")


def figure_adc_enob_and_spectrum() -> None:
    rows = read_csv("adc_dynamic_monte_carlo.csv")
    spectrum = read_csv("adc_worst_case_spectrum.csv")
    order = [
        ("current_nominal_12b", "Nominal\ndecoder", LEGACY),
        ("current_cal32_12b", "32-pair\n12-bit", "#CC79A7"),
        ("current_cal128_12b", "128-pair\n12-bit", "#E69F00"),
        ("current_cal128_q2", "128-pair\nQ2", CANDIDATE),
        ("fractional_cancel_cal128_12b", "Fractional\ncancel", PAPER),
    ]
    datasets = [np.asarray([float(r["enob"]) for r in rows if r["method"] == key]) for key, _, _ in order]
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.8), constrained_layout=True,
                             gridspec_kw={"wspace": 0.3})
    bp = axes[0].boxplot(datasets, patch_artist=True, widths=0.62, showfliers=False,
                         whis=(1, 99), medianprops={"color": "white", "lw": 1.2})
    for patch, (_, _, color) in zip(bp["boxes"], order):
        patch.set_facecolor(color); patch.set_edgecolor(color); patch.set_alpha(0.9)
    for element in ("whiskers", "caps"):
        for artist in bp[element]: artist.set_color(NEUTRAL); artist.set_linewidth(0.7)
    axes[0].axhline(11.5, color="red", lw=1.0, ls="--", label="Acceptance: 11.5 bit")
    axes[0].set_xticks(range(1, len(order) + 1))
    axes[0].set_xticklabels([label for _, label, _ in order], fontsize=6.5)
    axes[0].set(ylabel="ENOB (bit)", ylim=(8.0, 11.8))
    axes[0].grid(axis="y", color=GRID, lw=0.45, alpha=0.7)
    axes[0].legend(loc="lower right")

    for method, label, color in (
        ("calibrated_12b_integer", "Calibrated 12-bit integer", LEGACY),
        ("calibrated_q2", "Calibrated Q2", CANDIDATE),
    ):
        selected = [r for r in spectrum if r["method"] == method]
        f = np.asarray([float(r["normalized_frequency"]) for r in selected])
        db = np.asarray([float(r["relative_power_db"]) for r in selected])
        axes[1].plot(f, np.maximum(db, -145), color=color, lw=0.65, label=label)
    axes[1].set(xlabel=r"Normalized frequency, $f/f_s$", ylabel="Relative power (dBc)",
                xlim=(0, 0.5), ylim=(-130, 5))
    axes[1].grid(color=GRID, lw=0.4, alpha=0.65)
    axes[1].legend(loc="lower left")
    panel_labels(list(axes))
    save(fig, "fig06_adc_enob_and_spectrum")


def figure_static_and_hardware_cost() -> None:
    detail = read_csv("adc_static_q2_detail.csv")
    cost = read_csv("hardware_calibration_cost.csv")
    ideal = np.asarray([float(r["ideal_code"]) for r in detail])
    error = np.asarray([float(r["endpoint_fit_error_lsb"]) for r in detail])
    pairs = np.asarray([int(r["pairs"]) for r in cost])
    time_us = np.asarray([float(r["calibration_time_us_at_150ns"]) for r in cost])

    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.65), constrained_layout=True,
                             gridspec_kw={"wspace": 0.34})
    axes[0].plot(ideal, error, color=CANDIDATE, lw=0.75)
    axes[0].axhline(0, color=NEUTRAL, lw=0.7, ls=":")
    axes[0].set(xlabel="Ideal output code", ylabel="Q2 endpoint-fit error (LSB)",
                xlim=(0, 4095), ylim=(-1.05, 1.05))
    axes[0].grid(axis="y", color=GRID, lw=0.45, alpha=0.7)

    colors_bar = [CANDIDATE if value == 128 else "#A8A8A8" for value in pairs]
    axes[1].bar(np.arange(len(pairs)), time_us, color=colors_bar, width=0.68)
    axes[1].set_xticks(np.arange(len(pairs)))
    axes[1].set_xticklabels([str(v) for v in pairs])
    axes[1].set_yscale("log")
    axes[1].set(xlabel="Calibration pairs per stage", ylabel="Startup calibration time (µs)")
    axes[1].grid(axis="y", which="both", color=GRID, lw=0.45, alpha=0.7)
    for i, value in enumerate(time_us):
        axes[1].text(i, value * 1.12, f"{value:.1f}", ha="center", va="bottom", fontsize=6)
    panel_labels(list(axes))
    save(fig, "fig07_static_and_hardware_cost")


def main() -> None:
    figure_legacy_replay()
    figure_noise_scaling()
    figure_algorithm_efficacy()
    figure_offset_and_sensitivity()
    figure_provenance_flow()
    figure_adc_enob_and_spectrum()
    figure_static_and_hardware_cost()


if __name__ == "__main__":
    main()
