"""Reproducible validation protocols for the behavioral SAR ADC model."""

from .fft_protocol import (
    FFTProtocol,
    build_coherent_differential_sine,
    measure_positive_vfs,
    validate_fft_stimulus,
)

__all__ = [
    "FFTProtocol",
    "build_coherent_differential_sine",
    "measure_positive_vfs",
    "validate_fft_stimulus",
]
