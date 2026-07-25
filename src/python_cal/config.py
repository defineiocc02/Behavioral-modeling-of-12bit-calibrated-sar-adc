"""Authoritative configuration for the v3.0 Python SAR ADC model.

Active CDAC (per side, integer unit capacitors only):

    high: 32, 16, 8, 8, 4, 2, 1 Cu
    bridge: 2 Cu
    low: 32, 16, 8, 4, 2, 2, 1 Cu

Every high- and low-segment capacitor samples the input during normal
conversion.  The bridge capacitor is internal and has no bottom-plate switch.
Fourteen physical decisions plus one comparator-only terminal decision are
used; reconstruction is an ordinary calibrated weighted sum.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StageSpec:
    index: int
    name: str
    nominal_weight: float
    is_physical: bool
    role: str


# With CLOW=65 Cu and CBRIDGE=2 Cu:
# low unit effective weight = 2 Q0; high unit = CLOW+CBRIDGE = 67 Q0.
STAGE_SPECS: tuple[StageSpec, ...] = (
    StageSpec(0, "H32C", 2144, True, "signal"),
    StageSpec(1, "H16C", 1072, True, "signal"),
    StageSpec(2, "H8C-A", 536, True, "signal"),
    StageSpec(3, "H8C-R", 536, True, "signal"),
    StageSpec(4, "H4C", 268, True, "signal"),
    StageSpec(5, "H2C", 134, True, "signal"),
    StageSpec(6, "H1C", 67, True, "signal"),
    StageSpec(7, "L32C", 64, True, "signal"),
    StageSpec(8, "L16C", 32, True, "signal"),
    StageSpec(9, "L8C", 16, True, "signal"),
    StageSpec(10, "L4C", 8, True, "signal"),
    StageSpec(11, "L2C-A", 4, True, "signal"),
    StageSpec(12, "L2C-R", 4, True, "signal"),
    StageSpec(13, "L1C", 2, True, "signal"),
    StageSpec(14, "TERM", 1, False, "rounding"),
)

N_STAGES = len(STAGE_SPECS)
N_PHYSICAL = sum(s.is_physical for s in STAGE_SPECS)
NOMINAL_WEIGHTS_Q0 = tuple(s.nominal_weight for s in STAGE_SPECS)
SIGNAL_STAGES = tuple(s.index for s in STAGE_SPECS if s.role == "signal")
AUX_STAGES = tuple(s.index for s in STAGE_SPECS if s.role != "signal")
STAGE_NAMES = [s.name for s in STAGE_SPECS]

# 閳光偓閳光偓 TSMC 180nm 瀹搞儴澹撻崣鍌涙殶 閳光偓閳光偓
# 瀹搞儴澹? TSMC 180nm 1P6M CMOS
# MOM 閻㈤潧顔愮猾璇茬€? 濡亜鎮滈柅姘跺櫤 MOM (metal-oxide-metal fringe)
# 闁叉垵鐫樼仦? M4-M6 閸棗褰?(閸忕鐎?, 閸欘垶鈧?M2-M6 婢х偛濮炵€靛棗瀹?CU = 4e-15                   # 閸楁洑缍呴悽闈涱啇 4 fF (閻劍鍩涚憴鍕壐)

# Pelgrom 婢堕亶鍘?(閻╁瓨甯寸紒娆忕暰, 闁灝鍘ら崡鏇氱秴闁炬儳绱￠幑銏㈢暬)
# A_C 閳?1.0 %璺腑m  (娣囨繂鐣? TSMC 180nm MOM 鐎圭偞绁?0.5-0.8 %璺腑m)
# 1Cu 闂堛垻袧 閳?2 娓璵铏? (4 fF @ ~2 fF/娓璵铏?MOM 鐎靛棗瀹?
# 锜?铻朇/C)_1Cu = A_C / 閳?area) = 1.0 / 閳? 閳?0.707%
MOM_AC_PELGROM_PCT_UM = 1.0   # %璺腑m
MOM_1CU_AREA_UM2 = 2.0        # 娓璵铏?MOM_SIGMA_1CU = 0.00707       # 锜?铻朇/C)_1Cu 閳?0.707% (妫板嫯顓哥粻妤€鈧?

VREF = 1.8
VREFN = 0.0
VCM = 0.9
N_BITS = 12

C_B_NOMINAL = 2
C_LOW_NOMINAL = 65
C_HIGH_NOMINAL = 71
H_FACTOR_NOMINAL = 67

CAP_NOMINAL_CU = {
    "low_1c": 1,
    "low_2c_a": 2,
    "low_2c_r": 2,
    "low_4c": 4,
    "low_8c": 8,
    "low_16c": 16,
    "low_32c": 32,
    "bridge": 2,
    "high_1c": 1,
    "high_2c": 2,
    "high_4c": 4,
    "high_8c_a": 8,
    "high_8c_r": 8,
    "high_16c": 16,
    "high_32c": 32,
}

ALL_CAP_NAMES = [
    "low_1c", "low_2c_a", "low_2c_r", "low_4c",
    "low_8c", "low_16c", "low_32c",
    "bridge",
    "high_1c", "high_2c", "high_4c", "high_8c_a",
    "high_8c_r", "high_16c", "high_32c",
]

SIGNAL_WEIGHT_NOMINAL = sum(
    NOMINAL_WEIGHTS_Q0[i] for i in SIGNAL_STAGES
)  # 4887 Q0
AUX_WEIGHT_NOMINAL = sum(
    NOMINAL_WEIGHTS_Q0[i] for i in AUX_STAGES
)  # terminal = 1 Q0

# Recursive force-0/force-1 calibration.  The complete low segment is the
# 131-Q0 seed ruler.  As in segmented calibration practice, the smallest
# unit-cap groups are laid out as the matching reference rather than
# recursively self-calibrated through an offset-limited main comparator.
# The first high target is 67 Q0, leaving 64 Q0 of backend headroom.
BASE_RULER_STAGES = tuple(range(7, 15))
SHEN_CAL_TARGETS = [
    {"id": 0, "name": "H1C", "stage": 6, "nominal_q0": 67},
    {"id": 1, "name": "H2C", "stage": 5, "nominal_q0": 134},
    {"id": 2, "name": "H4C", "stage": 4, "nominal_q0": 268},
    {"id": 3, "name": "H8C-R", "stage": 3, "nominal_q0": 536},
    {"id": 4, "name": "H8C-A", "stage": 2, "nominal_q0": 536},
    {"id": 5, "name": "H16C", "stage": 1, "nominal_q0": 1072},
    {"id": 6, "name": "H32C", "stage": 0, "nominal_q0": 2144},
]
SHEN_CAL_TARGET_STAGES = tuple(t["stage"] for t in SHEN_CAL_TARGETS)
SHEN_LOWER_STAGES = {
    target["stage"]: [
        stage
        for stage in range(target["stage"] + 1, N_STAGES)
        if NOMINAL_WEIGHTS_Q0[stage] <= target["nominal_q0"]
    ]
    for target in SHEN_CAL_TARGETS
}

FRAC_BITS = 6
Q_SCALE = 1 << FRAC_BITS

# 閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡?#  閺嶁€冲櫙閸欏倹鏆?閳?12-bit 閸欏秷绻冩惔锕侇啎鐠侊繝鍘ょ純?#
#  鐎圭偤鐛欐宀冪槈 (鐟?analysis/ 閻╊喖缍?:
#    AVG_PAIRS 閹?16-512:  128 鐎电懓鎮?oracle gap < 1 dB, 256 鐎电懓鎮楁鍗炴嫲
#    閸ｎ亜锛?鑴?pairs 閻戭厼濮忛崶?  1mV 閸ｎ亜锛愭稉?64 鐎?gap=0.69 dB, 128 鐎?gap=0.66 dB
#    Dither 濞戝牐鐎虹€圭偤鐛?      閸ｎ亜锛?閳?1 LSB 閺?dither 閺冪姴顤冮惄?#
#  闁板秶鐤嗙痪?(閹恒劏宕橀崐?:
#    AVG_PAIRS = 128        閳?12-bit 閻㈡粎鍋? gap < 1 dB, 閺冨爼妫?= 512 閻?1/4
#    AVG_PAIRS = 64         閳?濠碘偓鏉? gap 閳?0.7 dB, 閺冨爼妫块崘宥呭櫤閸?#    AVG_PAIRS = 16         閳?娴犲懎缍嬪В鏃囩窛閸ｃ劌娅旀竟?< 0.5 mV 閺冭泛褰查悽?#    DITHER_LSB = (0.0,)  閳?閸ｎ亜锛?閳?1 LSB 閺?dither 閸愭ぞ缍? 瀹告彃鍙ч梻?# 閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡?AVG_PAIRS = 128           # 12-bit 閹恒劏宕?(閸?512 鏉╁洤瀹崇拋鎹愵吀)
WEIGHT_TOL = 0.20         # 閺夊啴鍣稿鍌氱埗濡偓濞村妲囬崐?鍗?0%
UPDATE_DEADBAND_LSB = 0.0 # 閺囧瓨鏌婂璇插隘 (0=缁備胶鏁?

# 閳光偓閳光偓 Dither 闁板秶鐤?閳光偓閳光偓
# 濞戝牐鐎虹€圭偤鐛欑紒鎾诡啈: 閸ｎ亜锛?閳?1 LSB 閹?AVG_PAIRS 閳?32 閺?dither 閺冪姴顤冮惄?
# 瑜版挸澧?1mV 閸ｎ亜锛?+ 128 鐎?閳?閺冪娀娓?dither. 閸忔娊妫撮崣顖滄阜 dither DAC 绾兛娆?
# 閼汇儵娓堕幁銏狀槻: SHEN_DITHER_LSB = (-1.5, -0.5, 0.5, 1.5)
SHEN_DITHER_LSB = (0.0,)

# All 14 physical conversion capacitors sample VIN; only bridge is internal.
VCM_SAMPLE_MASK = 0   # deprecated: 閸忋劑鍣伴弽宄版倵閺?VCM mask
PHYSICAL_TO_WEIGHT_STAGE = {  # deprecated: 娴犲懍缍旈弬鍥ㄣ€傛穱婵堟殌
    1: 13, 2: 12, 3: 11, 4: 10, 5: 9, 6: 8, 7: 7,
    8: 6, 9: 5, 10: 4, 11: 3, 12: 2, 13: 1, 14: 0,
}

# 閳光偓閳光偓 濮ｆ棁绶濋崳銊ユ珨婢?閳光偓閳光偓  缂佺喍绔?300 娓璙 RMS
CAL_NOISE_SIGMA_V = 0.0003    # 300 娓璙 RMS
CONV_NOISE_SIGMA_LSB = 0.68   # 300 娓璙 / (VREF/4096)

FFT_N = 4096
FFT_K = 1019   # ~2.49 MHz @ Fs=10 MHz (was 127, ~310 kHz)
FFT_FS = 10e6
FFT_AMPLITUDE_DBFS = -0.5
FFT_PHASE = 0.123

SCENARIOS = {
    "ideal": {"md": [1.0] * 7, "mu": [1.0] * 7},
    "det_alt_2pct": {
        "md": [1.02, 0.98, 1.02, 0.98, 1.02, 0.98, 1.02],
        "mu": [1.02, 0.98, 1.02, 0.98, 1.02, 0.98, 1.02],
    },
    "det_alt_5pct": {
        "md": [1.05, 0.95, 1.05, 0.95, 1.05, 0.95, 1.05],
        "mu": [1.05, 0.95, 1.05, 0.95, 1.05, 0.95, 1.05],
    },
}

# TSMC 180nm MOM 閸楁洖鍘撻悽闈涱啇婢堕亶鍘?#
# Pelgrom 缁粯鏆? A_C = 1.0 %璺腑m 閳?锜?铻朇/C)閳т竼u_pair 閳?1.0/閳? = 0.707%
# 娴犮儰绗?锜?閸у洣璐熼崡鏇氶嚋 Cu 閻ㄥ嫭鐖ｉ崙鍡楁▕ (娑撳秵妲?pair mismatch):
#   0.71% 閳?閸忕鐎?(optimised common-centroid + dummy)
#   1.0%  閳?娣囨繂鐣?(minimal area, no dummy)
# 婢堕亶鍘ょ€圭偟骞囧Ο鈥崇础:
#   "per_unit"            閳?闁?Cu 閻欘剛鐝?N(CU, CU璺熃), 锜絖cap = 锜?閳瓊   [姒涙顓? 閻椻晝鎮奭
#   "per_cap_scaled"      閳?閺佸鏁哥€?N(Cnom, Cnom璺熃/閳瓊), 娑?per_unit 缂佺喕顓哥粵澶嬫櫏, MC 閸旂娀鈧?#   "per_cap_flat_stress" 閳?閺佸鏁哥€?N(Cnom, Cnom璺熃), 婢堆冪毈閻㈤潧顔?锜?閻╃鎮?[闂堢偟澧块悶? 娴犲懎甯囬崝娑欑ゴ鐠囨槨
MC_SIGMA = 0.01
MISMATCH_MODE = "per_unit"
# 婢堕亶鍘ら懠鍐ㄦ纯: "all"             = 閸忋劎鏁哥€?(15 娑? 婢堕亶鍘?#           "calibrated_only" = 娴犲懏鐗庨崙鍡欐窗閺?(妤傛ɑ顔?7 娑? 婢堕亶鍘? 娴ｅ孩顔?濡椼儲甯撮弽鍥┬?#           "base_ruler_only" = 娴犲懎鐔€閸戝棗鏄?(娴ｅ孩顔?7+濡椼儲甯?1) 婢堕亶鍘? 妤傛ɑ顔岄弽鍥┬?MISMATCH_SCOPE = "all"

def should_mismatch(cap_name: str) -> bool:
    """閺勵垰鎯佺€电顕氶悽闈涱啇閸旂姴銇戦柊宥冣偓?""
    scope = MISMATCH_SCOPE
    if scope == "all":
        return True
    if scope == "calibrated_only":
        return cap_name.startswith("high_")
    if scope == "base_ruler_only":
        return cap_name.startswith("low_") or cap_name == "bridge"
    raise ValueError(f"unknown MISMATCH_SCOPE: {scope}")

# 閳光偓閳光偓 鏉堟挸鍙嗘穱鈥冲娇 閳光偓閳光偓
MC_SEEDS_PIPELINE = 100
MC_SEEDS_ISOLATION = 50
