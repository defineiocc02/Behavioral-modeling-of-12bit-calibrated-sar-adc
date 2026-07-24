"""Single-source FFT stimulus protocol for dynamic ADC comparisons.

The calibration result is only meaningful when nominal, calibrated, and
physical-reference decoders see exactly the same converter decisions.  This
module therefore owns the stimulus definition and the VFS measurement used by
all current dynamic experiments.

Definitions
-----------
``vfs_v`` is the positive differential input magnitude at which the nominal
decoder first reaches ``max_code - guard_codes``.  A ``dbfs`` value is a peak
amplitude ratio, so ``0 dBFS`` means a sine peak equal to ``vfs_v`` and
``-0.5 dBFS`` is the recommended non-clipping margin for this behavioral
model.  The returned metadata records the measured peak and clipping status;
it is not inferred from VREF.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import math
from typing import Callable

import numpy as np


@dataclass(frozen=True)
class FFTProtocol:
    """Explicit, hashable definition of a coherent dynamic test."""

    n_fft: int = 4096
    signal_bin: int = 127
    amplitude_dbfs: float = -0.5
    phase_rad: float = 0.123
    max_code_guard: int = 1

    def validate(self) -> None:
        if self.n_fft <= 0:
            raise ValueError("n_fft must be positive")
        if not 0 < self.signal_bin < self.n_fft // 2:
            raise ValueError("signal_bin must lie in the positive rFFT band")
        if math.gcd(self.signal_bin, self.n_fft) != 1:
            raise ValueError("signal_bin and n_fft must be coprime for coherent sampling")
        if self.max_code_guard < 0:
            raise ValueError("max_code_guard must be non-negative")

    def as_dict(self) -> dict:
        self.validate()
        return asdict(self)


def measure_positive_vfs(
    code_from_vdiff: Callable[[float], int],
    max_code: int,
    *,
    guard_codes: int = 1,
    initial_hi_v: float = 2.0,
    expand_limit: int = 12,
    iterations: int = 32,
) -> float:
    """Measure positive differential VFS with a deterministic bisection.

    The callback must be deterministic for a fixed input.  The returned
    threshold is the smallest tested input whose code is at least
    ``max_code - guard_codes``.  This deliberately mirrors the converter-side
    endpoint convention instead of assuming ``VREF/2`` or ``0.45*VREF``.
    """

    if max_code <= 0:
        raise ValueError("max_code must be positive")
    target = max_code - guard_codes
    if target <= 0:
        raise ValueError("guard_codes leaves no positive target code")
    lo = 0.0
    hi = float(initial_hi_v)
    if hi <= 0:
        raise ValueError("initial_hi_v must be positive")
    for _ in range(expand_limit):
        if int(code_from_vdiff(hi)) >= target:
            break
        hi *= 1.5
    else:
        raise RuntimeError("unable to bracket positive VFS")

    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if int(code_from_vdiff(mid)) >= target:
            hi = mid
        else:
            lo = mid
    return float(hi)


def build_coherent_differential_sine(
    vfs_v: float,
    protocol: FFTProtocol,
) -> tuple[np.ndarray, dict]:
    """Build a differential sine and return it with auditable metadata."""

    protocol.validate()
    if not np.isfinite(vfs_v) or vfs_v <= 0:
        raise ValueError("vfs_v must be finite and positive")
    amplitude_ratio = 10.0 ** (protocol.amplitude_dbfs / 20.0)
    amplitude_v = float(vfs_v * amplitude_ratio)
    sample_index = np.arange(protocol.n_fft, dtype=np.float64)
    vin = amplitude_v * np.sin(
        2.0 * np.pi * protocol.signal_bin * sample_index / protocol.n_fft
        + protocol.phase_rad
    )
    metadata = {
        **protocol.as_dict(),
        "vfs_v": float(vfs_v),
        "amplitude_ratio": float(amplitude_ratio),
        "amplitude_v": amplitude_v,
        "measured_peak_v": float(np.max(np.abs(vin))),
        "peak_ratio_to_vfs": float(np.max(np.abs(vin)) / vfs_v),
        "cycles_in_record": float(protocol.signal_bin),
        "coherent": True,
        "clipping": bool(np.max(np.abs(vin)) > vfs_v * (1.0 + 1e-12)),
    }
    return vin, metadata


def validate_fft_stimulus(vin: np.ndarray, vfs_v: float, protocol: FFTProtocol) -> dict:
    """Validate a stimulus before it is used for a path-to-path comparison."""

    protocol.validate()
    arr = np.asarray(vin, dtype=np.float64)
    if arr.shape != (protocol.n_fft,):
        raise ValueError(f"stimulus shape {arr.shape} != {(protocol.n_fft,)}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("stimulus contains non-finite values")
    peak = float(np.max(np.abs(arr)))
    return {
        "length_ok": True,
        "coherent": True,
        "clipping": bool(peak > vfs_v * (1.0 + 1e-12)),
        "measured_peak_v": peak,
        "peak_ratio_to_vfs": float(peak / vfs_v),
    }
