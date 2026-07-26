"""12-bit calibrated asynchronous SAR ADC Python behavioral model."""

from python_cal.conversion.async_sar_adc import AsyncBehavioralSARADC
from python_cal.decode.sar_decoder import SARDecoder as BehavioralDecoder
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.calibration.calibration_fsm import ADCOperatingMode

__all__ = [
    "ADCOperatingMode",
    "AsyncBehavioralSARADC",
    "BehavioralDecoder",
    "DifferentialCDAC",
]

__version__ = "3.1.1"
