"""
caldac_ruler_error.py — calDAC 尺子误差预测 (文档 41 C4, Chen §8.2)

桥接电容失配导致低段物理权重偏离标称。校准控制器用标称低段权重
解释 calDAC 码值 → 测量误差沿 wall 链传播。

本模块提供误差预测公式和有界性证明。
"""

import numpy as np
from dataclasses import dataclass
from python_cal import config as cfg


@dataclass
class CaldacRulerPrediction:
    """calDAC 尺子误差预测

    属性:
        epsilon_caldac: calDAC 物理权重相对偏差 (w_phys / w_nom - 1)
        predicted_alpha: 预测的校准增益误差 α
        measured_alpha: 实测 α (from GainModeAnalysis)
        alpha_match: 预测与实测是否一致 (|pred - meas| < 0.01)
        per_target_measured: list[dict] 每 target 实测值
        per_target_predicted: list[dict] 每 target 预测值
        cal_gain_bound_db: 有界性: cal gain 下限 (dB)
    """
    epsilon_caldac: float
    predicted_alpha: float
    measured_alpha: float
    alpha_match: bool
    per_target_measured: list
    per_target_predicted: list
    cal_gain_bound_db: float


def compute_caldac_physical_deviation(cdac) -> float:
    """计算 calDAC 低段物理权重相对标称的偏差

    ε_caldac = mean(w_phys[s] / w_nom[s] - 1) for s in CAL_DAC_STAGES
    """
    phys_w = cdac.get_physical_weights_q0()
    nom_w = cfg.NOMINAL_WEIGHTS_Q0
    deviations = []
    for s in cfg.CAL_DAC_STAGES:
        if nom_w[s] > 0:
            deviations.append(phys_w[s] / nom_w[s] - 1.0)
    return float(np.mean(deviations)) if deviations else 0.0


def predict_calibration_error(epsilon_caldac: float) -> dict:
    """预测 calDAC 尺子误差导致的校准权重偏差

    Chen §8.2: 后端 DAC 三类误差源之首——未校准低位电容失配。
    当 calDAC 物理权重 = (1+ε) × 标称 时:
      measured_residual ≈ true_residual / (1+ε)
      measured_weight = wall_sum + measured_residual

    沿 wall 链递归传播 (Chen 式 12.26):
      e_i ≈ Σ_{j<i} A_{ij} · e_j - ε · w_i_nom

    简化: 在增益模态主导场景, 近似为:
      Ŵ_i ≈ W_i_phys / (1+ε)
      α ≈ 1/(1+ε) - 1 ≈ -ε  (一阶泰勒)

    参数:
        epsilon_caldac: calDAC 物理权重相对偏差

    返回:
        dict: {target_name: predicted_weight_q0}
    """
    scale = 1.0 / (1.0 + epsilon_caldac)

    predictions = {}
    # 校准顺序: H1C-A → H1C-R → H2C → H4C → H8C → H16C → H32C
    cal_order = [
        ('H1C-A', 6, 65),
        ('H1C-R', 5, 65),
        ('H2C',   4, 130),
        ('H4C',   3, 260),
        ('H8C',   2, 520),
        ('H16C',  1, 1040),
        ('H32C',  0, 2080),
    ]

    for name, stage, nominal_q0 in cal_order:
        # 在增益主导假设下: Ŵ = W_phys / (1+ε) ≈ W_nom / (1+ε)
        # 但更精确的: wall 由已校准权重组成, 也受 ε 影响
        predictions[name] = {
            'stage': stage,
            'predicted_q0': nominal_q0 * scale,
            'epsilon_effect': nominal_q0 * (scale - 1.0),
        }

    predicted_alpha = scale - 1.0
    return predictions, predicted_alpha


def analyze_caldac_ruler_error(cal_report, cdac) -> CaldacRulerPrediction:
    """分析 calDAC 尺子误差: 预测 vs 实测

    文档 41 C4: 桥接/低段失配场景的校准误差有界性。

    参数:
        cal_report: CalibrationReport (含 gain_analysis)
        cdac: DifferentialCDAC

    返回:
        CaldacRulerPrediction
    """
    epsilon = compute_caldac_physical_deviation(cdac)
    predictions, predicted_alpha = predict_calibration_error(epsilon)

    ga = cal_report.gain_analysis
    measured_alpha = ga.alpha if ga else 0.0

    alpha_match = abs(predicted_alpha - measured_alpha) < 0.01

    # 逐 target 实测 vs 预测
    per_target_measured = []
    per_target_predicted = []
    for t in cal_report.targets:
        per_target_measured.append({
            'name': t.target_name,
            'stage': t.stage,
            'measured_q0': t.measured_weight_q0,
            'physical_q0': t.physical_weight_q0,
            'nominal_q0': t.nominal_weight_q0,
        })
        if t.target_name in predictions:
            per_target_predicted.append({
                'name': t.target_name,
                'stage': t.stage,
                'predicted_q0': predictions[t.target_name]['predicted_q0'],
                'physical_q0': t.physical_weight_q0,
            })

    # 有界性: cal gain = 20*log10(scale) ≈ 20*log10(1-|ε|) dB
    # 保守界: |ε| ≤ 2% → cal gain ≥ -0.18 dB
    # 实际测量中 decoder 归一化吸收增益 → 转换层 INL 来自低段权重未校准
    cal_gain_bound_db = 20.0 * np.log10(1.0 / (1.0 + abs(epsilon)))

    return CaldacRulerPrediction(
        epsilon_caldac=epsilon,
        predicted_alpha=predicted_alpha,
        measured_alpha=measured_alpha,
        alpha_match=alpha_match,
        per_target_measured=per_target_measured,
        per_target_predicted=per_target_predicted,
        cal_gain_bound_db=cal_gain_bound_db,
    )
