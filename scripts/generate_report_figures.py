"""Generate publication-quality figures for the mismatch validation report.

The script reads only committed-format CSV/JSON evidence from the formal
mismatch matrix.  It does not rerun, filter, or alter the ADC experiment.
Outputs are written as vector PDF/SVG plus a 300 dpi PNG preview.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

# Freeze vector metadata so repeated report builds do not dirty the worktree.
os.environ.setdefault("SOURCE_DATE_EPOCH", "1785024000")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams
from matplotlib.lines import Line2D
from matplotlib.patches import (
    FancyArrowPatch,
    FancyBboxPatch,
    Patch,
    Rectangle,
)


FIGURA_SCRIPTS = Path(
    os.environ.get(
        "FIGURA_SCRIPTS",
        Path.home() / ".agents" / "skills" / "figura" / "scripts",
    )
)
if FIGURA_SCRIPTS.exists():
    sys.path.insert(0, str(FIGURA_SCRIPTS))
    import colors  # type: ignore  # noqa: E402
    import export  # type: ignore  # noqa: E402
    import pubstyle  # type: ignore  # noqa: E402
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from report_figure_support import colors, export, pubstyle  # noqa: E402


CASE_ORDER = (
    "ideal_zero_noise",
    "mismatch_0p5_zero_noise",
    "mismatch_0p5_calnoise_0p3mV",
    "mismatch_1p0_zero_noise",
    "mismatch_1p0_calnoise_0p3mV",
)
CASE_LABELS = {
    "ideal_zero_noise": "Ideal",
    "mismatch_0p5_zero_noise": "0.5%\n0 mV",
    "mismatch_0p5_calnoise_0p3mV": (
        "0.5%\n0.3 mV"
    ),
    "mismatch_1p0_zero_noise": "1.0%\n0 mV",
    "mismatch_1p0_calnoise_0p3mV": (
        "1.0%\n0.3 mV"
    ),
}
MIN_SNDR_DB = 70.99
MIN_ENOB_BITS = 11.5
NAVY = "#17365D"
TEAL = "#167D85"
ORANGE = "#D97735"
GREEN = "#3D8C6A"
PURPLE = "#79558C"
INK = "#24303A"
MUTED = "#52606B"
PALE_BLUE = "#EAF2F7"
PALE_TEAL = "#E8F3F2"
PALE_ORANGE = "#FAEFE6"
PALE_GRAY = "#F3F5F6"


def _apply_report_style(extra: dict | None = None) -> None:
    """Apply Figura defaults plus an English-first report font stack."""

    params = {
        "font.family": "sans-serif",
        "font.sans-serif": [
            "Arial",
            "Noto Sans SC",
            "Microsoft YaHei",
            "DejaVu Sans",
        ],
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "svg.hashsalt": "sar-adc-v3.1.0",
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
    }
    if extra:
        params.update(extra)
    pubstyle.apply(extra=params)
    # Some external Figura versions reset the family after apply(); enforce it
    # once more so vector exports retain searchable text.
    rcParams.update(params)


def _export_figure(fig, name: str, outdir: Path) -> None:
    """Export all formats and normalize generated SVG whitespace."""

    export.save(fig, name, outdir=outdir)
    svg_path = outdir / f"{name}.svg"
    text = svg_path.read_text(encoding="utf-8")
    normalized = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    if normalized != text:
        svg_path.write_text(normalized, encoding="utf-8")


def _latest(path: Path, pattern: str) -> Path:
    matches = sorted(path.glob(pattern), key=lambda item: item.stat().st_mtime)
    if not matches:
        raise FileNotFoundError(f"no {pattern} under {path}")
    return matches[-1]


def _load_case(path: Path) -> dict[str, np.ndarray]:
    csv_path = _latest(path, "final_pipeline_*.csv")
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["valid"].lower() == "true"
        ]
    if not rows:
        raise RuntimeError(f"no valid rows in {csv_path}")

    def values(field: str) -> np.ndarray:
        return np.asarray([float(row[field]) for row in rows], dtype=float)

    return {
        "nominal_sndr": values("nominal_sndr"),
        "calibrated_sndr": values("calibrated_sndr"),
        "physical_sndr": values("physical_sndr"),
        "calibrated_enob": values("calibrated_enob"),
        "cal_gain": values("cal_gain_db"),
    }


def load_matrix(matrix_root: Path) -> tuple[dict, dict[str, dict]]:
    summary_path = matrix_root / "mismatch_matrix_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(
            f"{summary_path} is missing; run summarize_mismatch_matrix first"
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    missing = summary.get("missing_cases", [])
    if missing:
        raise RuntimeError(f"mismatch matrix is incomplete: {missing}")
    data = {
        label: _load_case(matrix_root / label)
        for label in CASE_ORDER
    }
    return summary, data


def _styled_boxplot(ax, data, positions, color, hatch, label):
    box = ax.boxplot(
        data,
        positions=positions,
        widths=0.22,
        patch_artist=True,
        showfliers=True,
        flierprops={
            "marker": "o",
            "markersize": 2.4,
            "markerfacecolor": color,
            "markeredgecolor": color,
            "alpha": 0.65,
        },
        medianprops={"color": "#1A1A1A", "linewidth": 1.1},
        whiskerprops={"color": color, "linewidth": 1.0},
        capprops={"color": color, "linewidth": 1.0},
        boxprops={"facecolor": color, "edgecolor": color, "alpha": 0.38},
    )
    for patch in box["boxes"]:
        patch.set_hatch(hatch)
    return Patch(
        facecolor=color,
        edgecolor=color,
        alpha=0.38,
        hatch=hatch,
        label=label,
    )


def figure_mismatch_performance(data: dict[str, dict], outdir: Path) -> None:
    """Show the actual mismatch story without promoting backsteps to a gate."""

    _apply_report_style()
    palette = colors.categorical(4)
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.25, 4.45),
        constrained_layout=True,
        gridspec_kw={"wspace": 0.24},
    )

    main_cases = (
        "ideal_zero_noise",
        "mismatch_0p5_zero_noise",
        "mismatch_0p5_calnoise_0p3mV",
        "mismatch_1p0_zero_noise",
        "mismatch_1p0_calnoise_0p3mV",
    )
    centers = np.arange(len(main_cases), dtype=float)
    offsets = (-0.25, 0.0, 0.25)
    series = (
        ("nominal_sndr", "Pre-calibration Q2", palette[1], "//"),
        ("calibrated_sndr", "Calibrated Q2", palette[0], ""),
        ("physical_sndr", "Physical-weight oracle", palette[2], "\\\\"),
    )
    handles = []
    for offset, (field, label, color, hatch) in zip(offsets, series):
        handles.append(
            _styled_boxplot(
                axes[0],
                [data[case][field] for case in main_cases],
                centers + offset,
                color,
                hatch,
                label,
            )
        )
    axes[0].axhline(
        MIN_SNDR_DB,
        color="#1A1A1A",
        linestyle=(0, (4, 2)),
        linewidth=1.0,
        label="Acceptance floor",
    )
    axes[0].set_xticks(centers)
    axes[0].set_xticklabels(
        [CASE_LABELS[case] for case in main_cases],
        fontsize=6.8,
        linespacing=1.05,
    )
    axes[0].set_ylabel("SNDR (dB)")
    axes[0].set_title("Mismatch impact and calibration recovery")
    all_sndr = np.concatenate(
        [
            data[case][field]
            for case in main_cases
            for field, _, _, _ in series
        ]
    )
    axes[0].set_ylim(np.floor(float(all_sndr.min())) - 1.0, 76)
    axes[0].legend(
        handles=handles
        + [
            Line2D(
                [0],
                [0],
                color="#1A1A1A",
                linestyle=(0, (4, 2)),
                label=f"Acceptance floor ({MIN_SNDR_DB:.2f} dB)",
            )
        ],
        loc="lower left",
        fontsize=7.4,
    )
    axes[0].text(
        0.98,
        0.985,
        "Ideal: n=1; mismatch conditions: n=100 each",
        transform=axes[0].transAxes,
        ha="right",
        va="top",
        fontsize=6.8,
        color="#555555",
    )

    compare_cases = CASE_ORDER[1:]
    x = np.arange(len(compare_cases), dtype=float)
    med = np.asarray(
        [np.median(data[case]["calibrated_sndr"]) for case in compare_cases]
    )
    low = np.asarray(
        [np.min(data[case]["calibrated_sndr"]) for case in compare_cases]
    )
    high = np.asarray(
        [np.max(data[case]["calibrated_sndr"]) for case in compare_cases]
    )
    axes[1].errorbar(
        x,
        med,
        yerr=np.vstack([med - low, high - med]),
        fmt="o",
        color=palette[0],
        markerfacecolor="white",
        markeredgewidth=1.2,
        markersize=5,
        capsize=4,
        elinewidth=1.2,
        label="Median; whiskers = full 100-seed range",
    )
    axes[1].scatter(
        x,
        low,
        marker="v",
        s=24,
        color=palette[1],
        zorder=3,
        label="Worst seed",
    )
    axes[1].axhline(
        MIN_SNDR_DB,
        color="#1A1A1A",
        linestyle=(0, (4, 2)),
        linewidth=1.0,
    )
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(
        [CASE_LABELS[case] for case in compare_cases],
        fontsize=6.8,
        linespacing=1.05,
    )
    axes[1].set_ylabel("Calibrated SNDR (dB)")
    axes[1].set_title("Post-calibration stability")
    axes[1].set_ylim(
        min(70.0, np.floor(float(low.min())) - 0.5),
        76,
    )
    axes[1].legend(loc="lower left", fontsize=7.4)
    for xi, value in zip(x, low):
        text_offset = 10 if value < 69.0 else -13
        axes[1].annotate(
            f"{value:.2f}",
            (xi, value),
            xytext=(0, text_offset),
            textcoords="offset points",
            ha="center",
            fontsize=7,
            color=palette[1],
        )

    for ax, label in zip(axes, ("a", "b")):
        ax.text(
            -0.13,
            1.04,
            f"({label})",
            transform=ax.transAxes,
            fontsize=10,
            fontweight="bold",
            va="bottom",
            ha="left",
        )
    _export_figure(fig, "fig_mismatch_performance", outdir)
    plt.close(fig)


def figure_noise_secondary(summary: dict, data: dict[str, dict], outdir: Path) -> None:
    """Keep calibration noise in its intended secondary role."""

    _apply_report_style()
    palette = colors.categorical(3)
    zero_05 = data["mismatch_0p5_zero_noise"]["calibrated_sndr"]
    noisy_05 = data[
        "mismatch_0p5_calnoise_0p3mV"
    ]["calibrated_sndr"]
    zero_10 = data["mismatch_1p0_zero_noise"]["calibrated_sndr"]
    noisy_10 = data[
        "mismatch_1p0_calnoise_0p3mV"
    ]["calibrated_sndr"]
    if len(zero_05) != len(noisy_05) or len(zero_10) != len(noisy_10):
        raise RuntimeError("noise comparison requires paired seed counts")
    delta_05 = noisy_05 - zero_05
    delta_10 = noisy_10 - zero_10

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.25, 2.85),
        constrained_layout=True,
        gridspec_kw={"wspace": 0.28},
    )
    for values, color, linestyle, label in (
        (zero_05, palette[0], "-", r"$\sigma_C=0.5\%$, 0 mV"),
        (noisy_05, palette[0], "--", r"$\sigma_C=0.5\%$, 0.3 mV"),
        (zero_10, palette[1], "-", r"$\sigma_C=1.0\%$, 0 mV"),
        (noisy_10, palette[1], "--", r"$\sigma_C=1.0\%$, 0.3 mV"),
    ):
        sorted_values = np.sort(values)
        p = (np.arange(len(values)) + 0.5) / len(values) * 100.0
        axes[0].plot(
            sorted_values,
            p,
            color=color,
            linestyle=linestyle,
            linewidth=1.5,
            label=label,
        )
    axes[0].axvline(
        MIN_SNDR_DB,
        color="#1A1A1A",
        linestyle=(0, (4, 2)),
        linewidth=1.0,
    )
    axes[0].set_xlabel("Calibrated SNDR (dB)")
    axes[0].set_ylabel("Empirical CDF (%)")
    axes[0].set_title("Calibration-only perturbation check")
    axes[0].legend(loc="lower left", fontsize=6.8)

    combined_delta = np.concatenate([delta_05, delta_10])
    bins = np.histogram_bin_edges(combined_delta, bins="fd")
    if len(bins) < 5:
        bins = np.linspace(
            float(combined_delta.min()) - 0.01,
            float(combined_delta.max()) + 0.01,
            9,
        )
    axes[1].hist(
        delta_05,
        bins=bins,
        histtype="step",
        color=palette[0],
        linewidth=1.4,
        label=(
            r"$\sigma_C=0.5\%$: median "
            f"{np.median(delta_05):+.3f} dB"
        ),
    )
    axes[1].hist(
        delta_10,
        bins=bins,
        histtype="step",
        color=palette[1],
        linestyle="--",
        linewidth=1.4,
        label=(
            r"$\sigma_C=1.0\%$: median "
            f"{np.median(delta_10):+.3f} dB"
        ),
    )
    axes[1].axvline(0.0, color="#1A1A1A", linewidth=1.0)
    axes[1].set_xlabel(
        r"Paired $\Delta$SNDR: 0.3 mV $-$ 0 mV calibration (dB)"
    )
    axes[1].set_ylabel("Seed count")
    axes[1].set_title("Effect of the secondary perturbation")
    axes[1].legend(loc="upper right", fontsize=7.0)
    axes[1].text(
        0.98,
        0.04,
        f"n={len(delta_05)} paired seeds per mismatch level",
        transform=axes[1].transAxes,
        ha="right",
        va="bottom",
        fontsize=7,
        color="#555555",
    )

    for ax, label in zip(axes, ("a", "b")):
        ax.text(
            -0.14,
            1.04,
            f"({label})",
            transform=ax.transAxes,
            fontsize=10,
            fontweight="bold",
            va="bottom",
            ha="left",
        )
    _export_figure(fig, "fig_noise_secondary", outdir)
    plt.close(fig)


def figure_validation_flow(outdir: Path) -> None:
    """Illustrate what calibration changes and what it deliberately does not."""

    _apply_report_style()
    palette = colors.categorical(4)
    fig, ax = plt.subplots(figsize=(7.25, 3.0))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4.2)
    ax.set_aspect("equal")
    ax.axis("off")

    def box(
        x,
        y,
        w,
        h,
        text,
        color,
        *,
        text_color="white",
        dashed=False,
        fontsize=8.3,
    ):
        patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            facecolor=color if not dashed else "white",
            edgecolor=color,
            linewidth=1.0,
            linestyle="--" if dashed else "-",
        )
        ax.add_patch(patch)
        ax.text(
            x + w / 2,
            y + h / 2,
            text,
            ha="center",
            va="center",
            color=text_color if not dashed else color,
            fontsize=fontsize,
            linespacing=1.15,
        )

    def arrow(x1, y1, x2, y2, *, dashed=False):
        ax.add_patch(
            FancyArrowPatch(
                (x1, y1),
                (x2, y2),
                arrowstyle="-|>",
                mutation_scale=11,
                linewidth=1.0,
                linestyle="--" if dashed else "-",
                color="#444444",
                shrinkA=4,
                shrinkB=4,
            )
        )

    box(0.2, 1.7, 1.55, 0.85, "Input\nsample", palette[0])
    box(2.15, 1.7, 2.10, 0.85, "Physical split-CDAC\nPER-UNIT mismatch", palette[1])
    box(4.70, 1.7, 1.75, 0.85, "15 comparator\ndecisions", palette[2])
    box(6.90, 2.65, 2.00, 0.75, "Nominal Q2\ndecoder", palette[1], dashed=True)
    box(6.90, 1.60, 2.00, 0.75, "Calibrated Q2\ndecoder", palette[0])
    box(6.90, 0.55, 2.00, 0.75, "Physical-weight\noracle", palette[2], dashed=True)
    box(
        9.35,
        1.42,
        2.45,
        1.12,
        "Metrics\nSNDR / ENOB\nDNL / INL\nmissing / rollback",
        palette[3],
        fontsize=7.6,
    )

    arrow(1.75, 2.125, 2.15, 2.125)
    arrow(4.25, 2.125, 4.70, 2.125)
    arrow(6.45, 2.125, 6.90, 3.025)
    arrow(6.45, 2.125, 6.90, 1.975)
    arrow(6.45, 2.125, 6.90, 0.925)
    arrow(8.90, 3.025, 9.35, 2.30)
    arrow(8.90, 1.975, 9.35, 1.975)
    arrow(8.90, 0.925, 9.35, 1.65)

    box(
        2.40,
        3.10,
        3.00,
        0.85,
        "P0/P1/N0/N1\nforeground weight estimate\n0.3 mV only here",
        palette[0],
        fontsize=7.2,
    )
    arrow(5.55, 2.55, 4.75, 3.10, dashed=True)
    arrow(5.40, 3.55, 7.35, 2.35, dashed=True)
    ax.text(
        6.0,
        0.15,
        "The same physical decisions feed all three paths; calibration updates digital weights, not the CDAC decisions.",
        ha="center",
        va="bottom",
        fontsize=7.5,
        color="#555555",
    )
    _export_figure(fig, "fig_validation_flow", outdir)
    plt.close(fig)


def _diagram_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    face: str,
    edge: str,
    fontsize: float = 7.5,
    text_color: str = INK,
    dashed: bool = False,
    radius: float = 0.012,
    zorder: int = 3,
):
    """Draw a report diagram node in axes-relative coordinates."""

    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.006,rounding_size={radius}",
        transform=ax.transAxes,
        facecolor=face,
        edgecolor=edge,
        linewidth=1.0,
        linestyle=(0, (4, 2)) if dashed else "-",
        zorder=zorder,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=text_color,
        linespacing=1.22,
        zorder=zorder + 1,
    )
    return patch


def _diagram_arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = MUTED,
    dashed: bool = False,
    both: bool = False,
    connectionstyle: str = "arc3",
    zorder: int = 2,
):
    """Draw a connection whose endpoints are already on node boundaries."""

    patch = FancyArrowPatch(
        start,
        end,
        transform=ax.transAxes,
        arrowstyle="<|-|>" if both else "-|>",
        mutation_scale=9,
        linewidth=0.95,
        color=color,
        linestyle=(0, (4, 2)) if dashed else "-",
        connectionstyle=connectionstyle,
        shrinkA=0,
        shrinkB=0,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def figure_project_architecture(outdir: Path) -> None:
    """Show repository layers, interfaces, authority, and evidence flow."""

    _apply_report_style({"font.size": 8})
    fig, ax = plt.subplots(figsize=(7.25, 6.35))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    columns = (
        (0.02, 0.315, "Python behavioral golden path", NAVY),
        (0.345, 0.315, "SystemVerilog calibration subset", TEAL),
        (0.67, 0.31, "Verilog-A AMS bridge", ORANGE),
    )
    for x, w, title, color in columns:
        ax.add_patch(
            FancyBboxPatch(
                (x, 0.235),
                w,
                0.715,
                boxstyle="round,pad=0.005,rounding_size=0.014",
                transform=ax.transAxes,
                facecolor="#FCFDFD",
                edgecolor="#CBD3D8",
                linewidth=0.9,
                zorder=0,
            )
        )
        ax.add_patch(
            Rectangle(
                (x, 0.895),
                w,
                0.055,
                transform=ax.transAxes,
                facecolor=color,
                edgecolor=color,
                zorder=1,
            )
        )
        ax.text(
            x + w / 2,
            0.922,
            title,
            transform=ax.transAxes,
            ha="center",
            va="center",
            color="white",
            fontsize=8.5,
            fontweight="bold",
            zorder=2,
        )

    # Python authority chain.
    py_nodes = (
        (0.052, 0.795, "config + topology\nStageSpec / caps / switches"),
        (0.052, 0.680, "physical\n2-node charge solver\ndifferential CDAC"),
        (0.052, 0.565, "comparator + async_control\ncomparator events\ntrial / commit"),
        (0.052, 0.450, "calibration + decode\nP0/P1/N0/N1\nQ8 weights / Q2 reconstruction"),
        (0.052, 0.335, "validation + pipeline\nFFT / reachable tree\n100-seed matrix"),
    )
    for x, y, label in py_nodes:
        _diagram_box(
            ax,
            x,
            y,
            0.25,
            0.072,
            label,
            face=PALE_BLUE,
            edge=NAVY,
            fontsize=6.5,
        )
    for (_, y1, _), (_, y2, _) in zip(py_nodes, py_nodes[1:]):
        _diagram_arrow(ax, (0.177, y1), (0.177, y2 + 0.072), color=NAVY)

    # RTL subset.  The vertical arrangement keeps labels off the data paths.
    _diagram_box(
        ax,
        0.388,
        0.805,
        0.225,
        0.062,
        "cal_top\nparameters, ports, integration",
        face=PALE_TEAL,
        edge=TEAL,
        fontsize=7.2,
    )
    _diagram_box(
        ax,
        0.388,
        0.685,
        0.225,
        0.073,
        "cal_fsm\nphase sequencing / accumulation\nrange check / Q8 commit",
        face=PALE_TEAL,
        edge=TEAL,
        fontsize=6.3,
    )
    _diagram_box(
        ax,
        0.388,
        0.555,
        0.225,
        0.073,
        "sar_subconverter\nrecursive lower-SAR\nQ8 signed sum",
        face=PALE_TEAL,
        edge=TEAL,
        fontsize=6.8,
    )
    _diagram_box(
        ax,
        0.410,
        0.425,
        0.180,
        0.073,
        "cal_weight_reg\n7×P/N×20-bit Q8",
        face="#FFFFFF",
        edge=TEAL,
        fontsize=7.0,
    )
    _diagram_box(
        ax,
        0.388,
        0.285,
        0.225,
        0.095,
        "verification proxy\nXSIM self-check\nVivado synthesis + timing",
        face=PALE_GRAY,
        edge=MUTED,
        fontsize=6.7,
    )
    _diagram_arrow(ax, (0.50, 0.805), (0.50, 0.758), color=TEAL)
    _diagram_arrow(ax, (0.488, 0.685), (0.488, 0.628), color=TEAL)
    _diagram_arrow(ax, (0.512, 0.628), (0.512, 0.685), color=NAVY)
    ax.text(
        0.525,
        0.657,
        "start / done / sum",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=5.5,
        color=MUTED,
    )
    # Register write runs in the left inner gutter.
    ax.plot(
        [0.388, 0.372, 0.372, 0.410],
        [0.721, 0.721, 0.462, 0.462],
        transform=ax.transAxes,
        color=TEAL,
        linewidth=0.95,
        zorder=2,
    )
    _diagram_arrow(ax, (0.398, 0.462), (0.410, 0.462), color=TEAL)
    ax.text(
        0.366,
        0.520,
        "write",
        transform=ax.transAxes,
        ha="right",
        va="center",
        fontsize=5.5,
        color=MUTED,
    )
    # Recursive read returns to the lower-SAR through the right inner gutter.
    _diagram_arrow(
        ax,
        (0.590, 0.462),
        (0.613, 0.590),
        color=TEAL,
        connectionstyle="arc3,rad=-0.18",
    )
    ax.text(
        0.620,
        0.515,
        "recursive read",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=5.4,
        color=MUTED,
        rotation=74,
    )
    _diagram_arrow(
        ax,
        (0.50, 0.425),
        (0.50, 0.380),
        color=MUTED,
        dashed=True,
    )

    # Verilog-A bridge and explicit missing authority.
    va_nodes = (
        (
            0.705,
            0.770,
            "cdac_behavioral.va\nP/N two-node matrices\nexternal mismatch multipliers",
            PALE_ORANGE,
            ORANGE,
            False,
        ),
        (
            0.705,
            0.625,
            "strongarm_cmp.va\noffset / optional noise / delay\nready output",
            PALE_ORANGE,
            ORANGE,
            False,
        ),
        (
            0.705,
            0.475,
            "Spectre / AMS testbench\nswitches + clock + comparator\nRTL co-simulation",
            "#FFFFFF",
            ORANGE,
            True,
        ),
        (
            0.705,
            0.335,
            "current evidence\nstructural / equation review\nno local compile or PDK signoff",
            PALE_GRAY,
            MUTED,
            True,
        ),
    )
    for x, y, label, face, edge, dashed in va_nodes:
        _diagram_box(
            ax,
            x,
            y,
            0.24,
            0.082,
            label,
            face=face,
            edge=edge,
            fontsize=6.4,
            dashed=dashed,
        )
    _diagram_arrow(ax, (0.825, 0.770), (0.825, 0.707), color=ORANGE, both=True)
    _diagram_arrow(
        ax,
        (0.825, 0.625),
        (0.825, 0.557),
        color=ORANGE,
        dashed=True,
    )
    _diagram_arrow(
        ax,
        (0.825, 0.475),
        (0.825, 0.417),
        color=MUTED,
        dashed=True,
    )

    # Cross-language checks are routed through the white gutters, never through
    # a node or label.
    ax.plot(
        [0.302, 0.326, 0.326, 0.388],
        [0.486, 0.486, 0.721, 0.721],
        transform=ax.transAxes,
        color=PURPLE,
        linewidth=0.95,
        linestyle=(0, (4, 2)),
        zorder=2,
    )
    _diagram_arrow(
        ax,
        (0.376, 0.721),
        (0.388, 0.721),
        color=PURPLE,
        dashed=True,
    )
    ax.text(
        0.331,
        0.595,
        "Q8 contract",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=5.5,
        color=PURPLE,
        rotation=90,
    )
    ax.plot(
        [0.052, 0.008, 0.008, 0.684, 0.684, 0.705],
        [0.716, 0.716, 0.972, 0.972, 0.811, 0.811],
        transform=ax.transAxes,
        color=PURPLE,
        linewidth=0.95,
        linestyle=(0, (4, 2)),
        zorder=2,
    )
    _diagram_arrow(
        ax,
        (0.693, 0.811),
        (0.705, 0.811),
        color=PURPLE,
        dashed=True,
    )
    ax.text(
        0.505,
        0.978,
        "same charge-conservation equations",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=5.8,
        color=PURPLE,
    )

    # Frozen delivery chain.
    ax.text(
        0.02,
        0.205,
        "Reproducible delivery chain (the only data path into the report)",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=8.2,
        color=NAVY,
        fontweight="bold",
    )
    chain = (
        (0.025, 0.082, 0.15, "spec.yml / config\nversioned parameters"),
        (0.205, 0.082, 0.15, "formal matrix run\nCSV + JSON"),
        (0.385, 0.082, 0.15, "evidence/\nfrozen files + SHA-256"),
        (0.565, 0.082, 0.17, "figures + LaTeX macros\nread frozen evidence"),
        (0.765, 0.082, 0.205, "XeLaTeX ×3\nPDF + page-by-page visual QA"),
    )
    for x, y, w, label in chain:
        _diagram_box(
            ax,
            x,
            y,
            w,
            0.075,
            label,
            face="#FFFFFF",
            edge=NAVY,
            fontsize=6.2,
        )
    for left, right in zip(chain, chain[1:]):
        _diagram_arrow(
            ax,
            (left[0] + left[2], 0.1195),
            (right[0], 0.1195),
            color=NAVY,
        )
    _diagram_arrow(
        ax,
        (0.177, 0.335),
        (0.28, 0.157),
        color=NAVY,
        dashed=True,
        connectionstyle="arc3,rad=0.08",
    )

    ax.plot(
        [0.026, 0.052],
        [0.022, 0.022],
        transform=ax.transAxes,
        color=INK,
        linewidth=1.0,
    )
    ax.text(
        0.058,
        0.022,
        "solid: implemented runtime data/control",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=6.2,
        color=MUTED,
    )
    ax.plot(
        [0.39, 0.416],
        [0.022, 0.022],
        transform=ax.transAxes,
        color=PURPLE,
        linewidth=1.0,
        linestyle=(0, (4, 2)),
    )
    ax.text(
        0.422,
        0.022,
        "dashed: cross-check or pending tool/PDK closure",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=6.2,
        color=MUTED,
    )

    _export_figure(fig, "fig_project_architecture", outdir)
    plt.close(fig)


def figure_rtl_architecture(outdir: Path) -> None:
    """Draw the synthesizable calibration subset and every major interface."""

    _apply_report_style({"font.size": 8})
    fig, ax = plt.subplots(figsize=(7.25, 5.05))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.add_patch(
        FancyBboxPatch(
            (0.185, 0.155),
            0.63,
            0.750,
            boxstyle="round,pad=0.008,rounding_size=0.018",
            transform=ax.transAxes,
            facecolor="#FBFDFD",
            edgecolor=TEAL,
            linewidth=1.3,
            linestyle=(0, (6, 2)),
            zorder=0,
        )
    )
    ax.text(
        0.500,
        0.855,
        "cal_top — synthesizable calibration subset\n(full ADC top not included)",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=8.0,
        color=TEAL,
        fontweight="bold",
        linespacing=1.15,
    )

    _diagram_box(
        ax,
        0.315,
        0.660,
        0.370,
        0.135,
        "cal_fsm\nP0 → P1 → N0 → N1 per pair\n"
        "accumulate / divide by 2N / validate / Q8 commit",
        face=PALE_TEAL,
        edge=TEAL,
        fontsize=6.9,
    )
    _diagram_box(
        ax,
        0.245,
        0.350,
        0.330,
        0.180,
        "sar_subconverter\n5-state lower-SAR; H1 → H32 recursive ruler\n"
        "cmp_out → trial/commit\nsigned_sum[23:0] Q8",
        face=PALE_BLUE,
        edge=NAVY,
        fontsize=6.9,
    )
    _diagram_box(
        ax,
        0.625,
        0.350,
        0.150,
        0.180,
        "cal_weight_reg\n7 entries per side\n20-bit Q8\nnominal reset values",
        face="#FFFFFF",
        edge=TEAL,
        fontsize=6.8,
    )

    _diagram_box(
        ax,
        0.015,
        0.655,
        0.140,
        0.140,
        "Host\nclk / rst_n / start",
        face=PALE_GRAY,
        edge=MUTED,
        fontsize=7.2,
    )
    _diagram_box(
        ax,
        0.015,
        0.345,
        0.140,
        0.190,
        "AMS boundary\nCDAC + comparator\ncmp_out\nswitch buses",
        face=PALE_ORANGE,
        edge=ORANGE,
        fontsize=6.7,
    )
    _diagram_box(
        ax,
        0.845,
        0.655,
        0.140,
        0.140,
        "Status\ncal_done\ncal_failed",
        face=PALE_GRAY,
        edge=MUTED,
        fontsize=7.0,
    )
    _diagram_box(
        ax,
        0.845,
        0.345,
        0.140,
        0.190,
        "Weight output\nweights_p/n[6:0]\n20-bit Q8 each\nnormal Q2 decoder",
        face=PALE_BLUE,
        edge=NAVY,
        fontsize=6.5,
        dashed=True,
    )

    _diagram_arrow(ax, (0.155, 0.725), (0.315, 0.725), color=MUTED)
    _diagram_arrow(ax, (0.685, 0.725), (0.845, 0.725), color=MUTED)

    # FSM-to-subconverter control and return-data paths use separate lanes.
    _diagram_arrow(ax, (0.405, 0.660), (0.385, 0.530), color=TEAL)
    ax.text(
        0.350,
        0.595,
        "target_idx / phase\nstart_subconv",
        transform=ax.transAxes,
        ha="right",
        va="center",
        fontsize=6.6,
        color=MUTED,
    )
    _diagram_arrow(ax, (0.465, 0.530), (0.505, 0.660), color=NAVY)
    ax.text(
        0.515,
        0.595,
        "done /\nsigned_sum",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=6.6,
        color=MUTED,
    )

    # Register read is horizontal and lands exactly on the lower-SAR boundary.
    _diagram_arrow(ax, (0.625, 0.440), (0.575, 0.440), color=TEAL)
    # FSM register write is routed through the clear right-hand lane.
    ax.plot(
        [0.630, 0.800, 0.800, 0.775],
        [0.660, 0.660, 0.485, 0.485],
        transform=ax.transAxes,
        color=TEAL,
        linewidth=0.95,
        zorder=2,
    )
    _diagram_arrow(
        ax,
        (0.787, 0.485),
        (0.775, 0.485),
        color=TEAL,
    )
    ax.text(
        0.795,
        0.585,
        "we / addr /\nwp / wn",
        transform=ax.transAxes,
        ha="right",
        va="center",
        fontsize=6.4,
        color=MUTED,
    )

    _diagram_arrow(ax, (0.155, 0.458), (0.245, 0.458), color=ORANGE)
    _diagram_arrow(ax, (0.245, 0.418), (0.155, 0.418), color=ORANGE)
    ax.text(
        0.200,
        0.476,
        "cmp_out",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=6.2,
        color=MUTED,
    )
    ax.text(
        0.200,
        0.399,
        "switch buses",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=6.1,
        color=MUTED,
    )
    _diagram_arrow(ax, (0.775, 0.440), (0.845, 0.440), color=NAVY)

    _diagram_box(
        ax,
        0.205,
        0.035,
        0.270,
        0.075,
        "XSIM PASS\n7 targets • four phases\nrecursive Q8 weights",
        face="#FFFFFF",
        edge=GREEN,
        fontsize=6.4,
    )
    _diagram_box(
        ax,
        0.525,
        0.035,
        0.270,
        0.075,
        "Vivado synthesis proxy\n449 LUT • 595 FF\n100 MHz constraint",
        face="#FFFFFF",
        edge=GREEN,
        fontsize=6.4,
    )
    _diagram_arrow(
        ax,
        (0.40, 0.155),
        (0.355, 0.110),
        color=MUTED,
        dashed=True,
    )
    _diagram_arrow(
        ax,
        (0.60, 0.155),
        (0.645, 0.110),
        color=MUTED,
        dashed=True,
    )

    ax.text(
        0.50,
        0.190,
        "Not in current top: normal SAR, Q2 decoder, CDC/DFT, ASIC STA.",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=6.4,
        color=ORANGE,
    )

    _export_figure(fig, "fig_rtl_architecture", outdir)
    plt.close(fig)


def figure_cdac_topology(outdir: Path) -> None:
    """Draw complete sampling/conversion connectivity for both CDAC sides."""

    _apply_report_style({"font.size": 8})
    fig, ax = plt.subplots(figsize=(7.25, 4.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    def capacitor(
        x: float,
        y_top: float,
        y_bottom: float,
        label: str,
        color: str,
        *,
        label_dx: float = 0.038,
        label_ha: str = "left",
    ):
        mid = (y_top + y_bottom) / 2
        gap = 0.018
        plate = 0.032
        ax.plot([x, x], [y_top, mid + gap], color=color, lw=1.1)
        ax.plot([x - plate, x + plate], [mid + gap, mid + gap], color=color, lw=1.3)
        ax.plot([x - plate, x + plate], [mid - gap, mid - gap], color=color, lw=1.3)
        ax.plot([x, x], [mid - gap, y_bottom], color=color, lw=1.1)
        ax.text(
            x + label_dx,
            mid,
            label,
            ha=label_ha,
            va="center",
            fontsize=7.2,
            color=INK,
        )

    def draw_side(x0: float, title: str, vin: str):
        x_top = x0 + 0.22
        y_top = 0.72
        y_bridge = 0.43
        y_bottom = 0.19
        color = NAVY if title == "P side" else TEAL

        ax.add_patch(
            FancyBboxPatch(
                (x0, 0.095),
                0.44,
                0.80,
                boxstyle="round,pad=0.006,rounding_size=0.018",
                transform=ax.transAxes,
                facecolor="#FCFDFD",
                edgecolor="#CDD5DA",
                linewidth=0.9,
            )
        )
        ax.text(
            x0 + 0.02,
            0.855,
            title,
            transform=ax.transAxes,
            ha="left",
            va="center",
            color=color,
            fontsize=9,
            fontweight="bold",
        )

        # Top-node bus and sample clamp.
        ax.plot([x0 + 0.08, x0 + 0.36], [y_top, y_top], color=color, lw=1.3)
        ax.scatter([x_top], [y_top], s=18, color=color, zorder=4)
        ax.text(
            x_top,
            y_top + 0.035,
            f"VTOP_{title[0]}",
            ha="center",
            va="bottom",
            fontsize=7.0,
            color=color,
            fontweight="bold",
        )
        ax.plot([x_top, x_top], [0.815, 0.775], color=color, lw=1.0)
        ax.plot([x_top, x_top + 0.025], [0.775, 0.755], color=color, lw=1.0)
        ax.plot([x_top, x_top], [0.740, y_top], color=color, lw=1.0)
        ax.text(
            x_top,
            0.825,
            "VCM (SAMPLE)",
            ha="center",
            va="bottom",
            fontsize=7.0,
            color=INK,
        )

        # High bank, bridge, and low bank.
        capacitor(x0 + 0.10, y_top, y_bottom, "high bank 71Cu", color)
        capacitor(x0 + 0.31, y_top, y_bridge, "bridge cap 2Cu", ORANGE)
        ax.plot(
            [x0 + 0.25, x0 + 0.38],
            [y_bridge, y_bridge],
            color=ORANGE,
            lw=1.2,
        )
        ax.scatter([x0 + 0.31], [y_bridge], s=18, color=ORANGE, zorder=4)
        ax.text(
            x0 + 0.31,
            y_bridge + 0.036,
            f"VBR_{title[0]}: floating",
            ha="center",
            va="bottom",
            fontsize=6.7,
            color=ORANGE,
            fontweight="bold",
        )
        capacitor(
            x0 + 0.38,
            y_bridge,
            y_bottom,
            "low bank 65Cu",
            color,
            label_dx=-0.038 if title == "N side" else 0.038,
            label_ha="right" if title == "N side" else "left",
        )

        # Bottom-plate bus and selector.
        ax.plot([x0 + 0.065, x0 + 0.405], [y_bottom, y_bottom], color=color, lw=1.2)
        ax.add_patch(
            FancyBboxPatch(
                (x0 + 0.035, 0.105),
                0.37,
                0.055,
                boxstyle="round,pad=0.004,rounding_size=0.009",
                transform=ax.transAxes,
                facecolor=PALE_GRAY,
                edgecolor=MUTED,
                linewidth=0.8,
            )
        )
        ax.text(
            x0 + 0.22,
            0.132,
            f"SAMPLE {vin}   |   CONVERT VREFP / VCM / VREFN",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=5.8,
            color=INK,
        )
        ax.plot([x0 + 0.22, x0 + 0.22], [y_bottom, 0.160], color=MUTED, lw=0.9)

        ax.text(
            x0 + 0.225,
            0.255,
            "Both segments sample the input;\nno sampling switch on the bridge node",
            ha="center",
            va="center",
            fontsize=7.0,
            color=INK,
            linespacing=1.25,
        )

    draw_side(0.035, "P side", "VINP")
    draw_side(0.525, "N side", "VINN")

    ax.add_patch(
        FancyArrowPatch(
            (0.255, 0.945),
            (0.745, 0.945),
            arrowstyle="<|-|>",
            mutation_scale=9,
            color=PURPLE,
            linewidth=1.0,
        )
    )
    ax.text(
        0.50,
        0.955,
        "Comparator reads VTOP_P − VTOP_N; P/N switches and mismatch parameters are independent",
        ha="center",
        va="bottom",
        fontsize=7.3,
        color=PURPLE,
        fontweight="bold",
    )

    _export_figure(fig, "fig_cdac_topology", outdir)
    plt.close(fig)


def figure_monotonicity(summary: dict, outdir: Path) -> None:
    """Explain local rollback and quantify its actual input-width footprint."""

    _apply_report_style()
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.25, 3.55),
        constrained_layout=True,
        gridspec_kw={"wspace": 0.30, "width_ratios": [1.08, 1.0]},
    )

    # Conceptual redundant transfer: one 1-LSB local rollback.
    x = np.arange(9, dtype=float)
    ideal = np.arange(9, dtype=float)
    local = np.asarray([0, 1, 2, 3, 4, 3, 5, 6, 7], dtype=float)
    axes[0].step(
        x,
        ideal,
        where="post",
        color="#A8B0B7",
        linewidth=1.2,
        linestyle=(0, (4, 2)),
        label="Ideal ordered staircase",
    )
    axes[0].step(
        x,
        local,
        where="post",
        color=NAVY,
        linewidth=1.8,
        label="Redundant weighted decode",
    )
    axes[0].fill_between(
        [4, 5],
        [3, 3],
        [4, 4],
        step="post",
        color=ORANGE,
        alpha=0.24,
    )
    axes[0].annotate(
        "Local rollback: 1 LSB",
        xy=(4.55, 3.05),
        xytext=(5.1, 1.35),
        arrowprops={
            "arrowstyle": "-|>",
            "color": ORANGE,
            "linewidth": 1.0,
        },
        color=ORANGE,
        fontsize=7.6,
        ha="center",
    )
    axes[0].annotate(
        "One output code can collect\nmultiple disjoint input intervals",
        xy=(3.45, 3.05),
        xytext=(2.15, 6.05),
        arrowprops={
            "arrowstyle": "-|>",
            "color": PURPLE,
            "linewidth": 1.0,
        },
        color=PURPLE,
        fontsize=7.2,
        ha="center",
    )
    axes[0].set_xlim(0, 8)
    axes[0].set_ylim(-0.2, 8.4)
    axes[0].set_xlabel("Input interval (conceptual)")
    axes[0].set_ylabel("Integer output code (LSB)")
    axes[0].set_title("Local rollback versus code-density")
    axes[0].legend(loc="lower right", fontsize=6.9)
    axes[0].spines["top"].set_visible(False)
    axes[0].spines["right"].set_visible(False)

    case_names = (
        "mismatch_0p5_calnoise_0p3mV",
        "mismatch_1p0_calnoise_0p3mV",
    )
    labels = ("0.5% nominal", "1.0% stress")
    quantiles = (
        ("p50", "P50", NAVY),
        ("p95", "P95", TEAL),
        ("max", "Max", ORANGE),
    )
    centers = np.arange(len(case_names), dtype=float)
    width = 0.22
    for offset, (key, label, color) in zip((-width, 0.0, width), quantiles):
        values = [
            100.0
            * summary["cases"][case]["transfer_integrity"][
                "integer_nonmonotonic_input_fraction"
            ][key]
            for case in case_names
        ]
        bars = axes[1].bar(
            centers + offset,
            values,
            width=width * 0.90,
            color=color,
            alpha=0.86,
            label=label,
        )
        for bar, value in zip(bars, values):
            axes[1].text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.010,
                f"{value:.3f}%",
                ha="center",
                va="bottom",
                fontsize=6.2,
                color=INK,
            )
    axes[1].set_xticks(centers)
    axes[1].set_xticklabels(labels)
    axes[1].set_ylabel("Affected input-width fraction (%)")
    axes[1].set_title("Frozen input-width footprint (100 seeds)")
    axes[1].legend(loc="upper left", ncol=3, fontsize=6.8)
    axes[1].set_ylim(0, 0.42)
    axes[1].text(
        0.02,
        0.58,
        "Max integer rollback = 1 LSB\n99/100 seeds show at least one rollback",
        transform=axes[1].transAxes,
        ha="left",
        va="top",
        fontsize=6.6,
        color=MUTED,
        bbox={
            "facecolor": "white",
            "edgecolor": "#CCD3D8",
            "boxstyle": "round,pad=0.28",
        },
    )

    for ax, label in zip(axes, ("a", "b")):
        ax.text(
            -0.13,
            1.04,
            f"({label})",
            transform=ax.transAxes,
            fontsize=10,
            fontweight="bold",
            va="bottom",
            ha="left",
        )
    _export_figure(fig, "fig_monotonicity_mechanism", outdir)
    plt.close(fig)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    committed_matrix = repo_root / "evidence" / "mismatch_matrix"
    working_matrix = (
        repo_root
        / "src"
        / "python_cal"
        / "validation_results"
        / "mismatch_matrix"
    )
    default_matrix = (
        committed_matrix
        if (committed_matrix / "mismatch_matrix_summary.json").exists()
        else working_matrix
    )
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--matrix-root",
        type=Path,
        default=default_matrix,
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=repo_root / "docs" / "figures" / "mismatch_report",
    )
    args = parser.parse_args()

    summary, data = load_matrix(args.matrix_root)
    figure_project_architecture(args.outdir)
    figure_cdac_topology(args.outdir)
    figure_validation_flow(args.outdir)
    figure_mismatch_performance(data, args.outdir)
    figure_noise_secondary(summary, data, args.outdir)
    figure_monotonicity(summary, args.outdir)
    figure_rtl_architecture(args.outdir)
    print(args.outdir.resolve())


if __name__ == "__main__":
    main()
