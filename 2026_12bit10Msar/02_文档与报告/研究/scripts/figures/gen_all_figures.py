#!/usr/bin/env python3
"""Generate refined publication-quality figures for CAAZ SAR ADC report.
Fixes: text overlap, label positioning, spacing."""

import sys, os
from pathlib import Path

SKILL = Path.home() / ".claude" / "skills" / "figura"
sys.path.insert(0, str(SKILL / "scripts"))

os.environ["MPLBACKEND"] = "Agg"
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pubstyle, colors, export

pubstyle.apply()

OUTDIR = Path("D:/ReedZhao/Document/Obsidian/日常/10_项目区/2026_12bit50Msar/05_研究报告/figures")
OUTDIR.mkdir(parents=True, exist_ok=True)

corners = ["TT", "FF", "SS", "SF", "FS"]
C = colors.categorical()

# Shared data
td24_enob = [11.38, 11.47, 11.18, 11.24, 11.42]
td26_enob = [11.61, 11.49, 11.55, 11.53, 11.47]
td24_snr  = [70.39, 70.79, 69.66, 69.44, 70.30]
td26_snr  = [71.81, 71.16, 71.48, 71.29, 70.92]

# ==================== FIGURE 1: PVT Performance (wider, cleaner) ====================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 3.8))
fig.suptitle("ADC Performance Across PVT Corners (NF=1)", fontsize=12, fontweight="bold", y=1.02)

x = np.arange(len(corners))
w = 0.30  # narrower bars for more space

def add_bar_labels(ax, bars, values, color, offset=0, fs=7.5):
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + offset,
                f"{val:.2f}", ha="center", va="bottom",
                fontsize=fs, color=color, fontweight="bold")

# Panel A: ENOB
ax1.bar(x - w/2, td24_enob, w, label=r"$t_d$=24.05 ns",
        color=C[0], alpha=0.85, edgecolor="white", linewidth=0.5)
b1 = ax1.bar(x + w/2, td26_enob, w, label=r"$t_d$=26.0 ns",
        color=C[1], alpha=0.85, edgecolor="white", linewidth=0.5)
ax1.set_ylabel("ENOB (bit)", fontsize=10)
ax1.set_xticks(x); ax1.set_xticklabels(corners, fontsize=10)
ax1.set_ylim(10.2, 12.1)
ax1.axhline(y=11.0, color="gray", ls="--", lw=0.8, alpha=0.5)
ax1.annotate("Target 11 bit", xy=(0.02, 11.05), fontsize=7, color="gray",
             xycoords=ax1.get_yaxis_transform())
add_bar_labels(ax1, b1, td26_enob, C[1], offset=0.15, fs=8)
# Only label top 3 for td24 to reduce clutter
for i in [0, 2, 3]:
    ax1.text(x[i] - w/2, td24_enob[i] + 0.08, f"{td24_enob[i]:.2f}",
             ha="center", va="bottom", fontsize=6.5, color=C[0])

# Panel B: SNR
ax2.bar(x - w/2, td24_snr, w, label=r"$t_d$=24.05 ns",
        color=C[0], alpha=0.85, edgecolor="white", linewidth=0.5)
b2 = ax2.bar(x + w/2, td26_snr, w, label=r"$t_d$=26.0 ns",
        color=C[1], alpha=0.85, edgecolor="white", linewidth=0.5)
ax2.set_ylabel("SNR (dB)", fontsize=10)
ax2.set_xticks(x); ax2.set_xticklabels(corners, fontsize=10)
ax2.set_ylim(66, 74)
ax2.axhline(y=70, color="gray", ls="--", lw=0.8, alpha=0.5)
ax2.annotate("Target 70 dB", xy=(0.02, 70.5), fontsize=7, color="gray",
             xycoords=ax2.get_yaxis_transform())
add_bar_labels(ax2, b2, td26_snr, C[1], offset=0.3, fs=8)

