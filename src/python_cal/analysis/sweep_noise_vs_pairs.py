"""
sweep_noise_vs_pairs.py
Sweep: comparator noise × AVG_PAIRS → SNDR / oracle gap
"""
import sys, os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # up to src/
sys.path.insert(0, SRC_DIR)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
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

# ══════════════════════════════════════════════════════════════════════
SEED = 42
MC_SIGMA = 0.01
NOISE_UV_LIST = [50, 100, 200, 500, 1000, 2000]
PAIRS_LIST = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]
N_FFT = cfg.FFT_N
FFT_K = cfg.FFT_K
MAX_CODE = (1 << cfg.N_BITS) - 1
VCM = cfg.VCM

FFT_PROTOCOL = FFTProtocol(
    n_fft=N_FFT, signal_bin=FFT_K,
    amplitude_dbfs=cfg.FFT_AMPLITUDE_DBFS, phase_rad=cfg.FFT_PHASE,
)

print("=" * 60)
print(f"  Noise x AVG_PAIRS sweep")
print(f"  MC_sigma={MC_SIGMA*100:.0f}%  Seed={SEED}")
print("=" * 60)

# ── caps & decisions (once) ──
rng = np.random.default_rng(SEED)
_mode = getattr(cfg, "MISMATCH_MODE", "per_unit")
def gen_caps():
    def side():
        c = {}
        for n in cfg.ALL_CAP_NAMES:
            ncu = cfg.CAP_NOMINAL_CU[n]
            if not cfg.should_mismatch(n):
                c[n] = cfg.CU * ncu
            elif _mode == "per_cap":
                c[n] = cfg.CU * ncu * rng.normal(1.0, MC_SIGMA)
            else:
                c[n] = sum(cfg.CU * rng.normal(1.0, MC_SIGMA) for _ in range(int(ncu)))
        return c
    return side(), side()

p_caps, n_caps = gen_caps()
cdac_mc = DifferentialCDAC.from_mismatch(p_caps=p_caps, n_caps=n_caps)

# pre-cal
adc = AsyncBehavioralSARADC(cdac=cdac_mc)
adc.enable_nominal_decode()
nom_dec = SARDecoder()
def conv_nom(vd):
    r = adc.convert(VCM + vd/2, VCM - vd/2)
    return nom_dec.decode(r.decisions)

vfs = measure_positive_vfs(conv_nom, MAX_CODE, guard_codes=1)
vin, _ = build_coherent_differential_sine(vfs, FFT_PROTOCOL)
decisions = []
for vd in vin:
    r = adc.convert(VCM + vd/2, VCM - vd/2)
    decisions.append(list(r.decisions))

codes_pre = [nom_dec.decode_fixed(d, fractional_bits=2) for d in decisions]
met_pre = compute_fft_coherent(codes_pre, n_bits=cfg.N_BITS, n_fft=N_FFT, signal_bin=FFT_K)

# ideal
cdac_id = DifferentialCDAC.ideal()
pw_id_p, pw_id_n = cdac_id.get_physical_weights_per_side_q0()
adc_id = AsyncBehavioralSARADC(cdac=cdac_id)
adc_id.enable_nominal_decode()
oracle_dec = SARDecoder(weights_p=list(pw_id_p), weights_n=list(pw_id_n))
def conv_id(vd):
    r = adc_id.convert(VCM + vd/2, VCM - vd/2)
    return oracle_dec.decode(r.decisions)
vfs_id = measure_positive_vfs(conv_id, MAX_CODE, guard_codes=1)
vin_id, _ = build_coherent_differential_sine(vfs_id, FFT_PROTOCOL)
dec_id = []
for vd in vin_id:
    r = adc_id.convert(VCM + vd/2, VCM - vd/2)
    dec_id.append(list(r.decisions))
codes_id = [oracle_dec.decode_fixed(d, fractional_bits=2) for d in dec_id]
met_id = compute_fft_coherent(codes_id, n_bits=cfg.N_BITS, n_fft=N_FFT, signal_bin=FFT_K)

ideal_sndr = met_id["sndr_db"]
print(f"  Pre-Cal: {met_pre['sndr_db']:.1f} dB  Ideal: {ideal_sndr:.1f} dB\n")

# ── sweep ──
sndr_grid = np.full((len(NOISE_UV_LIST), len(PAIRS_LIST)), np.nan)
gap_grid  = np.full((len(NOISE_UV_LIST), len(PAIRS_LIST)), np.nan)

