"""
calibration_trace.py — 校准 trace 数据结构

需求文档 33 §12: 完整校准 trace。
"""
from dataclasses import dataclass, field
from python_cal.topology.switch_state import DifferentialSwitchState


@dataclass(frozen=True)
class CalibrationSearchStepTrace:
    """单次 calDAC 搜索步骤 trace

    需求文档 33 §12: 每个 D+/D- 方向的 calDAC 步骤详情。
    """
    target_id: int
    target_name: str
    pair_index: int
    direction: int              # 0=D+, 1=D-
    caldac_stage: int           # calDAC stage (0..6, where 0=L32C, ...)

    committed_before: DifferentialSwitchState
    trial_state: DifferentialSwitchState
    committed_after: DifferentialSwitchState

    vtop_p: float
    vtop_n: float
    vbridge_p: float
    vbridge_n: float
    differential_v: float

    comparator_output: int
    trial_start_time_s: float
    dac_settled_time_s: float
    comparator_done_time_s: float
    commit_time_s: float


@dataclass(frozen=True)
class TargetCalibrationResult:
    """单个 target 的校准结果

    需求文档 33 §12: 每个 target 输出完整结果。
    """
    target_id: int
    target_name: str
    stage: int
    measured_weight_q0: float
    measured_weight_q: int
    nominal_weight_q0: float
    physical_weight_q0: float

    dplus_mean_q0: float
    dminus_mean_q0: float

    valid: bool
    saturated: bool
    completed_pairs: int

    start_time_s: float
    done_time_s: float
    traces: tuple = ()


@dataclass(frozen=True)
class GainModeAnalysis:
    """增益模态分解 (Chen §8.4, 文档 41 C3)

    e = Ŵ - W₀ = α·W₀ + e⊥

    属性:
        alpha: 增益误差系数 (标量, 无量纲)
        signal_weight_nominal_q0: 标称信号权重和
        signal_weight_calibrated_q0: 校准后信号权重和 (归一化分母)
        redundancy_offset_nominal_q0: 标称冗余中心偏移 O_Q^(nom)
        redundancy_offset_calibrated_q0: 校准后冗余中心偏移 O_Q^(cal)
        gain_absorbed_ratio: 增益模态被 decoder 归一化吸收的比例 (≈1.0)
        residual_rms_q0: 非增益残差 RMS (Q0)
        residual_max_q0: 非增益残差最大值 (Q0)
        per_stage: list[dict] 每个被校阶段的分解
    """
    alpha: float
    signal_weight_nominal_q0: float
    signal_weight_calibrated_q0: float
    redundancy_offset_nominal_q0: float
    redundancy_offset_calibrated_q0: float
    gain_absorbed_ratio: float
    residual_rms_q0: float
    residual_max_q0: float
    per_stage: tuple = ()

    @property
    def gain_percent(self) -> float:
        """增益误差百分比"""
        return self.alpha * 100.0

    @property
    def is_gain_dominant(self) -> bool:
        """增益模态是否主导 (Chen §8.4: 误差主要由增益组成)"""
        return abs(self.alpha) > 1e-9 and self.gain_absorbed_ratio > 0.99


