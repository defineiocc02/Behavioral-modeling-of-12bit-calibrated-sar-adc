"""
dither_heatmap.py — Dither delta heatmap: Noise x AVG_PAIRS
"""
import sys, os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # up to src/
sys.path.insert(0, SRC_DIR)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
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

SEED = 42; MC_SIGMA = 0.01
NOISE_UV = [50, 100, 200, 500, 1000, 2000]
PAIRS = [2, 4, 8, 16, 32, 64, 128, 256, 512]
N_FFT = cfg.FFT_N; FFT_K = cfg.FFT_K
MAX_CODE = (1 << cfg.N_BITS) - 1; VCM = cfg.VCM

FFT_PROTOCOL = FFTProtocol(
    n_fft=N_FFT, signal_bin=FFT_K,
    amplitude_dbfs=cfg.FFT_AMPLITUDE_DBFS, phase_rad=cfg.FFT_PHASE,
)

# shared setup
rng = np.random.default_rng(SEED)
_mode = getattr(cfg, "MISMATCH_MODE", "per_unit")
def gen():
    def side():
        c = {}
        for n in cfg.ALL_CAP_NAMES:
            ncu = cfg.CAP_NOMINAL_CU[n]
            if not cfg.should_mismatch(n):
                c[n] = cfg.CU * ncu
            elif _mode in ("per_cap_flat_stress", "per_cap"):
                c[n] = cfg.CU * ncu * rng.normal(1.0, MC_SIGMA)
            elif _mode == "per_cap_scaled":
                s = MC_SIGMA / np.sqrt(ncu)
                c[n] = cfg.CU * ncu * rng.normal(1.0, s)
            else:
                c[n] = sum(cfg.CU * rng.normal(1.0, MC_SIGMA) for _ in range(int(ncu)))
        return c
    return side(), side()

p_caps, n_caps = gen()
cdac_mc = DifferentialCDAC.from_mismatch(p_caps=p_caps, n_caps=n_caps)

adc = AsyncBehavioralSARADC(cdac=cdac_mc)
adc.enable_nominal_decode()
def conv(vd):
    r = adc.convert(VCM + vd/2, VCM - vd/2)
    return SARDecoder().decode(r.decisions)
vfs = measure_positive_vfs(conv, MAX_CODE, guard_codes=1)
vin, _ = build_coherent_differential_sine(vfs, FFT_PROTOCOL)
decisions = []
for vd in vin:
    r = adc.convert(VCM + vd/2, VCM - vd/2)
    decisions.append(list(r.decisions))
codes_pre = [SARDecoder().decode_fixed(d, 2) for d in decisions]
met_pre = compute_fft_coherent(codes_pre, n_bits=cfg.N_BITS, n_fft=N_FFT, signal_bin=FFT_K)

cdac_id = DifferentialCDAC.ideal()
adc_id = AsyncBehavioralSARADC(cdac=cdac_id)
adc_id.enable_nominal_decode()
pw_id_p, pw_id_n = cdac_id.get_physical_weights_per_side_q0()
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
codes_id = [oracle_dec.decode_fixed(d, 2) for d in dec_id]
met_id = compute_fft_coherent(codes_id, n_bits=cfg.N_BITS, n_fft=N_FFT, signal_bin=FFT_K)

ideal_sndr = met_id["sndr_db"]
print(f"Pre={met_pre['sndr_db']:.1f}dB  Ideal={ideal_sndr:.1f}dB")

# sweep
sndr_on  = np.full((len(NOISE_UV), len(PAIRS)), np.nan)
sndr_off = np.full((len(NOISE_UV), len(PAIRS)), np.nan)
delta    = np.full((len(NOISE_UV), len(PAIRS)), np.nan)

for i, nv in enumerate(NOISE_UV):
    noise_v = nv * 1e-6
    for j, np_ in enumerate(PAIRS):
        for mode, dither in [("on", (-1.5, -0.5, 0.5, 1.5)), ("off", (0.0,))]:
            shen = ShenCalibrationController(
                cdac=cdac_mc, comparator=DynamicComparator(),
                timing=TimingParams(), avg_pairs=np_,
                cal_noise_sigma=noise_v,
            )
            shen.fixed_dither_lsb = dither
            targets, cal_wp, cal_wn = shen.run(
                rng=np.random.default_rng(SEED + nv*100 + np_ + (0 if mode=="on" else 10000))
            )
            cal_dec = SARDecoder(weights_p=list(cal_wp), weights_n=list(cal_wn))
            codes = [cal_dec.decode_fixed(d, 2) for d in decisions]
            met = compute_fft_coherent(codes, n_bits=cfg.N_BITS, n_fft=N_FFT, signal_bin=FFT_K)
            if mode == "on":
                sndr_on[i, j] = met["sndr_db"]
                gap_on = ideal_sndr - met["sndr_db"]
            else:
                sndr_off[i, j] = met["sndr_db"]
                gap_off = ideal_sndr - met["sndr_db"]
        delta[i, j] = sndr_on[i, j] - sndr_off[i, j]
        print(f"  {nv:>4d}uV  N={np_:>3d}  ON={sndr_on[i,j]:.2f}  OFF={sndr_off[i,j]:.2f}  d={delta[i,j]:+.2f}")