for i, noise_uv in enumerate(NOISE_UV_LIST):
    noise_v = noise_uv * 1e-6
    for j, n_pairs in enumerate(PAIRS_LIST):
        shen = ShenCalibrationController(
            cdac=cdac_mc, comparator=DynamicComparator(),
            timing=TimingParams(), avg_pairs=n_pairs,
            cal_noise_sigma=noise_v,
        )
        targets, cal_wp, cal_wn = shen.run(
            rng=np.random.default_rng(SEED + i*1000 + j)
        )
        cal_dec = SARDecoder(weights_p=list(cal_wp), weights_n=list(cal_wn))
        codes = [cal_dec.decode_fixed(d, fractional_bits=2) for d in decisions]
        met = compute_fft_coherent(codes, n_bits=cfg.N_BITS, n_fft=N_FFT, signal_bin=FFT_K)
        sndr_grid[i, j] = met["sndr_db"]
        gap_grid[i, j] = ideal_sndr - met["sndr_db"]
        print(f"  noise={noise_uv:>4d}uV  pairs={n_pairs:>3d}  "
              f"SNDR={met['sndr_db']:.2f}  gap={gap_grid[i,j]:.3f}")

# ── theoretical contour ──
# sigma_W_per_pair (LSB) = comparator_noise(V) / (VREF/4096) * sqrt(2)/2
# For H1C (67 Q0), 3-sigma calibration error target < 0.5 LSB
LSB_V = cfg.VREF / (1 << cfg.N_BITS)

# ══════════════════════════════════════════════════════════════════════
# PLOT
# ══════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(20, 6.5))
fig.suptitle(
    f"Comparator Noise vs AVG_PAIRS  |  "
    f"MC $\\sigma$ = {MC_SIGMA*100:.0f}%, Seed={SEED}  |  "
    f"Pre-Cal = {met_pre['sndr_db']:.1f} dB, Ideal = {ideal_sndr:.1f} dB",
    fontsize=13, fontweight="bold", y=0.99,
)

# ── Panel A: SNDR heatmap ──
ax = axes[0]
X, Y = np.meshgrid(PAIRS_LIST, NOISE_UV_LIST)
im = ax.pcolormesh(X, Y, sndr_grid, cmap="RdYlBu_r",
                    vmin=65, vmax=ideal_sndr, edgecolors='white', linewidth=0.5)
ax.set_xscale("log", base=2)
ax.set_yscale("log")
ax.set_xlabel("AVG_PAIRS", fontsize=11)
ax.set_ylabel("Comparator Noise [uV RMS]", fontsize=11)
ax.set_title("Post-Cal SNDR [dB]", fontsize=12, fontweight="bold")
ax.set_xticks(PAIRS_LIST)
ax.set_xticklabels([str(p) for p in PAIRS_LIST], fontsize=8)
ax.set_yticks(NOISE_UV_LIST)
ax.set_yticklabels([str(n) for n in NOISE_UV_LIST])
for i, nv in enumerate(NOISE_UV_LIST):
    for j, np_ in enumerate(PAIRS_LIST):
        v = sndr_grid[i, j]
        if not np.isnan(v):
            fc = "white" if v < 70 else "black"
            ax.text(np_, nv, f"{v:.1f}", ha="center", va="center",
                    fontsize=7, color=fc, fontweight="bold")
cb = plt.colorbar(im, ax=ax, shrink=0.82)
cb.set_label("SNDR [dB]", fontsize=10)

# ── Panel B: Oracle gap heatmap ──
ax = axes[1]
im2 = ax.pcolormesh(X, Y, gap_grid, cmap="YlOrRd",
                     vmin=0, vmax=15, edgecolors='white', linewidth=0.5)
ax.set_xscale("log", base=2)
ax.set_yscale("log")
ax.set_xlabel("AVG_PAIRS", fontsize=11)
ax.set_ylabel("Comparator Noise [uV RMS]", fontsize=11)
ax.set_title("Oracle Gap [dB]", fontsize=12, fontweight="bold")
ax.set_xticks(PAIRS_LIST)
ax.set_xticklabels([str(p) for p in PAIRS_LIST], fontsize=8)
ax.set_yticks(NOISE_UV_LIST)
ax.set_yticklabels([str(n) for n in NOISE_UV_LIST])
for i, nv in enumerate(NOISE_UV_LIST):
    for j, np_ in enumerate(PAIRS_LIST):
        v = gap_grid[i, j]
        if not np.isnan(v):
            fc = "white" if v > 3 else "black"
            ax.text(np_, nv, f"{v:.2f}", ha="center", va="center",
                    fontsize=7, color=fc, fontweight="bold")
cb2 = plt.colorbar(im2, ax=ax, shrink=0.82)
cb2.set_label("Gap [dB]", fontsize=10)

