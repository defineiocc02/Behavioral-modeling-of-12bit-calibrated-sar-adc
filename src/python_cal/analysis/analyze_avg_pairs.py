"""
analyze_avg_pairs.py — AVG_PAIRS 对校准精度的影响
扫: 16, 32, 64, 128, 256, 512
固定 MC_SIGMA=0.01, Seed=42
"""
import sys, os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # up to src/
sys.path.insert(0, SRC_DIR)

import numpy as np
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
PAIRS_LIST = [16, 32, 64, 128, 256, 512]
N_FFT = cfg.FFT_N
FFT_K = cfg.FFT_K
MAX_CODE = (1 << cfg.N_BITS) - 1
VCM = cfg.VCM

FFT_PROTOCOL = FFTProtocol(
    n_fft=N_FFT, signal_bin=FFT_K,
    amplitude_dbfs=cfg.FFT_AMPLITUDE_DBFS, phase_rad=cfg.FFT_PHASE,
)

# generate caps once
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

# ideal oracle
cdac_id = DifferentialCDAC.ideal()
pw_id_p, pw_id_n = cdac_id.get_physical_weights_per_side_q0()

# shared decisions (pre-cal)
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

print("=" * 70)
print(f"  AVG_PAIRS sweep  |  MC_sigma={MC_SIGMA*100:.0f}%  Seed={SEED}")
print(f"  Pre-Cal: {met_pre['sndr_db']:.2f} dB / {met_pre['enob']:.2f} b")
print(f"  Ideal:   {met_id['sndr_db']:.2f} dB / {met_id['enob']:.2f} b")
print("=" * 70)

print(f"\n{'Pairs':>6s}  {'SNDR':>7s}  {'ENOB':>6s}  {'Gap':>7s}  "
      f"{'H1_err%':>8s}  {'H2_err%':>8s}  {'H8A_err%':>8s}  {'H32_err%':>8s}  {'Valid':>5s}  {'Time':>8s}")
print("-" * 85)

import time

for n_pairs in PAIRS_LIST:
    t0 = time.time()
    shen = ShenCalibrationController(
        cdac=cdac_mc, comparator=DynamicComparator(),
        timing=TimingParams(), avg_pairs=n_pairs,
        cal_noise_sigma=cfg.CAL_NOISE_SIGMA_V,
    )
    targets, cal_wp, cal_wn = shen.run(rng=np.random.default_rng(SEED + n_pairs))
    elapsed = time.time() - t0
    valid = all(t['valid'] for t in targets)

    cal_dec = SARDecoder(weights_p=list(cal_wp), weights_n=list(cal_wn))
    codes_post = [cal_dec.decode_fixed(d, fractional_bits=2) for d in decisions]
    met_post = compute_fft_coherent(codes_post, n_bits=cfg.N_BITS, n_fft=N_FFT, signal_bin=FFT_K)
    gap = met_id["sndr_db"] - met_post["sndr_db"]

    # per-target errors
    errs = {}
    for t in targets:
        errs[t['target_name']] = abs(t['W_avg'] - t['nominal']) / t['nominal'] * 100

    print(
        f"{n_pairs:>6d}  {met_post['sndr_db']:>6.2f}  {met_post['enob']:>5.2f}  "
        f"{gap:>6.2f}  "
        f"{errs.get('H1C', 0):>7.3f}  {errs.get('H2C', 0):>7.3f}  "
        f"{errs.get('H8C-A', 0):>7.3f}  {errs.get('H32C', 0):>7.3f}  "
        f"{'OK' if valid else 'FAIL':>5s}  {elapsed:>7.2f}s"
    )

# theoretical noise estimate
sigma_single = cfg.CAL_NOISE_SIGMA_V * np.sqrt(2) / 2  # half-diff of two noisy measurements
sigma_single_lsb = sigma_single / (cfg.VREF / (1 << cfg.N_BITS))
print(f"\nTheoretical: comparator noise = {cfg.CAL_NOISE_SIGMA_V*1e3:.1f} mV RMS")
print(f"  Per-pair W_k measurement std = {sigma_single_lsb:.2f} LSB = {sigma_single*1e3:.3f} mV")
for n in PAIRS_LIST:
    std_w = sigma_single_lsb / np.sqrt(n)
    # H1C is 67 Q0, calibration error translates to DNL
    h1_3sigma = 3 * std_w  # 3-sigma calibration error in LSB
    print(f"  N={n:>3d}: sigma_W = {std_w:.3f} LSB, 3-sigma(H1) = {h1_3sigma:.3f} LSB → "
          f"{'PASS' if h1_3sigma < 0.5 else 'MARGINAL' if h1_3sigma < 1.0 else 'FAIL'}")
