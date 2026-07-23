"""
review41_pn_check.py — 41 号审查附件：P/N asym 与 bridge +2% 场景校准抽查
========================================================================
审查方独立执行，只 import 生产包，不修改任何模型源码。
方法对齐构建方 run_behavioral_audit.py §11: 同一批 decisions, 三种 decoder。
"""
import sys, json, time
import numpy as np

sys.path.insert(0, r"C:\Users\Administrator\Desktop\SAR_ADC_IDEAL_CAL_REPLACEMENT_V6_CLEAN\src")

from python_cal import config as cfg
from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
from python_cal.decode.sar_decoder import SARDecoder
from python_cal.physical.differential_cdac import DifferentialCDAC

N, K = cfg.FFT_N, cfg.FFT_K
VFS = 0.859893
AMP = VFS * 10 ** (cfg.FFT_AMPLITUDE_DBFS / 20.0)
n = np.arange(N)
VIN = AMP * np.sin(2 * np.pi * K * n / N + cfg.FFT_PHASE)
VCM = cfg.VCM


def sndr(codes):
    codes = np.asarray(codes, dtype=float)
    x = codes - np.mean(codes)
    P = np.abs(np.fft.rfft(x)) ** 2
    sig = P[K]
    harm = set()
    for h in range(2, 33):
        b = (h * K) % N
        b = min(b, N - b)
        if b in (0, K):
            continue
        harm.add(b)
    harm = sorted(harm)
    mask = np.ones(len(P), bool)
    mask[0] = False
    mask[K] = False
    for b in harm:
        mask[b] = False
    p_hd = P[harm].sum()
    return 10 * np.log10(sig / (p_hd + P[mask].sum()))


def run_scenario(tag, cdac):
    t0 = time.time()
    adc = AsyncBehavioralSARADC(cdac=cdac)
    adc.enable_nominal_decode()
    decisions = []
    for vd in VIN:
        r = adc.convert(VCM + vd / 2, VCM - vd / 2)
        decisions.append(list(r.decisions))

    codes_nom = [SARDecoder().decode(d) for d in decisions]
    phys_w = cdac.get_physical_weights_q0()
    codes_phy = [SARDecoder(weights=list(phys_w)).decode(d) for d in decisions]

    rep = adc.run_calibration(avg_pairs=16, rng=None, cal_noise_sigma=0.0)
    cal_w0 = list(rep.weights_q0)
    codes_cal = [SARDecoder(weights=cal_w0).decode(d) for d in decisions]

    per_target = []
    for t in rep.targets:
        per_target.append(dict(
            name=t.target_name, stage=t.stage,
            physical=round(t.physical_weight_q0, 3),
            measured=round(t.measured_weight_q0, 3),
            err_q0=round(t.measured_weight_q0 - t.physical_weight_q0, 3),
            dplus=round(t.dplus_mean_q0, 3), dminus=round(t.dminus_mean_q0, 3),
        ))
    return {
        "scenario": tag,
        "sndr_nominal": round(sndr(codes_nom), 2),
        "sndr_calibrated": round(sndr(codes_cal), 2),
        "sndr_physical": round(sndr(codes_phy), 2),
        "cal_valid": rep.valid,
        "per_target": per_target,
        "phys_w_stage0to6": [round(phys_w[s], 3) for s in range(7)],
        "cal_w_stage0to6": [round(cal_w0[s], 3) for s in range(7)],
        "low_seg_phys_w_stage7to12": [round(phys_w[s], 3) for s in range(7, 13)],
        "elapsed_s": round(time.time() - t0, 1),
    }


out = {}
# P/N asym: md=+2% (P), mu=-2% (N)
out["pn_asym"] = run_scenario(
    "P/N asym",
    DifferentialCDAC.from_mismatch(md=[1.02] * 7, mu=[0.98] * 7))
# bridge +2%
CU = cfg.CU
caps = {'low_1c': 1 * CU, 'low_2c': 2 * CU, 'low_4c': 4 * CU, 'low_8c': 8 * CU,
        'low_16c': 16 * CU, 'low_32c': 32 * CU, 'bridge': 2 * CU * 1.02,
        'high_1c_a': 1 * CU, 'high_1c_r': 1 * CU, 'high_2c': 2 * CU,
        'high_4c': 4 * CU, 'high_8c': 8 * CU, 'high_16c': 16 * CU,
        'high_32c': 32 * CU}
out["bridge_2pct"] = run_scenario(
    "bridge +2%",
    DifferentialCDAC.from_mismatch(p_caps=caps, n_caps=caps))

print(json.dumps(out, indent=1, ensure_ascii=False))
