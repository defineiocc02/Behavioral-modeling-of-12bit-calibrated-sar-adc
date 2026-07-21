from __future__ import annotations

import sys
from pathlib import Path

SKILL_SCRIPTS = Path(r"C:\Users\Administrator\.agents\skills\figura\scripts")
sys.path.insert(0, str(SKILL_SCRIPTS))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

import colors
import export
import pubstyle


pubstyle.apply(venue="ieee")
colors.apply_cycle()
PALETTE = colors.categorical()


def digital_trace(ax, y, intervals, color, label):
    for start, stop in intervals:
        ax.add_patch(Rectangle((start, y), stop - start, 0.55, facecolor=color, edgecolor="none"))
    ax.text(-2.5, y + 0.275, label, ha="right", va="center")


def main() -> None:
    outdir = Path(__file__).resolve().parent.parent / "figures"
    fig, axes = plt.subplots(2, 1, figsize=(6.8, 4.8), constrained_layout=True)

    ax = axes[0]
    targets = [
        ("C12", "2053.81", 0),
        ("C11", "1027.82", 1),
        ("C10", "513.12", 2),
        ("C9", "256", 3),
        ("CR", "256", 4),
        ("C8", "128", 5),
    ]
    for index, (name, weight, stage) in enumerate(targets):
        x = index * 1.0
        color = PALETTE[1] if name == "CR" else PALETTE[0]
        ax.add_patch(Rectangle((x, 1.15), 0.82, 0.72, facecolor=color, alpha=0.18, edgecolor=color, lw=1.0))
        ax.text(x + 0.41, 1.56, name, ha="center", va="center", weight="bold")
        ax.text(x + 0.41, 1.31, f"w={weight}\nstage {stage}", ha="center", va="center", fontsize=7)
        sequence = 6 - index
        ax.text(x + 0.41, 2.02, f"{sequence}", ha="center", va="center", color=color, weight="bold")

    low_x = 1.35
    low_w = 3.35
    ax.add_patch(Rectangle((low_x, 0.02), low_w, 0.72, facecolor=PALETTE[2], alpha=0.18, edgecolor=PALETTE[2], lw=1.0))
    ax.text(low_x + low_w / 2, 0.47, "Six-bit calibration DAC: C7 ... C1", ha="center", va="center", weight="bold")
    ax.text(low_x + low_w / 2, 0.20, "decoder weights 48+32+20+12+8+4+2; half-weight search range = 63 LSB", ha="center", va="center", fontsize=7)
    ax.add_patch(
        FancyArrowPatch(
            (low_x + low_w / 2, 0.74),
            (5.41, 1.12),
            arrowstyle="-|>",
            mutation_scale=9,
            color=PALETTE[2],
            lw=1.1,
            connectionstyle="arc3,rad=-0.12",
        )
    )
    ax.text(5.0, 0.82, "measure C8 first", color=PALETTE[2], fontsize=7, ha="right")
    ax.text(3.0, 2.28, "Calibration order", ha="center", va="center", weight="bold")
    ax.annotate("", xy=(0.35, 2.02), xytext=(5.4, 2.02), arrowprops=dict(arrowstyle="-|>", color="0.35", lw=0.9))
    ax.set_xlim(-0.25, 5.9)
    ax.set_ylim(-0.05, 2.48)
    ax.axis("off")
    ax.set_title("(a) Physical CDAC hierarchy and recursive weight calibration", loc="left")

    ax = axes[1]
    ax.axvspan(0.0, 18.1, color=PALETTE[3], alpha=0.12, lw=0)
    ax.axvspan(18.1, 100.0, color=PALETTE[2], alpha=0.08, lw=0)
    digital_trace(ax, 3.0, [(0.1, 18.1)], PALETTE[3], "COM RST")
    digital_trace(ax, 2.1, [(0.1, 14.1)], PALETTE[1], "RST1")
    digital_trace(ax, 1.2, [(10, 15), (20, 25), (30, 35), (40, 45), (50, 55), (60, 65), (70, 75), (80, 85), (90, 95)], PALETTE[0], "CAL_CLK")
    digital_trace(ax, 0.3, [(22, 27), (32, 37), (42, 47), (52, 57), (62, 67), (72, 77), (82, 87), (92, 97)], PALETTE[4], "COMP CLK")
    sample_times = [25, 35, 45, 55, 65, 75, 85, 95]
    ax.scatter(sample_times, [0.12] * len(sample_times), s=14, marker="v", color=PALETTE[4], zorder=3)
    ax.axvline(14.1, color=PALETTE[1], lw=0.8, ls="--", alpha=0.8)
    ax.axvline(18.1, color=PALETTE[3], lw=0.8, ls="--", alpha=0.8)
    ax.text(13.6, 3.72, "frame arm", ha="right", va="bottom", fontsize=7)
    ax.text(18.6, 4.02, "IAZ release", ha="left", va="bottom", fontsize=7)
    ax.text(60, -0.25, "8 valid captures: sign + C7,C6,C5,C4,C3,C2,C1", ha="center", va="top", fontsize=7)
    ax.text(7.5, 0.05, "invalid", color=PALETTE[3], ha="center", va="center", fontsize=7)
    ax.text(58, 3.82, "valid calibration window", color=PALETTE[2], ha="center", va="center", fontsize=7)
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.45, 4.25)
    ax.set_xlabel("Time within one conversion frame (ns)")
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", alpha=0.22)
    ax.set_title("(b) Frame-synchronous comparator usage", loc="left")

    export.save(fig, "fig_architecture_timing", formats=("pdf", "svg", "png"), outdir=outdir)


if __name__ == "__main__":
    main()
