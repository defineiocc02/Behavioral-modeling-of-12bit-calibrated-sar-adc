"""
run_final_calibration_pipeline.py — SAR ADC 校准验收管线

完整流程:
  1. 生成 MC 失配场景 (unit-cap sigma from config.MC_SIGMA)
  2. Seven-target high-segment calibration using P/N half differences
     Order: H1→H2→H4→H8-R→H8-A→H16→H32
     Ruler: the complete 131-Q0 low segment plus terminal
     高段递归: 使用已校准高段 + 标称低段作为 ruler
  3. 静态审计: 对 Q2 加权 decoder 做精确可达决策树检查
  4. 动态验证: SNDR/SFDR/ENOB (coherent sine FFT, Q2 weighted output)
  5. 归一化权重比例误差: e_ratio = (Ŵ_i/ΣŴ)/(W_i/ΣW) - 1
  6. Monte Carlo yield: config.MC_SEEDS_PIPELINE seeds
  7. 输出: CSV + JSON + Markdown 报告

验收标准:
  - gap P50 <= 0.5 dB AND gap P95 <= 2.0 dB -> PASS
  - gap P50 <= 1.0 dB AND gap P95 <= 3.0 dB -> CONDITIONAL PASS
  - 否则 -> FAIL

变更历史:
  v3.0 locks the 138-Cu integer array, full-array sampling, ordinary
  weighted-sum decode, exact code-density static metrics and coherent FFT.
  - v6: 每 seed 精确可达静态审计；不改变论文式加权 decoder
"""
import sys, os, math, csv, json, hashlib, time
import numpy as np
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SRC_DIR)
OUT_DIR = os.path.join(SCRIPT_DIR, "validation_results", "final_pipeline")
os.makedirs(OUT_DIR, exist_ok=True)

from python_cal import config as cfg
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.comparator.dynamic_comparator import DynamicComparator
from python_cal.async_control.timing import TimingParams
from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
from python_cal.decode.sar_decoder import SARDecoder
from python_cal.topology.cdac_topology import VCM, VREF, CU, N_STAGES, N_BITS
from python_cal.calibration.shen_calibrator import ShenCalibrationController
from python_cal.calibration.calibration_fsm import ADCOperatingMode
from python_cal.provenance import generate_manifest, save_manifest_compact
from python_cal.fft_metrics import compute_fft_coherent
from python_cal.validation.fft_protocol import (
    FFTProtocol,
    build_coherent_differential_sine,
    measure_positive_vfs,
    validate_fft_stimulus,
)
from python_cal.validation.reachable_codebook import (
    audit_reachable_codebook,
    enumerate_reachable_leaves,
)

# ===================================================================
# 参数 (全部从 config 引用, 不硬编码)
# ===================================================================
MC_SEEDS   = int(os.environ.get("SAR_MC_SEEDS", cfg.MC_SEEDS_PIPELINE))
MC_SIGMA   = cfg.MC_SIGMA
CAL_NOISE  = cfg.CAL_NOISE_SIGMA_V
AVG_PAIRS  = int(os.environ.get("SAR_AVG_PAIRS", cfg.AVG_PAIRS))
MAX_CODE   = (1 << N_BITS) - 1  # 4095
N_FFT      = cfg.FFT_N
FFT_K      = cfg.FFT_K
SINE_AMP   = cfg.FFT_AMPLITUDE_DBFS
SINE_PHASE = cfg.FFT_PHASE
FFT_PROTOCOL = FFTProtocol(
    n_fft=N_FFT,
    signal_bin=FFT_K,
    amplitude_dbfs=SINE_AMP,
    phase_rad=SINE_PHASE,
)
OUTPUT_FRACTIONAL_BITS = 2

# 用户绝对验收门。oracle gap 只作相对诊断，不能替代绝对 ENOB 门。
MIN_CAL_ENOB_BITS = 11.5
MIN_CAL_SNDR_DB = 6.02 * MIN_CAL_ENOB_BITS + 1.76

# 从 config 派生
TARGET_STAGES = list(cfg.SHEN_CAL_TARGET_STAGES)
STAGE_NAMES   = list(cfg.STAGE_NAMES)
ALL_CAP_NAMES = list(cfg.ALL_CAP_NAMES)

