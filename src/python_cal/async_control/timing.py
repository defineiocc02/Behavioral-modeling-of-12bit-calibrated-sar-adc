"""
timing.py — 时序参数

需求文档 §12: DAC settling 必须有行为模型。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TimingParams:
    """SAR ADC 行为级时序参数

    所有时间单位为秒 (s)。
    """
    sample_duration_s:  float = 10e-9   # 采样持续时间
    dac_settle_tau_s:   float = 1e-9    # DAC settling RC 时间常数
    dac_residual_target_v: float = 1e-6 # settling 残差目标 (V)
    ideal_settling:     bool = True     # True=瞬时稳态, False=RC 衰减
    reset_duration_s:   float = 5e-9    # 复位持续时间
