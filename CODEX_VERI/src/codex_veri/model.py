"""Timing-free mathematical models for recursive SAR ADC weight calibration.

The centered model implements Huang's signed-coordinate equations.  The legacy
replay model is deliberately separate: it reproduces the measured Spectre pair
codes without pretending that their phase/settling behavior is a mathematical
property of Huang's algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Iterable, Mapping, Sequence


NOMINAL_STAGES: tuple[tuple[str, float], ...] = (
    ("H1C-A", 65.0),
    ("H1C-R", 65.0),
    ("H2C", 130.0),
    ("H4C", 260.0),
    ("H8C", 520.0),
    ("H16C", 1040.0),
    ("H32C", 2080.0),
)

# Project candidate reach: six low calibration trials plus the 1 LSB terminal.
# This is an engineering bound, not a value stated by Huang Section 4.5.
CANDIDATE_MAX_ABS_RESIDUAL_CODE = 64.0 + 32.0 + 16.0 + 8.0 + 4.0 + 2.0 + 1.0


@dataclass(frozen=True)
class PairDecision:
    target: float
    wall: float
    residual: float
    d_plus: float
    d_minus: float
    estimate: float
    offset: float
    noise_plus: float
    noise_minus: float


@dataclass(frozen=True)
class StageEstimate:
    name: str
    physical: float
    wall: float
    estimate: float
    error: float
    pairs: tuple[PairDecision, ...]


class SaturationError(ValueError):
    """A directional conversion is outside the declared calibration range."""


def quantize_signed(value: float, step: float | None = 1.0, *, tie: str = "away") -> float:
    """Quantize in a signed coordinate while preserving odd symmetry.

    `step=None` is the continuous algebraic reference.  Supported tie modes are
    `away` and `toward`, both of which satisfy Q(-x)=-Q(x).  Exact zero always
    maps to zero and never receives a terminal increment.
    """

    if step is None:
        return float(value)
    if not math.isfinite(value) or not math.isfinite(step) or step <= 0:
        raise ValueError("value must be finite and step must be positive")
    if value == 0.0:
        return 0.0
    magnitude = abs(value) / step
    lower = math.floor(magnitude)
    fraction = magnitude - lower
    eps = 1e-12
    if fraction > 0.5 + eps:
        code = lower + 1
    elif fraction < 0.5 - eps:
        code = lower
    elif tie == "away":
        code = lower + 1
    elif tie == "toward":
        code = lower
    else:
        raise ValueError(f"unsupported tie mode: {tie}")
    return math.copysign(code * step, value)


def huang_equation_pair(
    target: float,
    *,
    offset_plus: float = 0.0,
    offset_minus: float | None = None,
    noise_plus: float = 0.0,
    noise_minus: float = 0.0,
    step: float | None = 1.0,
    tie: str = "away",
    max_abs_code: float | None = None,
) -> PairDecision:
    """Paper-level implementation of Huang equations (4.17)-(4.19).

    This function intentionally has no terminal bit and no recursive wall.  The
    quantizer/tie rule is an explicit engineering policy because Section 4.5 does
    not specify the digital boundary rule.  Saturation is reported, never clipped.
    """

    if offset_minus is None:
        offset_minus = offset_plus
    y_plus = target + offset_plus + noise_plus
    y_minus = -target + offset_minus + noise_minus
    if max_abs_code is not None and (abs(y_plus) > max_abs_code or abs(y_minus) > max_abs_code):
        raise SaturationError("Huang pair exceeds declared symmetric calibration range")
    d_plus = quantize_signed(y_plus, step, tie=tie)
    d_minus = quantize_signed(y_minus, step, tie=tie)
    return PairDecision(
        target=float(target), wall=0.0, residual=float(target),
        d_plus=float(d_plus), d_minus=float(d_minus),
        estimate=float((d_plus - d_minus) / 2.0),
        offset=float((offset_plus + offset_minus) / 2.0),
        noise_plus=float(noise_plus), noise_minus=float(noise_minus),
    )


def signed_pair(
    target: float,
    *,
    wall: float = 0.0,
    offset: float = 0.0,
    noise_plus: float = 0.0,
    noise_minus: float = 0.0,
    step: float | None = 1.0,
    tie: str = "away",
    max_abs_residual_code: float | None = CANDIDATE_MAX_ABS_RESIDUAL_CODE,
) -> PairDecision:
    """One engineering wall-plus-signed-residual measurement pair.

    This is a project candidate, not a rule stated in Huang Section 4.5. The
    calibrated quantity is represented as a recursive wall plus a signed
    residual.  The same signed quantizer is used in both directions:

        D+ = +wall + Q(+residual + offset + n+)
        D- = -wall + Q(-residual + offset + n-)
        W_hat = (D+ - D-) / 2

    Constant comparator offset cancels exactly in the continuous reference and
    remains bounded by finite quantization in the discrete model.
    """

    residual = target - wall
    y_plus = residual + offset + noise_plus
    y_minus = -residual + offset + noise_minus
    if max_abs_residual_code is not None:
        if not math.isfinite(max_abs_residual_code) or max_abs_residual_code <= 0:
            raise ValueError("max_abs_residual_code must be positive and finite")
        if abs(y_plus) > max_abs_residual_code or abs(y_minus) > max_abs_residual_code:
            raise SaturationError("wall-plus-signed residual exceeds declared candidate reach")
    q_plus = quantize_signed(y_plus, step, tie=tie)
    q_minus = quantize_signed(y_minus, step, tie=tie)
    d_plus = wall + q_plus
    d_minus = -wall + q_minus
    estimate = (d_plus - d_minus) / 2.0
    return PairDecision(
        target=float(target),
        wall=float(wall),
        residual=float(residual),
        d_plus=float(d_plus),
        d_minus=float(d_minus),
        estimate=float(estimate),
        offset=float(offset),
        noise_plus=float(noise_plus),
        noise_minus=float(noise_minus),
    )


def calibrate_centered_recursive(
    physical_weights: Mapping[str, float] | None = None,
    *,
    pairs: int = 1,
    step: float | None = 1.0,
    tie: str = "away",
    offset: float = 0.0,
    noise_source: Callable[[str, int, str], float] | None = None,
    max_abs_residual_code: float | None = CANDIDATE_MAX_ABS_RESIDUAL_CODE,
) -> tuple[StageEstimate, ...]:
    """Calibrate low-to-high using the project wall-plus-signed candidate."""

    if pairs <= 0:
        raise ValueError("pairs must be positive")
    physical = dict(NOMINAL_STAGES)
    if physical_weights is not None:
        physical.update({k: float(v) for k, v in physical_weights.items()})
    if set(physical) != {name for name, _ in NOMINAL_STAGES}:
        raise ValueError("physical_weights contains an unknown stage")
    if not all(math.isfinite(value) and value > 0.0 for value in physical.values()):
        raise ValueError("all physical weights must be positive and finite")
    estimates: list[StageEstimate] = []
    for name, _ in NOMINAL_STAGES:
        wall = sum(stage.estimate for stage in estimates)
        pair_results: list[PairDecision] = []
        for index in range(pairs):
            n_plus = 0.0 if noise_source is None else float(noise_source(name, index, "+"))
            n_minus = 0.0 if noise_source is None else float(noise_source(name, index, "-"))
            pair_results.append(
                signed_pair(
                    physical[name],
                    wall=wall,
                    offset=offset,
                    noise_plus=n_plus,
                    noise_minus=n_minus,
                    step=step,
                    tie=tie,
                    max_abs_residual_code=max_abs_residual_code,
                )
            )
        estimate = sum(pair.estimate for pair in pair_results) / pairs
        estimates.append(
            StageEstimate(
                name=name,
                physical=physical[name],
                wall=wall,
                estimate=estimate,
                error=estimate - physical[name],
                pairs=tuple(pair_results),
            )
        )
    return tuple(estimates)


def legacy_magnitude_pair(
    target: float,
    *,
    wall: float = 0.0,
    offset: float = 0.0,
    noise_plus: float = 0.0,
    noise_minus: float = 0.0,
    step: float | None = 1.0,
    tie: str = "away",
) -> PairDecision:
    """Legacy two-magnitude abstraction with a hard zero boundary.

    Converting each direction to a nonnegative residual magnitude rectifies
    comparator/noise excursions around zero.  The returned D- is signed only
    after that rectification, exposing why a nominal zero residual can acquire
    a positive mean and then propagate through a recursive wall.
    """

    residual = target - wall
    q_plus = max(0.0, quantize_signed(residual + offset + noise_plus, step, tie=tie))
    q_minus_mag = max(0.0, quantize_signed(residual - offset + noise_minus, step, tie=tie))
    d_plus = wall + q_plus
    d_minus = -wall - q_minus_mag
    estimate = (d_plus - d_minus) / 2.0
    return PairDecision(
        target=float(target), wall=float(wall), residual=float(residual),
        d_plus=float(d_plus), d_minus=float(d_minus), estimate=float(estimate),
        offset=float(offset), noise_plus=float(noise_plus), noise_minus=float(noise_minus),
    )


def calibrate_legacy_magnitude_recursive(
    physical_weights: Mapping[str, float] | None = None,
    *,
    pairs: int = 1,
    step: float | None = 1.0,
    tie: str = "away",
    offset: float = 0.0,
    noise_source: Callable[[str, int, str], float] | None = None,
) -> tuple[StageEstimate, ...]:
    """Low-to-high legacy magnitude recursion used for controlled A/B tests."""

    if pairs <= 0:
        raise ValueError("pairs must be positive")
    physical = dict(NOMINAL_STAGES)
    if physical_weights is not None:
        physical.update({k: float(v) for k, v in physical_weights.items()})
    estimates: list[StageEstimate] = []
    for name, _ in NOMINAL_STAGES:
        wall = sum(stage.estimate for stage in estimates)
        pair_results: list[PairDecision] = []
        for index in range(pairs):
            n_plus = 0.0 if noise_source is None else float(noise_source(name, index, "+"))
            n_minus = 0.0 if noise_source is None else float(noise_source(name, index, "-"))
            pair_results.append(
                legacy_magnitude_pair(
                    physical[name], wall=wall, offset=offset,
                    noise_plus=n_plus, noise_minus=n_minus, step=step, tie=tie,
                )
            )
        estimate = sum(pair.estimate for pair in pair_results) / pairs
        estimates.append(
            StageEstimate(name, physical[name], wall, estimate,
                          estimate - physical[name], tuple(pair_results))
        )
    return tuple(estimates)


def calibrate_legacy_replay(
    h1r_pair_estimates: Sequence[float],
    *,
    h1a_pair_estimates: Sequence[float] | None = None,
    physical_weights: Mapping[str, float] | None = None,
) -> tuple[StageEstimate, ...]:
    """Replay the observed unipolar recursive failure without hiding its origin.

    H1C-A and H1C-R may be taken from actual pair half-differences parsed from
    the Spectre log. Later stages use the legacy
    nonnegative-residual limitation: when the recursive wall already exceeds
    the physical target, the search cannot subtract the excess and returns the
    wall.  This exactly captures the measured geometric propagation mechanism.
    """

    if not h1r_pair_estimates:
        raise ValueError("at least one H1C-R pair estimate is required")
    physical = dict(NOMINAL_STAGES)
    if physical_weights is not None:
        physical.update({k: float(v) for k, v in physical_weights.items()})
    h1a_values = (
        tuple(float(value) for value in h1a_pair_estimates)
        if h1a_pair_estimates is not None
        else (physical["H1C-A"],)
    )
    if not h1a_values:
        raise ValueError("at least one H1C-A pair estimate is required")
    out: list[StageEstimate] = []
    h1a_pairs = tuple(
        PairDecision(physical["H1C-A"], 0.0, physical["H1C-A"], value, -value, value, 0.0, 0.0, 0.0)
        for value in h1a_values
    )
    h1a_estimate = sum(h1a_values) / len(h1a_values)
    out.append(
        StageEstimate(
            "H1C-A", physical["H1C-A"], 0.0, h1a_estimate,
            h1a_estimate - physical["H1C-A"], h1a_pairs,
        )
    )
    wall = out[0].estimate
    h1r_pairs = tuple(
        PairDecision(physical["H1C-R"], wall, physical["H1C-R"] - wall, value, -value, value, 0.0, 0.0, 0.0)
        for value in h1r_pair_estimates
    )
    h1r_estimate = sum(h1r_pair_estimates) / len(h1r_pair_estimates)
    out.append(StageEstimate("H1C-R", physical["H1C-R"], wall, h1r_estimate, h1r_estimate - physical["H1C-R"], h1r_pairs))
    for name, _ in NOMINAL_STAGES[2:]:
        wall = sum(stage.estimate for stage in out)
        residual = physical[name] - wall
        estimate = wall + max(residual, 0.0)
        pair = PairDecision(physical[name], wall, residual, estimate, -estimate, estimate, 0.0, 0.0, 0.0)
        out.append(StageEstimate(name, physical[name], wall, estimate, estimate - physical[name], (pair,)))
    return tuple(out)


def estimates_by_name(stages: Iterable[StageEstimate]) -> dict[str, float]:
    return {stage.name: stage.estimate for stage in stages}