# ===================================================================
# 静态测试工具
# ===================================================================
def _make_adc(cdac, wp, wn):
    adc = AsyncBehavioralSARADC(cdac=cdac)
    adc._decoder = SARDecoder(weights_p=list(wp), weights_n=list(wn))
    adc._nominal_decode_enabled = True
    object.__setattr__(adc, 'mode', ADCOperatingMode.READY)
    return adc

def _conv(adc, vd):
    """Single differential conversion → decoded code."""
    r = adc.convert(VCM + vd/2, VCM - vd/2)
    return SARDecoder().decode(r.decisions)

# ===================================================================
# MC 电容生成
# ===================================================================
def gen_mc_caps(seed):
    """Generate P/N independent caps with unit-cap-level MC mismatch."""
    rng = np.random.default_rng(seed)
    def make_side():
        caps = {}
        for name in ALL_CAP_NAMES:
            cu_val = cfg.CAP_NOMINAL_CU[name]
            if cu_val >= 1:
                caps[name] = sum(CU * rng.normal(1.0, MC_SIGMA) for _ in range(int(cu_val)))
            else:
                caps[name] = CU * cu_val * rng.normal(1.0, MC_SIGMA)
        return caps
    return make_side(), make_side()

# ===================================================================
# 单 seed 运行
# ===================================================================
def run_one_seed(seed, _seed_idx):
    """Run calibration, exact reachable static audit, and coherent FFT."""
    p_caps, n_caps = gen_mc_caps(seed)
    cdac = DifferentialCDAC.from_mismatch(p_caps=p_caps, n_caps=n_caps)
    pw_p, pw_n = cdac.get_physical_weights_per_side_q0()
    pw = [(p + n) / 2.0 for p, n in zip(pw_p, pw_n)]
    rng = np.random.default_rng(seed + 50000)

    # --- 标准 Shen 校准 ---
    shen = ShenCalibrationController(
        cdac=cdac, comparator=DynamicComparator(),
        timing=TimingParams(), avg_pairs=AVG_PAIRS,
        cal_noise_sigma=CAL_NOISE,
    )

    valid = False
    wp = wn = list(cfg.NOMINAL_WEIGHTS_Q0)
    targets = []
    calibration_error = None
    try:
        targets, wp, wn = shen.run(rng=rng)
        valid = all(t['valid'] for t in targets)
    except Exception as exc:
        valid = False
        calibration_error = f"{type(exc).__name__}: {exc}"

    # --- Dynamic VFS measurement and one auditable FFT stimulus ---
    adc = _make_adc(cdac, cfg.NOMINAL_WEIGHTS_Q0, cfg.NOMINAL_WEIGHTS_Q0)
    vfs = measure_positive_vfs(
        lambda vd: _conv(adc, vd),
        MAX_CODE,
        guard_codes=FFT_PROTOCOL.max_code_guard,
    )
    vin, fft_meta = build_coherent_differential_sine(vfs, FFT_PROTOCOL)
    fft_check = validate_fft_stimulus(vin, vfs, FFT_PROTOCOL)
    if fft_check["clipping"]:
        raise RuntimeError(f"FFT stimulus clips at seed={seed}: {fft_check}")

    decisions = []
    for vd in vin:
        r = adc.convert(VCM + vd/2, VCM - vd/2)
        decisions.append(list(r.decisions))

    nominal_decoder = SARDecoder()
    physical_decoder = SARDecoder(
        weights_p=list(pw_p), weights_n=list(pw_n)
    )
    met_nom_int = compute_fft_coherent(
        [nominal_decoder.decode(d) for d in decisions],
        n_bits=N_BITS, n_fft=N_FFT, signal_bin=FFT_K,
    )
    met_phy_int = compute_fft_coherent(
        [physical_decoder.decode(d) for d in decisions],
        n_bits=N_BITS, n_fft=N_FFT, signal_bin=FFT_K,
    )
    met_phy = compute_fft_coherent(
        [physical_decoder.decode_fixed(d, fractional_bits=2)
         for d in decisions],
        n_bits=N_BITS, n_fft=N_FFT, signal_bin=FFT_K,
    )

    if valid:
        calibrated_decoder = SARDecoder(
            weights_p=list(wp), weights_n=list(wn)
        )
        reachable_leaves = enumerate_reachable_leaves(cdac)
        static_result = audit_reachable_codebook(
            cdac,
            calibrated_decoder,
            leaves=reachable_leaves,
        )
        met_cal_int = compute_fft_coherent(
            [calibrated_decoder.decode(d) for d in decisions],
            n_bits=N_BITS, n_fft=N_FFT, signal_bin=FFT_K,
        )
        met_cal = compute_fft_coherent(
            [calibrated_decoder.decode_fixed(d, fractional_bits=2)
             for d in decisions],
            n_bits=N_BITS, n_fft=N_FFT, signal_bin=FFT_K,
        )
    else:
        met_cal = {"sndr_db": -999, "sfdr_db": -999, "enob": 0}
        met_cal_int = dict(met_cal)
        calibrated_decoder = None
        static_result = {}

    # --- Weight errors (absolute Q0) ---
    h_errors = {}
    for ts in TARGET_STAGES:
        h_errors[f"err_{STAGE_NAMES[ts]}"] = (
            round(float(max(
                abs(wp[ts] - pw_p[ts]),
                abs(wn[ts] - pw_n[ts]),
            )), 4)
            if valid else 999
        )

    # --- Normalized weight ratio errors ---
    # e_ratio = (Ŵ_i / ΣŴ) / (W_i / ΣW) - 1
    # This removes global scale factor and reveals per-weight relative accuracy.
    ratio_errors = {}
    if valid:
        sum_wp_cal = sum(wp)
        sum_wp_phy = sum(pw_p)
        for ts in TARGET_STAGES:
            ri_cal = wp[ts] / sum_wp_cal if sum_wp_cal > 0 else 0
            ri_phy = pw_p[ts] / sum_wp_phy if sum_wp_phy > 0 else 1e-30
            e_ratio = (ri_cal / ri_phy - 1.0) if ri_phy > 0 else 999
            ratio_errors[f"ratio_{STAGE_NAMES[ts]}"] = round(float(e_ratio), 6)
    else:
        for ts in TARGET_STAGES:
            ratio_errors[f"ratio_{STAGE_NAMES[ts]}"] = 999

    # --- Exact static audit of the unmodified calibrated weighted decoder ---
    if valid:
        stat = {
            "method": static_result["method"],
            "n_reachable_leaves": static_result["n_reachable_leaves"],
            "n_missing": static_result["n_missing_codes"],
            "n_non_monotonic": static_result["n_integer_backsteps"],
            "n_float_backsteps": static_result["n_float_backsteps"],
            "max_integer_jump": static_result["max_integer_jump"],
            "worst_float_step_lsb": static_result[
                "worst_float_step_lsb"
            ],
            "dnl_peak": static_result["dnl_peak_lsb"],
            "dnl_rms": static_result["dnl_rms_lsb"],
            "inl_peak": static_result["inl_peak_lsb"],
            "inl_rms": static_result["inl_rms_lsb"],
        }
    else:
        stat = {"n_missing": -1, "n_non_monotonic": -1,
                "dnl_peak": None, "dnl_rms": None,
                "inl_peak": None, "inl_rms": None}

    # --- Result ---
    gap = round(met_phy["sndr_db"] - met_cal["sndr_db"], 3) if valid else -999
    gain = round(
        met_cal["sndr_db"] - met_nom_int["sndr_db"], 3
    ) if valid else -999

    return {
        "seed": seed,
        "valid": valid,
        "nominal_sndr": met_nom_int["sndr_db"],
        "physical_sndr": met_phy["sndr_db"],
        "calibrated_sndr": met_cal["sndr_db"],
        "physical_sndr_int12": met_phy_int["sndr_db"],
        "calibrated_sndr_int12": met_cal_int["sndr_db"],
        "oracle_gap_db": gap,
        "cal_gain_db": gain,
        "nominal_enob": met_nom_int["enob"],
        "physical_enob": met_phy["enob"],
        "calibrated_enob": met_cal["enob"],
        "physical_enob_int12": met_phy_int["enob"],
        "calibrated_enob_int12": met_cal_int["enob"],
        "nominal_sfdr": met_nom_int["sfdr_db"],
        "physical_sfdr": met_phy["sfdr_db"],
        "calibrated_sfdr": met_cal["sfdr_db"],
        "calibration_error": calibration_error or "",
        "fft_vfs_v": round(float(vfs), 9),
        "fft_amplitude_v": round(float(fft_meta["amplitude_v"]), 9),
        "fft_peak_ratio_to_vfs": round(float(fft_meta["peak_ratio_to_vfs"]), 9),
        "fft_clipping": bool(fft_meta["clipping"]),
        **h_errors,
        **ratio_errors,
        "static": stat,
    }

