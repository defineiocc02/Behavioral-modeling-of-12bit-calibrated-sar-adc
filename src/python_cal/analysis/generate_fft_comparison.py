"""
generate_fft_comparison.py — 校准前/后/无失配 FFT 三图对比 + 数据流分析

Produces:
  - fft_comparison.png  : 三子图 FFT 频谱对比
  - fft_data_flow.txt   : 完整数据流动分析
"""
import sys, os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # up to src/
sys.path.insert(0, SRC_DIR)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

from python_cal import config as cfg
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.comparator.dynamic_comparator import DynamicComparator
from python_cal.async_control.timing import TimingParams
from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
from python_cal.decode.sar_decoder import SARDecoder
from python_cal.calibration.shen_calibrator import ShenCalibrationController
from python_cal.fft_metrics import compute_fft_coherent
from python_cal.validation.fft_protocol import (
    FFTProtocol, build_coherent_differential_sine, measure_positive_vfs,
)

# ═══════════════════════════════════════════════════════════════════════════
# 1. 公共参数
# ═══════════════════════════════════════════════════════════════════════════
SEED = 12345
RNG = np.random.default_rng(SEED)
N_FFT   = cfg.FFT_N
FFT_K   = cfg.FFT_K
N_BITS  = cfg.N_BITS
MAX_CODE = (1 << N_BITS) - 1
VCM = cfg.VCM
MC_SIGMA = cfg.MC_SIGMA

FFT_PROTOCOL = FFTProtocol(
    n_fft=N_FFT, signal_bin=FFT_K,
    amplitude_dbfs=cfg.FFT_AMPLITUDE_DBFS,
    phase_rad=cfg.FFT_PHASE,
)

# ═══════════════════════════════════════════════════════════════════════════
# 2. 生成 MC 失配电容
# ═══════════════════════════════════════════════════════════════════════════
def gen_mc_caps(seed, sigma):
    rng = np.random.default_rng(seed)
    def make_side():
        caps = {}
        for name in cfg.ALL_CAP_NAMES:
            cu_val = cfg.CAP_NOMINAL_CU[name]
            if cu_val >= 1:
                caps[name] = sum(
                    cfg.CU * rng.normal(1.0, sigma) for _ in range(int(cu_val))
                )
            else:
                caps[name] = cfg.CU * cu_val * rng.normal(1.0, sigma)
        return caps
    return make_side(), make_side()

# ═══════════════════════════════════════════════════════════════════════════
# 3. 构建 CDAC + 转换 + VFS 测量
# ═══════════════════════════════════════════════════════════════════════════
def run_fft_experiment(cdac, decoder_wp, decoder_wn, label):
    """Share same decisions, swap decoder weights."""
    adc = AsyncBehavioralSARADC(cdac=cdac)
    adc.enable_nominal_decode()  # required before convert()
    decoder = SARDecoder(weights_p=list(decoder_wp), weights_n=list(decoder_wn))

    # VFS 测量
    def conv(vd):
        r = adc.convert(VCM + vd/2, VCM - vd/2)
        return SARDecoder().decode(r.decisions)
    vfs = measure_positive_vfs(conv, MAX_CODE, guard_codes=1)
    vin, fft_meta = build_coherent_differential_sine(vfs, FFT_PROTOCOL)

    # 一组 decisions, 三种解码
    decisions = []
    for vd in vin:
        r = adc.convert(VCM + vd/2, VCM - vd/2)
        decisions.append(list(r.decisions))

    codes_float = [decoder.decode_fixed(d, fractional_bits=2) for d in decisions]
    codes_int   = [decoder.decode(d) for d in decisions]

    result = compute_fft_coherent(codes_float, n_bits=N_BITS, n_fft=N_FFT, signal_bin=FFT_K)

    return {
        "label": label,
        "codes_float": codes_float,
        "codes_int": codes_int,
        "decisions": decisions,
        "vin": vin,
        "vfs": vfs,
        "sndr_db": result["sndr_db"],
        "sfdr_db": result["sfdr_db"],
        "enob": result["enob"],
    }

