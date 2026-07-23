"""
calibration_registers.py — 校准寄存器

需求文档 33 §9: 定义独立寄存器组。
每完成一个 target，立即写入校准权重。
"""
from dataclasses import dataclass
from python_cal import config as cfg

DEFAULT_NOMINAL_WEIGHTS_Q = [int(w * cfg.Q_SCALE) for w in cfg.NOMINAL_WEIGHTS_Q0]


@dataclass
class CalibrationRegisters:
    """校准寄存器

    需求文档 33 §9:
      weights_q: 校准后的 Q6 权重 (14 级)
      valid_bits: 每级是否有效
      saturation_bits: 每级是否饱和
      target_complete: 每级是否完成
      calibration_done: 全部校准是否完成
    """
    weights_q: list[int]
    valid_bits: list[bool]
    saturation_bits: list[bool]
    target_complete: list[bool]
    calibration_done: bool = False

    @classmethod
    def default(cls):
        """创建默认寄存器 (标称权重)"""
        return cls(
            weights_q=list(DEFAULT_NOMINAL_WEIGHTS_Q),
            valid_bits=[False] * 14,
            saturation_bits=[False] * 14,
            target_complete=[False] * 7,
            calibration_done=False,
        )

    def write_target(self, target_id: int, stage: int,
                     measured_weight_q: int, valid: bool, sat: bool):
        """写入单个 target 的校准结果"""
        self.weights_q[stage] = measured_weight_q
        self.valid_bits[target_id] = valid
        self.saturation_bits[target_id] = sat
        self.target_complete[target_id] = True

    def finish(self):
        """标记校准完成"""
        self.calibration_done = True

    def get_calibrated_weights_q0(self):
        """获取校准后 Q0 权重 (用于 decoder)"""
        return [w / cfg.Q_SCALE for w in self.weights_q]
