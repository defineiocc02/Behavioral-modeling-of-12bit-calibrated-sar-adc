"""Active foreground calibration package.

Only the comparator-observable force-0/force-1 half-difference path is kept.
Retired calDAC-search and oracle-leaking experiments remain in Git history.
"""

from .shen_calibrator import ShenCalibrationController

__all__ = ["ShenCalibrationController"]
