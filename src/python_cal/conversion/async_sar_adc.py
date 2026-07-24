"""Top-level asynchronous differential SAR ADC behavioral model."""

from __future__ import annotations

from dataclasses import dataclass, field

from python_cal import config as cfg
from python_cal.async_control.handshake import AsyncSARController
from python_cal.async_control.timing import TimingParams
from python_cal.calibration.calibration_fsm import ADCOperatingMode
from python_cal.calibration.shen_calibrator import ShenCalibrationController
from python_cal.comparator.dynamic_comparator import DynamicComparator
from python_cal.decode.sar_decoder import SARDecoder
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.topology.cdac_topology import VCM
from python_cal.topology.switching_policy import DifferentialSwitchingPolicy


@dataclass
class AsyncBehavioralSARADC:
    """Charge-conserving CDAC, asynchronous control, and calibrated decoder.

    Physical decisions and digital reconstruction remain deliberately
    separated: updating decoder weights never changes the comparator path.
    The only active calibration path is the Shen-derived P/N split-side
    force-0/force-1 controller.
    """

    cdac: DifferentialCDAC = field(default_factory=DifferentialCDAC.ideal)
    comparator: DynamicComparator = field(default_factory=DynamicComparator)
    timing: TimingParams = field(default_factory=TimingParams)
    mode: ADCOperatingMode = ADCOperatingMode.RESET
    calibration_result: dict | None = None
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

    def reset(self):
        """Reset physical, calibration, and decoder state."""

        self.cdac.reset()
        self.mode = ADCOperatingMode.RESET
        self.calibration_result = None
        self._nominal_decode_enabled = False
        self._decoder = SARDecoder()

    def enable_nominal_decode(self):
        """Enable conversion with nominal decoder weights."""

        self._nominal_decode_enabled = True
        self.mode = ADCOperatingMode.READY
        self._decoder = SARDecoder()

    def run_calibration(
        self,
        avg_pairs: int = cfg.AVG_PAIRS,
        rng=None,
        cal_noise_sigma_v: float | None = None,
    ) -> dict:
        """Run the single supported Shen-derived calibration protocol."""

        return self.run_shen_calibration(
            avg_pairs=avg_pairs,
            rng=rng,
            cal_noise_sigma_v=cal_noise_sigma_v,
        )

    def run_shen_calibration(
        self,
        avg_pairs: int = cfg.AVG_PAIRS,
        rng=None,
        cal_noise_sigma_v: float | None = None,
    ) -> dict:
        """Calibrate H1 through H32 using lower-SAR half differences."""

        self.mode = ADCOperatingMode.CALIBRATION
        noise_v = (
            cfg.CAL_NOISE_SIGMA_V
            if cal_noise_sigma_v is None
            else cal_noise_sigma_v
        )
        controller = ShenCalibrationController(
            cdac=self.cdac,
            comparator=self.comparator,
            timing=self.timing,
            avg_pairs=avg_pairs,
            cal_noise_sigma=noise_v,
        )
        targets, weights_p, weights_n = controller.run(rng=rng)
        result = {
            "protocol": "Shen-derived force-0/force-1 half difference",
            "targets": targets,
            "full_wp": weights_p,
            "full_wn": weights_n,
            "valid": bool(
                len(targets) == len(cfg.SHEN_CAL_TARGETS)
                and all(target["valid"] for target in targets)
            ),
        }
        self.calibration_result = result
        if result["valid"]:
            self._decoder.update_weights_per_side(weights_p, weights_n)
            self._nominal_decode_enabled = False
            self.mode = ADCOperatingMode.READY
        else:
            self.mode = ADCOperatingMode.ERROR
        return result

    def apply_calibration(self, result: dict):
        """Restore a previously saved Shen calibration result."""

        required = {"full_wp", "full_wn", "valid"}
        missing = required.difference(result)
        if missing:
            raise ValueError(
                f"calibration result missing fields: {sorted(missing)}"
            )
        self.calibration_result = dict(result)
        if result["valid"]:
            self._decoder.update_weights_per_side(
                list(result["full_wp"]),
                list(result["full_wn"]),
            )
            self._nominal_decode_enabled = False
            self.mode = ADCOperatingMode.READY
        else:
            self.mode = ADCOperatingMode.ERROR

    def convert(self, vinp: float, vinn: float, rng=None):
        """Run one asynchronous conversion."""

        if self.mode not in (
            ADCOperatingMode.READY,
            ADCOperatingMode.CONVERSION,
        ):
            if not self._nominal_decode_enabled:
                raise RuntimeError(
                    f"ADC not ready: mode={self.mode.value}. "
                    "Run calibration or enable nominal decode first."
                )
        self.mode = ADCOperatingMode.CONVERSION
        result = self._controller.start_conversion(vinp, vinn, rng=rng)
        self.mode = ADCOperatingMode.READY
        return result

    def convert_diff(self, vin_diff: float, rng=None):
        vip = VCM + vin_diff / 2.0
        vin = VCM - vin_diff / 2.0
        return self.convert(vip, vin, rng=rng)

    def convert_batch(self, vin_diff_samples, rng=None):
        return [
            self.convert_diff(float(vin_diff), rng=rng)
            for vin_diff in vin_diff_samples
        ]

    def decode(self, decisions) -> int:
        return self._decoder.decode(decisions)

    def decode_float(self, decisions) -> float:
        return self._decoder.decode_float(decisions)

    def decode_fixed(self, decisions, fractional_bits: int = 2) -> float:
        return self._decoder.decode_fixed(decisions, fractional_bits)

    def decode_detailed(self, decisions):
        return self._decoder.decode_detailed(decisions)