# Delta annotations with arrows
for i in range(len(corners)):
    delta = td26_snr[i] - td24_snr[i]
    color = C[3] if delta > 1.5 else "gray"
    ax2.annotate(f"+{delta:.2f} dB", (x[i] + w/2, td26_snr[i] + 0.65),
                ha="center", fontsize=7.5, color=color, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=color, lw=0.5))

ax1.legend(fontsize=8, frameon=False, loc="lower right")
ax2.legend(fontsize=8, frameon=False, loc="lower right")
plt.tight_layout()
export.save(fig, "Fig1_PVT_Performance", outdir=str(OUTDIR), formats=("pdf", "svg", "png"))
plt.close()
print("[OK] Fig1 saved")

# ==================== FIGURE 2: CAAZ Eta (wider bars, better labels) ====================
eta_b1 = [86.8, 89.4, 82.5, 78.8, 90.9]
eta_b2 = [87.9, 89.4, 83.9, 79.7, 91.2]

fig, ax = plt.subplots(figsize=(5.5, 3.8))
fig.suptitle(r"CAAZ Noise Cancellation Efficiency $\eta$", fontsize=12, fontweight="bold", y=1.02)

x = np.arange(len(corners))
w = 0.30

b1 = ax.bar(x - w/2, eta_b1, w, label="Batch 1 (old export)",
            color=C[2], alpha=0.85, edgecolor="white", linewidth=0.5)
b2 = ax.bar(x + w/2, eta_b2, w, label="Batch 2 (new export)",
            color=C[3], alpha=0.85, edgecolor="white", linewidth=0.5)

ax.axhline(y=85, color="red", ls="--", lw=1.0, alpha=0.6, zorder=0)
ax.text(4.5, 85.5, r"$\eta$=85% target", fontsize=7.5, color="red", ha="right")

ax.set_ylabel(r"$\eta$ (%)", fontsize=10)
ax.set_xticks(x); ax.set_xticklabels(corners, fontsize=11)
ax.set_ylim(70, 100)

# Labels: batch1 above bar, batch2 below top edge with offset
for i in range(len(corners)):
    ax.text(x[i] - w/2, eta_b1[i] + 0.3, f"{eta_b1[i]:.1f}%",
            ha="center", fontsize=7.5, color=C[2])
    ax.text(x[i] + w/2, eta_b2[i] + 0.3, f"{eta_b2[i]:.1f}%",
            ha="center", fontsize=7.5, fontweight="bold", color=C[3])

# SF annotation moved to safer position
ax.annotate("Worst PVT\nSF 79.7%", xy=(3.2, 79.7), xytext=(4.3, 75),
            arrowprops=dict(arrowstyle="->", color="red", lw=0.8),
            fontsize=8, color="red", ha="center",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="red", alpha=0.8))

ax.legend(fontsize=8, frameon=False, loc="lower left")
plt.tight_layout()
export.save(fig, "Fig2_CAAZ_Eta", outdir=str(OUTDIR), formats=("pdf", "svg", "png"))
plt.close()
print("[OK] Fig2 saved")

# ==================== FIGURE 3: Power Breakdown (donut + horizontal bar) ====================
modules = ["COMPOWER\n(preamp+SR)", "SWITCHPOWER\n(switch)", "LOGICPOWER\n(SAR_LOGIC)", "SYNCPOWER\n(SYNC)"]
powers = [363.7, 97.14, 149.0, 110.4]
total = sum(powers)
pcts = [p/total*100 for p in powers]
pcolors = [C[0], C[1], C[2], C[4]]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.8),
                                gridspec_kw={"width_ratios": [1.2, 1.8]})
fig.suptitle(rf"Power Breakdown (TT, $t_d$=26ns, NF=1)  —  Total: {total:.0f} $\mu$W",
             fontsize=11, fontweight="bold", y=1.02)

