"""
config.py — 全局参数（与 VA 参数一一对应）
=============================================
对齐 VA 文件: params.scs, tb_huang_cal_sine.scs, DEC_CAL_PHY_HUANG_V6.va

所有参数值直接来源于 VA 源码，不经过任何"近似"或"合理假设"。
"""

from dataclasses import dataclass

# ============================================================================
# 阶段元数据 (StageSpec)
# ============================================================================

@dataclass(frozen=True)
class StageSpec:
    """14 级 SAR 转换阶段统一元数据

    属性:
        index: 阶段索引 (0..13)
        name: 阶段名称
        nominal_weight: 标称权重 (Q0)
        is_physical: 是否对应物理电容 (terminal=False)
        role: 功能角色 ("signal" / "aux_redundant" / "cal_dac" / "rounding")
    """
    index: int
    name: str
    nominal_weight: float
    is_physical: bool
    role: str


STAGE_SPECS: tuple[StageSpec, ...] = tuple([
    StageSpec(index=0,  name="H32C",   nominal_weight=2080, is_physical=True,  role="signal"),
    StageSpec(index=1,  name="H16C",   nominal_weight=1040, is_physical=True,  role="signal"),
    StageSpec(index=2,  name="H8C",    nominal_weight=520,  is_physical=True,  role="signal"),
    StageSpec(index=3,  name="H4C",    nominal_weight=260,  is_physical=True,  role="signal"),
    StageSpec(index=4,  name="H2C",    nominal_weight=130,  is_physical=True,  role="signal"),
    StageSpec(index=5,  name="H1C-R",  nominal_weight=65,   is_physical=True,  role="aux_redundant"),
    StageSpec(index=6,  name="H1C-A",  nominal_weight=65,   is_physical=True,  role="signal"),
    StageSpec(index=7,  name="L32C",   nominal_weight=64,   is_physical=True,  role="cal_dac"),
    StageSpec(index=8,  name="L16C",   nominal_weight=32,   is_physical=True,  role="cal_dac"),
    StageSpec(index=9,  name="L8C",    nominal_weight=16,   is_physical=True,  role="cal_dac"),
    StageSpec(index=10, name="L4C",    nominal_weight=8,    is_physical=True,  role="cal_dac"),
    StageSpec(index=11, name="L2C",    nominal_weight=4,    is_physical=True,  role="cal_dac"),
    StageSpec(index=12, name="L1C",    nominal_weight=2,    is_physical=True,  role="cal_dac"),
    StageSpec(index=13, name="T1C",    nominal_weight=1,    is_physical=True,  role="cal_dac"),
])

# === 派生常量 (从 STAGE_SPECS 推导) ===
N_STAGES = len(STAGE_SPECS)
NOMINAL_WEIGHTS_Q0 = tuple(s.nominal_weight for s in STAGE_SPECS)
SIGNAL_STAGES = tuple(s.index for s in STAGE_SPECS if s.role == "signal")
AUX_STAGES = tuple(
    s.index for s in STAGE_SPECS
    if s.role in {"aux_redundant", "cal_dac", "rounding"}
)

# ============================================================================
# CDAC 物理参数 (对齐 cdac_binary_mc.va)
# ============================================================================
CU = 4e-15            # 单位电容 (F)
VREF = 1.8            # 参考电压 VREFP (V)
VREFN = 0.0           # 参考电压 VREFN (V)
VCM = 0.9             # 共模电压 (V)

# CDAC 拓扑常量
C_B_NOMINAL = 2       # 桥接电容 (单位 Cu)
C_LOW_NOMINAL = 63    # 低段总电容 (单位 Cu): 1+2+4+8+16+32
C_HIGH_NOMINAL = 64   # 高段总电容 (单位 Cu): 1+1+2+4+8+16+32

# 桥接比例 H = (C_L_total + C_B) * 2 / C_B = 65
# 有效权重: 低段 = C_i * 2/Cu, 高段 = C_i * H/Cu = C_i * 65/Cu
H_FACTOR_NOMINAL = 65

