#!/usr/bin/env python3
"""
IEEE TVLSI Paper Figures Generator v2
High-quality academic plots matching paper data exactly.
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

# ---------------------------------------------------------------------------
# IEEE Style Setup
# ---------------------------------------------------------------------------
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
rcParams['mathtext.fontset'] = 'stix'
rcParams['font.size'] = 9
rcParams['axes.labelsize'] = 10
rcParams['axes.titlesize'] = 10
rcParams['xtick.labelsize'] = 8
rcParams['ytick.labelsize'] = 8
rcParams['legend.fontsize'] = 8
rcParams['axes.linewidth'] = 0.8
rcParams['xtick.direction'] = 'in'
rcParams['ytick.direction'] = 'in'
rcParams['xtick.major.width'] = 0.6
rcParams['ytick.major.width'] = 0.6
rcParams['lines.linewidth'] = 1.2
rcParams['figure.dpi'] = 300

# Color-blind friendly palette (Tol / IEEE modern)
C_BL = '#004488'   # deep blue
C_RD = '#BB5566'   # brick red
C_GN = '#228833'   # forest green
C_YL = '#DDAA33'   # muted gold
C_PR = '#AA3377'   # purple
C_CY = '#66CCEE'   # cyan
C_GY = '#888888'   # grey
C_BK = '#000000'
C_WH = '#FFFFFF'

COLORS = [C_BL, C_RD, C_GN, C_YL, C_PR, C_CY]
MARKERS = ['o', 's', '^', 'D', 'p', 'h']
LABELS_CORNER = ['TT', 'FF', 'SS', r'SF$_{-40}$', r'SF$_{35}$', 'FS']

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'figures')
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def save_fig(fig, name):
    fig.savefig(os.path.join(OUT_DIR, f'{name}.pdf'), format='pdf',
                bbox_inches='tight', pad_inches=0.02, transparent=True)
    fig.savefig(os.path.join(OUT_DIR, f'{name}.png'), format='png',
                bbox_inches='tight', pad_inches=0.02, dpi=300, transparent=True)
    plt.close(fig)
    print(f'  Saved {name}.pdf / .png')

# ---------------------------------------------------------------------------
# Fig.4  PVT ENOB Comparison (24.1 ns)  — 论文实际引用
# ---------------------------------------------------------------------------
def fig4_pvt_enob():
    print('[1/5] Fig.4 PVT ENOB Comparison...')

    # Data from Table in paper (tab:pvt 24.1ns column)
    enob_on  = np.array([10.78, 10.64, 10.68, 10.92, 10.59, 10.77])
    enob_off = np.array([10.35, 10.36, 10.50, 10.51, 10.12, 10.37])
    delta    = enob_on - enob_off

    fig, ax = plt.subplots(figsize=(3.5, 2.2))
    x = np.arange(len(LABELS_CORNER))
    bw = 0.35

    bars_off = ax.bar(x - bw/2, enob_off, bw, label='Without CAAZ',
                      color='#B3D9F2', edgecolor='white', linewidth=0.5, zorder=3)
    bars_on  = ax.bar(x + bw/2, enob_on,  bw, label='With CAAZ',
                      color=C_BL, edgecolor='white', linewidth=0.5, zorder=3)

    # Delta annotations
    for i, (d, on, off) in enumerate(zip(delta, enob_on, enob_off)):
        ymax = max(on, off)
        ax.annotate(f'+{d:.2f}', xy=(x[i], ymax), xytext=(0, 4),
                    textcoords='offset points', ha='center', va='bottom',
                    fontsize=7, color=C_RD, fontweight='bold', zorder=5)

    # Target line
    ax.axhline(10.5, color=C_BK, linestyle='--', linewidth=0.8, zorder=2)
    ax.text(5.35, 10.47, 'target', fontsize=7, color=C_BK,
            ha='right', va='top', fontstyle='italic')

    ax.set_xticks(x)
    ax.set_xticklabels(LABELS_CORNER)
    ax.set_ylabel('ENOB [bit]')
    ax.set_xlabel('Process Corner')
    ax.set_xlim(-0.5, len(LABELS_CORNER)-0.5)
    ax.set_ylim(9.8, 11.5)
    ax.tick_params(axis='both', which='both', length=2.5, pad=2)
    ax.legend(loc='upper right', frameon=True, edgecolor=C_BK, fancybox=False,
              framealpha=0.9)
    ax.grid(True, linestyle=':', alpha=0.25, color=C_BK, zorder=1)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    save_fig(fig, 'Fig4_Noise_Suppression')

# ---------------------------------------------------------------------------
# Fig.5  Noise Decomposition Waterfall  — 研究报告用
# ---------------------------------------------------------------------------
def fig5_noise_waterfall():
    print('[2/5] Fig.5 Noise Decomposition Waterfall...')

    # Data from paper Table I (tab:noise)
    stages = ['Quantization\nOnly', 'Raw kT/C\nAdded', 'CAAZ\nCancelled', 'Full\nSystem']
    # ENOB values derived from SNR: ENOB = (SNR - 1.76) / 6.02
    snr_vals = [74.0, 71.4, 73.4, 70.8]
    enob_vals = [(s - 1.76) / 6.02 for s in snr_vals]
    enob_vals = [round(e, 2) for e in enob_vals]  # [11.99, 11.57, 11.90, 11.47]

    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    x = np.arange(len(stages))
    colors_bar = [C_GN, C_RD, C_BL, C_PR]

    bars = ax.bar(x, enob_vals, 0.55, color=colors_bar, edgecolor='white',
                  linewidth=0.5, zorder=3)

    # Value labels on bars
    for bar, val in zip(bars, enob_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f'{val:.2f}', ha='center', va='bottom', fontsize=8,
                fontweight='bold', color=C_BK)

    # Delta arrows (drawn between bars)
    deltas = [enob_vals[i+1] - enob_vals[i] for i in range(len(enob_vals)-1)]
    for i, d in enumerate(deltas):
        x0 = x[i] + 0.55/2 + 0.12
        x1 = x[i+1] - 0.55/2 - 0.12
        y0 = enob_vals[i]
        y1 = enob_vals[i+1]
        ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle='->', color=C_GY, lw=1.0,
                                    connectionstyle='arc3,rad=0'))
        sign = '+' if d > 0 else ''
        label_y = max(y0, y1) + 0.08
        ax.text((x0+x1)/2, label_y,
                f'{sign}{d:.2f}', ha='center', va='bottom', fontsize=7,
                color=C_RD, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(stages, fontsize=7)
    ax.set_ylabel('ENOB [bit]')
    ax.set_ylim(11.0, 12.3)
    ax.grid(True, axis='y', linestyle=':', alpha=0.25, color=C_BK, zorder=1)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    save_fig(fig, 'Fig5_Noise_Waterfall')

# ---------------------------------------------------------------------------
# Fig.6  Offset Sensitivity  — 论文实际引用 (修正数据)
# ---------------------------------------------------------------------------
def fig6_offset_sensitivity():
    print('[3/5] Fig.6 Offset Sensitivity (corrected data)...')

    # CORRECTED: from CSV / Table II in paper
    vos   = np.array([0, 2, 5])
    e_avg = np.array([11.08, 11.13, 10.89])   # FIXED: was [10.94, ...]
    e_std = np.array([0.12, 0.10, 0.03])

    fig, ax = plt.subplots(figsize=(3.5, 2.2))

    ax.errorbar(vos, e_avg, yerr=e_std, fmt='o-', color=C_BL,
                markersize=7, markerfacecolor=C_BL, markeredgecolor='white',
                markeredgewidth=0.8, linewidth=1.5, capsize=4, capthick=1.0,
                zorder=3, label='ENOB (mean ± std)')

    # Annotation box
    ax.text(3.5, 10.95, 'ENOB drop < 0.25 bit\nat 5 mV input offset',
            fontsize=7, color=C_RD, fontweight='bold',
            ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                      edgecolor=C_BK, linewidth=0.6))

    ax.set_xlim(-0.8, 6.2)
    ax.set_ylim(10.70, 11.30)
    ax.set_xticks(vos)
    ax.set_xlabel('Injected Input Offset [mV]')
    ax.set_ylabel('ENOB [bit]')
    ax.grid(True, linestyle=':', alpha=0.25, color=C_BK, zorder=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis='both', which='both', length=2.5, pad=2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    save_fig(fig, 'Fig6_Offset_Sensitivity')

# ---------------------------------------------------------------------------
# Fig.7  Settling Time Sweep  — 研究报告用
# ---------------------------------------------------------------------------
def fig7_time_window():
    print('[4/5] Fig.7 Settling Time Sweep...')

    td = np.array([1, 2, 5, 10])
    dat = np.array([
        [10.85, 11.22, 11.47, 11.48],
        [10.78, 11.15, 11.39, 11.40],
        [10.88, 11.25, 11.50, 11.51],
        [10.86, 11.23, 11.48, 11.49],
        [10.83, 11.20, 11.45, 11.46],
        [10.84, 11.21, 11.46, 11.47],
    ])

    fig, ax = plt.subplots(figsize=(3.5, 2.4))

    for i in range(6):
        ax.plot(td, dat[i], '-'+MARKERS[i], color=COLORS[i],
                markersize=5, markerfacecolor='white', markeredgewidth=0.8,
                linewidth=1.2, label=LABELS_CORNER[i], zorder=3)

    ax.set_xlim(0.3, 10.7)
    ax.set_ylim(10.6, 11.7)
    ax.set_xticks(td)
    ax.set_xlabel(r'Settling Time $t_d$ [ns]')
    ax.set_ylabel('ENOB [bit]')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.22),
              ncol=6, frameon=True, edgecolor=C_BK, fancybox=False,
              framealpha=0.9, columnspacing=0.8)
    ax.grid(True, linestyle=':', alpha=0.25, color=C_BK, zorder=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis='both', which='both', length=2.5, pad=2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    save_fig(fig, 'Fig7_Time_Window_Sweep')

# ---------------------------------------------------------------------------
# Fig.8  Noise Distribution  — 论文实际引用 (现代饼图风格)
# ---------------------------------------------------------------------------
def fig8_noise_distribution():
    print('[5/5] Fig.8 Noise Distribution (modern pie charts)...')

    # Data from Table I (tab:noise)
    labels = ['Quantization\nNoise', r'kT/C Sampling\nNoise', 'Other Circuit\nNoise']
    without = [38.95, 31.40, 29.65]
    with_caa = [52.49, 7.60, 39.91]
    colors = ['#E8D5B7', C_RD, C_BL]  # pale gold, red, blue

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2))

    # Left: Without CAAZ
    ax = axes[0]
    wedges, texts, autotexts = ax.pie(
        without, labels=None, autopct='%1.1f%%',
        colors=colors, startangle=90, counterclock=False,
        pctdistance=0.65, wedgeprops=dict(width=0.45, edgecolor='white', linewidth=1.5))
    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_fontweight('bold')
        autotext.set_color(C_BK)
    ax.set_title('Without CAAZ', fontsize=10, fontweight='bold', pad=10)
    ax.text(0, -1.35, 'Total: 1.656$\\times$10$^{-7}$ V$^2$\nSNR: 69.91 dB',
            ha='center', va='top', fontsize=8, color=C_GY)

    # Right: With CAAZ
    ax = axes[1]
    wedges2, texts2, autotexts2 = ax.pie(
        with_caa, labels=None, autopct='%1.1f%%',
        colors=colors, startangle=90, counterclock=False,
        pctdistance=0.65, wedgeprops=dict(width=0.45, edgecolor='white', linewidth=1.5))
    for autotext in autotexts2:
        autotext.set_fontsize(9)
        autotext.set_fontweight('bold')
        autotext.set_color(C_BK)
    ax.set_title('With CAAZ', fontsize=10, fontweight='bold', pad=10)
    ax.text(0, -1.35, 'Total: 1.229$\\times$10$^{-7}$ V$^2$\nSNR: 70.80 dB',
            ha='center', va='top', fontsize=8, color=C_GY)

    # Shared legend below
    fig.legend(wedges, ['Quantization Noise', r'kT/C Sampling Noise', 'Other Circuit Noise'],
               loc='lower center', ncol=3, frameon=False,
               bbox_to_anchor=(0.5, -0.02), fontsize=8)

    plt.tight_layout(rect=[0, 0.06, 1, 1])
    save_fig(fig, 'Fig8_Noise_Pie_Charts')

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print('=== IEEE TVLSI Figures Generator v2 ===')
    fig4_pvt_enob()
    fig5_noise_waterfall()
    fig6_offset_sensitivity()
    fig7_time_window()
    fig8_noise_distribution()
    print(f'=== All figures saved to {OUT_DIR} ===')
