"""
review38_experiments.py — 38 号审查文档附件：独立验证实验
==========================================================
【状态: OBSOLETE — 保留作历史证据, 勿用于复测】
本脚本写于 decoder ÷2 修复之前, VFS=0.4301 V 是老 decoder 的**假满量程**
（真实满量程为 ±0.8597 V, 1 code-LSB = 2 Q0）。
其 A/B/C/D 结果 (67.52 dB / 2047 缺码) 记录的是"老 decoder + 半量程扫描"
混合状态下的现象, 其中 D1 奇偶锁定证据仍有效, 但 38 号 P0-C(ii) 已撤回。
当前代码的核查请使用 reports/review_monitor_check.py。
======================================================================
审查方独立执行，不修改 python_cal 任何源码。

实验设计（对应 37 号文档 §九 的 A/B/D 思想）:
  A: ideal CDAC + nominal decode 的 FFT SNDR —— 与 v2.0.0 报告 §11 交叉核对
  B: ideal CDAC + 排序码本最近电平搜索 (research/codebook_search) ——
     区分"贪心 SAR 搜索/decoder"与"DAC level 集合"谁是缺码来源
  C: 高段电容 ±0.1% 非比例扰动 + physical decode —— 打破精确整数权重网格,
     检验 67.5 dB 与半数缺码是否为"整数权重粒度伪影"
  D: 4097 点 DC 扫描统计 unique/missing/non-monotonic + 缺失码奇偶模式
"""
import sys, json, time
import numpy as np

sys.path.insert(0, r"C:\Users\Administrator\Desktop\SAR_ADC_IDEAL_CAL_REPLACEMENT_V6_CLEAN\src")

from python_cal import config as cfg
from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.research.codebook_search import CodebookNearestSearch

N, K = cfg.FFT_N, cfg.FFT_K
VFS = 0.4301                       # v2.0.0 报告 §10.5 实测满量程 (单边, V)
AMP = VFS * 10 ** (cfg.FFT_AMPLITUDE_DBFS / 20.0)
n = np.arange(N)
VIN = AMP * np.sin(2 * np.pi * K * n / N + cfg.FFT_PHASE)


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
    p_nd = p_hd + P[mask].sum()
    return 10 * np.log10(sig / p_nd), 10 * np.log10(sig / max(p_hd, 1e-30))


def fft_run(convert_fn):
    codes = np.array([convert_fn(float(v)) for v in VIN])
    return sndr_thd(codes)


def dc_missing(convert_fn, npts=4097):
    vs = np.linspace(-VFS, VFS, npts)
    cs = np.array([convert_fn(float(v)) for v in vs])
    uniq = np.unique(cs)
    in_range = uniq[(uniq >= 0) & (uniq <= 4095)]
    missing_set = sorted(set(range(4096)) - set(in_range.tolist()))
    nonmono = int((np.diff(cs) < 0).sum())
    n_even = sum(1 for c in missing_set if c % 2 == 0)
    return dict(unique=len(in_range), missing=len(missing_set),
                nonmono=nonmono, missing_even=n_even,
                missing_odd=len(missing_set) - n_even)


t0 = time.time()
log = {}

# --- A: ideal CDAC + nominal decode (报告交叉核对, 预期 ~67.5) ---
adc = AsyncBehavioralSARADC(cdac=DifferentialCDAC.ideal())
adc.enable_nominal_decode()

def conv_ideal(v):
    r = adc.convert_diff(v)
    return adc.decode(r.decisions)

s, t = fft_run(conv_ideal)
log['A_ideal_nominal_FFT'] = dict(sndr=round(s, 2), thd=round(t, 2), expect='~67.5 per report')

# --- B: ideal CDAC + exhaustive sorted-codebook nearest search (E2) ---
cb = CodebookNearestSearch(DifferentialCDAC.ideal(), weights_q0=None,
                           conv_noise_sigma=0.0)
codes_b = cb.convert_batch(VIN, rng=None)
s, t = sndr_thd(codes_b)
log['B_ideal_codebook_FFT'] = dict(sndr=round(s, 2), thd=round(t, 2),
                                   note='>=73 => 缺码源自贪心搜索/decoder; ~67.5 => 指向 DAC level 集合')

# --- C: 高段 ±0.1% 非比例扰动 + physical decode (E1) ---
CU = cfg.CU
factors = {'high_1c_a': 1.0007, 'high_1c_r': 0.9993, 'high_2c': 1.0011,
           'high_4c': 0.9989, 'high_8c': 1.0013, 'high_16c': 0.9987,
           'high_32c': 1.0003}
nom_cu = {'high_1c_a': 1, 'high_1c_r': 1, 'high_2c': 2, 'high_4c': 4,
          'high_8c': 8, 'high_16c': 16, 'high_32c': 32}
caps = {'low_1c': 1 * CU, 'low_2c': 2 * CU, 'low_4c': 4 * CU, 'low_8c': 8 * CU,
        'low_16c': 16 * CU, 'low_32c': 32 * CU, 'bridge': 2 * CU}
for k, f in factors.items():
    caps[k] = nom_cu[k] * CU * f

cdac_p = DifferentialCDAC.from_mismatch(p_caps=caps, n_caps=caps)
phys_w = cdac_p.get_physical_weights_q0()
adc_p = AsyncBehavioralSARADC(cdac=cdac_p)
adc_p.enable_nominal_decode()
adc_p._decoder.update_weights(list(phys_w))

def conv_pert(v):
    r = adc_p.convert_diff(v)
    return adc_p.decode(r.decisions)

s, t = fft_run(conv_pert)
log['C_perturbed_physical_FFT'] = dict(
    sndr=round(s, 2), thd=round(t, 2),
    phys_w_stage0to6=[round(phys_w[i], 3) for i in range(7)],
    note='SNDR 回升 => 67.5 为整数权重粒度伪影; 不变 => 支持架构解释')

# --- D: DC 扫描缺码统计 ---
log['D1_dc_ideal_nominal'] = dc_missing(conv_ideal)
log['D2_dc_perturbed_physical'] = dc_missing(conv_pert)

log['elapsed_s'] = round(time.time() - t0, 1)
print(json.dumps(log, indent=1, ensure_ascii=False))
