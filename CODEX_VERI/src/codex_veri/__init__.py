"""Python golden model for the CODEX_VERI calibration gate."""

from .model import (
    NOMINAL_STAGES,
    PairDecision,
    SaturationError,
    StageEstimate,
    calibrate_centered_recursive,
    calibrate_legacy_magnitude_recursive,
    calibrate_legacy_replay,
    huang_equation_pair,
    quantize_signed,
    signed_pair,
)

__all__ = [
    "NOMINAL_STAGES",
    "PairDecision",
    "SaturationError",
    "StageEstimate",
    "calibrate_centered_recursive",
    "calibrate_legacy_magnitude_recursive",
    "calibrate_legacy_replay",
    "huang_equation_pair",
    "quantize_signed",
    "signed_pair",
]