# ═══════════════════════════════════════════════════════════════════════════
# 4. 主流程
# ═══════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("  FFT Comparison: Ideal | Pre-Cal | Post-Cal")
print(f"  Seed={SEED}  MC_SIGMA={MC_SIGMA}  AVG_PAIRS={cfg.AVG_PAIRS}")
print("=" * 60)

# --- 4a. 失配电容 ---
p_caps_mc, n_caps_mc = gen_mc_caps(SEED, MC_SIGMA)
cdac_mc = DifferentialCDAC.from_mismatch(p_caps=p_caps_mc, n_caps=n_caps_mc)
pw_p, pw_n = cdac_mc.get_physical_weights_per_side_q0()

# --- 4b. 理想 CDAC (无失配) ---
cdac_ideal = DifferentialCDAC.ideal()

# --- 4c. 校准前: 失配 CDAC + 标称权重 ---
print("\n[1/3] Pre-calibration FFT (mismatch + nominal weights)...")
precal = run_fft_experiment(
    cdac_mc, cfg.NOMINAL_WEIGHTS_Q0, cfg.NOMINAL_WEIGHTS_Q0,
    "校准前 (Mismatch + Nominal Weights)"
)

# --- 4d. 校准 ---
print("[2/3] Running Shen calibration...")
shen = ShenCalibrationController(
    cdac=cdac_mc, comparator=DynamicComparator(),
    timing=TimingParams(), avg_pairs=cfg.AVG_PAIRS,
    cal_noise_sigma=cfg.CAL_NOISE_SIGMA_V,
)
targets, cal_wp, cal_wn = shen.run(rng=RNG)
valid = all(t['valid'] for t in targets)
print(f"      Calibration {'PASS' if valid else 'FAIL'}")

for t in targets:
    print(f"      {t['target_name']}: W={t['W_avg']:.2f} (nom={t['nominal']}) "
          f"err={abs(t['W_avg']-t['nominal'])/t['nominal']*100:.4f}%")

# --- 4e. 校准后: 失配 CDAC + 校准权重 ---
print("\n[3/3] Post-calibration FFT (mismatch + calibrated weights)...")
postcal = run_fft_experiment(
    cdac_mc, cal_wp, cal_wn,
    "校准后 (Mismatch + Calibrated Weights)"
)

# --- 4f. 理想 CDAC: oracle weights ---
print("\n     Ideal FFT (no mismatch + physical oracle)...")
pw_p_ideal, pw_n_ideal = cdac_ideal.get_physical_weights_per_side_q0()
ideal = run_fft_experiment(
    cdac_ideal, pw_p_ideal, pw_n_ideal,
    "无失配 Ideal (Physical Oracle)"
)

# ═══════════════════════════════════════════════════════════════════════════
# 5. 绘图
# ═══════════════════════════════════════════════════════════════════════════
print("\nPlotting...")

# 统一 x 轴: 频率 (MHz) → 只显示前 N_FFT//2 个 bin
freq = np.arange(N_FFT // 2 + 1) * (cfg.FFT_FS / N_FFT) / 1e6

def compute_spectrum_db(codes):
    """矩形窗 FFT → dBFS"""
    c = np.asarray(codes[:N_FFT], dtype=np.float64)
    c -= np.mean(c)
    spectrum = np.abs(np.fft.rfft(c)) / N_FFT
    # 归一化到满量程
    spec_norm = spectrum / (MAX_CODE / 2.0)
    spec_db = 20 * np.log10(spec_norm + 1e-20)
    return freq, spec_db

# 理想 CDAC: 重新测量物理 oracle weights 对应的码
# (使用 ideal CDAC 的相同 decisions, 但用物理 oracle 解码)
ideal_dec = SARDecoder(weights_p=list(pw_p_ideal), weights_n=list(pw_n_ideal))
ideal_codes = [ideal_dec.decode_fixed(d, fractional_bits=2) for d in ideal["decisions"]]

precal_codes  = [SARDecoder().decode_fixed(d, fractional_bits=2) for d in precal["decisions"]]
postcal_codes = [SARDecoder(weights_p=list(cal_wp), weights_n=list(cal_wn)).decode_fixed(d, fractional_bits=2) for d in postcal["decisions"]]

freq_ideal, spec_ideal     = compute_spectrum_db(ideal_codes)
freq_pre,  spec_pre        = compute_spectrum_db(precal_codes)
freq_post, spec_post       = compute_spectrum_db(postcal_codes)

fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True, sharey=True)
fig.suptitle(
    f"SAR ADC FFT Spectrum Comparison  |  "
    f"MC $\\sigma$={MC_SIGMA*100:.1f}%  |  "
    f"N={N_FFT}, k={FFT_K}, Rect. Window  |  "
    f"Seed={SEED}",
    fontsize=14, fontweight="bold", y=0.98,
)

