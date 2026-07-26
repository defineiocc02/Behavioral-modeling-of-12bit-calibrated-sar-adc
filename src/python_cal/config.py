"""Authoritative configuration for the v3.1 Python SAR ADC model.

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

# Behavioral scale only.  CU is not a PDK MOMCAP selection or area claim.
CU = 4e-15

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

CAL_WEIGHT_FRAC_BITS = 8
# Calibration weights are stored as Q8 in the synthesizable RTL; Python uses
# the same lattice after every target update.

# ═══════════════════════════════════════════════════════════════════════════
#  校准参数 — 当前正式矩阵采用 128 pairs。
#
#  128 是本轮 Python/RTL 共同实现值，不外推为跨 PDK 的全局最优值。
#  零校准扰动组用于隔离失配；300 μV RMS 组仅检查比较器输入等效扰动
#  能否解除重复 lower-SAR 结果的量化锁定。
# ═══════════════════════════════════════════════════════════════════════════
AVG_PAIRS = 128           # 12-bit 推荐 (原 512 过度设计)
WEIGHT_TOL = 0.20         # 权重异常检测阈值 ±20%

# ── Dither 配置 ──
# 正式矩阵不依赖额外 dither DAC；0.3 mV 是校准比较器输入等效噪声。
# 若目标比较器噪声不足以解除量化锁定，可再评估受控 dither，而不是
# 在当前行为模型中预先增加硬件。
SHEN_DITHER_LSB = (0.0,)

# ── 比较器噪声 ──
# 失配主验证通过 SAR_CAL_NOISE_SIGMA_V=0 隔离校准噪声；300 μV 仅作为
# 校准抗扰动对照。正常转换的 Python 主路径不注入噪声。
CAL_NOISE_SIGMA_V = 0.0003

FFT_N = 4096
FFT_K = 1019   # ~2.49 MHz @ Fs=10 MHz (was 127, ~310 kHz)
FFT_FS = 10e6
FFT_AMPLITUDE_DBFS = -0.5
FFT_PHASE = 0.123

# 单位电容失配探索值。没有当前 PDK MOMCAP Monte Carlo/版图抽取证据，
# 因此 0.5% 作为标称研究点、1% 作为压力点，均不得表述为工艺签核值。
# 以下 sigma 是单个 Cu 的标准差，不是整个 group 的相对标准差。
MC_SIGMA = 0.01
# 失配实现模式:
#   "per_unit"            — 逐 Cu 独立 N(CU, CU·σ), σ_cap = σ/√N   [默认, 物理]
#   "per_cap_scaled"      — 整电容 N(Cnom, Cnom·σ/√N), 与 per_unit 统计等效, MC 加速
#   "per_cap_flat_stress" — 整电容 N(Cnom, Cnom·σ), 大小电容 σ 相同 [非物理, 仅压力测试]
MISMATCH_MODE = "per_unit"
# 失配范围: "all"             = 全电容 (15 个) 失配
#           "calibrated_only" = 仅校准目标 (高段 7 个) 失配, 低段+桥接标称
#           "base_ruler_only" = 仅基准尺 (低段 7+桥接 1) 失配, 高段标称
MISMATCH_SCOPE = "all"

def should_mismatch(cap_name: str) -> bool:
    """是否对该电容加失配。"""
    scope = MISMATCH_SCOPE
    if scope == "all":
        return True
    if scope == "calibrated_only":
        return cap_name.startswith("high_")
    if scope == "base_ruler_only":
        return cap_name.startswith("low_") or cap_name == "bridge"
    raise ValueError(f"unknown MISMATCH_SCOPE: {scope}")

# ── 输入信号 ──
MC_SEEDS_PIPELINE = 100