# 电容数量 (每个电容的 Cu 值)
CAP_NOMINAL_CU = {
    # 低段 (behind bridge): k=1..6
    'low_1c':  1,  'low_2c':  2,  'low_4c':  4,
    'low_8c':  8,  'low_16c': 16, 'low_32c': 32,
    'low_term': 0.5,
    # 桥接: k=7 (internal)
    'bridge':  2,
    # 高段 (direct to top plate): k=8..14
    'high_1c_a': 1, 'high_1c_r': 1, 'high_2c': 2,
    'high_4c': 4,   'high_8c': 8,   'high_16c': 16, 'high_32c': 32,
}

# 所有电容名称列表 (按物理顺序, 供 MC 失配生成遍历)
ALL_CAP_NAMES = [
    'low_1c', 'low_2c', 'low_4c', 'low_8c', 'low_16c', 'low_32c', 'low_term',
    'bridge',
    'high_1c_a', 'high_1c_r', 'high_2c', 'high_4c', 'high_8c', 'high_16c', 'high_32c',
]

# 阶段名称列表 (索引 0..13)
STAGE_NAMES = [
    "H32C", "H16C", "H8C", "H4C", "H2C", "H1C-R", "H1C-A",
    "L32C", "L16C", "L8C", "L4C", "L2C", "L1C", "T1C",
]

# ============================================================================
# 权重定义 (从 STAGE_SPECS 自动推导, 不再单独维护)
# ============================================================================
# 14 个权重: w0..w13 (SAR 阶段 0..13)
# 高段 (signal, 阶段 0-4, 6):
#   w0=H32C=2080, w1=H16C=1040, w2=H8C=520, w3=H4C=260, w4=H2C=130, w6=H1C-A=65
# 冗余 (aux, 阶段 5):
#   w5=H1C-R=65
# calDAC (aux, 阶段 7-12):
#   w7=L32C=64, w8=L16C=32, w9=L8C=16, w10=L4C=8, w11=L2C=4, w12=L1C=2
# 终端 (aux, 阶段 13):
#   w13=terminal=1

SIGNAL_WEIGHT_NOMINAL = sum(NOMINAL_WEIGHTS_Q0[i] for i in SIGNAL_STAGES)  # 4095
AUX_WEIGHT_NOMINAL = sum(NOMINAL_WEIGHTS_Q0[i] for i in AUX_STAGES)       # 192

# ============================================================================
# 电容 → 权重阶段映射
# ============================================================================
# VA BITD/BITU[1..13] → 内部电容索引
# 低段: BITD[1..6] → cp1..cp6 (L1C..L32C) → 权重 w12..w7 (倒序)
# 桥接: 内部 cp7 → 无直接权重映射
# 高段: BITD[7..13] → cp8..cp14 (H1C-A..H32C) → 权重 w6..w0 (倒序)
# 终端: 无物理电容 → w13

# [DEPRECATED] 旧版校准目标 (7个，对齐 VA 第 282-311 行)
# 仅用于 AsyncCalibrationController (calDAC搜索方案)，已被 SHEN_CAL_TARGETS 取代。
CAL_TARGETS = [
    {'id': 0, 'name': 'H1C-A', 'stage': 6, 'nominal_q0': 65,  'cap_key': 'high_1c_a'},
    {'id': 1, 'name': 'H1C-R', 'stage': 5, 'nominal_q0': 65,  'cap_key': 'high_1c_r'},
    {'id': 2, 'name': 'H2C',   'stage': 4, 'nominal_q0': 130, 'cap_key': 'high_2c'},
    {'id': 3, 'name': 'H4C',   'stage': 3, 'nominal_q0': 260, 'cap_key': 'high_4c'},
    {'id': 4, 'name': 'H8C',   'stage': 2, 'nominal_q0': 520, 'cap_key': 'high_8c'},
    {'id': 5, 'name': 'H16C',  'stage': 1, 'nominal_q0': 1040,'cap_key': 'high_16c'},
    {'id': 6, 'name': 'H32C',  'stage': 0, 'nominal_q0': 2080,'cap_key': 'high_32c'},
]

# [DEPRECATED] calDAC 搜索阶段: 仅用于 AsyncCalibrationController
CAL_DAC_STAGES = [7, 8, 9, 10, 11, 12, 13]  # L32C..T1C
CAL_DAC_SEARCH_COUNT = 7

