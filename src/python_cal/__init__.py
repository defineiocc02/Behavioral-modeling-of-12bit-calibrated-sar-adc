"""
python_cal — SAR ADC 异步行为级模型

需求文档 32: 从开关电容 SAR ADC 的物理工作原理出发，
独立实现完整、自洽的异步全差分 SAR ADC 行为级模型。

需求文档 33: 集成异步校准子系统。

模块:
  topology/       — 电容拓扑与开关状态
  physical/       — 电荷守恒求解器与 CDAC 模型
  comparator/     — 动态比较器
  async_control/  — 异步握手与 FSM
  conversion/     — 顶层 ADC 模型
  decode/         — 数字解码器
  calibration/    — 异步校准控制器
  tests/          — 测试套件
  research/       — 旧模型归档 (参考用，不参与转换)
"""

from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
from python_cal.decode.sar_decoder import SARDecoder as BehavioralDecoder
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.calibration.calibration_fsm import ADCOperatingMode, CalibrationState
from python_cal.calibration.calibration_registers import CalibrationRegisters
from python_cal.calibration.calibration_trace import (
    CalibrationReport, TargetCalibrationResult, CalibrationSearchStepTrace
)

__version__ = "2.0.0"
