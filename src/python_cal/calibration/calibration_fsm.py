"""Calibration state definitions.

``CalibrationState`` and ``CalibrationEventType`` describe only the deprecated
calDAC-search controller. The active Shen path uses ``ShenCalibrationState``;
keeping the two vocabularies separate prevents old DPLUS/DMINUS terminology
from being mistaken for the P0/P1/N0/N1 half-difference protocol.
"""
from enum import Enum


class CalibrationState(Enum):
    """[DEPRECATED] Legacy calDAC-search controller state."""
    IDLE = "idle"
    TARGET_SETUP = "target_setup"
    DPLUS_SAMPLE = "dplus_sample"
    DPLUS_SEARCH = "dplus_search"
    DMINUS_SAMPLE = "dminus_sample"
    DMINUS_SEARCH = "dminus_search"
    PAIR_ACCUMULATE = "pair_accumulate"
    TARGET_ESTIMATE = "target_estimate"
    TARGET_VALIDATE = "target_validate"
    TARGET_COMMIT = "target_commit"
    NEXT_TARGET = "next_target"
    DONE = "done"
    FAILED = "failed"


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
    """ADC 全局工作模式 (需求文档 33 §3)"""
    RESET = "reset"
    CALIBRATION = "calibration"
    READY = "ready"
    CONVERSION = "conversion"
    ERROR = "error"


class CalibrationEventType(Enum):
    """[DEPRECATED] Legacy calDAC-search event vocabulary."""
    CAL_START = "cal_start"
    TARGET_START = "target_start"
    DPLUS_START = "dplus_start"
    DPLUS_DONE = "dplus_done"
    DMINUS_START = "dminus_start"
    DMINUS_DONE = "dminus_done"
    CAL_DAC_TRIAL = "cal_dac_trial"
    CAL_DAC_SETTLED = "cal_dac_settled"
    CAL_CMP_REQUEST = "cal_cmp_request"
    CAL_CMP_DONE = "cal_cmp_done"
    CAL_BIT_COMMIT = "cal_bit_commit"
    PAIR_DONE = "pair_done"
    TARGET_ESTIMATED = "target_estimated"
    TARGET_COMMITTED = "target_committed"
    CAL_DONE = "cal_done"
    CAL_FAILED = "cal_failed"