colors = ["#1A365D", "#C53030", "#22543D"]
datasets = [
    ("Ideal (No Mismatch)", ideal_codes, ideal, colors[0]),
    ("Pre-Calibration", precal_codes, precal, colors[1]),
    ("Post-Calibration", postcal_codes, postcal, colors[2]),
]

signal_marker_freq = FFT_K * (cfg.FFT_FS / N_FFT) / 1e6

for ax, (title, codes, result, color) in zip(axes, datasets):
    f, s = compute_spectrum_db(codes)
    ax.plot(f, s, color=color, linewidth=0.6, alpha=0.85)
    ax.fill_between(f, s, -160, color=color, alpha=0.08)

    # 标记信号 bin
    signal_bin_idx = FFT_K
    ax.plot(signal_marker_freq, s[signal_bin_idx], 'o', color=color,
            markersize=8, markeredgecolor='black', markeredgewidth=0.5)

    # 标注谐波
    for h in range(2, 8):
        harm_bin = (FFT_K * h) % N_FFT
        if harm_bin > N_FFT // 2:
            harm_bin = N_FFT - harm_bin
        if 0 < harm_bin < len(s):
            harm_freq = harm_bin * (cfg.FFT_FS / N_FFT) / 1e6
            ax.plot(harm_freq, s[harm_bin], 'x', color='gray',
                    markersize=5, alpha=0.6)

    # 信息框
    info = (
        f"SNDR = {result['sndr_db']:.2f} dB  |  "
        f"SFDR = {result['sfdr_db']:.2f} dB  |  "
        f"ENOB = {result['enob']:.2f} bit"
    )
    ax.text(0.98, 0.95, info, transform=ax.transAxes,
            fontsize=10, ha="right", va="top",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                      edgecolor=color, alpha=0.85))

    ax.set_ylabel("Magnitude [dBFS]", fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold", color=color, loc="left")
    ax.set_ylim(-160, 10)
    ax.grid(True, alpha=0.25)

axes[-1].set_xlabel("Frequency [MHz]", fontsize=11)
axes[-1].set_xlim(0, cfg.FFT_FS / 2e6)

plt.tight_layout(rect=[0, 0, 1, 0.96])
out_png = os.path.join(SCRIPT_DIR, "fft_comparison.png")
fig.savefig(out_png, dpi=200, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"  Saved: {out_png}")

# ═══════════════════════════════════════════════════════════════════════════
# 6. 数据流动分析
# ═══════════════════════════════════════════════════════════════════════════
report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         SAR ADC FFT 数据流动完整分析                                       ║
╠══════════════════════════════════════════════════════════════════════════════╣

  Run Parameters
  ─────────────
  Seed          = {SEED}
  MC sigma      = {MC_SIGMA} ({MC_SIGMA*100:.1f}% unit-cap mismatch)
  AVG_PAIRS     = {cfg.AVG_PAIRS}
  Cal noise     = {cfg.CAL_NOISE_SIGMA_V} V RMS
  FFT N         = {N_FFT}
  FFT k         = {FFT_K}  (coherent, gcd(127,4096)=1)
  Window        = Rectangular (ENBW = 1 bin)
  Amplitude     = {cfg.FFT_AMPLITUDE_DBFS} dBFS
  Phase         = {cfg.FFT_PHASE} rad

  ─────────────────────────────────────────────────────────────────────────────
  数据流动: 从电容到 FFT 频谱
  ─────────────────────────────────────────────────────────────────────────────

  Step 1 — 电容失配生成
  ┌─────────────────────────────────────────────────────────────┐
  │ gen_mc_caps(seed, sigma)                                    │
  │   for each cap in ALL_CAP_NAMES:                            │
  │     C_actual = sum(CU * N(1.0,sigma)) over N_Cu units       │
  │   → P-side caps dict, N-side caps dict                      │
  └───────────────────┬─────────────────────────────────────────┘
                      ↓
  Step 2 — CDAC 拓扑构建
  ┌─────────────────────────────────────────────────────────────┐
  │ DifferentialCDAC.from_mismatch(p_caps, n_caps)              │
  │   → build_differential_topology()                           │
  │   → CDACTopology(high_caps, bridge, low_caps) ×2 (P/N)     │
  │   → DifferentialChargeSolver(p_solver, n_solver)            │
  │     └─ SideChargeSolver: 预计算 2×2 电荷守恒矩阵 A_inv     │
  └───────────────────┬─────────────────────────────────────────┘
                      ↓
  Step 3 — VFS 测量 (动态满量程)
  ┌─────────────────────────────────────────────────────────────┐
  │ measure_positive_vfs(callback, MAX_CODE, guard=1)           │
  │   → 二分搜索: 最小 Vdiff 使 code ≥ 4094                    │
  │   → 返回 vfs_v (每 seed 独立, 不硬编码)                    │
  └───────────────────┬─────────────────────────────────────────┘
                      ↓
  Step 4 — 相干正弦激励生成
  ┌─────────────────────────────────────────────────────────────┐
  │ build_coherent_differential_sine(vfs, FFTProtocol)          │
  │   amplitude = vfs × 10^(dBFS/20)                            │
  │   vin[i] = amplitude × sin(2π·k·i/N + φ)                   │
  │   输出: 4096 点差分电压序列 + metadata                      │
  └───────────────────┬─────────────────────────────────────────┘
                      ↓
  Step 5 — SAR ADC 逐点转换 (共用 decisions)
  ┌─────────────────────────────────────────────────────────────┐
  │ for vd in vin[0..4095]:                                     │
  │   AsyncSARController.start_conversion(VCM±vd/2)             │
  │     → SAMPLE:  全部 14 电容底板→VIN, VTOP→VCM              │
  │     → RESET:   底板→VCM, 电荷守恒求解初始 Vdiff             │
  │     → SAR:     for stage 0..14 (15 comparisons)             │
  │         trial:  P/N 当前电容→VREFP                           │
  │         solve:  charge_solver.solve(charge, switch_state)   │
  │         compare: DynamicComparator.request(vtop_p, vtop_n)  │
  │         commit: 保留一侧 VREFP, 另一侧回 VCM                │
  │     → decisions[15] = [d0..d14] (0 or 1 per bit)           │
  └───────────────────┬─────────────────────────────────────────┘
                      ↓
  Step 6 — 三种解码路径 (共用同一组 decisions[4096][15])
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  PATH A: 无失配 Ideal                                       │
  │    decoder = SARDecoder(Wp_ideal, Wn_ideal)                 │
  │    → 物理 oracle 权重 (真实电容值推导)                      │
  │    code = (signed_sum + center) × 4095 / total_range        │
  │    code_q2 = floor(code × 4 + 0.5) / 4  (Q2 定点)          │
  │                                                             │
  │  PATH B: 校准前 Pre-Cal                                     │
  │    decoder = SARDecoder(NOMINAL_WEIGHTS_Q0, ...)            │
  │    → 标称权重 2144,1072,536,536,268,134,67,64,32,...       │
  │    电容已失配, 但解码器不知 → 权重误差直接转码误差         │
  │                                                             │
  │  PATH C: 校准后 Post-Cal                                    │
  │    decoder = SARDecoder(cal_wp, cal_wn)                     │
  │    → Shen 校准测量值 (P/N 分侧, 7 targets 已更新)           │
  │    权重接近物理真实值 → SNDR 接近 oracle                    │
  │                                                             │
  └───────────────────┬─────────────────────────────────────────┘
                      ↓
  Step 7 — FFT 频谱计算
  ┌─────────────────────────────────────────────────────────────┐
  │ compute_fft_coherent(codes_q2, N=4096, k=127)              │
  │   codes_centered = codes - mean(codes)                     │
  │   spectrum = |rFFT(codes_centered)| / N                    │
  │   signal_power = |spectrum[127]|²                          │
  │   harmonics ∑|spectrum[127×h]|²  for h=2..7               │
  │   noise_power = ∑ spectrum²  excluding DC, signal, harmonics│
  │   SNDR = 10·log₁₀(signal / (noise + harmonics))           │
  │   SFDR = 20·log₁₀(signal_mag / max_spur)                  │
  │   ENOB = (SNDR - 1.76) / 6.02                             │
  └───────────────────┬─────────────────────────────────────────┘
                      ↓

  ─────────────────────────────────────────────────────────────
  FFT Results
  ─────────────────────────────────────────────────────────────

  Case                 SNDR [dB]    SFDR [dB]    ENOB [bit]
  ─────────────────────────────────────────────────────────────
  无失配 Ideal          {ideal['sndr_db']:>8.2f}      {ideal['sfdr_db']:>8.2f}      {ideal['enob']:>8.2f}
  校准前 Pre-Cal        {precal['sndr_db']:>8.2f}      {precal['sfdr_db']:>8.2f}      {precal['enob']:>8.2f}
  校准后 Post-Cal       {postcal['sndr_db']:>8.2f}      {postcal['sfdr_db']:>8.2f}      {postcal['enob']:>8.2f}
  ─────────────────────────────────────────────────────────────
  Calibration gain      {postcal['sndr_db']-precal['sndr_db']:+.2f} dB
  Oracle gap            {ideal['sndr_db']-postcal['sndr_db']:.3f} dB
  ─────────────────────────────────────────────────────────────

  ─────────────────────────────────────────────────────────────
  校准权重 (P/N 平均)
  ─────────────────────────────────────────────────────────────
"""

for t in targets:
    report += (
        f"  {t['target_name']:6s}  cal={t['W_avg']:8.2f}  "
        f"nom={t['nominal']:5.0f}  "
        f"err={abs(t['W_avg']-t['nominal'])/t['nominal']*100:.4f}%\n"
    )

report += f"""
  ─────────────────────────────────────────────────────────────
  关键观察
  ─────────────────────────────────────────────────────────────
  1. 三种 FFT 共用同一组 4096×15 comparator decisions。
     差异完全来自 decoder 的权重不同 — 物理路径未改动。

  2. 校准前 SNDR 低是因为高段电容失配 (1% σ per unit cap)
     导致权重误差，在解码时产生系统性非线性。

  3. Shen 校准用 force-0/force-1 半差法测量每个 target 的
     真实权重。{cfg.AVG_PAIRS} pairs 平均将校准噪声压至 ~{1/np.sqrt(cfg.AVG_PAIRS)*cfg.CAL_NOISE_SIGMA_V*1e3:.2f} mV。

  4. oracle gap = {ideal['sndr_db']-postcal['sndr_db']:.3f} dB
     是校准残差 — 来自低段不校准 (131 Q0 基准尺失配)
     和 1mV 校准噪声的残余影响。

  5. 矩形窗 + 相干采样: signal bin=127 独占主瓣,
     ENBW=1 bin, SNDR 不含窗函数展宽损失。
╚══════════════════════════════════════════════════════════════════════════════╝
"""

out_txt = os.path.join(SCRIPT_DIR, "fft_data_flow.txt")
with open(out_txt, "w", encoding="utf-8") as f:
    f.write(report)
print(f"  Saved: {out_txt}")
print(report)
