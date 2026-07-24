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
from python_cal.calibration.shen_calibrator import ShenCalibrationController
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
                         cal_noise_sigma: float | None = None,
                         caldac_passes: int = 2) -> CalibrationReport:
        """[DEPRECATED] 执行完整校准 (旧版 calDAC 搜索方案)

        **警告: 此方法使用 AsyncCalibrationController，包含 Oracle 泄漏**
        _(calibrate_caldac_weights() 直接读取模拟 ΔV)。_

        当前活跃验证脚本应使用 `ShenCalibrationController` 代替。
        此方法仅保留用于历史兼容性测试。

        需求文档 33 §19:
          adc.reset()
          cal_report = adc.run_calibration(avg_pairs=128, rng=cal_rng)
          assert cal_report.valid

        参数:
            avg_pairs: 每个 target 的 D+/D- 测量对数
            rng: numpy.random.Generator
            cal_noise_sigma: 校准期间比较器噪声 (V RMS), None=使用主比较器噪声
            caldac_passes: calDAC 自校准迭代次数, 2=C4a 收敛, 1=原始行为

        返回:
            CalibrationReport
        """
        import warnings
        warnings.warn(
            "AsyncCalibrationController is DEPRECATED (Oracle leakage in "
            "_calibrate_caldac_weights). Use ShenCalibrationController instead.",
            DeprecationWarning, stacklevel=2
        )
        self.mode = ADCOperatingMode.CALIBRATION

        # Lazy import keeps the deprecated calDAC-search implementation out of
        # the active package import path. Only callers of this compatibility
        # method load it, and they receive the deprecation warning above.
        from python_cal.calibration.calibration_controller import (
            AsyncCalibrationController,
        )

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
                cal_controller.compute_noise_sigma_v_from_lsb(
                    cfg.CAL_NOISE_SIGMA_LSB
                )
        try:
            report = cal_controller.run(
                rng=rng, caldac_passes=caldac_passes
            )
        except TypeError as exc:
            # Compatibility with the original deprecated controller, whose
            # run() signature did not expose caldac_passes.
            if "caldac_passes" not in str(exc):
                raise
            report = cal_controller.run(rng=rng)

        self.calibration_registers = cal_controller.registers
        self.calibration_report = report

        if report.valid:
            self.mode = ADCOperatingMode.READY
            if (
                hasattr(report, "weights_q0_p")
                and hasattr(report, "weights_q0_n")
            ):
                self._decoder.update_weights_per_side(
                    list(report.weights_q0_p),
                    list(report.weights_q0_n),
                )
            else:
                self._decoder.update_weights(list(report.weights_q0))
        else:
            self.mode = ADCOperatingMode.ERROR

        return report

    def run_shen_calibration(self, avg_pairs: int = cfg.AVG_PAIRS, rng=None,
                              cal_noise_sigma_v: float | None = None
                              ) -> dict:
        """执行 Shen 2018 式校准 (lower-SAR 子转换)

        与旧 calDAC balance-search 方案不同:
          - 使用 force-0/force-1 + lower-SAR 子转换测量权重
          - 无需 calDAC 自校准
          - VREFN/VREFP 对称半差 + 固定 dither 抵消失调/锁码
          - stage 13 是 comparator-only terminal

        参数:
            avg_pairs: P0/P1/N0/N1 测量对数
            rng: numpy.random.Generator
            cal_noise_sigma_v: 校准期间比较器噪声 (V RMS),
                               None=cfg.CAL_NOISE_SIGMA_V

        返回:
            dict: {
                'targets': list[dict],  # 每 target 的 W_P, W_N, W_avg, valid
                'full_wp': list[float], # 14 元素完整 P 侧权重
                'full_wn': list[float], # 14 元素完整 N 侧权重
                'valid': bool,
            }
        """
        self.mode = ADCOperatingMode.CALIBRATION

        noise_v = (
            cal_noise_sigma_v
            if cal_noise_sigma_v is not None
            else cfg.CAL_NOISE_SIGMA_V
        )
        shen_ctrl = ShenCalibrationController(
            cdac=self.cdac,
            comparator=self.comparator,
            timing=self.timing,
            avg_pairs=avg_pairs,
            cal_noise_sigma=noise_v,
        )
        targets_result, full_wp, full_wn = shen_ctrl.run(rng=rng)

        valid = all(t['valid'] for t in targets_result)

        if valid:
            self.mode = ADCOperatingMode.READY
            self._decoder.update_weights_per_side(list(full_wp), list(full_wn))
        else:
            self.mode = ADCOperatingMode.ERROR

        return {
            'targets': targets_result,
            'full_wp': full_wp,
            'full_wn': full_wn,
            'valid': valid,
        }

    def apply_calibration(self, report: CalibrationReport):
        """手动应用校准报告

        用于从已保存的校准报告恢复。
        GPT 建议: 分侧 decoder。
        """
        self.calibration_report = report
        self.calibration_registers.weights_q = list(report.weights_q)
        self.calibration_registers.calibration_done = report.valid
        if (
            hasattr(report, "weights_q0_p")
            and hasattr(report, "weights_q0_n")
        ):
            self._decoder.update_weights_per_side(
                list(report.weights_q0_p),
                list(report.weights_q0_n),
            )
        else:
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

    def decode_float(self, decisions) -> float:
        """浮点参考重构，不增加物理 SAR 位数。"""
        return self._decoder.decode_float(decisions)

    def decode_fixed(self, decisions, fractional_bits: int = 2) -> float:
        """定点重构；默认 Q2，即 0.25 LSB 数字输出步长。"""
        return self._decoder.decode_fixed(decisions, fractional_bits)

    def decode_detailed(self, decisions):
        """解码并返回详细信息"""
        return self._decoder.decode_detailed(decisions)