# Theoretical 3-sigma(H1C) = 0.5 LSB contour
# N_req = (3 * noise_V / (LSB_V * sqrt(N)) * sqrt(2)/2 * 1/0.5)^2
# solving: N = (3 * noise_V * sqrt(2) / (2 * LSB_V * 0.5))^2
#        = (3 * noise_V / (sqrt(2) * LSB_V))^2
#        = (3 * noise_V * 4096 / (sqrt(2) * VREF))^2
theo_n_grid = np.logspace(0, 9, 100)  # wide range for smooth curve
theo_noise = 3 * LSB_V * np.sqrt(theo_n_grid) / (np.sqrt(2))
# Actually let me compute: 3 * sigma_W_per_pair / sqrt(N) = 0.5 → N = (6*sigma_single)^2
# sigma_single = noise_V * sqrt(2)/2 / LSB_V (in LSB units)
# 3 * sigma_single / sqrt(N) = 0.5 → N = (6 * sigma_single)^2
# Where sigma_single_LSB = noise_V / LSB_V * sqrt(2)/2
# N = 36 * (noise_V / LSB_V)^2 * 2 / 4 = 36 * (noise_V / LSB_V)^2 * 0.5
# N = 18 * (noise_V / LSB_V)^2
# noise_V = LSB_V * sqrt(N / 18)

# ── Panel C: FFT spectra at key boundaries ──
ax = axes[2]

def compute_spectrum_db(codes):
    c = np.asarray(codes[:N_FFT], dtype=np.float64)
    c -= np.mean(c)
    spec = np.abs(np.fft.rfft(c)) / N_FFT
    spec_norm = spec / (MAX_CODE / 2.0)
    return 20 * np.log10(spec_norm + 1e-20)

freq = np.arange(N_FFT // 2 + 1) * (cfg.FFT_FS / N_FFT) / 1e6
signal_freq = FFT_K * (cfg.FFT_FS / N_FFT) / 1e6

# Pick 3 representative (noise, pairs) combos
cases = [
    (50, 4, "#1A365D", "50 uV, N=4"),
    (200, 16, "#2C7A7B", "200 uV, N=16"),
    (1000, 128, "#C53030", "1 mV, N=128"),
]
for nv, np_, color, label in cases:
    # re-run calibration for this exact combo
    shen = ShenCalibrationController(
        cdac=cdac_mc, comparator=DynamicComparator(),
        timing=TimingParams(), avg_pairs=np_,
        cal_noise_sigma=nv * 1e-6,
    )
    targets, cal_wp, cal_wn = shen.run(
        rng=np.random.default_rng(SEED + nv * 100 + np_)
    )
    cal_dec = SARDecoder(weights_p=list(cal_wp), weights_n=list(cal_wn))
    codes = [cal_dec.decode_fixed(d, fractional_bits=2) for d in decisions]
    spec = compute_spectrum_db(codes)
    met = compute_fft_coherent(codes, n_bits=cfg.N_BITS, n_fft=N_FFT, signal_bin=FFT_K)
    ax.plot(freq, spec, color=color, linewidth=0.7, alpha=0.85, label=label)
    ax.plot(signal_freq, spec[FFT_K], 'D', color=color, markersize=5,
            markeredgecolor='black', markeredgewidth=0.3)

ax.set_xlabel("Frequency [MHz]", fontsize=11)
ax.set_ylabel("Magnitude [dBFS]", fontsize=11)
ax.set_title("Spectra at Representative (Noise, N) Pairs", fontsize=12, fontweight="bold")
ax.set_ylim(-160, 15)
ax.set_xlim(0, cfg.FFT_FS / 2e6)
ax.grid(True, alpha=0.2)
ax.legend(fontsize=9, framealpha=0.8, loc="lower left")

# annotate optimum region
ax_b = axes[1]
# Draw "sweet spot" = gap < 1 dB region
for i, nv in enumerate(NOISE_UV_LIST):
    for j, np_ in enumerate(PAIRS_LIST):
        if not np.isnan(gap_grid[i, j]) and gap_grid[i, j] < 1.0:
            ax_b.plot(np_, nv, 'o', color='#22543D', markersize=8,
                      markerfacecolor='none', markeredgewidth=1.5, alpha=0.5)

plt.tight_layout(rect=[0, 0, 1, 0.95])
out = os.path.join(SCRIPT_DIR, "noise_vs_pairs_sweep.png")
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"\nSaved: {out}")

# ── Optimal N formula ──
print("\n" + "=" * 60)
print("  Optimal N = 18 * (noise_uV / LSB_uV)^2")
print(f"  LSB = {LSB_V*1e6:.0f} uV")
print("=" * 60)
for nv in NOISE_UV_LIST:
    n_opt = int(np.ceil(18 * (nv / (LSB_V*1e6))**2))
    n_opt = max(1, n_opt)
    # find closest available PAIRS_LIST
    closest = min(PAIRS_LIST, key=lambda x: abs(x - n_opt))
    print(f"  {nv:>4d} uV  ->  N_opt = {n_opt:>4d}  ->  use {closest}")
