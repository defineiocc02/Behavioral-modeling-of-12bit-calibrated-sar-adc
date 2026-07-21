#!/usr/bin/env python3
"""
IEEE TVLSI Paper Figures Generator v3
Strictly unified style: minimal, clean, consistent.
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

# ---------------------------------------------------------------------------
# STRICT UNIFIED STYLE
# ---------------------------------------------------------------------------
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
rcParams['mathtext.fontset'] = 'stix'
rcParams['font.size'] = 9
rcParams['axes.labelsize'] = 10
rcParams['axes.titlesize'] = 10
rcParams['xtick.labelsize'] = 9
rcParams['ytick.labelsize'] = 9
rcParams['legend.fontsize'] = 8.5
rcParams['axes.linewidth'] = 0.6
rcParams['xtick.direction'] = 'in'
rcParams['ytick.direction'] = 'in'
rcParams['xtick.major.width'] = 0.5
rcParams['ytick.major.width'] = 0.5
rcParams['xtick.minor.width'] = 0.3
rcParams['ytick.minor.width'] = 0.3
rcParams['lines.linewidth'] = 1.0
rcParams['figure.dpi'] = 300

# Single unified palette - all figures use ONLY these colors
C_PRIMARY   = '#1f4e79'   # deep blue (main)
C_SECONDARY = '#c55a5a'   # muted red (accent)
C_TERTIARY  = '#70ad47'   # green (tertiary)
C_QUAT      = '#ffc000'   # gold
C_QUIN      = '#9e480e'   # brown
C_SEN       = '#636363'   # gray
C_BLACK     = '#000000'
C_WHITE     = '#ffffff'
C_LIGHT     = '#d9e2f3'   # light blue fill
C_GRID      = '#d0d0d0'   # grid color

COLORS = [C_PRIMARY, C_SECONDARY, C_TERTIARY, C_QUAT, C_QUIN, C_SEN]
MARKERS = ['o', 's', '^', 'D', 'v', 'p']
LABELS_CORNER = ['TT', 'FF', 'SS', r'SF$_{-40}$', r'SF$_{35}$', 'FS']

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'figures')
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def setup_axis(ax, show_grid=True):
    """Apply unified axis style."""
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(0.6)
    ax.spines['bottom'].set_linewidth(0.6)
    ax.tick_params(axis='both', which='major', length=3, width=0.5, pad=2)
    ax.tick_params(axis='both', which='minor', length=1.5, width=0.3)
    if show_grid:
        ax.grid(True, linestyle='-', alpha=0.2, color=C_GRID, linewidth=0.4)
    ax.set_axisbelow(True)

def save_fig(fig, name):
    fig.savefig(os.path.join(OUT_DIR, f'{name}.pdf'), format='pdf',
                bbox_inches='tight', pad_inches=0.02, transparent=True)
    fig.savefig(os.path.join(OUT_DIR, f'{name}.png'), format='png',
                bbox_inches='tight', pad_inches=0.02, dpi=300, transparent=True)
    plt.close(fig)
    print(f'  Saved {name}.pdf / .png')

# ---------------------------------------------------------------------------
# Fig.4  PVT ENOB Comparison
# ---------------------------------------------------------------------------
def fig4_pvt_enob():
    print('[1/5] Fig.4 PVT ENOB...')
    enob_on  = np.array([10.78, 10.64, 10.68, 10.92, 10.59, 10.77])
    enob_off = np.array([10.35, 10.36, 10.50, 10.51, 10.12, 10.37])
    delta    = enob_on - enob_off

    fig, ax = plt.subplots(figsize=(3.5, 2.0))
    x = np.arange(len(LABELS_CORNER))
    bw = 0.32

    ax.bar(x - bw/2, enob_off, bw, label='Without CAAZ',
           color=C_LIGHT, edgecolor=C_PRIMARY, linewidth=0.5, zorder=3)
    ax.bar(x + bw/2, enob_on,  bw, label='With CAAZ',
           color=C_PRIMARY, edgecolor=C_PRIMARY, linewidth=0.5, zorder=3)

    for i, d in enumerate(delta):
        ymax = max(enob_on[i], enob_off[i])
        ax.text(x[i], ymax + 0.04, f'+{d:.2f}', ha='center', va='bottom',
                fontsize=7.5, color=C_SECONDARY, fontweight='bold')

    ax.axhline(10.5, color=C_BLACK, linestyle='--', linewidth=0.6, zorder=2)
    ax.text(5.3, 10.46, 'target', fontsize=7, color=C_SEN,
            ha='right', va='top', fontstyle='italic')

    ax.set_xticks(x)
    ax.set_xticklabels(LABELS_CORNER)
    ax.set_ylabel('ENOB [bit]')
    ax.set_xlabel('Process Corner')
    ax.set_xlim(-0.5, len(LABELS_CORNER)-0.5)
    ax.set_ylim(9.9, 11.4)
    ax.legend(loc='upper right', frameon=False, fontsize=8)
    setup_axis(ax)
    save_fig(fig, 'Fig4_Noise_Suppression')

# ---------------------------------------------------------------------------
# Fig.5  Noise Waterfall
# ---------------------------------------------------------------------------
def fig5_noise_waterfall():
    print('[2/5] Fig.5 Noise Waterfall...')
    stages = ['Quant.\nOnly', 'Raw kT/C\nAdded', 'CAAZ\nCancelled', 'Full\nSystem']
    snr_vals = [74.0, 71.4, 73.4, 70.8]
    enob_vals = [round((s - 1.76) / 6.02, 2) for s in snr_vals]

    fig, ax = plt.subplots(figsize=(3.5, 2.3))
    x = np.arange(len(stages))

    bars = ax.bar(x, enob_vals, 0.5, color=[C_TERTIARY, C_SECONDARY, C_PRIMARY, C_QUIN],
                  edgecolor=C_WHITE, linewidth=0.8, zorder=3)

    for bar, val in zip(bars, enob_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.03,
                f'{val:.2f}', ha='center', va='bottom', fontsize=9,
                fontweight='bold', color=C_BLACK)

    deltas = [enob_vals[i+1] - enob_vals[i] for i in range(3)]
    for i, d in enumerate(deltas):
        x_mid = (x[i] + x[i+1]) / 2
        y_mid = (enob_vals[i] + enob_vals[i+1]) / 2
        ax.annotate('', xy=(x[i+1]-0.28, enob_vals[i+1]),
                    xytext=(x[i]+0.28, enob_vals[i]),
                    arrowprops=dict(arrowstyle='->', color=C_SEN, lw=0.8))
        sign = '+' if d > 0 else ''
        ax.text(x_mid, max(enob_vals[i], enob_vals[i+1]) + 0.06,
                f'{sign}{d:.2f}', ha='center', va='bottom', fontsize=7.5,
                color=C_SECONDARY, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(stages, fontsize=8)
    ax.set_ylabel('ENOB [bit]')
    ax.set_ylim(11.2, 12.15)
    setup_axis(ax)
    save_fig(fig, 'Fig5_Noise_Waterfall')

# ---------------------------------------------------------------------------
# Fig.6  Offset Sensitivity
# ---------------------------------------------------------------------------
def fig6_offset_sensitivity():
    print('[3/5] Fig.6 Offset...')
    vos   = np.array([0, 2, 5])
    e_avg = np.array([11.08, 11.13, 10.89])
    e_std = np.array([0.12, 0.10, 0.03])

    fig, ax = plt.subplots(figsize=(3.5, 2.0))

    ax.errorbar(vos, e_avg, yerr=e_std, fmt='-o', color=C_PRIMARY,
                markersize=6, markerfacecolor=C_PRIMARY, markeredgecolor=C_WHITE,
                markeredgewidth=0.6, linewidth=1.2, capsize=3, capthick=0.8,
                zorder=3)

    ax.text(3.5, 10.96, 'ENOB drop < 0.25 bit\nat 5 mV offset',
            fontsize=7.5, color=C_SECONDARY, fontweight='bold',
            ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.25', facecolor=C_WHITE,
                      edgecolor=C_SEN, linewidth=0.5, alpha=0.95))

    ax.set_xlim(-0.6, 6.0)
    ax.set_ylim(10.72, 11.28)
    ax.set_xticks(vos)
    ax.set_xlabel('Injected Input Offset [mV]')
    ax.set_ylabel('ENOB [bit]')
    setup_axis(ax)
    save_fig(fig, 'Fig6_Offset_Sensitivity')

# ---------------------------------------------------------------------------
# Fig.7  Time Window
# ---------------------------------------------------------------------------
def fig7_time_window():
    print('[4/5] Fig.7 Time Window...')
    td = np.array([1, 2, 5, 10])
    dat = np.array([
        [10.85, 11.22, 11.47, 11.48],
        [10.78, 11.15, 11.39, 11.40],
        [10.88, 11.25, 11.50, 11.51],
        [10.86, 11.23, 11.48, 11.49],
        [10.83, 11.20, 11.45, 11.46],
        [10.84, 11.21, 11.46, 11.47],
    ])

    fig, ax = plt.subplots(figsize=(3.5, 2.2))

    for i in range(6):
        ax.plot(td, dat[i], '-'+MARKERS[i], color=COLORS[i],
                markersize=4.5, markerfacecolor=C_WHITE, markeredgewidth=0.6,
                linewidth=1.0, label=LABELS_CORNER[i], zorder=3)

    ax.set_xlim(0.5, 10.5)
    ax.set_ylim(10.65, 11.65)
    ax.set_xticks(td)
    ax.set_xlabel(r'Settling Time $t_d$ [ns]')
    ax.set_ylabel('ENOB [bit]')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.18),
              ncol=6, frameon=True, edgecolor=C_SEN, fancybox=False,
              framealpha=0.95, columnspacing=0.6, fontsize=7.5)
    setup_axis(ax)
    save_fig(fig, 'Fig7_Time_Window_Sweep')

# ---------------------------------------------------------------------------
# Fig.8  Pie Charts
# ---------------------------------------------------------------------------
def fig8_noise_distribution():
    print('[5/5] Fig.8 Pie...')
    colors = ['#f4e4c1', C_SECONDARY, C_PRIMARY]  # unified palette
    without = [38.95, 31.40, 29.65]
    with_caa = [52.49, 7.60, 39.91]

    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.8))

    for idx, (data, title, total_txt) in enumerate([
        (without, 'Without CAAZ', 'Total: 1.656$\\times$10$^{-7}$ V$^2$\nSNR: 69.91 dB'),
        (with_caa, 'With CAAZ', 'Total: 1.229$\\times$10$^{-7}$ V$^2$\nSNR: 70.80 dB')
    ]):
        ax = axes[idx]
        wedges, texts, autotexts = ax.pie(
            data, labels=None, autopct='%1.1f%%',
            colors=colors, startangle=90, counterclock=False,
            pctdistance=0.6, wedgeprops=dict(width=0.5, edgecolor=C_WHITE, linewidth=2))

        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_fontweight('bold')
            autotext.set_color(C_BLACK)

        ax.set_title(title, fontsize=10, fontweight='bold', pad=8, color=C_BLACK)
        ax.text(0, -1.25, total_txt, ha='center', va='top', fontsize=8, color=C_SEN)

    fig.legend(wedges, ['Quantization Noise', r'kT/C Sampling Noise', 'Other Circuit Noise'],
               loc='lower center', ncol=3, frameon=False,
               bbox_to_anchor=(0.5, -0.02), fontsize=8.5)

    plt.tight_layout(rect=[0, 0.06, 1, 1])
    save_fig(fig, 'Fig8_Noise_Pie_Charts')

# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print('=== IEEE TVLSI Figures v3 (Unified Style) ===')
    fig4_pvt_enob()
    fig5_noise_waterfall()
    fig6_offset_sensitivity()
    fig7_time_window()
    fig8_noise_distribution()
    print(f'=== Done: {OUT_DIR} ===')
