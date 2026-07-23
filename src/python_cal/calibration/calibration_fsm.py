"""
calibration_fsm.py — 校准 FSM 状态定义

需求文档 33 §10: 校准异步状态机。
"""
from enum import Enum


class CalibrationState(Enum):
    """校准 FSM 状态"""
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


class ADCOperatingMode(Enum):
    """ADC 全局工作模式 (需求文档 33 §3)"""
    RESET = "reset"
    CALIBRATION = "calibration"
    READY = "ready"
    CONVERSION = "conversion"
    ERROR = "error"


class CalibrationEventType(Enum):
    """校准事件类型 (需求文档 33 §11)"""
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