# plot
fig, axes = plt.subplots(1, 3, figsize=(22, 6))
fig.suptitle(
    f"Dither ON vs OFF Heatmap  |  "
    f"MC \\sigma={MC_SIGMA*100:.0f}%, Seed={SEED}  |  "
    f"Pre={met_pre['sndr_db']:.1f}dB, Ideal={ideal_sndr:.1f}dB",
    fontsize=13, fontweight="bold", y=1.01,
)

X, Y = np.meshgrid(PAIRS, NOISE_UV)

# panel A: delta heatmap
ax = axes[0]
norm = TwoSlopeNorm(vmin=-2, vcenter=0, vmax=10)
im = ax.pcolormesh(X, Y, delta, cmap="RdBu_r", norm=norm, edgecolors='white', linewidth=0.8)
ax.set_xscale("log", base=2)
ax.set_yscale("log")
ax.set_xlabel("AVG_PAIRS", fontsize=12)
ax.set_ylabel("Comparator Noise [uV RMS]", fontsize=12)
ax.set_title("Delta SNDR = ON - OFF [dB]", fontsize=13, fontweight="bold")
ax.set_xticks(PAIRS)
ax.set_xticklabels([str(p) for p in PAIRS], fontsize=8)
ax.set_yticks(NOISE_UV)
ax.set_yticklabels([str(n) for n in NOISE_UV])
for i, nv in enumerate(NOISE_UV):
    for j, np_ in enumerate(PAIRS):
        v = delta[i, j]
        if not np.isnan(v):
            fc = "white" if abs(v) > 4 else "black"
            ax.text(np_, nv, f"{v:+.1f}", ha="center", va="center", fontsize=7.5,
                    color=fc, fontweight="bold")
cb = plt.colorbar(im, ax=ax, shrink=0.82, ticks=[-2, 0, 2, 4, 6, 8, 10])
cb.set_label("SNDR Delta [dB]", fontsize=10)
ax.axhline(439, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
ax.text(PAIRS[-1]*0.7, 460, "1 LSB = 439 uV", fontsize=8, color='gray', va='bottom')

# panel B: ON SNDR
im2 = ax = axes[1]
ax2 = axes[1]
im2 = ax2.pcolormesh(X, Y, sndr_on, cmap="RdYlBu_r", vmin=62, vmax=ideal_sndr+1,
                     edgecolors='white', linewidth=0.8)
ax2.set_xscale("log", base=2)
ax2.set_yscale("log")
ax2.set_xlabel("AVG_PAIRS", fontsize=12)
ax2.set_title("SNDR: Dither ON [dB]", fontsize=13, fontweight="bold")
ax2.set_xticks(PAIRS)
ax2.set_xticklabels([str(p) for p in PAIRS], fontsize=8)
ax2.set_yticks(NOISE_UV)
ax2.set_yticklabels([])
for i, nv in enumerate(NOISE_UV):
    for j, np_ in enumerate(PAIRS):
        v = sndr_on[i, j]
        if not np.isnan(v):
            fc = "white" if v < 69 else "black"
            ax2.text(np_, nv, f"{v:.1f}", ha="center", va="center", fontsize=7.5,
                    color=fc, fontweight="bold")
cb2 = plt.colorbar(im2, ax=ax2, shrink=0.82)
cb2.set_label("SNDR [dB]", fontsize=10)

# panel C: OFF SNDR
ax3 = axes[2]
im3 = ax3.pcolormesh(X, Y, sndr_off, cmap="RdYlBu_r", vmin=62, vmax=ideal_sndr+1,
                     edgecolors='white', linewidth=0.8)
ax3.set_xscale("log", base=2)
ax3.set_yscale("log")
ax3.set_xlabel("AVG_PAIRS", fontsize=12)
ax3.set_title("SNDR: Dither OFF [dB]", fontsize=13, fontweight="bold")
ax3.set_xticks(PAIRS)
ax3.set_xticklabels([str(p) for p in PAIRS], fontsize=8)
ax3.set_yticks(NOISE_UV)
ax3.set_yticklabels([])
for i, nv in enumerate(NOISE_UV):
    for j, np_ in enumerate(PAIRS):
        v = sndr_off[i, j]
        if not np.isnan(v):
            fc = "white" if v < 69 else "black"
            ax3.text(np_, nv, f"{v:.1f}", ha="center", va="center", fontsize=7.5,
                    color=fc, fontweight="bold")
cb3 = plt.colorbar(im3, ax=ax3, shrink=0.82)
cb3.set_label("SNDR [dB]", fontsize=10)

plt.tight_layout(rect=[0, 0, 1, 0.94])
out = os.path.join(SCRIPT_DIR, "dither_heatmap.png")
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"\nSaved: {out}")