@dataclass(frozen=True)
class CalibrationReport:
    """完整校准报告

    需求文档 33 §12: 最终校准报告。
    """
    weights_q: tuple
    weights_q0: tuple
    targets: tuple   # tuple[TargetCalibrationResult, ...]

    all_targets_complete: bool
    valid: bool
    calibration_start_time_s: float
    calibration_done_time_s: float
    gain_analysis: GainModeAnalysis | None = None

    @property
    def total_calibration_time_s(self) -> float:
        return self.calibration_done_time_s - self.calibration_start_time_s

    def with_gain_analysis(self, physical_weights_q0: list[float],
                           nominal_weights_q0: list[float] | None = None
                           ) -> 'CalibrationReport':
        """附加增益模态分解

        文档 41 C3: 校准后必须显式化增益模态归一化。

        参数:
            physical_weights_q0: 物理 oracle 权重 (Q0)
            nominal_weights_q0: 标称权重, 默认使用 config.NOMINAL_WEIGHTS_Q0

        返回:
            新的 CalibrationReport (含 gain_analysis)
        """
        if nominal_weights_q0 is None:
            from python_cal.config import NOMINAL_WEIGHTS_Q0
            nominal_weights_q0 = list(NOMINAL_WEIGHTS_Q0)

        cal_w = list(self.weights_q0)
        phys_w = list(physical_weights_q0)
        nom_w = list(nominal_weights_q0)

        # 信号阶段 (0,1,2,3,4,6)
        signal_stages = [0, 1, 2, 3, 4, 6]
        # 辅助阶段 (5,7,8,9,10,11,12,13)
        aux_stages = [5, 7, 8, 9, 10, 11, 12, 13]

        # 归一化分母
        signal_nom = sum(nom_w[s] for s in signal_stages)
        signal_cal = sum(cal_w[s] for s in signal_stages)

        # 冗余中心偏移 O_Q = Σ_aux Ŵ_i / 2 (Chen 式 12.26)
        aux_nom = sum(nom_w[s] for s in aux_stages)
        aux_cal = sum(cal_w[s] for s in aux_stages)
        redundancy_offset_nom = aux_nom / 2.0
        redundancy_offset_cal = aux_cal / 2.0

        # 增益误差 α: 最小二乘拟合 e = α·W₀ + ε
        # α = Σ(e_i · w_i_nom) / Σ(w_i_nom²)
        # 仅对信号阶段做 (校准目标 stages 0-6)
        cal_target_stages = [6, 5, 4, 3, 2, 1, 0]  # 校准顺序
        num = 0.0
        den = 0.0
        for s in cal_target_stages:
            e_i = cal_w[s] - phys_w[s]
            w0_i = nom_w[s]
            num += e_i * w0_i
            den += w0_i * w0_i

        alpha = num / den if den > 0 else 0.0

        # 分解 e = α·W₀ + e⊥
        per_stage = []
        residuals = []
        for s in cal_target_stages:
            e_i = cal_w[s] - phys_w[s]
            gain_component = alpha * nom_w[s]
            orth_component = e_i - gain_component
            residuals.append(orth_component)
            per_stage.append({
                'stage': s,
                'name': ['H32C', 'H16C', 'H8C', 'H4C', 'H2C', 'H1C-R', 'H1C-A'][6 - s],
                'cal_q0': round(cal_w[s], 6),
                'phys_q0': round(phys_w[s], 6),
                'nom_q0': nom_w[s],
                'error_q0': round(e_i, 6),
                'gain_component_q0': round(gain_component, 6),
                'orthogonal_q0': round(orth_component, 6),
            })

        residual_rms = (sum(r**2 for r in residuals) / len(residuals))**0.5 if residuals else 0.0
        residual_max = max(abs(r) for r in residuals) if residuals else 0.0

        # 增益吸收比例: decoder 归一化分母 signal_cal 已包含增益
        # 理想吸收: signal_cal / signal_nom = 1+α 或接近
        # gain_absorbed_ratio = 1 - |signal_cal/signal_nom - (1+α)| / |α|
        if abs(alpha) > 1e-12:
            theoretical_ratio = 1.0 + alpha
            actual_ratio = signal_cal / signal_nom
            gain_absorbed_ratio = 1.0 - min(abs(actual_ratio - theoretical_ratio) / abs(alpha), 1.0)
        else:
            gain_absorbed_ratio = 1.0

        gain_analysis = GainModeAnalysis(
            alpha=alpha,
            signal_weight_nominal_q0=signal_nom,
            signal_weight_calibrated_q0=signal_cal,
            redundancy_offset_nominal_q0=redundancy_offset_nom,
            redundancy_offset_calibrated_q0=redundancy_offset_cal,
            gain_absorbed_ratio=round(gain_absorbed_ratio, 6),
            residual_rms_q0=round(residual_rms, 6),
            residual_max_q0=round(residual_max, 6),
            per_stage=tuple(per_stage),
        )

        return CalibrationReport(
            weights_q=self.weights_q,
            weights_q0=self.weights_q0,
            targets=self.targets,
            all_targets_complete=self.all_targets_complete,
            valid=self.valid,
            calibration_start_time_s=self.calibration_start_time_s,
            calibration_done_time_s=self.calibration_done_time_s,
            gain_analysis=gain_analysis,
        )