# ===================================================================
# Main (direct execution script — run with: python run_final_calibration_pipeline.py)
# ===================================================================
run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
run_id = hashlib.md5(run_timestamp.encode()).hexdigest()[:8]
mode_label = (
    "7-target high-segment calibration + full-array sampling + Q2 weighted decoder + rectangular coherent FFT"
)

print("=" * 70)
print(f"  SAR ADC Final Calibration Pipeline")
print(f"  Run ID: {run_id}")
print(f"  Mode: {mode_label}")
print(f"  {MC_SEEDS} MC seeds, sigma={MC_SIGMA*100:.1f}% unit-cap")
print(f"  Calibration: {AVG_PAIRS} pairs, cal_noise={CAL_NOISE} V")
print("  Static test: exact reachable decision tree for every seed")
print("=" * 70)

results = []
t_start = time.time()

for si in range(MC_SEEDS):
    seed = 10000 + si
    r = run_one_seed(seed, si)
    results.append(r)

    if (si + 1) % 5 == 0:
        vr = [x for x in results if x["valid"]]
        if vr:
            gaps = [x["oracle_gap_db"] for x in vr]
            elapsed = time.time() - t_start
            print(f"  {si+1}/{MC_SEEDS}: valid={len(vr)}, "
                  f"gap P50={np.percentile(gaps,50):.3f}dB, "
                  f"time={elapsed:.0f}s")

