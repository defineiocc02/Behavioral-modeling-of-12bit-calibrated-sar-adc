"""
review_monitor_check.py — 监控核查脚本（审查方，只读/独立实验，不改模型代码）
======================================================================
核查对象: reports/bridge_root_cause_report.md 声称
  "Verdict: MODELING_BUG; DC sweep missing 0/4096; Bridge SAR SNDR 73.59"

核查项:
  P1: 从构建方 dc_sweep_raw.csv 独立统计 unique/missing/nonmono/奇偶
  P2: 从构建方 reachable_levels.csv 统计 level 数与 1-LSB 网格覆盖
  P3: 当前代码（新 decoder ÷2）下重跑审查方实验 A/D（±0.43 与 ±0.86 两种扫描范围）
  P4: 当前代码零噪声校准 ideal CDAC —— H1C-A 是否测得 65（terminal 修复是否生效）
"""
import sys, json, time
import numpy as np

sys.path.insert(0, r"C:\Users\Administrator\Desktop\SAR_ADC_IDEAL_CAL_REPLACEMENT_V6_CLEAN\src")
REPORTS = r"C:\Users\Administrator\Desktop\SAR_ADC_IDEAL_CAL_REPLACEMENT_V6_CLEAN\src\python_cal\reports"

from python_cal import config as cfg
from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
from python_cal.physical.differential_cdac import DifferentialCDAC

out = {}
t0 = time.time()

# ---------- P1: 构建方 DC sweep CSV 独立统计 ----------
import csv
with open(REPORTS + r"\dc_sweep_raw.csv") as f:
    rows = list(csv.DictReader(f))
vin = np.array([float(r["vin_diff"]) for r in rows])
for col in ["code_nominal", "code_physical"]:
    codes = np.array([int(r[col]) for r in rows])
    uniq = np.unique(codes)
    in_r = uniq[(uniq >= 0) & (uniq <= 4095)]
    missing = sorted(set(range(4096)) - set(in_r.tolist()))
    nonmono = int((np.diff(codes) < 0).sum())
    out[f"P1_builder_dc_{col}"] = dict(
        n_rows=len(rows), vin_min=float(vin.min()), vin_max=float(vin.max()),
        unique=len(in_r), missing=len(missing), nonmono=nonmono,
        missing_even=sum(1 for c in missing if c % 2 == 0),
        missing_odd=sum(1 for c in missing if c % 2 == 1),
        clip_low=int((codes == 0).sum()), clip_high=int((codes == 4095).sum()),
    )

# ---------- P2: reachable_levels.csv ----------
with open(REPORTS + r"\reachable_levels.csv") as f:
    rows = list(csv.DictReader(f))
vd = np.array([float(r["vdiff_v"]) for r in rows])
cn = np.array([int(r["code_nominal"]) for r in rows])
out["P2_reachable"] = dict(
    n_rows=len(rows), unique_vdiff=len(np.unique(vd)),
    unique_code_nominal=len(np.unique(cn)),
    vdiff_min=float(vd.min()), vdiff_max=float(vd.max()),
)

# ---------- P3: 当前代码重跑 FFT 与 DC ----------
N, K = cfg.FFT_N, cfg.FFT_K

def sndr_thd(codes):
    x = codes.astype(float) - codes.mean()
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
    return 10 * np.log10(sig / (p_hd + P[mask].sum())), 10 * np.log10(sig / max(p_hd, 1e-30))

adc = AsyncBehavioralSARADC(cdac=DifferentialCDAC.ideal())
adc.enable_nominal_decode()

def conv(v):
    r = adc.convert_diff(v)
    return adc.decode(r.decisions)

for tag, vfs in [("half_0.4301", 0.4301), ("full_0.8597", 0.85968269)]:
    n = np.arange(N)
    amp = vfs * 10 ** (cfg.FFT_AMPLITUDE_DBFS / 20.0)
    vsin = amp * np.sin(2 * np.pi * K * n / N + cfg.FFT_PHASE)
    codes = np.array([conv(float(v)) for v in vsin])
    s, t = sndr_thd(codes)
    # DC 扫描
    vs = np.linspace(-vfs, vfs, 4097)
    cs = np.array([conv(float(v)) for v in vs])
    uniq = np.unique(cs)
    in_r = uniq[(uniq >= 0) & (uniq <= 4095)]
    missing = sorted(set(range(4096)) - set(in_r.tolist()))
    out[f"P3_current_{tag}"] = dict(
        fft_sndr=round(s, 2), fft_thd=round(t, 2),
        dc_unique=len(in_r), dc_missing=len(missing),
        dc_nonmono=int((np.diff(cs) < 0).sum()),
        missing_even=sum(1 for c in missing if c % 2 == 0),
        missing_odd=sum(1 for c in missing if c % 2 == 1),
        code_min=int(cs.min()), code_max=int(cs.max()),
    )

# ---------- P4: 零噪声校准 terminal 修复验证 ----------
cal_adc = AsyncBehavioralSARADC(cdac=DifferentialCDAC.ideal())
rep = cal_adc.run_calibration(avg_pairs=16, rng=None, cal_noise_sigma=0.0)
tg = rep.targets
out["P4_cal_ideal_zero_noise"] = dict(
    valid=rep.valid,
    h1ca_measured=tg[0].measured_weight_q0,
    h32c_measured=tg[6].measured_weight_q0,
    phys_refs=[round(t.physical_weight_q0, 2) for t in tg],
    measured=[round(t.measured_weight_q0, 2) for t in tg],
)

out["elapsed_s"] = round(time.time() - t0, 1)
print(json.dumps(out, indent=1, ensure_ascii=False))