# ============================================================================
# Shen 2018 式校准配置
# ============================================================================
# 基础尺子: L32C..T1C (7个低段电容, stage 7-13), 总范围 127 Q0
# 不会被递归算法自校准。H1R 已从尺子移除，作为第0个校准目标。
BASE_RULER_STAGES = (7, 8, 9, 10, 11, 12, 13)  # L32C..T1C (仅低段标称)

# Shen 校准目标: 7 个 (H1R 最优先, 用低段尺子测量)
# 校准顺序: H1R → H1A → H2C → H4C → H8C → H16C → H32C
SHEN_CAL_TARGETS = [
    {'id': 0, 'name': 'H1C-R', 'stage': 5, 'nominal_q0': 65},
    {'id': 1, 'name': 'H1C-A', 'stage': 6, 'nominal_q0': 65},
    {'id': 2, 'name': 'H2C',   'stage': 4, 'nominal_q0': 130},
    {'id': 3, 'name': 'H4C',   'stage': 3, 'nominal_q0': 260},
    {'id': 4, 'name': 'H8C',   'stage': 2, 'nominal_q0': 520},
    {'id': 5, 'name': 'H16C',  'stage': 1, 'nominal_q0': 1040},
    {'id': 6, 'name': 'H32C',  'stage': 0, 'nominal_q0': 2080},
]

# Shen 校准目标 stage 索引 (便于遍历)
SHEN_CAL_TARGET_STAGES = tuple(t['stage'] for t in SHEN_CAL_TARGETS)  # (5,6,4,3,2,1,0)

