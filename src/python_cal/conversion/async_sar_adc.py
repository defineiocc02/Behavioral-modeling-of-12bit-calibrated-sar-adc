"""
async_sar_adc.py — 异步全差分 SAR ADC 行为级模型

需求文档 32 §2: 核心模型。
从开关电容 SAR ADC 的物理工作原理出发,
独立实现完整、自洽的异步 SAR ADC。

需求文档 33: 集成校准子系统。
"""
from dataclasses import dataclass, field

from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.comparator.dynamic_comparator import DynamicComparator
from python_cal.async_control.handshake import AsyncSARController
from python_cal.async_control.timing import TimingParams
from python_cal.topology.switching_policy import DifferentialSwitchingPolicy
from python_cal.topology.cdac_topology import VCM, VREF
from python_cal.decode.sar_decoder import SARDecoder
from python_cal.calibration.calibration_registers import CalibrationRegisters
from python_cal.calibration.calibration_controller import AsyncCalibrationController
from python_cal.calibration.calibration_trace import CalibrationReport
from python_cal.calibration.calibration_fsm import ADCOperatingMode
from python_cal import config as cfg


@dataclass
class AsyncBehavioralSARADC:
    """异步全差分 SAR ADC 行为级模型

    需求文档 32 §2: 不参考任何 VA 实现, 由拓扑、电荷守恒和
    异步握手规则自洽地产生结果。

    需求文档 33 §19: 统一 API, 支持校准和正常转换。

    使用方式:
      adc = AsyncBehavioralSARADC()
      adc.reset()

      # 可选: 不校准, 使用 nominal decoder
      adc.enable_nominal_decode()
      result = adc.convert(vinp, vinn)

      # 或: 运行真实校准
      report = adc.run_calibration(rng=cal_rng)
      result = adc.convert(vinp, vinn, rng=conv_rng)

      # 解码
      code = adc.decode(result.decisions)
    """

    cdac: DifferentialCDAC = field(default_factory=DifferentialCDAC.ideal)
    comparator: DynamicComparator = field(default_factory=DynamicComparator)
    timing: TimingParams = field(default_factory=TimingParams)

    # 校准/模式状态
    mode: ADCOperatingMode = ADCOperatingMode.RESET
    calibration_registers: CalibrationRegisters = field(
        default_factory=CalibrationRegisters.default
    )
    calibration_report: CalibrationReport | None = None
    _nominal_decode_enabled: bool = False

    def __post_init__(self):
        self._policy = DifferentialSwitchingPolicy()
        self._controller = AsyncSARController(
            cdac=self.cdac,
            comparator=self.comparator,
            switching_policy=self._policy,
            timing=self.timing,
        )
        self._decoder = SARDecoder()

    # === 模式管理 ===

    def reset(self):
        """复位 ADC 到 RESET 状态"""
        self.mode = ADCOperatingMode.RESET
        self.calibration_registers = CalibrationRegisters.default()
        self.calibration_report = None
        self._nominal_decode_enabled = False
        self._decoder = SARDecoder()

    def enable_nominal_decode(self):
        """启用标称解码器 (跳过校准, 使用理想权重)"""
        self._nominal_decode_enabled = True
        self.mode = ADCOperatingMode.READY
        self._decoder = SARDecoder()

    def run_calibration(self, avg_pairs: int = 128, rng=None,
                         cal_noise_sigma: float | None = None) -> CalibrationReport:
        """执行完整校准

        需求文档 33 §19:
          adc.reset()
          cal_report = adc.run_calibration(avg_pairs=128, rng=cal_rng)
          assert cal_report.valid

        参数:
            avg_pairs: 每个 target 的 D+/D- 测量对数
            rng: numpy.random.Generator
            cal_noise_sigma: 校准期间比较器噪声 (V RMS), None=使用主比较器噪声

        返回:
            CalibrationReport
        """
        self.mode = ADCOperatingMode.CALIBRATION

        cal_controller = AsyncCalibrationController(
            cdac=self.cdac,
            comparator=self.comparator,
            timing=self.timing,
            avg_pairs=avg_pairs,
            registers=self.calibration_registers,
        )
        if cal_noise_sigma is not None:
            cal_controller.cal_noise_sigma = cal_noise_sigma
        else:
            # C2: 默认使用 config.CAL_NOISE_SIGMA (LSB) → V RMS
            # 零噪声仅作 debug, 正式运行必须含抖动
            cal_controller.cal_noise_sigma = \
                cal_controller.compute_noise_sigma_v_from_lsb(cfg.CAL_NOISE_SIGMA)
        report = cal_controller.run(rng=rng)

        self.calibration_registers = cal_controller.registers
        self.calibration_report = report

        if report.valid:
            self.mode = ADCOperatingMode.READY
            # 加载校准权重到 decoder
            self._decoder.update_weights(
                list(report.weights_q0)
            )
        else:
            self.mode = ADCOperatingMode.ERROR

        return report

    def apply_calibration(self, report: CalibrationReport):
        """手动应用校准报告

        用于从已保存的校准报告恢复。
        """
        self.calibration_report = report
        self.calibration_registers.weights_q = list(report.weights_q)
        self.calibration_registers.calibration_done = report.valid
        self._decoder.update_weights(list(report.weights_q0))
        self.mode = ADCOperatingMode.READY if report.valid else ADCOperatingMode.ERROR

    # === 转换 ===

    def convert(self, vinp: float, vinn: float, rng=None):
        """执行一次 ADC 转换

        需求文档 33 §3: 仅在 READY 模式下允许转换。
        未校准且未启用 nominal decode 时抛出异常。

        参数:
            vinp, vinn: 差分输入电压 (V)
            rng: numpy.random.Generator (None = 无噪声)

        返回:
            AsyncSARConversionResult
        """
        if self.mode not in (ADCOperatingMode.READY, ADCOperatingMode.CONVERSION):
            if not self._nominal_decode_enabled:
                raise RuntimeError(
                    f"ADC not ready: mode={self.mode.value}. "
                    f"Call run_calibration() or enable_nominal_decode() first."
                )
        self.mode = ADCOperatingMode.CONVERSION
        result = self._controller.start_conversion(vinp, vinn, rng=rng)
        self.mode = ADCOperatingMode.READY
        return result

    def convert_diff(self, vin_diff: float, rng=None):
        """差分输入便捷接口

        vin_diff = VIP - VIN
        """
        vip = VCM + vin_diff / 2.0
        vin = VCM - vin_diff / 2.0
        return self.convert(vip, vin, rng=rng)

    def convert_batch(self, vin_diff_samples, rng=None):
        """批量转换 (差分输入)"""
        results = []
        for vd in vin_diff_samples:
            results.append(self.convert_diff(float(vd), rng=rng))
        return results

    # === 解码 ===

    def decode(self, decisions) -> int:
        """解码 SAR decisions → ADC code

        使用校准后权重 (如果有) 或标称权重。
        """
        return self._decoder.decode(decisions)

    def decode_detailed(self, decisions):
        """解码并返回详细信息"""
        return self._decoder.decode_detailed(decisions)