elapsed_total = time.time() - t_start

# ===================================================================
# Statistics
# ===================================================================
valid_r = [r for r in results if r["valid"]]
nv = len(valid_r)

if nv == 0:
    print("\n  ALL CALIBRATIONS FAILED!")
    sys.exit(1)

gaps = np.array([r["oracle_gap_db"] for r in valid_r])
gains = np.array([r["cal_gain_db"] for r in valid_r])
sndr_cal = np.array([r["calibrated_sndr"] for r in valid_r])
sndr_phy = np.array([r["physical_sndr"] for r in valid_r])
enob_cal = np.array([r["calibrated_enob"] for r in valid_r])
enob_phy = np.array([r["physical_enob"] for r in valid_r])
sndr_cal_int12 = np.array([
    r["calibrated_sndr_int12"] for r in valid_r
])
enob_cal_int12 = np.array([
    r["calibrated_enob_int12"] for r in valid_r
])

n_neg_gain = sum(1 for g in gains if g < 0)

# Exact static stats for the unmodified weighted decoder
dnl_peaks = np.array([
    r["static"]["dnl_peak"] for r in valid_r
    if r["static"].get("dnl_peak") is not None
])
inl_peaks = np.array([
    r["static"]["inl_peak"] for r in valid_r
    if r["static"].get("inl_peak") is not None
])
n_missing_codes = sum(r["static"]["n_missing"] for r in valid_r
                      if r["static"].get("n_missing", -1) >= 0)
n_non_monotonic = sum(
    r["static"]["n_non_monotonic"] for r in valid_r
    if r["static"].get("n_non_monotonic", -1) >= 0
)

# Per-target weight errors (absolute Q0)
h_errs = {}
for ts in TARGET_STAGES:
    sname = STAGE_NAMES[ts]
    errs = np.array([r[f"err_{sname}"] for r in valid_r])
    h_errs[sname] = {
        "P50": round(float(np.percentile(errs, 50)), 4),
        "P95": round(float(np.percentile(errs, 95)), 4),
        "mean": round(float(np.mean(errs)), 4),
    }

