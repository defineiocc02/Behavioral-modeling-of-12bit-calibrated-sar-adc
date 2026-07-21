#!/usr/bin/env python3
"""Regenerate all research-report figures with professional figura styling."""

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

C = colors.categorical()

# ============ Fig4: Noise Suppression ============
fig, ax = plt.subplots(figsize=pubstyle.figsize("single"))
fig.suptitle(r"Noise Suppression Effect ($t_d$=24.1 ns)", fontsize=11, fontweight="bold", y=1.02)

corners_old = ["TT", "FF", "SS", r"SF$_{-40}$", r"SF$_{35}$", "FS"]
enob_with    = [10.78, 10.64, 10.68, 10.92, 10.59, 10.77]
enob_without = [10.35, 10.36, 10.50, 10.51, 10.12, 10.37]
delta_enob   = [0.43, 0.28, 0.18, 0.41, 0.47, 0.40]

x = np.arange(len(corners_old))
w = 0.30

b1 = ax.bar(x - w/2, enob_without, w, label="Without CAAZ",
            color=C[0], alpha=0.75, edgecolor="white", lw=0.5)
b2 = ax.bar(x + w/2, enob_with, w, label="With CAAZ",
            color=C[1], alpha=0.85, edgecolor="white", lw=0.5)

for i in range(len(corners_old)):
    ax.text(x[i]+w/2, enob_with[i]+0.06, f"+{delta_enob[i]:.2f}",
            ha="center", fontsize=7.5, fontweight="bold", color=C[3])

ax.set_ylabel("ENOB (bit)", fontsize=10)
ax.set_ylim(9.8, 11.3)
ax.set_xticks(x); ax.set_xticklabels(corners_old, fontsize=9)
ax.legend(fontsize=9, frameon=False)
plt.tight_layout()
export.save(fig, "Fig4_Noise_Suppression", outdir=str(OUTDIR), formats=("pdf", "svg", "png"))
plt.close()

# ============ Fig5: Noise Waterfall ============
fig, ax = plt.subplots(figsize=pubstyle.figsize("single"))
fig.suptitle("Noise Source Decomposition (TT Corner)", fontsize=11, fontweight="bold", y=1.02)

labels = ["Quant.", "Raw kT/C", "Other Circuit", "Total (w/o CAAZ)"]
values = [6.450e-8, 5.200e-8, 4.907e-8, 1.656e-7]
colors_wf = [C[0], C[2], C[4], "gray"]

xpos = np.arange(len(labels))
bars = ax.bar(xpos, values, color=colors_wf, alpha=0.85, edgecolor="white", lw=0.5)
ax.set_ylabel("Noise Power (V$^2$)", fontsize=10)
ax.set_xticks(xpos); ax.set_xticklabels(labels, fontsize=8, rotation=15)
for bar, val in zip(bars, values):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()*1.02,
            f"{val*1e8:.2f}e-8", ha="center", fontsize=7.5)
plt.tight_layout()
export.save(fig, "Fig5_Noise_Waterfall", outdir=str(OUTDIR), formats=("pdf", "svg", "png"))
plt.close()

# ============ Fig6: Offset Sensitivity ============
fig, ax = plt.subplots(figsize=pubstyle.figsize("single"))
fig.suptitle("Offset Sensitivity Analysis ($t_d$=25 ns)", fontsize=11, fontweight="bold", y=1.02)

offsets = [0, 2, 5]
enob_mean = [11.08, 11.13, 10.89]
enob_min  = [10.94, 11.03, 10.85]
enob_max  = [11.18, 11.25, 10.92]

ax.fill_between(offsets, enob_min, enob_max, alpha=0.15, color=C[1])
ax.plot(offsets, enob_mean, 'o-', color=C[1], lw=1.8, markersize=8, label="Mean ENOB")
ax.plot(offsets, enob_min, 'v--', color=C[0], lw=0.8, markersize=5, alpha=0.7, label="Min")
ax.plot(offsets, enob_max, '^--', color=C[0], lw=0.8, markersize=5, alpha=0.7, label="Max")

for i in range(len(offsets)):
    ax.annotate(f"{enob_mean[i]:.2f}", (offsets[i]+0.05, enob_mean[i]+0.1),
                fontsize=9, fontweight="bold", color=C[1])

ax.set_xlabel("Injected Offset (mV)", fontsize=10)
ax.set_ylabel("ENOB (bit)", fontsize=10)
ax.set_ylim(10.5, 11.6)
ax.legend(fontsize=8, frameon=False)
plt.tight_layout()
export.save(fig, "Fig6_Offset_Sensitivity", outdir=str(OUTDIR), formats=("pdf", "svg", "png"))
plt.close()

# ============ Fig7: Time Window Sweep ============
fig, ax = plt.subplots(figsize=pubstyle.figsize("single"))
fig.suptitle("Time Window Sweep ($t_d$=24.1--25.0 ns)", fontsize=11, fontweight="bold", y=1.02)

td_vals = [24.1, 24.3, 24.5, 24.7, 25.0]
enob_tt = [10.78, 10.82, 10.85, 10.89, 10.94]
enob_ff = [10.64, 10.68, 10.71, 10.73, 10.76]
enob_ss = [10.68, 10.75, 10.83, 10.92, 11.01]

ax.plot(td_vals, enob_tt, 'o-', color=C[0], lw=1.8, markersize=7, label="TT")
ax.plot(td_vals, enob_ff, 's-', color=C[1], lw=1.8, markersize=7, label="FF")
ax.plot(td_vals, enob_ss, 'D-', color=C[2], lw=1.8, markersize=7, label="SS")

ax.set_xlabel("$t_d$ (ns)", fontsize=10)
ax.set_ylabel("ENOB (bit)", fontsize=10)
ax.legend(fontsize=9, frameon=False)
plt.tight_layout()
export.save(fig, "Fig7_Time_Window_Sweep", outdir=str(OUTDIR), formats=("pdf", "svg", "png"))
plt.close()

# ============ Fig8: Noise Pie Charts ============
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3.6))
fig.suptitle("Noise Distribution: w/o CAAZ (left) vs w/ CAAZ (right)", fontsize=11, fontweight="bold", y=1.05)

labels_pie = ["Quantization", "kT/C Noise", "Other Circuit"]
colors_pie = [C[0], C[2], C[4]]

# Left: without CAAZ
data_left = [6.450e-8, 5.200e-8, 4.907e-8]
wedges_l, texts_l = ax1.pie(data_left, labels=None, colors=colors_pie,
    startangle=90, wedgeprops={"edgecolor":"white","lw":1})
ax1.set_title(f"Without CAAZ\nSNR≈69.6 dB", fontsize=10, color=C[0])

# Right: with CAAZ
data_right = [6.450e-8, 5.898e-9, 4.907e-8]
wedges_r, texts_r = ax2.pie(data_right, labels=None, colors=colors_pie,
    startangle=90, wedgeprops={"edgecolor":"white","lw":1})
ax2.set_title(f"With CAAZ\nSNR≈70.8 dB", fontsize=10, color=C[1])

# Shared legend
fig.legend(wedges_l, ["Quant. (39%)", "kT/C (31%→7%)", "Other (30%→48%)"],
           loc="lower center", ncol=3, fontsize=8, frameon=False)

plt.tight_layout(rect=[0,0.08,1,1])
export.save(fig, "Fig8_Noise_Pie_Charts", outdir=str(OUTDIR), formats=("pdf", "svg", "png"))
plt.close()

print("[OK] 5 research figures regenerated")
