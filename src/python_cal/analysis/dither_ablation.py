"""
dither_ablation.py — Dither ON vs OFF across AVG_PAIRS
"""
import sys, os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # up to src/
sys.path.insert(0, SRC_DIR)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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

SEED = 42
MC_SIGMA = 0.01
PAIRS_LIST = [2, 4, 8, 16, 32, 64, 128, 256, 512]
N_FFT = cfg.FFT_N
FFT_K = cfg.FFT_K
MAX_CODE = (1 << cfg.N_BITS) - 1
VCM = cfg.VCM

FFT_PROTOCOL = FFTProtocol(
    n_fft=N_FFT, signal_bin=FFT_K,
    amplitude_dbfs=cfg.FFT_AMPLITUDE_DBFS, phase_rad=cfg.FFT_PHASE,
)

# ── shared setup ──
rng = np.random.default_rng(SEED)
_mode = getattr(cfg, "MISMATCH_MODE", "per_unit")
def gen():
    def side():
        c = {}
        for n in cfg.ALL_CAP_NAMES:
            ncu = cfg.CAP_NOMINAL_CU[n]
            if _mode == "per_cap":
                c[n] = cfg.CU * ncu * rng.normal(1.0, MC_SIGMA)
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
pw_id_p, pw_id_n = cdac_id.get_physical_weights_per_side_q0()
oracle_dec = SARDecoder(weights_p=list(pw_id_p), weights_n=list(pw_id_n))
met_id = compute_fft_coherent(
    [oracle_dec.decode_fixed(d, 2) for d in decisions], n_bits=cfg.N_BITS, n_fft=N_FFT, signal_bin=FFT_K
)

# ── run both dither ON and OFF ──
results = {"on": {}, "off": {}}
cal_noises = [100, 500, 1000]  # uV → test noise dependence

for nv in cal_noises:
    noise_v = nv * 1e-6
    for mode, dither in [("on", (-1.5, -0.5, 0.5, 1.5)), ("off", (0.0,))]:
        label = f"{nv}uV_{mode}"
        sndrs = []
        gaps = []
        for n_pairs in PAIRS_LIST:
            shen = ShenCalibrationController(
                cdac=cdac_mc, comparator=DynamicComparator(),
                timing=TimingParams(), avg_pairs=n_pairs,
                cal_noise_sigma=noise_v,
            )
            shen.fixed_dither_lsb = dither  # override
            targets, cal_wp, cal_wn = shen.run(
                rng=np.random.default_rng(SEED + nv * 100 + n_pairs + (0 if mode == "on" else 10000))
            )
            cal_dec = SARDecoder(weights_p=list(cal_wp), weights_n=list(cal_wn))
            codes = [cal_dec.decode_fixed(d, 2) for d in decisions]
            met = compute_fft_coherent(codes, n_bits=cfg.N_BITS, n_fft=N_FFT, signal_bin=FFT_K)
            sndrs.append(met["sndr_db"])
            gaps.append(met_id["sndr_db"] - met["sndr_db"])
        results[mode][label] = {"sndr": sndrs, "gap": gaps}

print("=" * 80)
print(f"  Dither ON  vs  OFF  |  Pre={met_pre['sndr_db']:.1f}dB  Ideal={met_id['sndr_db']:.1f}dB")
print("=" * 80)
for nv in cal_noises:
    on_key = f"{nv}uV_on"
    off_key = f"{nv}uV_off"
    print(f"\n  ---- comparator noise = {nv} uV ----")
    print(f"  {'Pairs':>6s}  {'ON-SNDR':>8s}  {'OFF-SNDR':>8s}  {'Delta':>8s}  {'ON-gap':>8s}  {'OFF-gap':>8s}")
    for j, np_ in enumerate(PAIRS_LIST):
        s_on  = results["on"][on_key]["sndr"][j]
        s_off = results["off"][off_key]["sndr"][j]
        g_on  = results["on"][on_key]["gap"][j]
        g_off = results["off"][off_key]["gap"][j]
        print(f"  {np_:>6d}  {s_on:>8.2f}  {s_off:>8.2f}  {s_on-s_off:>+8.2f}  {g_on:>8.3f}  {g_off:>8.3f}")

# ── PLOT ──
fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), sharey=True)
fig.suptitle(
    "Dither Ablation: ON vs OFF  |  "
    f"Pre-Cal = {met_pre['sndr_db']:.1f} dB, Ideal = {met_id['sndr_db']:.1f} dB",
    fontsize=13, fontweight="bold", y=0.99,
)

colors = {"on": "#2C7A7B", "off": "#C53030"}
for idx, nv in enumerate(cal_noises):
    ax = axes[idx]
    on_key = f"{nv}uV_on"
    off_key = f"{nv}uV_off"
    ax.plot(PAIRS_LIST, results["on"][on_key]["sndr"], 'o-', color=colors["on"],
            linewidth=1.5, markersize=6, label="Dither ON")
    ax.plot(PAIRS_LIST, results["off"][off_key]["sndr"], 's--', color=colors["off"],
            linewidth=1.5, markersize=6, label="Dither OFF")
    ax.axhline(met_id["sndr_db"], color="#1A365D", linestyle=":", linewidth=1,
               label=f"Ideal = {met_id['sndr_db']:.1f} dB")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("AVG_PAIRS", fontsize=10)
    ax.set_title(f"Comparator Noise = {nv} uV RMS", fontsize=11, fontweight="bold")
    ax.set_xticks(PAIRS_LIST)
    ax.set_xticklabels([str(p) for p in PAIRS_LIST], fontsize=7, rotation=30)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, framealpha=0.8)

axes[0].set_ylabel("Post-Cal SNDR [dB]", fontsize=11)
plt.tight_layout(rect=[0, 0, 1, 0.94])
out = os.path.join(SCRIPT_DIR, "dither_ablation.png")
fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"\nSaved: {out}")