# Per-target normalized ratio errors
ratio_errs = {}
for ts in TARGET_STAGES:
    sname = STAGE_NAMES[ts]
    rerrs = np.array([abs(r[f"ratio_{sname}"]) for r in valid_r])
    ratio_errs[sname] = {
        "P50": round(float(np.percentile(rerrs, 50)), 6),
        "P95": round(float(np.percentile(rerrs, 95)), 6),
        "mean": round(float(np.mean(rerrs)), 6),
    }

# ===================================================================
# Verdicts: relative oracle diagnostic, absolute dynamic gate, and static gate
# ===================================================================
gap_p50 = float(np.percentile(gaps, 50))
gap_p95 = float(np.percentile(gaps, 95))
gap_pass_05 = int(sum(1 for g in gaps if g <= 0.5))
gap_pass_10 = int(sum(1 for g in gaps if g <= 1.0))

if gap_p50 <= 0.5 and gap_p95 <= 2.0:
    oracle_gap_verdict = "PASS"
elif gap_p50 <= 1.0 and gap_p95 <= 3.0:
    oracle_gap_verdict = "CONDITIONAL PASS"
else:
    oracle_gap_verdict = "FAIL"

absolute_dynamic_pass = (
    nv == MC_SEEDS
    and bool(np.all(enob_cal > MIN_CAL_ENOB_BITS))
    and bool(np.all(sndr_cal > MIN_CAL_SNDR_DB))
)
absolute_dynamic_verdict = "PASS" if absolute_dynamic_pass else "FAIL"

# Paper-style static signoff uses the exact deterministic limit of a slow-ramp
# code-density test: no missing codes, no jump wider than one output code, and
# peak DNL/INL <= 1 LSB.  Formal sub-LSB local backsteps are reported
# separately; redundant decision-word overlap makes that a strictly stronger
# property than the DNL/INL convention used in silicon measurements.
static_pass = (
    nv == MC_SEEDS
    and n_missing_codes == 0
    and all(r["static"]["max_integer_jump"] <= 1 for r in valid_r)
    and len(dnl_peaks) == MC_SEEDS
    and bool(np.all(dnl_peaks <= 1.0))
    and len(inl_peaks) == MC_SEEDS
    and bool(np.all(inl_peaks <= 1.0))
)
static_verdict = "PASS" if static_pass else "FAIL"
formal_monotonic_verdict = (
    "PASS" if n_non_monotonic == 0 else "DIAGNOSTIC FAIL"
)

acceptance_verdict = (
    "PASS" if absolute_dynamic_verdict == "PASS" and static_verdict == "PASS"
    else "FAIL"
)

print(f"\n{'='*70}")
print(f"  FINAL RESULTS")
print(f"{'='*70}")
print(f"  Valid calibrations:  {nv}/{MC_SEEDS}")
print(f"  Oracle gap P50:      {gap_p50:.3f} dB")
print(f"  Oracle gap P95:      {gap_p95:.3f} dB")
print(f"  Gap <= 0.5 dB:       {gap_pass_05}/{MC_SEEDS}")
print(f"  Gap <= 1.0 dB:       {gap_pass_10}/{MC_SEEDS}")
print(f"  SNDR cal P50:        {np.percentile(sndr_cal,50):.2f} dB")
print(f"  SNDR int12 P50:      {np.percentile(sndr_cal_int12,50):.2f} dB")
print(f"  SNDR phy P50:        {np.percentile(sndr_phy,50):.2f} dB")
print(f"  ENOB cal P50:        {np.percentile(enob_cal,50):.2f} bit")
print(f"  ENOB int12 P50:      {np.percentile(enob_cal_int12,50):.2f} bit")
print(f"  ENOB phy P50:        {np.percentile(enob_phy,50):.2f} bit")
print(f"  Negative gain:       {n_neg_gain}/{nv} ({n_neg_gain/nv*100:.1f}%)")
if len(dnl_peaks) > 0:
    print(f"  DNL peak P95:        {np.percentile(dnl_peaks,95):.4f} LSB")
    print(f"  INL peak P95:        {np.percentile(inl_peaks,95):.4f} LSB")
    print(f"  Total missing codes: {n_missing_codes}")
    print(f"  Integer backsteps:   {n_non_monotonic}")
