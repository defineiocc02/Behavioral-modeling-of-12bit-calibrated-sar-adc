"""Generate the release figures from the active configuration and final run."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "font.family": "DejaVu Sans",
})

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from python_cal import config as cfg  # noqa: E402

RESULTS = SRC / "python_cal" / "validation_results" / "final_pipeline"
OUT = ROOT / "docs" / "assets" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {
    "blue": "#0072B2",
    "orange": "#D55E00",
    "green": "#009E73",
    "purple": "#CC79A7",
    "gray": "#666666",
}


def _load_release():
    summaries = []
    for path in RESULTS.glob("final_summary_*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        summaries.append((int(data.get("mc_seeds", 0)), path.stat().st_mtime, path, data))
    if not summaries:
        raise FileNotFoundError("run the final calibration pipeline first")
    _, _, summary_path, summary = max(summaries)
    run_id = summary["run_id"]
    csv_path = RESULTS / f"final_pipeline_{run_id}.csv"
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return summary_path, csv_path, summary, rows


def _save(fig, stem):
    for suffix in ("png", "svg", "pdf"):
        fig.savefig(OUT / f"{stem}.{suffix}", dpi=220, bbox_inches="tight")
    svg_path = OUT / f"{stem}.svg"
    svg_text = svg_path.read_text(encoding="utf-8")
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n",
        encoding="utf-8",
    )
    plt.close(fig)


def _style(ax, title, ylabel=None):
    ax.set_title(title, weight="bold")
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)


def architecture():
    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.axis("off")
    labels = [
        ("Full-array\nsampling", 0.04, COLORS["blue"]),
        ("138-Cu split CDAC\ncharge solver", 0.24, COLORS["green"]),
        ("15 asynchronous\ncomparisons", 0.45, COLORS["orange"]),
        ("7-target foreground\nweight calibration", 0.66, COLORS["purple"]),
        ("Plain weighted sum\nQ2 output", 0.86, COLORS["blue"]),
    ]
    for label, x, color in labels:
        ax.text(
            x, 0.5, label, ha="center", va="center", color="white",
            fontsize=11, weight="bold",
            bbox=dict(boxstyle="round,pad=0.65", fc=color, ec="none"),
            transform=ax.transAxes,
        )
    for x0, x1 in zip([0.11, 0.32, 0.53, 0.74], [0.18, 0.39, 0.60, 0.81]):
        ax.annotate(
            "", xy=(x1, 0.5), xytext=(x0, 0.5),
            arrowprops=dict(arrowstyle="->", lw=2, color=COLORS["gray"]),
            xycoords=ax.transAxes,
        )
    ax.text(
        0.5, 0.12,
        "No LUT, DP remap, sparse exception table, or hidden low-segment input path",
        ha="center", transform=ax.transAxes, fontsize=10,
    )
    _save(fig, "fig01_model_architecture")


def capacitor_topology():
    high = [32, 16, 8, 8, 4, 2, 1]
    low = [32, 16, 8, 4, 2, 2, 1]
    labels = ["H32", "H16", "H8A", "H8R", "H4", "H2", "H1",
              "B", "L32", "L16", "L8", "L4", "L2A", "L2R", "L1"]
    values = high + [2] + low
    colors = [COLORS["blue"]] * 7 + [COLORS["orange"]] + [COLORS["green"]] * 7
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.bar(labels, values, color=colors)
    _style(ax, "Active integer CDAC: 71 Cu | 2 Cu bridge | 65 Cu", "Capacitance (Cu)")
    ax.text(0.99, 0.93, "138 Cu per side", ha="right", transform=ax.transAxes, weight="bold")
    _save(fig, "fig02_cdac_topology")


def weights_and_margins():
    weights = np.asarray(cfg.NOMINAL_WEIGHTS_Q0, dtype=float)
    labels = cfg.STAGE_NAMES
    margins = np.asarray([
        np.sum(weights[index + 1:]) - weight
        for index, weight in enumerate(weights[:-1])
    ])
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=False)
    axes[0].bar(labels, weights, color=COLORS["blue"])
    axes[0].set_yscale("log")
    _style(axes[0], "Bridge-derived effective decision weights", "Q0 weight (log)")
    axes[1].bar(labels[:-1], margins, color=np.where(margins >= 0, COLORS["green"], COLORS["orange"]))
    axes[1].axhline(0, color="black", lw=1)
    _style(axes[1], "Backend range minus current weight", "Q0 margin")
    axes[1].tick_params(axis="x", rotation=45)
    _save(fig, "fig03_weights_and_redundancy")


def dynamic_mc(rows):
    seeds = np.asarray([int(row["seed"]) for row in rows])
    before = np.asarray([float(row["nominal_sndr"]) for row in rows])
    calibrated = np.asarray([float(row["calibrated_sndr"]) for row in rows])
    oracle = np.asarray([float(row["physical_sndr"]) for row in rows])
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.scatter(seeds, before, s=18, label="Before calibration", color=COLORS["orange"])
    ax.scatter(seeds, calibrated, s=18, label="Calibrated Q2", color=COLORS["green"])
    ax.scatter(seeds, oracle, s=14, label="Physical oracle", color=COLORS["blue"])
    _style(ax, "Monte Carlo dynamic performance", "SNDR (dB)")
    ax.set_xlabel("Seed")
    ax.legend(ncol=3)
    _save(fig, "fig04_dynamic_monte_carlo")


def gap_distribution(rows):
    gap = np.sort(np.asarray([float(row["oracle_gap_db"]) for row in rows]))
    cdf = np.arange(1, len(gap) + 1) / len(gap)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.plot(gap, cdf, lw=2.4, color=COLORS["blue"])
    ax.axvline(0.5, ls="--", color=COLORS["green"], label="0.5 dB target")
    _style(ax, "Calibration gap to physical oracle", "Empirical CDF")
    ax.set_xlabel("Oracle gap (dB)")
    ax.legend()
    _save(fig, "fig05_oracle_gap_cdf")


def static_mc(rows):
    dnl = np.asarray([float(row["dnl_peak"]) for row in rows])
    inl = np.asarray([float(row["inl_peak"]) for row in rows])
    back = np.asarray([int(row["n_non_monotonic"]) for row in rows])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    axes[0].boxplot([dnl, inl], tick_labels=["DNL peak", "INL peak"])
    axes[0].axhline(1.0, ls="--", color=COLORS["orange"])
    _style(axes[0], "Exact code-density static metrics", "LSB")
    axes[1].hist(back, bins=16, color=COLORS["purple"], alpha=0.85)
    _style(axes[1], "Formal sub-LSB overlap diagnostic", "Seed count")
    axes[1].set_xlabel("Integer backstep boundaries per seed")
    _save(fig, "fig06_static_signoff")


def calibration_error(summary):
    errors = summary["weight_errors"]
    labels = list(errors)
    p50 = [errors[label]["P50"] for label in labels]
    p95 = [errors[label]["P95"] for label in labels]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.bar(x - 0.18, p50, 0.36, label="P50", color=COLORS["blue"])
    ax.bar(x + 0.18, p95, 0.36, label="P95", color=COLORS["orange"])
    ax.set_xticks(x, labels)
    _style(ax, "Per-target calibration error", "Absolute error (Q0)")
    ax.legend()
    _save(fig, "fig07_calibration_error")


def hardware_cost():
    labels = ["Capacitance\n(Cu/side)", "Normal\ncomparisons", "Calibration\nsub-conversions / 1000"]
    old = [128, 14, 14.336]
    new = [138, 15, 14.336]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(x - 0.2, old, 0.4, label="Retired v2.1", color="#BBBBBB")
    ax.bar(x + 0.2, new, 0.4, label="v3.0", color=COLORS["green"])
    ax.set_xticks(x, labels)
    _style(ax, "Hardware and timing delta", "Normalized displayed value")
    ax.legend()
    ax.text(1, 20, "+1 normal comparison", ha="center")
    ax.text(2, 25, "Calibration work unchanged", ha="center")
    _save(fig, "fig08_hardware_cost")


def candidate_comparison():
    audit_path = (
        SRC / "python_cal" / "validation_results" / "cdac_design_audit.json"
    )
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    old = audit["candidates"]["retired_95cu"]["summary"]
    new = audit["candidates"]["v3_138cu"]["summary"]
    labels = ["Missing codes", "Max jump", "DNL peak", "INL peak"]
    old_values = [
        old["missing_codes"]["p50"],
        old["max_integer_jump"]["max"],
        old["dnl_peak_lsb"]["p95"],
        old["inl_peak_lsb"]["p95"],
    ]
    new_values = [
        new["missing_codes"]["p50"],
        new["max_integer_jump"]["max"],
        new["dnl_peak_lsb"]["p95"],
        new["inl_peak_lsb"]["p95"],
    ]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    ax.bar(x - 0.2, old_values, 0.4, label="Retired 95 Cu", color=COLORS["orange"])
    ax.bar(x + 0.2, new_values, 0.4, label="v3.0 138 Cu", color=COLORS["green"])
    ax.set_xticks(x, labels)
    _style(ax, "1000-seed CDAC architecture audit", "Reported value")
    ax.legend()
    _save(fig, "fig09_cdac_candidate_comparison")


def main():
    summary_path, csv_path, summary, rows = _load_release()
    architecture()
    capacitor_topology()
    weights_and_margins()
    dynamic_mc(rows)
    gap_distribution(rows)
    static_mc(rows)
    calibration_error(summary)
    hardware_cost()
    candidate_comparison()
    manifest = {
        "summary": str(summary_path.relative_to(ROOT)),
        "table": str(csv_path.relative_to(ROOT)),
        "figures": [f"fig{index:02d}" for index in range(1, 10)],
        "window": "rectangular",
        "generated_from_code": True,
    }
    (OUT / "figure_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"Generated 9 figure sets in {OUT}")


if __name__ == "__main__":
    main()
