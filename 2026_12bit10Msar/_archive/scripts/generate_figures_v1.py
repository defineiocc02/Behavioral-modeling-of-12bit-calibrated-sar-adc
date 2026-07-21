"""
IEEE TVLSI 论文图表重绘脚本 (最终修正版)
- 去除所有灰色/难看的黄色
- Fig.6 使用 TT 工艺角数据与论文一致
- 学术级图例
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif', 'serif'],
    'font.size': 9,
    'axes.labelsize': 9,
    'axes.titlesize': 9,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 7.5,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'pdf.compression': 9,
    'axes.linewidth': 0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'xtick.major.size': 3,
    'ytick.major.size': 3,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'axes.grid': True,
    'grid.linewidth': 0.4,
    'grid.alpha': 0.25,
    'grid.color': '#D0D0D0',
    'grid.linestyle': ':',
    'axes.axisbelow': True,
})

# ==== 学术配色 ====
C_BL      = '#0072BD'    # IEEE blue   – 主色
C_OR      = '#D95319'    # IEEE orange – 对比
C_GN      = '#77AC30'    # IEEE green
C_SAND    = '#C49A3C'    # warm bronze  (替代黄色)
C_PL      = '#7E2F8E'    # IEEE purple
C_CY      = '#4DBEEE'    # IEEE cyan
C_SKY     = '#99CCEE'    # sky blue     (w/o CAAZ)
C_ICE     = '#D6E4F0'    # ice blue     (饼图 Quant)
C_BK      = '#000000'
C_WH      = '#FFFFFF'

out_dir = Path(__file__).parent.parent / 'figures'
out_dir.mkdir(exist_ok=True)

print(f'输出: {out_dir}')

# ========================== Fig.4 ==========================
def fig4():
    corners = ['TT','FF','SS',r'SF$_{-40}$',r'SF$_{35}$','FS']
    enob_on  = [10.78, 10.64, 10.68, 10.92, 10.59, 10.77]
    enob_off = [10.35, 10.36, 10.50, 10.51, 10.12, 10.37]
    delta    = [round(a-b,2) for a,b in zip(enob_on, enob_off)]

    fig, ax = plt.subplots(figsize=(3.5, 2.2))
    x = np.arange(len(corners)); bw = 0.35

    b1 = ax.bar(x-bw/2, enob_off, bw, color=C_SKY, edgecolor='none', zorder=3)
    b2 = ax.bar(x+bw/2, enob_on,  bw, color=C_BL,  edgecolor='none', zorder=3)

    for i, d in enumerate(delta):
        ax.text(x[i], max(enob_on[i],enob_off[i])+0.06, f'+{d:.2f}',
                ha='center', va='bottom', fontsize=7.5,
                color=C_OR, fontweight='bold')

    ax.axhline(10.5, color=C_BK, ls='--', lw=0.8, zorder=4)
    ax.text(len(corners)-0.15, 10.48, 'Target', ha='right', va='bottom',
            fontsize=7, fontstyle='italic', color=C_BK)

    ax.set_xticks(x); ax.set_xticklabels(corners)
    ax.set_ylabel('ENOB [bit]'); ax.set_xlabel('Process Corner')
    ax.set_ylim(9.8, 11.5); ax.set_yticks(np.arange(9.8, 11.6, 0.2))

    leg = ax.legend([b2, b1], ['With CAAZ', 'Without CAAZ'],
                    loc='upper right', frameon=True,
                    edgecolor=C_BK, facecolor=C_WH, framealpha=1,
                    fontsize=7.5, handlelength=1.2, handleheight=0.7)
    leg.get_frame().set_linewidth(0.6)

    plt.tight_layout(pad=0.3)
    fig.savefig(out_dir/'Fig4_Noise_Suppression.pdf', format='pdf',
                bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)
    print('[1/5] Fig.4 PVT ENOB')

# ========================== Fig.5 ==========================
def fig5():
    stages = ['Quant.\nOnly','+Raw\nkT/C','+Cancelled\nkT/C','Full\nSystem']
    enob   = [12.00, 11.57, 11.90, 11.47]
    colors = [C_ICE, C_OR, C_GN, C_BL]
    labels = ['Quantization Baseline','Raw kT/C Penalty',
              'kT/C Recovery Gain','Circuit Noise Floor']

    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    x = np.arange(len(stages))
    ax.bar(x, enob, width=0.55, color=colors, edgecolor='none', zorder=3)

    for xi, yi in zip(x, enob):
        ax.text(xi, yi+0.03, f'{yi:.2f}', ha='center', va='bottom',
                fontsize=8, color=C_BK)

    # arrows with labels
    changes = [None, -0.43, +0.33, -0.43]
    for i in range(1, len(stages)):
        y0, y1 = enob[i-1], enob[i]
        x0, x1 = x[i-1]+0.28, x[i]-0.28
        dy = y1 - y0
        clr = C_GN if dy > 0 else C_OR
        ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle='->', color=clr, lw=1.2))
        ax.text((x0+x1)/2, (y0+y1)/2 + (0.08 if dy>0 else -0.08),
                f'{dy:+.2f} bit', ha='center',
                va='bottom' if dy>0 else 'top',
                fontsize=7.5, color=clr, fontweight='bold')

    ax.set_xticks(x); ax.set_xticklabels(stages)
    ax.set_ylabel('ENOB [bit]')
    ax.set_ylim(10.8, 12.3); ax.set_yticks(np.arange(10.8,12.4,0.2))

    patches = [mpatches.Patch(color=c, label=l)
               for c,l in zip(colors, labels)]
    ax.legend(handles=patches, loc='upper center', ncol=4,
              bbox_to_anchor=(0.5, 1.18), frameon=False,
              fontsize=7, handlelength=1.0, columnspacing=0.8)

    plt.tight_layout(pad=0.5, rect=[0, 0, 1, 0.88])
    fig.savefig(out_dir/'Fig5_Noise_Waterfall.pdf', format='pdf',
                bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)
    print('[2/5] Fig.5 Noise Waterfall')

# ========================== Fig.6 ==========================
def fig6():
    # TT corner data (与论文 PVT 表格一致)
    vos     = [0, 2, 5]
    eAvg    = [10.94, 11.19, 10.88]   # TT corner
    eMin    = [10.94, 11.03, 10.85]   # min across corners
    eMax    = [11.18, 11.25, 10.92]   # max across corners
    err_lo  = [a-b for a,b in zip(eAvg, eMin)]
    err_hi  = [b-a for a,b in zip(eAvg, eMax)]

    fig, ax = plt.subplots(figsize=(3.5, 2.2))

    ax.fill_between(vos, eMin, eMax, color=C_BL, alpha=0.12,
                    edgecolor='none', zorder=2)
    ax.errorbar(vos, eAvg, yerr=[err_lo, err_hi], fmt='o-',
                color=C_BL, markersize=7, markerfacecolor=C_BL,
                markeredgecolor=C_WH, markeredgewidth=0.8,
                linewidth=1.8, capsize=5, capthick=1.2, zorder=4)

    for xi, yi in zip(vos, eAvg):
        ax.text(xi, yi+0.06, f'{yi:.2f}', ha='center', va='bottom',
                fontsize=8, color=C_BK)

    ax.text(3.0, 11.06, 'ENOB drop < 0.25 bit\n@ 5 mV offset',
            ha='center', va='center', fontsize=7.5, color=C_OR,
            fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=C_WH,
                      edgecolor=C_BK, linewidth=0.6))

    ax.set_xlim(-0.8, 6.0); ax.set_ylim(10.70, 11.45)
    ax.set_xticks(vos)
    ax.set_yticks(np.arange(10.7, 11.5, 0.1))
    ax.set_xlabel('Injected Input Offset [mV]'); ax.set_ylabel('ENOB [bit]')

    plt.tight_layout(pad=0.3)
    fig.savefig(out_dir/'Fig6_Offset_Sensitivity.pdf', format='pdf',
                bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)
    print('[3/5] Fig.6 Offset Sensitivity')

# ========================== Fig.7 ==========================
def fig7():
    td = [1, 2, 5, 10]
    data = {
        'TT': [10.85, 11.22, 11.47, 11.48],
        'FF': [10.78, 11.15, 11.39, 11.40],
        'SS': [10.88, 11.25, 11.50, 11.51],
        r'SF$_{-40}$': [10.86, 11.23, 11.48, 11.49],
        r'SF$_{35}$': [10.83, 11.20, 11.45, 11.46],
        'FS': [10.84, 11.21, 11.46, 11.47],
    }
    clrs   = [C_BL, C_OR, C_GN, C_SAND, C_PL, C_CY]
    mkrs   = ['o','s','^','d','v','h']

    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    hh = []
    for i, (lbl, vals) in enumerate(data.items()):
        h, = ax.plot(td, vals, '-', color=clrs[i], marker=mkrs[i],
                     markersize=5.5, markerfacecolor=C_WH,
                     markeredgewidth=0.8, linewidth=1.4, label=lbl, zorder=3)
        hh.append(h)

    ax.axhline(10.5, color=C_BK, ls='--', lw=0.8, zorder=4)
    ax.set_xlim(0.5, 10.5); ax.set_ylim(10.6, 11.7)
    ax.set_xticks(td)
    ax.set_yticks(np.arange(10.6, 11.8, 0.2))
    ax.set_xlabel(r'Noise Sampling Settling Time $t_d$ [ns]')
    ax.set_ylabel('ENOB [bit]')

    ax.legend(loc='upper center', ncol=6, bbox_to_anchor=(0.5, 1.25),
              frameon=False, columnspacing=0.4, fontsize=6.5,
              handlelength=1.0, handletextpad=0.4)

    plt.tight_layout(pad=0.5, rect=[0, 0, 1, 0.85])
    fig.savefig(out_dir/'Fig7_Time_Window_Sweep.pdf', format='pdf',
                bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)
    print('[4/5] Fig.7 Settling Time Sweep')

# ========================== Fig.8 ==========================
def fig8():
    sizes_L  = [38.95, 31.40, 29.65]
    sizes_R  = [52.49,  7.60, 39.91]
    colors   = [C_ICE, C_OR, C_BL]   # ice blue / orange / IEEE blue

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(4.0, 2.0))

    for ax, sizes, title, total, snr in [
        (axL, sizes_L, 'Without CAAZ', r'$1.656{\times}10^{-7}$ V$^2$', '69.91 dB'),
        (axR, sizes_R, 'With CAAZ',    r'$1.229{\times}10^{-7}$ V$^2$', '70.80 dB')
    ]:
        wedges, _ = ax.pie(sizes, colors=colors,
                           startangle=90,
                           wedgeprops=dict(width=0.55, edgecolor=C_WH, linewidth=1.0))

        ax.set_title(title, fontsize=9, fontweight='bold', pad=4)
        ax.text(0, 0, f'SNR\n{snr}', ha='center', va='center',
                fontsize=8, fontweight='bold', color=C_BK)

        # sector labels
        text_colors = [C_BK, C_WH, C_WH]  # Quant→black, kT/C→white, Other→white
        for w, s, tc in zip(wedges, sizes, text_colors):
            ang = (w.theta2 - w.theta1)/2. + w.theta1
            r = 0.72
            ax.text(r*np.cos(np.deg2rad(ang)), r*np.sin(np.deg2rad(ang)),
                    f'{s:.1f}%', ha='center', va='center',
                    fontsize=7.5, color=tc, fontweight='bold')

        ax.text(0, -1.25, f'Total: {total}', ha='center', va='top',
                fontsize=7.5, color=C_BK)

    # 统一图例（底部）
    patches = [mpatches.Patch(color=c, label=l) for c,l in zip(
        colors, ['Quantization', r'$kT/C$ Sampling', 'Other Circuit'])]
    fig.legend(handles=patches, loc='lower center', ncol=3,
               bbox_to_anchor=(0.5, -0.06), frameon=False, fontsize=7,
               handlelength=1.0, handletextpad=0.4, columnspacing=0.6)

    plt.tight_layout(pad=0.8, rect=[0, 0.06, 1, 1])
    fig.savefig(out_dir/'Fig8_Noise_Pie_Charts.pdf', format='pdf',
                bbox_inches='tight', pad_inches=0.03)
    plt.close(fig)
    print('[5/5] Fig.8 Noise Pie Charts')

# ========================== Main ==========================
if __name__ == '__main__':
    fig4(); fig5(); fig6(); fig7(); fig8()
    print(f'\nDone → {out_dir}')
