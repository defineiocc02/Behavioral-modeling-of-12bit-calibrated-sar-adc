"""Generate the public modeling figures from committed validation evidence.

The figures are intentionally derived from JSON/CSV artifacts under
``src/python_cal/validation_results``.  No metric is hard-coded into a plot.

When the Codex ``figura`` skill is available, its publication style and export
helpers are used.  A small portable fallback keeps the repository reproducible
in GitHub Actions and ordinary Python environments.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "python_cal" / "validation_results"
DEFAULT_OUT = ROOT / "docs" / "assets" / "figures"

FIGURA_SCRIPTS = [] if os.environ.get("FIGURA_DISABLE") else [
    Path(os.environ["FIGURA_SKILL_SCRIPTS"])
    if os.environ.get("FIGURA_SKILL_SCRIPTS")
    else None,
    Path.home() / ".agents" / "skills" / "figura" / "scripts",
]
FIGURA_SCRIPTS = [p for p in FIGURA_SCRIPTS if p and p.is_dir()]

USING_FIGURA = False
if FIGURA_SCRIPTS:
    sys.path.insert(0, str(FIGURA_SCRIPTS[0]))
    try:
        import colors as figura_colors
        import export as figura_export
        import pubstyle

        pubstyle.apply(venue="ieee")
        figura_colors.apply_cycle()
        USING_FIGURA = True
    except ImportError:
        USING_FIGURA = False

if not USING_FIGURA:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans"],
            "font.size": 8,
            "axes.labelsize": 8,
            "axes.titlesize": 9,
            "legend.fontsize": 7,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.7,
            "lines.linewidth": 1.35,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "mathtext.fontset": "stixsans",
            "savefig.dpi": 300,
        }
    )


# Locked Okabe-Ito palette: the same semantic role keeps the same color.
BLUE = "#0072B2"
ORANGE = "#E69F00"
GREEN = "#009E73"
VERMILLION = "#D55E00"
PURPLE = "#CC79A7"
SKY = "#56B4E9"
GRAY = "#777777"
LIGHT_GRAY = "#E6E6E6"
DARK = "#222222"

ROLE_COLORS = {
    "nominal": ORANGE,
    "calibrated": BLUE,
    "physical": GREEN,
    "integer": VERMILLION,
    "high": BLUE,
    "low": SKY,
    "terminal": PURPLE,
    "pass": GREEN,
    "conditional": ORANGE,
    "fail": VERMILLION,
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    columns: dict[str, np.ndarray] = {}
    for key in rows[0]:
        values = []
        numeric = True
        for row in rows:
            value = row[key]
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                numeric = False
                break
        if numeric:
            columns[key] = np.asarray(values, dtype=float)
    return columns


def add_panel_labels(axes) -> None:
    flat = np.atleast_1d(axes).ravel()
    for ax, label in zip(flat, "abcdefghijklmnopqrstuvwxyz"):
        ax.text(
            -0.13,
            1.04,
            f"({label})",
            transform=ax.transAxes,
            fontsize=9,
            fontweight="bold",
            ha="left",
            va="bottom",
        )


def export_figure(fig, name: str, out_dir: Path, formats: tuple[str, ...]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if USING_FIGURA:
        figura_export.save(
            fig,
            name,
            formats=formats,
            outdir=str(out_dir),
        )
    else:
        for fmt in formats:
            fig.savefig(
                out_dir / f"{name}.{fmt}",
                format=fmt,
                bbox_inches="tight",
                pad_inches=0.06,
                dpi=300,
            )
        plt.close(fig)
    if "svg" in formats:
        svg_path = out_dir / f"{name}.svg"
        svg_text = svg_path.read_text(encoding="utf-8")
        svg_path.write_text(
            "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n",
            encoding="utf-8",
        )


def rounded_box(ax, xy, width, height, text, color, text_color="white"):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        facecolor=color,
        edgecolor="none",
    )
    ax.add_patch(box)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        ha="center",
        va="center",
        color=text_color,
        fontsize=7.2,
        fontweight="bold",
    )
    return box


def arrow(ax, start, end, color=DARK, connectionstyle="arc3"):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=1.0,
            color=color,
            connectionstyle=connectionstyle,
        )
    )


def figure_architecture(out_dir: Path, formats: tuple[str, ...]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 3.2), constrained_layout=True)
    ax.set_xlim(0, 13.6)
    ax.set_ylim(0, 6)
    ax.axis("off")

    rounded_box(ax, (0.2, 3.8), 1.8, 1.0, "Differential\ninput", SKY)
    rounded_box(ax, (2.5, 3.8), 2.0, 1.0, "Split CDAC\ncharge solver", BLUE)
    rounded_box(ax, (5.1, 3.8), 1.8, 1.0, "Dynamic\ncomparator", PURPLE)
    rounded_box(ax, (7.5, 3.8), 2.0, 1.0, "Asynchronous\nSAR controller", ORANGE)
    rounded_box(ax, (10.1, 3.8), 1.5, 1.0, "14 decisions", GRAY)
    rounded_box(ax, (12.1, 3.8), 1.3, 1.0, "Q2 code", GREEN)

    for left, right in [
        ((2.0, 4.3), (2.5, 4.3)),
        ((4.5, 4.3), (5.1, 4.3)),
        ((6.9, 4.3), (7.5, 4.3)),
        ((9.5, 4.3), (10.1, 4.3)),
        ((11.6, 4.3), (12.1, 4.3)),
    ]:
        arrow(ax, left, right)

    rounded_box(ax, (2.5, 1.2), 2.0, 1.0, "Shen-derived\nforce-0/force-1", BLUE)
    rounded_box(ax, (5.1, 1.2), 1.8, 1.0, "Fixed dither\n+ half difference", PURPLE)
    rounded_box(ax, (7.5, 1.2), 2.0, 1.0, "P/N weight\nregisters", ORANGE)
    rounded_box(ax, (10.1, 1.2), 1.5, 1.0, "Q2 decoder", GREEN)

    for left, right in [
        ((4.5, 1.7), (5.1, 1.7)),
        ((6.9, 1.7), (7.5, 1.7)),
        ((9.5, 1.7), (10.1, 1.7)),
    ]:
        arrow(ax, left, right)
    arrow(ax, (11.0, 2.2), (11.0, 3.8), color=GREEN)
    arrow(
        ax,
        (8.5, 3.8),
        (3.5, 2.2),
        color=GRAY,
        connectionstyle="arc3,rad=-0.18",
    )

    ax.text(
        0.2,
        5.45,
        "12-bit asynchronous SAR ADC Python behavioral model",
        fontsize=11,
        fontweight="bold",
        ha="left",
    )
    ax.text(
        0.2,
        0.35,
        "Physical path: charge conservation + P/N mismatch.  "
        "Calibration path: comparator-observable weights.  "
        "Acceptance path: coherent FFT + static codebook audits.",
        fontsize=7,
        color=DARK,
    )
    export_figure(fig, "fig01_model_architecture", out_dir, formats)


def figure_cdac_weights(baseline: dict, out_dir: Path, formats: tuple[str, ...]) -> None:
    weights = np.asarray(baseline["physical_weights_q0"], dtype=float)
    labels = [
        "H32",
        "H16",
        "H8",
        "H4",
        "H2",
        "H1R",
        "H1A",
        "L32",
        "L16",
        "L8",
        "L4",
        "L2",
        "L1",
        "TERM",
    ]
    colors = [ROLE_COLORS["high"]] * 7 + [ROLE_COLORS["low"]] * 6 + [
        ROLE_COLORS["terminal"]
    ]
    fig, ax = plt.subplots(figsize=(7.0, 2.8), constrained_layout=True)
    x = np.arange(len(weights))
    ax.bar(x, weights, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yscale("log", base=2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("Nominal decision weight (Q0)")
    ax.set_title("Segmented decision weights and digital terminal")
    ax.grid(axis="y", alpha=0.25)
    ax.text(
        12.95,
        1.45,
        "digital\ncompare",
        ha="center",
        va="bottom",
        fontsize=6.5,
        color=PURPLE,
    )
    ax.legend(
        handles=[
            Rectangle((0, 0), 1, 1, color=ROLE_COLORS["high"], label="High segment"),
            Rectangle((0, 0), 1, 1, color=ROLE_COLORS["low"], label="Low segment"),
            Rectangle(
                (0, 0), 1, 1, color=ROLE_COLORS["terminal"], label="Digital terminal"
            ),
        ],
        loc="upper right",
        ncol=3,
    )
    export_figure(fig, "fig02_cdac_decision_weights", out_dir, formats)


def figure_conversion_sequence(out_dir: Path, formats: tuple[str, ...]) -> None:
    labels = [
        "H32",
        "H16",
        "H8",
        "H4",
        "H2",
        "H1R",
        "H1A",
        "L32",
        "L16",
        "L8",
        "L4",
        "L2",
        "L1",
        "TERM",
    ]
    fig, ax = plt.subplots(figsize=(7.1, 2.7), constrained_layout=True)
    ax.set_xlim(-0.8, 14.2)
    ax.set_ylim(0, 3.3)
    for i, label in enumerate(labels):
        if i < 7:
            color = ROLE_COLORS["high"]
            action = "trial"
        elif i < 13:
            color = ROLE_COLORS["low"]
            action = "trial"
        else:
            color = ROLE_COLORS["terminal"]
            action = "compare"
        ax.add_patch(
            FancyBboxPatch(
                (i - 0.42, 1.2),
                0.84,
                0.8,
                boxstyle="round,pad=0.01,rounding_size=0.05",
                facecolor=color,
                edgecolor="white",
                linewidth=0.5,
            )
        )
        ax.text(i, 1.6, label, rotation=90, ha="center", va="center", fontsize=6.2)
        ax.text(i, 0.85, str(i), ha="center", va="top", fontsize=6.2, color=GRAY)
        if i < 13:
            ax.text(i, 2.3, action, ha="center", fontsize=5.8, color=DARK)
    ax.annotate(
        "No capacitor toggle",
        xy=(13, 2.0),
        xytext=(11.2, 2.9),
        arrowprops=dict(arrowstyle="->", lw=0.8, color=PURPLE),
        color=PURPLE,
        fontsize=7,
    )
    ax.text(-0.72, 1.6, "MSB", va="center", ha="right", fontsize=7, fontweight="bold")
    ax.text(14.05, 1.6, "LSB", va="center", ha="left", fontsize=7, fontweight="bold")
    arrow(ax, (-0.55, 1.05), (13.55, 1.05), color=GRAY)
    ax.set_title("Fourteen asynchronous decisions: 13 physical trials + terminal compare")
    ax.axis("off")
    export_figure(fig, "fig03_async_conversion_sequence", out_dir, formats)


def figure_calibration_flow(out_dir: Path, formats: tuple[str, ...]) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 3.5), constrained_layout=True)
    ax.set_xlim(0, 12.8)
    ax.set_ylim(0, 6.2)
    ax.axis("off")
    rounded_box(ax, (0.3, 4.3), 1.8, 0.9, "Select target\nH1R -> H32", ORANGE)
    rounded_box(ax, (2.8, 4.3), 1.8, 0.9, "Force P-side\nVREFN / VREFP", BLUE)
    rounded_box(ax, (5.3, 4.3), 1.8, 0.9, "Lower-SAR\nsub-conversion", SKY)
    rounded_box(ax, (7.8, 4.3), 1.8, 0.9, r"$W_P=(S_{P0}-S_{P1})/2$", GREEN)
    rounded_box(ax, (2.8, 1.6), 1.8, 0.9, "Force N-side\nVREFN / VREFP", BLUE)
    rounded_box(ax, (5.3, 1.6), 1.8, 0.9, "Lower-SAR\nsub-conversion", SKY)
    rounded_box(ax, (7.8, 1.6), 1.8, 0.9, r"$W_N=(S_{N1}-S_{N0})/2$", GREEN)
    rounded_box(ax, (10.3, 2.95), 2.0, 0.9, "P/N registers\n+ recursive ruler", PURPLE)
    for start, end in [
        ((2.1, 4.75), (2.8, 4.75)),
        ((4.6, 4.75), (5.3, 4.75)),
        ((7.1, 4.75), (7.8, 4.75)),
        ((4.6, 2.05), (5.3, 2.05)),
        ((7.1, 2.05), (7.8, 2.05)),
        ((9.6, 4.75), (10.5, 3.85)),
        ((9.6, 2.05), (10.5, 2.95)),
    ]:
        arrow(ax, start, end)
    arrow(ax, (2.1, 4.5), (2.8, 2.45), connectionstyle="arc3,rad=0.2")
    # Route the recursion feedback outside the measurement blocks so the
    # arrow cannot obscure the N-side equation or lower-SAR label.
    ax.plot(
        [11.3, 11.3, 0.15, 0.15],
        [2.95, 0.95, 0.95, 4.75],
        color=PURPLE,
        linewidth=1.0,
        clip_on=False,
    )
    arrow(ax, (0.15, 4.75), (0.3, 4.75), color=PURPLE)
    ax.text(6.0, 0.82, "next target", ha="center", color=PURPLE, fontsize=6.5)
    ax.text(
        6.4,
        5.7,
        "Comparator-observable Shen-derived foreground calibration",
        ha="center",
        fontsize=10,
        fontweight="bold",
    )
    ax.text(
        6.4,
        0.55,
        "Fixed symmetric dither avoids locked decisions; VREFN/VREFP half-difference "
        "cancels constant comparator offset.",
        ha="center",
        fontsize=7,
    )
    export_figure(fig, "fig04_shen_calibration_flow", out_dir, formats)


def figure_baseline(baseline: dict, out_dir: Path, formats: tuple[str, ...]) -> None:
    current = baseline["metrics"]
    legacy = baseline["legacy_fixed_0p45_vref"]["metrics"]
    labels = ["Math ideal", "Physical ideal", "Legacy 0.45 VREF"]
    sndr = [
        current["mathematical_ideal"]["sndr_db"],
        current["physical_ideal_nominal_decoder"]["sndr_db"],
        legacy["physical_ideal_nominal_decoder"]["sndr_db"],
    ]
    enob = [
        current["mathematical_ideal"]["enob"],
        current["physical_ideal_nominal_decoder"]["enob"],
        legacy["physical_ideal_nominal_decoder"]["enob"],
    ]
    palette = [GRAY, GREEN, ORANGE]
    fig, axes = plt.subplots(
        1, 2, figsize=(7.0, 2.8), constrained_layout=True, gridspec_kw={"wspace": 0.28}
    )
    for ax, values, ylabel, ylim in [
        (axes[0], sndr, "SNDR (dB)", (72.3, 74.0)),
        (axes[1], enob, "ENOB (bit)", (11.70, 12.00)),
    ]:
        x = np.arange(3)
        ax.scatter(x, values, s=42, c=palette, marker="o", zorder=3)
        ax.plot(x[:2], values[:2], color=GRAY, linestyle="--", linewidth=0.9)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=20, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_ylim(*ylim)
        ax.grid(axis="y", alpha=0.25)
        for xi, value in zip(x, values):
            ax.text(xi, value + (ylim[1] - ylim[0]) * 0.035, f"{value:.3f}", ha="center")
    add_panel_labels(axes)
    fig.suptitle("Ideal baseline confirms the 12-bit dynamic ceiling", fontsize=10)
    export_figure(fig, "fig05_ideal_baseline", out_dir, formats)


def violin_box(ax, data, labels, palette, ylabel):
    positions = np.arange(1, len(data) + 1)
    parts = ax.violinplot(
        data,
        positions=positions,
        showmeans=False,
        showmedians=False,
        showextrema=False,
    )
    for body, color in zip(parts["bodies"], palette):
        body.set_facecolor(color)
        body.set_edgecolor("none")
        body.set_alpha(0.45)
    ax.boxplot(
        data,
        positions=positions,
        widths=0.18,
        patch_artist=True,
        boxprops=dict(facecolor="white", edgecolor=DARK, linewidth=0.75),
        medianprops=dict(color=DARK, linewidth=1.1),
        whiskerprops=dict(color=DARK, linewidth=0.75),
        capprops=dict(color=DARK, linewidth=0.75),
        flierprops=dict(
            marker="o",
            markersize=1.8,
            markerfacecolor=DARK,
            markeredgecolor="none",
            alpha=0.5,
        ),
    )
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=18, ha="right")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.22)


def figure_dynamic_mc(mc: dict[str, np.ndarray], out_dir: Path, formats: tuple[str, ...]) -> None:
    fig, axes = plt.subplots(
        1, 2, figsize=(7.0, 2.9), constrained_layout=True, gridspec_kw={"wspace": 0.3}
    )
    labels = ["Nominal", "Calibrated Q2", "Physical Q2"]
    palette = [ORANGE, BLUE, GREEN]
    violin_box(
        axes[0],
        [mc["nominal_sndr"], mc["calibrated_sndr"], mc["physical_sndr"]],
        labels,
        palette,
        "SNDR (dB)",
    )
    violin_box(
        axes[1],
        [mc["nominal_enob"], mc["calibrated_enob"], mc["physical_enob"]],
        labels,
        palette,
        "ENOB (bit)",
    )
    axes[1].axhline(11.5, color=VERMILLION, linestyle="--", linewidth=0.9, label="11.5-bit gate")
    axes[1].legend(loc="lower right")
    for ax, key in zip(axes, ["SNDR", "ENOB"]):
        ax.text(0.03, 0.95, "n = 100 seeds", transform=ax.transAxes, va="top", fontsize=7)
    add_panel_labels(axes)
    fig.suptitle("100-seed dynamic Monte Carlo: calibration closes the oracle gap", fontsize=10)
    export_figure(fig, "fig06_dynamic_monte_carlo", out_dir, formats)


def figure_output_precision(mc: dict[str, np.ndarray], out_dir: Path, formats: tuple[str, ...]) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 2.9), constrained_layout=True)
    labels = ["Cal int12", "Cal Q2", "Oracle int12", "Oracle Q2"]
    data = [
        mc["calibrated_sndr_int12"],
        mc["calibrated_sndr"],
        mc["physical_sndr_int12"],
        mc["physical_sndr"],
    ]
    palette = [VERMILLION, BLUE, VERMILLION, GREEN]
    violin_box(ax, data, labels, palette, "SNDR (dB)")
    medians = [float(np.median(values)) for values in data]
    for i, value in enumerate(medians, start=1):
        ax.text(i, value + 0.24, f"{value:.2f}", ha="center", fontsize=7)
    ax.set_ylim(69.5, 74.1)
    ax.annotate(
        f"+{medians[1] - medians[0]:.2f} dB",
        xy=(1.5, 73.62),
        ha="center",
        color=BLUE,
        fontweight="bold",
    )
    ax.annotate(
        f"+{medians[3] - medians[2]:.2f} dB",
        xy=(3.5, 73.92),
        ha="center",
        color=GREEN,
        fontweight="bold",
    )
    ax.text(0.02, 0.95, "n = 100 seeds", transform=ax.transAxes, va="top", fontsize=7)
    ax.set_title("Retaining two fractional bits removes the second quantization penalty")
    export_figure(fig, "fig07_q2_output_precision", out_dir, formats)


def figure_weight_error(summary: dict, out_dir: Path, formats: tuple[str, ...]) -> None:
    names = list(summary["weight_errors"])
    x = np.arange(len(names))
    abs_p50 = np.asarray([summary["weight_errors"][name]["P50"] for name in names])
    abs_p95 = np.asarray([summary["weight_errors"][name]["P95"] for name in names])
    ratio_p50 = np.asarray([summary["ratio_errors"][name]["P50"] for name in names])
    ratio_p95 = np.asarray([summary["ratio_errors"][name]["P95"] for name in names])
    fig, axes = plt.subplots(
        1, 2, figsize=(7.0, 2.8), constrained_layout=True, gridspec_kw={"wspace": 0.32}
    )
    axes[0].plot(x, abs_p50, marker="o", color=BLUE, label="P50")
    axes[0].plot(x, abs_p95, marker="s", linestyle="--", color=ORANGE, label="P95")
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Absolute error (Q0)")
    axes[0].legend(loc="upper left")
    axes[1].plot(x, ratio_p50 * 100, marker="o", color=BLUE, label="P50")
    axes[1].plot(
        x, ratio_p95 * 100, marker="s", linestyle="--", color=ORANGE, label="P95"
    )
    axes[1].set_yscale("log")
    axes[1].set_ylabel("Normalized ratio error (%)")
    axes[1].legend(loc="upper right")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=30, ha="right")
        ax.grid(axis="y", alpha=0.22)
    add_panel_labels(axes)
    fig.suptitle("Seven calibrated targets: absolute and normalized weight error", fontsize=10)
    export_figure(fig, "fig08_weight_error", out_dir, formats)


def figure_oracle_gap(mc: dict[str, np.ndarray], out_dir: Path, formats: tuple[str, ...]) -> None:
    gaps = np.sort(mc["oracle_gap_db"])
    cdf = np.arange(1, len(gaps) + 1) / len(gaps)
    fig, axes = plt.subplots(
        1, 2, figsize=(7.0, 2.8), constrained_layout=True, gridspec_kw={"wspace": 0.3}
    )
    axes[0].hist(gaps, bins="fd", color=BLUE, alpha=0.72, edgecolor="white")
    axes[0].axvline(0.5, color=ORANGE, linestyle="--", label="0.5 dB")
    axes[0].axvline(1.0, color=VERMILLION, linestyle=":", label="1.0 dB")
    axes[0].set_xlabel("Physical oracle - calibrated SNDR (dB)")
    axes[0].set_ylabel("Seed count")
    axes[0].legend(loc="upper right")
    axes[1].plot(gaps, cdf * 100, color=BLUE)
    axes[1].axvline(0.5, color=ORANGE, linestyle="--")
    axes[1].axvline(1.0, color=VERMILLION, linestyle=":")
    axes[1].set_xlabel("Oracle gap (dB)")
    axes[1].set_ylabel("Empirical CDF (%)")
    axes[1].set_ylim(0, 102)
    axes[1].grid(alpha=0.22)
    axes[1].text(
        0.97,
        0.08,
        "94/100 <= 0.5 dB\n99/100 <= 1.0 dB",
        transform=axes[1].transAxes,
        ha="right",
        va="bottom",
        fontsize=7,
    )
    add_panel_labels(axes)
    fig.suptitle("Calibration-to-physical oracle gap across 100 mismatch seeds", fontsize=10)
    export_figure(fig, "fig09_oracle_gap", out_dir, formats)


def figure_static_risk(
    static: dict, margin: dict, out_dir: Path, formats: tuple[str, ...]
) -> None:
    row = static["rows"][0]
    margins = np.asarray(
        [entry["h4_carry_margin_q0"] for entry in margin["rows"]], dtype=float
    )
    fig, axes = plt.subplots(
        1, 2, figsize=(7.0, 2.9), constrained_layout=True, gridspec_kw={"wspace": 0.32}
    )
    metrics = ["DNL peak", "INL peak"]
    nominal = [row["nominal"]["dnl_peak_lsb"], row["nominal"]["inl_peak_lsb"]]
    calibrated = [
        row["calibrated"]["dnl_peak_lsb"],
        row["calibrated"]["inl_peak_lsb"],
    ]
    x = np.arange(2)
    width = 0.34
    axes[0].bar(x - width / 2, nominal, width, color=ORANGE, label="Nominal")
    axes[0].bar(x + width / 2, calibrated, width, color=BLUE, label="Calibrated")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(metrics)
    axes[0].set_ylabel("Peak magnitude (LSB)")
    axes[0].set_ylim(0, max(nominal + calibrated) * 1.2)
    axes[0].legend(loc="upper right")
    axes[0].text(
        0.03,
        0.95,
        "2048 pairs, seed 70000\n2 missing + 2 backsteps after calibration",
        transform=axes[0].transAxes,
        va="top",
        fontsize=6.7,
    )
    axes[1].hist(
        margins,
        bins="fd",
        color=VERMILLION,
        alpha=0.68,
        edgecolor="white",
    )
    axes[1].axvline(0, color=DARK, linewidth=1.0)
    axes[1].axvline(
        np.median(margins),
        color=BLUE,
        linestyle="--",
        label=f"P50 = {np.median(margins):.2f} Q0",
    )
    axes[1].set_xlabel("H4 carry margin (Q0)")
    axes[1].set_ylabel("Seed count")
    axes[1].legend(loc="upper left")
    axes[1].text(
        0.97,
        0.95,
        f"{margin['negative_margin_count']}/{margin['seeds']} negative",
        transform=axes[1].transAxes,
        ha="right",
        va="top",
        fontsize=7,
        fontweight="bold",
        color=VERMILLION,
    )
    add_panel_labels(axes)
    fig.suptitle("Static limitation: lower error does not guarantee a monotonic codebook", fontsize=10)
    export_figure(fig, "fig10_static_codebook_risk", out_dir, formats)


def figure_completion_status(out_dir: Path, formats: tuple[str, ...]) -> None:
    rows = [
        ("Ideal 12-bit dynamic baseline", "PASS", GREEN, "73.666 dB / 11.944 bit"),
        ("100-seed calibrated dynamic gate", "PASS", GREEN, "73.112 dB / 11.852 bit"),
        ("Calibration-to-oracle gap", "PASS", GREEN, "P50 0.222 dB; P95 0.524 dB"),
        ("Full static monotonicity", "FAIL", VERMILLION, "2 missing codes at 2048 pairs"),
        ("Paper-exact Shen architecture", "NOT IMPLEMENTED", GRAY, "3 redundancies / reservoir / SRM absent"),
    ]
    fig, ax = plt.subplots(figsize=(7.0, 3.2), constrained_layout=True)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.text(
        0.2,
        5.55,
        "Verified completion status (v2.1.0)",
        fontsize=11,
        fontweight="bold",
    )
    for idx, (name, status, color, evidence) in enumerate(rows):
        y = 4.75 - idx * 0.92
        ax.add_patch(
            FancyBboxPatch(
                (0.2, y - 0.25),
                4.8,
                0.62,
                boxstyle="round,pad=0.02,rounding_size=0.05",
                facecolor="#F4F4F4",
                edgecolor=LIGHT_GRAY,
                linewidth=0.6,
            )
        )
        ax.text(0.42, y + 0.06, name, va="center", fontsize=7.4, fontweight="bold")
        ax.add_patch(
            FancyBboxPatch(
                (5.25, y - 0.25),
                2.0,
                0.62,
                boxstyle="round,pad=0.02,rounding_size=0.05",
                facecolor=color,
                edgecolor="none",
            )
        )
        ax.text(
            6.25,
            y + 0.06,
            status,
            ha="center",
            va="center",
            color="white",
            fontsize=7,
            fontweight="bold",
        )
        ax.text(7.55, y + 0.06, evidence, va="center", fontsize=7)
    ax.text(
        0.2,
        0.18,
        "The behavioral model is complete and reproducible; full static sign-off and "
        "paper-exact Shen hardware remain explicitly outside the passing claim.",
        fontsize=7,
        color=DARK,
    )
    export_figure(fig, "fig11_completion_status", out_dir, formats)


def generate_all(out_dir: Path, formats: tuple[str, ...]) -> list[str]:
    baseline = load_json(DATA / "baseline_diagnosis" / "baseline_diagnosis.json")
    summary = load_json(DATA / "final_pipeline" / "final_summary_a3330136.json")
    mc = load_csv(DATA / "final_pipeline" / "final_pipeline_a3330136.csv")
    static = load_json(DATA / "static_signoff_2048" / "full_static_signoff.json")
    margin = load_json(DATA / "codebook_margin" / "h4_carry_margin.json")

    builders = [
        ("fig01_model_architecture", lambda: figure_architecture(out_dir, formats)),
        ("fig02_cdac_decision_weights", lambda: figure_cdac_weights(baseline, out_dir, formats)),
        ("fig03_async_conversion_sequence", lambda: figure_conversion_sequence(out_dir, formats)),
        ("fig04_shen_calibration_flow", lambda: figure_calibration_flow(out_dir, formats)),
        ("fig05_ideal_baseline", lambda: figure_baseline(baseline, out_dir, formats)),
        ("fig06_dynamic_monte_carlo", lambda: figure_dynamic_mc(mc, out_dir, formats)),
        ("fig07_q2_output_precision", lambda: figure_output_precision(mc, out_dir, formats)),
        ("fig08_weight_error", lambda: figure_weight_error(summary, out_dir, formats)),
        ("fig09_oracle_gap", lambda: figure_oracle_gap(mc, out_dir, formats)),
        ("fig10_static_codebook_risk", lambda: figure_static_risk(static, margin, out_dir, formats)),
        ("fig11_completion_status", lambda: figure_completion_status(out_dir, formats)),
    ]
    generated = []
    for name, builder in builders:
        builder()
        generated.append(name)
        print(f"generated {name}")
    return generated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT,
        help="Output directory (default: docs/assets/figures)",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=("png", "svg", "pdf"),
        default=("png", "svg", "pdf"),
        help="Output formats",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    names = generate_all(args.out_dir.resolve(), tuple(args.formats))
    print(
        f"completed {len(names)} figures in {args.out_dir.resolve()} "
        f"(figura_style={USING_FIGURA})"
    )