# Donut pie
wedges, texts = ax1.pie(powers, labels=None, colors=pcolors,
                         startangle=90, wedgeprops={"edgecolor": "white", "linewidth": 1.5},
                         radius=1.2)
# Add center label
ax1.annotate(f"{total:.0f}\n$\mu$W", (0, 0), fontsize=14, fontweight="bold",
             color="gray", ha="center", va="center")
# Label wedges with arrows
for i, (wedge, pct) in enumerate(zip(wedges, pcts)):
    ang = (wedge.theta2 + wedge.theta1) / 2
    r = 1.5
    xa = r * np.cos(np.deg2rad(ang))
    ya = r * np.sin(np.deg2rad(ang))
    ang_mid = np.deg2rad((wedge.theta2 + wedge.theta1) / 2)
    cx = 0.6 * np.cos(ang_mid)
    cy = 0.6 * np.sin(ang_mid)
    ax1.annotate(f"{modules[i].split(chr(10))[0]}\n{pct:.0f}%",
                 xy=(cx, cy),
                 xytext=(xa, ya),
                 arrowprops=dict(arrowstyle="->", lw=0.6, color="gray"),
                 ha="center", fontsize=8, color="black")

# Horizontal bar
bars = ax2.barh(modules, powers, color=pcolors, edgecolor="white",
                 height=0.55, alpha=0.9)
ax2.set_xlim(0, 450)
ax2.set_xlabel("Power ($\mu$W)", fontsize=10)
for bar, pct in zip(bars, pcts):
    ax2.text(bar.get_width() + 8, bar.get_y() + bar.get_height()/2,
             f"{bar.get_width():.0f} $\mu$W  ({pct:.0f}%)",
             va="center", fontsize=9, fontweight="bold", color="black")

plt.tight_layout()
export.save(fig, "Fig3_Power_Breakdown", outdir=str(OUTDIR), formats=("pdf", "svg", "png"))
plt.close()
print("[OK] Fig3 saved")

# ==================== FIGURE 4: td Sweep (cleaner layout) ====================
fig, ax = plt.subplots(figsize=(5.5, 3.8))
fig.suptitle("Impact of $t_d$ Extension on SNR", fontsize=12, fontweight="bold", y=1.02)

x = np.arange(len(corners))
w = 0.30

ax.bar(x - w/2, td24_snr, w, label=r"$t_d$=24.05 ns ($\eta\approx$0)",
       color=C[0], alpha=0.85, edgecolor="white", linewidth=0.5)
b = ax.bar(x + w/2, td26_snr, w, label=r"$t_d$=26.0 ns ($\eta$ active)",
       color=C[1], alpha=0.85, edgecolor="white", linewidth=0.5)

ax.set_ylabel("SNR (dB)", fontsize=10)
ax.set_xticks(x); ax.set_xticklabels(corners, fontsize=11)
ax.set_ylim(66, 75)
ax.legend(fontsize=8, frameon=False, loc="lower right")

# Delta labels with green/orange color coding
for i in range(len(corners)):
    delta = td26_snr[i] - td24_snr[i]
    clr = C[3] if delta > 1.5 else "gray"
    ax.annotate(f"+{delta:.2f} dB", (x[i] + w/2, td26_snr[i] + 0.5),
                ha="center", fontsize=9, fontweight="bold", color=clr)
    # also show td24 value below
    ax.text(x[i] - w/2, td24_snr[i] - 0.5, f"{td24_snr[i]:.1f}",
            ha="center", fontsize=7, color=C[0])
    ax.text(x[i] + w/2, td26_snr[i] - 0.5, f"{td26_snr[i]:.1f}",
            ha="center", fontsize=7, color=C[1], fontweight="bold")

plt.tight_layout()
export.save(fig, "Fig4_td_Sweep_SNR", outdir=str(OUTDIR), formats=("pdf", "svg", "png"))
plt.close()
print("[OK] Fig4 saved")
print("[OK] ALL FIGURES GENERATED")
