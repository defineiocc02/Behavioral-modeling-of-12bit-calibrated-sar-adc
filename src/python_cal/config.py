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

FRAC_BITS = 6
Q_SCALE = 1 << FRAC_BITS
# Seven targets x four directional sub-conversions x 512 pairs = 14336
# calibration sub-conversions, equal to the retired pipeline (not increased).
AVG_PAIRS = 512
WEIGHT_TOL = 0.20
UPDATE_DEADBAND_LSB = 0.0

# All 14 physical conversion capacitors sample VIN; only bridge is internal.
VCM_SAMPLE_MASK = 0
PHYSICAL_TO_WEIGHT_STAGE = {
    1: 13, 2: 12, 3: 11, 4: 10, 5: 9, 6: 8, 7: 7,
    8: 6, 9: 5, 10: 4, 11: 3, 12: 2, 13: 1, 14: 0,
}

CAL_NOISE_SIGMA_V = 0.001
CONV_NOISE_SIGMA_LSB = 0.15

FFT_N = 4096
FFT_K = 127
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

MC_SIGMA = 0.005
MC_SEEDS_PIPELINE = 100
MC_SEEDS_ISOLATION = 50