print(f"  Elapsed:             {elapsed_total:.0f}s")
print(f"")
print(f"  Per-target weight errors (P50 / P95 Q0):")
for ts in TARGET_STAGES:
    sname = STAGE_NAMES[ts]
    e = h_errs[sname]
    print(f"    {sname:6s}: abs_err P50={e['P50']:.4f}  P95={e['P95']:.4f}")
print(f"")
print(f"  Per-target normalized ratio errors (P50 / P95):")
for ts in TARGET_STAGES:
    sname = STAGE_NAMES[ts]
    re = ratio_errs[sname]
    print(f"    {sname:6s}: |e_ratio| P50={re['P50']:.6f}  P95={re['P95']:.6f}")
print(f"")
print(f"\n  ORACLE GAP VERDICT: {oracle_gap_verdict}  (P50={gap_p50:.3f} dB, P95={gap_p95:.3f} dB)")
print(f"  ABSOLUTE DYNAMIC:   {absolute_dynamic_verdict}  (ENOB>{MIN_CAL_ENOB_BITS:.1f}, SNDR>{MIN_CAL_SNDR_DB:.2f} dB)")
print(f"  STATIC VERDICT:   {static_verdict}")
print(f"  FORMAL MONOTONIC: {formal_monotonic_verdict}")
print(f"  ACCEPTANCE VERDICT: {acceptance_verdict}")

# ===================================================================
# Provenance Manifest (溯源)
# ===================================================================
manifest = generate_manifest(
    repo_dir=SRC_DIR,
    random_seed=10000,
    fft_n=N_FFT,
    fft_k=FFT_K,
    fft_fs=cfg.FFT_FS,
    amp_dbfs=SINE_AMP,
    mc_seeds=MC_SEEDS,
    mc_sigma_pct=MC_SIGMA * 100,
    avg_pairs=AVG_PAIRS,
    cal_noise_sigma_v=cfg.CAL_NOISE_SIGMA_V,
)
save_manifest_compact(manifest, OUT_DIR)
print(f"  Provenance saved: {OUT_DIR}/run_manifest.json")

# ===================================================================
# Save CSV
# ===================================================================
csv_path = os.path.join(OUT_DIR, f"final_pipeline_{run_id}.csv")
base_fields = ["seed","valid","calibration_error",
               "nominal_sndr","physical_sndr","calibrated_sndr","oracle_gap_db","cal_gain_db",
               "nominal_enob","physical_enob","calibrated_enob",
               "physical_sndr_int12","calibrated_sndr_int12",
               "physical_enob_int12","calibrated_enob_int12",
               "nominal_sfdr","physical_sfdr","calibrated_sfdr"]
static_fields = [
    "dnl_peak", "dnl_rms", "inl_peak", "inl_rms",
    "n_missing", "n_non_monotonic", "n_float_backsteps",
    "worst_float_step_lsb", "max_integer_jump",
]
fields = base_fields + static_fields
for ts in TARGET_STAGES:
    fields.append(f"err_{STAGE_NAMES[ts]}")
for ts in TARGET_STAGES:
    fields.append(f"ratio_{STAGE_NAMES[ts]}")

