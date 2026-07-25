"""
compare_old_vs_new.py — Old (AVG=512) vs New (AVG=128) head-to-head
Same MC sigma, same seed.
"""
import sys, os, time
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
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

N_FFT = cfg.FFT_N; FFT_K = cfg.FFT_K
MAX_CODE = (1 << cfg.N_BITS) - 1
VCM = cfg.VCM
MC_SIGMA = cfg.MC_SIGMA
CAL_NOISE = cfg.CAL_NOISE_SIGMA_V
DITHER = cfg.SHEN_DITHER_LSB

FFT_PROTOCOL = FFTProtocol(
    n_fft=N_FFT, signal_bin=FFT_K,
    amplitude_dbfs=cfg.FFT_AMPLITUDE_DBFS, phase_rad=cfg.FFT_PHASE,
)

# single MC seed for fair comparison
BASE_SEED = 12345
rng = np.random.default_rng(BASE_SEED)

def gen_caps(seed):
    r = np.random.default_rng(seed)
    def side():
        c = {}
        for n in cfg.ALL_CAP_NAMES:
            ncu = cfg.CAP_NOMINAL_CU[n]
            c[n] = sum(cfg.CU * r.normal(1.0, MC_SIGMA) for _ in range(int(ncu)))
        return c
    return side(), side()

p_caps, n_caps = gen_caps(BASE_SEED)
cdac_mc = DifferentialCDAC.from_mismatch(p_caps=p_caps, n_caps=n_caps)

# shared decisions
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

# pre-cal
codes_pre = [SARDecoder().decode_fixed(d, 2) for d in decisions]
met_pre = compute_fft_coherent(codes_pre, n_bits=cfg.N_BITS, n_fft=N_FFT, signal_bin=FFT_K)

# ideal (no mismatch, physical oracle)
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

# run calibration at different AVG_PAIRS
pairs_list = [128, 512]
results = {}

for np_ in pairs_list:
    t0 = time.perf_counter()
    shen = ShenCalibrationController(
        cdac=cdac_mc, comparator=DynamicComparator(),
        timing=TimingParams(), avg_pairs=np_,
        cal_noise_sigma=CAL_NOISE,
    )
    shen.fixed_dither_lsb = DITHER
    targets, cal_wp, cal_wn = shen.run(
        rng=np.random.default_rng(BASE_SEED + np_)
    )
    elapsed = time.perf_counter() - t0

    cal_dec = SARDecoder(weights_p=list(cal_wp), weights_n=list(cal_wn))
    codes = [cal_dec.decode_fixed(d, 2) for d in decisions]
    met = compute_fft_coherent(codes, n_bits=cfg.N_BITS, n_fft=N_FFT, signal_bin=FFT_K)
    results[np_] = {
        "sndr": met["sndr_db"], "sfdr": met["sfdr_db"],
        "enob": met.get("enob", 0.0), "gap": ideal_sndr - met["sndr_db"],
        "time": elapsed, "weights": (cal_wp, cal_wn),
    }

# also run with old dither (512, dither ON) for reference
t0 = time.perf_counter()
shen = ShenCalibrationController(
    cdac=cdac_mc, comparator=DynamicComparator(),
    timing=TimingParams(), avg_pairs=512,
    cal_noise_sigma=CAL_NOISE,
)
shen.fixed_dither_lsb = (-1.5, -0.5, 0.5, 1.5)
targets, cal_wp, cal_wn = shen.run(
    rng=np.random.default_rng(BASE_SEED + 99999)
)
elapsed = time.perf_counter() - t0
cal_dec = SARDecoder(weights_p=list(cal_wp), weights_n=list(cal_wn))
codes = [cal_dec.decode_fixed(d, 2) for d in decisions]
met = compute_fft_coherent(codes, n_bits=cfg.N_BITS, n_fft=N_FFT, signal_bin=FFT_K)
results["512-old"] = {
    "sndr": met["sndr_db"], "sfdr": met["sfdr_db"],
    "enob": met.get("enob", 0.0), "gap": ideal_sndr - met["sndr_db"],
    "time": elapsed, "weights": (cal_wp, cal_wn),
}

# ── print table ──
print("=" * 90)
print(f"  Old (AVG=512) vs New (AVG=128)  |  MC_SIGMA={MC_SIGMA}  Seed={BASE_SEED}")
print(f"  Pre={met_pre['sndr_db']:.1f}dB  Ideal={ideal_sndr:.1f}dB")
print("=" * 90)
print(f"  {'':>12s}  {'SNDR':>7s}  {'SFDR':>7s}  {'ENOB':>7s}  {'Oracle Gap':>11s}  {'Time':>7s}")
print(f"  {'─'*12}  {'─'*7}  {'─'*7}  {'─'*7}  {'─'*11}  {'─'*7}")

for label in ["128-str", "512-str", "512-old"]:
    if label == "128-str":
        r, tag = results[128], "NEW (AVG=128)"
    elif label == "512-str":
        r, tag = results[512], "512 w/ dither"
    else:
        r, tag = results["512-old"], "OLD (ref)"
    print(f"  {tag:>12s}  {r['sndr']:>7.2f}  {r['sfdr']:>7.2f}  {r['enob']:>7.2f}  {r['gap']:>11.4f}  {r['time']:>6.2f}s")

print(f"\n  AVG=128 vs AVG=512 delta SNDR: {results[128]['sndr']-results[512]['sndr']:+.2f} dB")
print(f"  AVG=128 vs OLD delta SNDR:      {results[128]['sndr']-results['512-old']['sndr']:+.2f} dB")

# ── plot weight comparison ──
fig, axes = plt.subplots(1, 1, figsize=(10, 6))

stages = cfg.SHEN_CAL_TARGET_STAGES
names = [cfg.STAGE_NAMES[s] for s in stages]
nom_w = [cfg.NOMINAL_WEIGHTS_Q0[s] for s in stages]

x = np.arange(len(names))
w = 0.25

for idx, (label, key) in enumerate([("OLD (AVG=512)", "512-old"), ("NEW (AVG=128)", 128)]):
    wp, wn = results[key]["weights"]
    cal_w_avg = [(wp[s] + wn[s]) / 2 for s in stages]
    err = [(cal_w_avg[i] - nom_w[i]) / nom_w[i] * 100 for i in range(len(stages))]
    bars = axes.bar(x + idx * w, err, w, label=label, alpha=0.85)

axes.axhline(0, color='black', linewidth=0.6)
axes.set_xticks(x + w / 2)
axes.set_xticklabels(names, fontsize=10)
axes.set_ylabel("Weight Error [%]", fontsize=12)
axes.set_title(f"Calibrated Weight Error: OLD (AVG=512) vs NEW (AVG=128)\n"
               f"MC={MC_SIGMA*100:.0f}%  Seed={BASE_SEED}", fontsize=12, fontweight="bold")
axes.legend(fontsize=10)
axes.grid(axis='y', alpha=0.25)

for idx, (label, key) in enumerate([("OLD", "512-old"), ("NEW", 128)]):
    wp, wn = results[key]["weights"]
    for i, s in enumerate(stages):
        cal_w_avg = (wp[s] + wn[s]) / 2
        e = (cal_w_avg - nom_w[i]) / nom_w[i] * 100
        axes.text(x[i] + idx * w, e + (0.03 if e >= 0 else -0.08),
                 f"{e:+.2f}%", ha='center', fontsize=7, rotation=90)

plt.tight_layout()
out = os.path.join(SCRIPT_DIR, "old_vs_new_comparison.png")
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"\nSaved: {out}")

print("\nDone.")
