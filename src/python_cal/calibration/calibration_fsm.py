"""State definitions for the active Shen-derived calibration path."""
from enum import Enum


class ShenCalibrationState(Enum):
    """State vocabulary for the active comparator-observable Shen path."""

    IDLE = "idle"
    TARGET_SETUP = "target_setup"
    P0_SUBCONVERSION = "p0_subconversion"
    P1_SUBCONVERSION = "p1_subconversion"
    N0_SUBCONVERSION = "n0_subconversion"
    N1_SUBCONVERSION = "n1_subconversion"
    PAIR_ACCUMULATE = "pair_accumulate"
    TARGET_ESTIMATE = "target_estimate"
    TARGET_VALIDATE = "target_validate"
    TARGET_COMMIT = "target_commit"
    NEXT_TARGET = "next_target"
    DONE = "done"
    FAILED = "failed"


class ADCOperatingMode(Enum):
    """Top-level ADC operating mode."""
    RESET = "reset"
    CALIBRATION = "calibration"
    READY = "ready"
    CONVERSION = "conversion"
    ERROR = "error"