with open(csv_path, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(fields)
    for r in results:
        row = [r.get(f, "") for f in base_fields]
        for field in static_fields:
            row.append(r["static"].get(field, ""))
        for ts in TARGET_STAGES:
            row.append(r.get(f"err_{STAGE_NAMES[ts]}", ""))
        for ts in TARGET_STAGES:
            row.append(r.get(f"ratio_{STAGE_NAMES[ts]}", ""))
        w.writerow(row)
print(f"\n  CSV saved: {csv_path}")

# ===================================================================
# Save summary JSON
# ===================================================================
summary = {
    "run_id": run_id,
    "timestamp": run_timestamp,
    "mode": mode_label,
    "mc_seeds": MC_SEEDS,
    "mc_sigma": MC_SIGMA,
    "cal_noise_sigma_v": CAL_NOISE,
    "avg_pairs": AVG_PAIRS,
    "output_fractional_bits": OUTPUT_FRACTIONAL_BITS,
    "static_test": "exact_reachable_decision_tree_every_seed",
    "static_linearity": "exact_code_density_interval_widths",
    "formal_backsteps_reported_separately": True,
    "oracle_gap_verdict": oracle_gap_verdict,
    "absolute_dynamic_verdict": absolute_dynamic_verdict,
    "acceptance_verdict": acceptance_verdict,
    "min_cal_enob_bits": MIN_CAL_ENOB_BITS,
    "min_cal_sndr_db": MIN_CAL_SNDR_DB,
    "static_verdict": static_verdict,
    "formal_monotonic_verdict": formal_monotonic_verdict,
    "n_valid": nv,
    "n_total": MC_SEEDS,
    "gap_p50_db": gap_p50,
    "gap_p95_db": gap_p95,
    "gap_pass_05db": gap_pass_05,
    "gap_pass_10db": gap_pass_10,
    "sndr_cal_p50_db": round(float(np.percentile(sndr_cal, 50)), 3),
    "sndr_cal_int12_p50_db": round(
        float(np.percentile(sndr_cal_int12, 50)), 3
    ),
    "sndr_phy_p50_db": round(float(np.percentile(sndr_phy, 50)), 3),
    "enob_cal_p50": round(float(np.percentile(enob_cal, 50)), 3),
    "enob_cal_int12_p50": round(
        float(np.percentile(enob_cal_int12, 50)), 3
    ),
    "enob_phy_p50": round(float(np.percentile(enob_phy, 50)), 3),
    "negative_gain_pct": round(n_neg_gain / nv * 100, 1) if nv > 0 else 100,
    "dnl_peak_p95_lsb": round(float(np.percentile(dnl_peaks, 95)), 4) if len(dnl_peaks) > 0 else -1,
    "inl_peak_p95_lsb": round(float(np.percentile(inl_peaks, 95)), 4) if len(inl_peaks) > 0 else -1,
    "total_missing_codes": int(n_missing_codes),
    "total_integer_backsteps": int(n_non_monotonic),
    "elapsed_s": round(elapsed_total, 1),
    "weight_errors": h_errs,
    "ratio_errors": ratio_errs,
}

json_path = os.path.join(OUT_DIR, f"final_summary_{run_id}.json")
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=2)
print(f"  JSON saved: {json_path}")