# 每个 target 的 lower-SAR 阶段 (按权重降序排列)
SHEN_LOWER_STAGES = {
    5: [7, 8, 9, 10, 11, 12, 13],                              # H1R: 低段标称尺子
    6: [5, 7, 8, 9, 10, 11, 12, 13],                           # H1A: H1R(cal) + 低段
    4: [5, 6, 7, 8, 9, 10, 11, 12, 13],                        # H2C
    3: [4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
    2: [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
    1: [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
    0: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
}

# ============================================================================
# 校准参数 (对齐 DEC_CAL_PHY_HUANG_V6.va)
# ============================================================================
FRAC_BITS = 6                # Q6 定点精度
Q_SCALE = 1 << FRAC_BITS     # 64
AVG_PAIRS = 512              # 平均对数 (AVG_PAIRS_LOG2=9, 噪声~0.033 LSB) — PASS verified
WEIGHT_TOL = 0.20            # 权重更新容差 ±20%
UPDATE_DEADBAND_LSB = 0.0    # 更新死区 (LSB): 0=禁用, 对齐VA典型值1.0

# [DEPRECATED] 墙构建: 仅用于旧版 AsyncCalibrationController (calDAC搜索方案)
# target_id=0 (H1C-A): wall = {} → wall_stages=[]
# target_id=1 (H1C-R): wall = {w6} → wall_stages=[6]
# ...
# target_id=6 (H32C):  wall = {w1,w2,w3,w4,w5,w6}
WALL_STAGES = {
    0: [],
    1: [6],
    2: [5, 6],
    3: [4, 5, 6],
    4: [3, 4, 5, 6],
    5: [2, 3, 4, 5, 6],
    6: [1, 2, 3, 4, 5, 6],
}

# ============================================================================
# 开关 / VCM 掩码 (对齐 SWITCH_CAL.va)
# ============================================================================
# VCM 采样掩码: k=1..6 (calDAC) 和 k=8 (H1C-R) 在正常采样时接 VCM
# mask=382 = 0b101111110
# 位设置: k=1(L1C),2(L2C),3(L4C),4(L8C),5(L16C),6(L32C),8(H1C-R)
# 信号分支: k=7(H1C-A),9..13(H2C,H4C,H8C,H16C,H32C)
VCM_SAMPLE_MASK = 382

# 物理电容索引 → 权重阶段的映射
# BITD/BITU[k] → cp/cn[k], k=1..13
# k=1..6: 低段 (behind bridge), 权重 w12..w7 (倒序)
# k=7..13: 高段 (direct), 权重 w6..w0 (倒序)
PHYSICAL_TO_WEIGHT_STAGE = {
    1: 12, 2: 11, 3: 10, 4: 9, 5: 8, 6: 7,     # 低段 → calDAC
    7: 6, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1, 13: 0,  # 高段 → signal
}

# ============================================================================
# 噪声参数 (对齐策略文档 §3 P1-S4)
# ============================================================================
# 注意: CAL_NOISE_SIGMA_V 是权威值 (V)，ShenCalibrationController 的 cal_noise_sigma
# 参数接收 V 单位。CAL_NOISE_SIGMA_LSB 仅供旧版 AsyncCalibrationController 参考。
CAL_NOISE_SIGMA_V = 0.001    # 校准期间比较器噪声 RMS (V), ≈2.3 LSB@VREF=1.8V
CAL_OFFSET_SIGMA_V = 0.5     # 失调标准差 (V)  — 需确认是否为 LSB 单位
CAL_NOISE_SIGMA_LSB = 0.50   # [DEPRECATED] 校准噪声 RMS (LSB), 仅旧控制器使用
CAL_OFFSET_SIGMA_LSB = 0.5   # [DEPRECATED] 失调标准差 (LSB), 仅旧控制器使用
CAL_ZERO_TIE_THRESHOLD = 0.2 # 零残差检测阈值 (LSB), 对齐 VA ~0.003*VFS
CONV_NOISE_SIGMA_LSB = 0.15  # 正常转换期间比较器噪声 RMS (LSB)

# ============================================================================
# FFT 参数 (对齐策略文档 §3 P1-S5)
# ============================================================================
FFT_N = 4096                # FFT 点数
FFT_K = 127                 # 相干采样 bin (gcd(127,4096)=1)
FFT_FS = 10e6               # 采样率 (Hz)
FFT_AMPLITUDE_DBFS = -0.5   # 输入幅度 (dBFS)
FFT_PHASE = 0.123           # 输入相位 (rad)

# ============================================================================
# 确定性失配场景 (对齐策略文档 §3 P1-S6 / §6 P2-S2)
# ============================================================================
# md/mu 数组长度为 7，对应高段电容 md8..md14 / mu8..mu14
# 映射: H1C-A, H1C-R, H2C, H4C, H8C, H16C, H32C

SCENARIOS = {
    'ideal': {
        'md': [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        'mu': [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    },
    'det_alt_2pct': {
        'md': [1.02, 0.98, 1.02, 0.98, 1.02, 0.98, 1.02],
        'mu': [1.02, 0.98, 1.02, 0.98, 1.02, 0.98, 1.02],
    },
    'det_alt_5pct': {
        'md': [1.05, 0.95, 1.05, 0.95, 1.05, 0.95, 1.05],
        'mu': [1.05, 0.95, 1.05, 0.95, 1.05, 0.95, 1.05],
    },
    'det_high_array_common_pos_2pct': {
        'md': [1.02, 1.02, 1.02, 1.02, 1.02, 1.02, 1.02],
        'mu': [1.02, 1.02, 1.02, 1.02, 1.02, 1.02, 1.02],
    },
    'det_high_array_common_neg_2pct': {
        'md': [0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98],
        'mu': [0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98],
    },
}

# MC 参数
# 注意: MC_SIGMA 是管线级权威值 (0.5%)，所有验收脚本必须从此引用。
# MC_SIGMA_C_REL (2%) 是旧版定义，保留仅作参考。
MC_SIGMA = 0.005            # 单位电容相对标准差 0.5% (管线级权威值)
MC_SIGMA_C_REL = 0.02       # [DEPRECATED] 单位电容相对标准差 2% (旧版)
MC_SAMPLES = 4000           # MC 样本数
MC_BASE_SEED = 13579        # 基础种子 (对齐 cdac_binary_mc.va)
MC_SEEDS_PIPELINE = 100     # 管线验收 MC seed 数 (≥100 保证统计置信度)
MC_SEEDS_ISOLATION = 50     # 隔离实验 MC seed 数

# ============================================================================
# VA 仿真相关参数
# ============================================================================
VA_SIM_TIME_PER_RUN = 520e-6  # 每次仿真的瞬态时间 (s)
VA_CAL_TIME = 75e-6           # 校准阶段时间 (s)
VA_CONV_START = 82e-6         # 转换阶段开始时间 (s)
VA_CONV_END = 491.6e-6        # 转换阶段结束时间 (s)