# ===================================================================
# Report
# ===================================================================
report_path = os.path.join(OUT_DIR, f"final_report_{run_id}.md")
report = [
    f"# SAR ADC Calibration Pipeline — Final Validation Report",
    f"",
    f"**Run ID:** `{run_id}`",
    f"**Date:** {run_timestamp}",
    f"**Mode:** {mode_label}",
    f"**MC Seeds:** {MC_SEEDS}, unit-cap sigma={MC_SIGMA*100:.1f}%",
    f"**Calibration:** {AVG_PAIRS} avg pairs, cal_noise={CAL_NOISE} V",
    f"**Static test:** exact reachable decision tree for every seed",
    f"",
    f"## Summary",
    f"",
    f"| Metric | Value |",
    f"|--------|-------|",
    f"| Valid calibrations | {nv}/{MC_SEEDS} |",
    f"| Oracle gap P50 | {gap_p50:.3f} dB |",
    f"| Oracle gap P95 | {gap_p95:.3f} dB |",
    f"| Gap <= 0.5 dB | {gap_pass_05}/{MC_SEEDS} ({gap_pass_05/MC_SEEDS*100:.0f}%) |",
    f"| Gap <= 1.0 dB | {gap_pass_10}/{MC_SEEDS} ({gap_pass_10/MC_SEEDS*100:.0f}%) |",
    f"| SNDR cal P50 (Q2) | {np.percentile(sndr_cal,50):.2f} dB |",
    f"| SNDR cal P50 (integer 12b diagnostic) | {np.percentile(sndr_cal_int12,50):.2f} dB |",
    f"| ENOB cal P50 (Q2) | {np.percentile(enob_cal,50):.2f} bit |",
    f"| ENOB cal P50 (integer 12b diagnostic) | {np.percentile(enob_cal_int12,50):.2f} bit |",
    f"| Negative gain | {n_neg_gain}/{nv} ({n_neg_gain/nv*100:.1f}%) |",
    f"| DNL peak P95 | {round(float(np.percentile(dnl_peaks,95)),4) if len(dnl_peaks)>0 else 'N/A'} LSB |",
    f"| INL peak P95 | {round(float(np.percentile(inl_peaks,95)),4) if len(inl_peaks)>0 else 'N/A'} LSB |",
    f"| Total missing codes | {int(n_missing_codes)} |",
    f"| Formal sub-LSB integer backsteps (diagnostic) | {int(n_non_monotonic)} |",
    f"| Elapsed | {elapsed_total:.0f}s |",
    f"",
    f"## Verdict",
    f"",
    f"**Oracle-gap diagnostic: {oracle_gap_verdict}** (gap P50 = {gap_p50:.3f} dB, P95 = {gap_p95:.3f} dB)",
    f"**Absolute dynamic gate: {absolute_dynamic_verdict}** (all calibrated ENOB > {MIN_CAL_ENOB_BITS:.1f} bit and SNDR > {MIN_CAL_SNDR_DB:.2f} dB)",
    f"**Static code-density: {static_verdict}; formal monotonic diagnostic: "
    f"{formal_monotonic_verdict}.**",
    f"**Top-level acceptance: {acceptance_verdict}**",
    f"",
    f"## Per-Target Weight Errors (Absolute Q0)",
    f"",
    f"| Target | P50 (Q0) | P95 (Q0) | Mean (Q0) |",
    f"|--------|:---:|:---:|:---:|",
]
for ts in TARGET_STAGES:
    sname = STAGE_NAMES[ts]
    e = h_errs[sname]
    report.append(f"| {sname} | {e['P50']:.4f} | {e['P95']:.4f} | {e['mean']:.4f} |")

report += [
    f"",
    f"## Per-Target Normalized Ratio Errors |e_ratio|",
    f"",
    f"`e_ratio = (Wcal_i/sum(Wcal)) / (Wphy_i/sum(Wphy)) - 1`; "
    f"the global scale factor is removed.",
    f"",
    f"| Target | P50 | P95 | Mean |",
    f"|--------|:---:|:---:|:---:|",
]
for ts in TARGET_STAGES:
    sname = STAGE_NAMES[ts]
    re = ratio_errs[sname]
    report.append(f"| {sname} | {re['P50']:.6f} | {re['P95']:.6f} | {re['mean']:.6f} |")

report += [
    f"",
    f"## Method",
    f"",
    f"- **Calibration:** Shen 2018 force-0/force-1 protocol, P/N split-side",
    f"- **Targets:** 7 stages (H1, H2, H4, H8-R, H8-A, H16, H32)",
    f"- **Base ruler:** complete low segment plus terminal (131 Q0 total)",
    f"- **Calibration order:** H1->H2->H4->H8-R->H8-A->H16->H32",
    f"- **Decoder:** 15-stage P/N weights, direct Q2 weighted reconstruction",
    f"- **Static test:** exact deterministic decision-tree partition for every seed",
    f"- **FFT:** {N_FFT}-point, rectangular window (coherent sampling), bin k={FFT_K}",
    f"",
]

report += [
    f"## Known Limitations",
    f"",
    f"- **Dynamic output:** Acceptance uses Q2 reconstruction. Integer 12-bit output",
    f"  is retained as a diagnostic because it adds a second quantization.",
    f"- **Static scope:** The exact reachable decision tree is an offline audit.",
    f"  It does not sort outputs, alter codes, or add a table to the decoder.",
    f"- **Reference scope:** Chen 2024 informs the local backend-range criterion;",
    f"  its auxiliary comparator and three-bridge circuit are not copied.",
    f"",
]

with open(report_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(report))
print(f"  Report saved: {report_path}")

print(f"\n{'='*70}")
print(f"  PIPELINE COMPLETE — {acceptance_verdict}")
print(f"  Output: {OUT_DIR}")
print(f"{'='*70}")
