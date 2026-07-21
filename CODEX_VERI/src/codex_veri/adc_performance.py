"""Independent physical/decoder model and ADC performance measurements.

The physical CDAC weights create SAR decisions.  Decoder weights are applied
only after those decisions have been frozen.  Keeping the two vectors separate
prevents the tautological error where a calibrated vector is used as its own
physical truth.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

import numpy as np


N_BITS = 12
MAX_CODE = (1 << N_BITS) - 1
NOMINAL_WEIGHTS = np.asarray(
    [2080, 1040, 520, 260, 130, 65, 65, 64, 32, 16, 8, 4, 2, 1],
    dtype=float,
)
SIGNAL_INDICES = np.asarray([0, 1, 2, 3, 4, 6], dtype=int)
HIGH_STAGE_TO_INDEX = {
    "H1C-A": 6,
    "H1C-R": 5,
    "H2C": 4,
    "H4C": 3,
    "H8C": 2,
    "H16C": 1,
    "H32C": 0,
}


@dataclass(frozen=True)
class DynamicMetrics:
    sndr_db: float
    enob: float
    sfdr_db: float
    thd_db: float
    time_domain_sndr_db: float
    clip_count: int
    fundamental_bin: int
    sample_count: int


@dataclass(frozen=True)
class StaticMetrics:
    monotonic_violations: int
    worst_code_backstep: int
    missing_codes: int
    dnl_min_lsb: float
    dnl_max_lsb: float
    inl_peak_lsb: float
    offset_error_lsb: float
    gain_error_lsb: float


def auxiliary_indices(weight_count: int) -> np.ndarray:
    if weight_count < len(NOMINAL_WEIGHTS):
        raise ValueError("weight vector is shorter than the active 14 decisions")
    return np.asarray([i for i in range(weight_count) if i not in set(SIGNAL_INDICES)], dtype=int)


def validate_weights(weights: Sequence[float]) -> np.ndarray:
    out = np.asarray(weights, dtype=float)
    if out.ndim != 1 or len(out) < len(NOMINAL_WEIGHTS):
        raise ValueError("weights must be a one-dimensional vector with at least 14 entries")
    if not np.all(np.isfinite(out)) or np.any(out <= 0.0):
        raise ValueError("all weights must be positive and finite")
    return out


def generate_split_cdac_weights(
    rng: np.random.Generator,
    *,
    sigma_unit_relative: float = 0.01,
    clip_sigma: float = 3.0,
    fractional_decisions: Sequence[float] = (),
) -> np.ndarray:
    """Generate differential effective weights from the Verilog-A unit model.

    Each N*Cu element is the sum of N independently mismatched unit caps on
    each differential side.  Bridge mismatch changes the high/low ratio.
    Returned weights use the same nominal-LSB coordinates as NOMINAL_WEIGHTS.
    Fractional decisions are architectural extensions and are not capacitor
    mismatched by this model.
    """

    if sigma_unit_relative < 0.0 or clip_sigma <= 0.0:
        raise ValueError("invalid mismatch parameters")

    def units(count: int) -> float:
        z = rng.normal(0.0, sigma_unit_relative, count)
        z = np.clip(z, -clip_sigma * sigma_unit_relative, clip_sigma * sigma_unit_relative)
        return float(np.sum(1.0 + z))

    side_vectors: list[np.ndarray] = []
    for _ in range(2):
        low = np.asarray([units(n) for n in (1, 2, 4, 8, 16, 32)], dtype=float)
        bridge = units(2)
        high = np.asarray([units(n) for n in (1, 1, 2, 4, 8, 16, 32)], dtype=float)
        high_gain = 2.0 * (float(np.sum(low)) + bridge) / bridge
        # Conversion order is high descending, low descending, terminal.
        side_vectors.append(np.concatenate((high[::-1] * high_gain, low[::-1] * 2.0, [1.0])))
    physical = 0.5 * (side_vectors[0] + side_vectors[1])
    if fractional_decisions:
        extra = np.asarray(tuple(fractional_decisions), dtype=float)
        if np.any(extra <= 0.0) or not np.all(np.isfinite(extra)):
            raise ValueError("fractional decisions must be positive and finite")
        physical = np.concatenate((physical, extra))
    return physical


def coherent_sine(
    sample_count: int,
    tone_bin: int,
    *,
    amplitude_dbfs: float = -0.915,
    phase_rad: float = 0.123,
) -> np.ndarray:
    if sample_count <= 0 or sample_count % 2 or tone_bin <= 0 or tone_bin >= sample_count // 2:
        raise ValueError("invalid coherent record")
    if math.gcd(sample_count, tone_bin) != 1:
        raise ValueError("tone bin must be coprime with sample count")
    amplitude = 0.5 * 10.0 ** (amplitude_dbfs / 20.0)
    n = np.arange(sample_count, dtype=float)
    return 0.5 + amplitude * np.sin(2.0 * np.pi * tone_bin * n / sample_count + phase_rad)


def sar_decisions(
    normalized_input: Sequence[float],
    physical_weights: Sequence[float],
    *,
    input_noise_lsb: Sequence[float] | None = None,
) -> np.ndarray:
    """Run fixed-order compare-then-commit SAR decisions in physical space."""

    physical = validate_weights(physical_weights)
    x = np.asarray(normalized_input, dtype=float)
    if x.ndim != 1 or not np.all(np.isfinite(x)):
        raise ValueError("normalized_input must be a finite one-dimensional record")
    aux = auxiliary_indices(len(physical))
    target = x * float(np.sum(physical[SIGNAL_INDICES])) + 0.5 * float(np.sum(physical[aux]))
    if input_noise_lsb is not None:
        noise = np.asarray(input_noise_lsb, dtype=float)
        if noise.shape != x.shape or not np.all(np.isfinite(noise)):
            raise ValueError("input_noise_lsb must match the input record")
        target = target + noise * float(np.sum(physical[SIGNAL_INDICES])) / MAX_CODE
    accumulated = np.zeros_like(target)
    decisions = np.zeros((len(x), len(physical)), dtype=np.bool_)
    for index, weight in enumerate(physical):
        bit = accumulated + weight <= target
        decisions[:, index] = bit
        accumulated += bit * weight
    return decisions


def decode_decisions(
    decisions: np.ndarray,
    decoder_weights: Sequence[float],
    *,
    integer_output: bool = True,
) -> np.ndarray:
    decoder = validate_weights(decoder_weights)
    bits = np.asarray(decisions)
    if bits.ndim != 2 or bits.shape[1] != len(decoder):
        raise ValueError("decision matrix width and decoder vector do not match")
    aux = auxiliary_indices(len(decoder))
    signal_weight = float(np.sum(decoder[SIGNAL_INDICES]))
    centered = bits.astype(float) @ decoder - 0.5 * float(np.sum(decoder[aux]))
    code = MAX_CODE * centered / signal_weight
    if integer_output:
        code = np.rint(code)
    return np.clip(code, 0.0, float(MAX_CODE))


def convert(
    normalized_input: Sequence[float],
    physical_weights: Sequence[float],
    decoder_weights: Sequence[float],
    *,
    input_noise_lsb: Sequence[float] | None = None,
    integer_output: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    decisions = sar_decisions(normalized_input, physical_weights, input_noise_lsb=input_noise_lsb)
    return decisions, decode_decisions(decisions, decoder_weights, integer_output=integer_output)


def pack_decisions(decisions: np.ndarray) -> np.ndarray:
    bits = np.asarray(decisions, dtype=np.bool_)
    if bits.ndim != 2 or bits.shape[1] > 31:
        raise ValueError("decision matrix must contain 1..31 columns")
    packed = np.zeros(bits.shape[0], dtype=np.uint32)
    for index in range(bits.shape[1]):
        packed |= bits[:, index].astype(np.uint32) << np.uint32(index)
    return packed


def build_monotonic_transition_lut(
    normalized_training_input: Sequence[float], decisions: np.ndarray
) -> np.ndarray:
    """Build a monotonic codeword LUT from an independent dense ramp.

    The LUT is an explicit second calibration layer.  It is not attributed to
    Huang's recursive weight estimator.  Each observed SAR decision interval
    is assigned the nearest ideal code at its input midpoint, then constrained
    to be monotonic in transition order.
    """

    x = np.asarray(normalized_training_input, dtype=float)
    packed = pack_decisions(decisions)
    if x.ndim != 1 or len(x) != len(packed) or np.any(np.diff(x) <= 0.0):
        raise ValueError("training input must be strictly increasing and match decisions")
    starts = np.concatenate(([0], np.flatnonzero(np.diff(packed) != 0) + 1))
    ends = np.concatenate((starts[1:], [len(packed)]))
    words = packed[starts]
    if len(np.unique(words)) != len(words):
        raise ValueError("a decision codeword occupies disjoint input intervals")
    midpoints = 0.5 * (x[starts] + x[ends - 1])
    mapped = np.clip(np.rint(midpoints * MAX_CODE), 0, MAX_CODE).astype(np.int16)
    mapped = np.maximum.accumulate(mapped)
    lut = np.full(1 << decisions.shape[1], -1, dtype=np.int16)
    lut[words] = mapped
    return lut


def decode_transition_lut(decisions: np.ndarray, lut: np.ndarray) -> np.ndarray:
    packed = pack_decisions(decisions)
    table = np.asarray(lut)
    if table.ndim != 1 or int(np.max(packed)) >= len(table):
        raise ValueError("invalid transition LUT")
    codes = table[packed]
    if np.any(codes < 0):
        raise ValueError("evaluation encountered an untrained decision codeword")
    return codes.astype(float)


def fractional_cancellation_codes(
    normalized_input: Sequence[float],
    physical_weights: Sequence[float],
    calibrated_weights: Sequence[float],
    *,
    input_noise_lsb: Sequence[float] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Behavioral oracle for analog fractional-part cancellation.

    The high-bit physical decisions are retained.  A fractional-value DAC is
    assumed to cancel their calibrated non-integer residue before the final
    integer-grid decisions.  Remaining error is therefore the high-weight
    estimation error, not a second independent 1-LSB requantization.  This is
    an architecture candidate inspired by fractional-value-capacitor DNL
    enhancement; it is deliberately separate from the existing VA path.
    """

    physical = validate_weights(physical_weights)
    calibrated = validate_weights(calibrated_weights)
    if len(physical) != len(NOMINAL_WEIGHTS) or len(calibrated) != len(NOMINAL_WEIGHTS):
        raise ValueError("fractional cancellation oracle currently targets the active 14-decision CDAC")
    x = np.asarray(normalized_input, dtype=float)
    noise = np.zeros_like(x) if input_noise_lsb is None else np.asarray(input_noise_lsb, dtype=float)
    if noise.shape != x.shape:
        raise ValueError("input noise must match input")
    decisions = sar_decisions(x, physical, input_noise_lsb=noise)
    high_error = decisions[:, :7].astype(float) @ (calibrated[:7] - physical[:7])
    high_error_lsb = high_error * MAX_CODE / float(np.sum(physical[SIGNAL_INDICES]))
    codes = np.floor(x * MAX_CODE + noise + high_error_lsb)
    return decisions, np.clip(codes, 0.0, float(MAX_CODE))


def build_context_transition_lut(
    normalized_training_input: Sequence[float],
    decisions: np.ndarray,
    raw_codes: Sequence[float],
    *,
    context_bits: int = 7,
) -> np.ndarray:
    """Train a monotonic LUT keyed by high-bit context and raw 12-bit code."""

    x = np.asarray(normalized_training_input, dtype=float)
    bits = np.asarray(decisions, dtype=np.bool_)
    codes = np.asarray(raw_codes, dtype=int)
    if (
        x.ndim != 1
        or bits.ndim != 2
        or len(x) != len(bits)
        or codes.shape != x.shape
        or context_bits <= 0
        or context_bits > bits.shape[1]
        or np.any(np.diff(x) <= 0.0)
        or np.any((codes < 0) | (codes > MAX_CODE))
    ):
        raise ValueError("invalid context-LUT training record")
    context = pack_decisions(bits[:, :context_bits]).astype(np.uint32)
    keys = (context << np.uint32(N_BITS)) | codes.astype(np.uint32)
    starts = np.concatenate(([0], np.flatnonzero(np.diff(keys) != 0) + 1))
    ends = np.concatenate((starts[1:], [len(keys)]))
    segment_keys = keys[starts]
    if len(np.unique(segment_keys)) != len(segment_keys):
        raise ValueError("a context/code key occupies disjoint input intervals")
    midpoint = 0.5 * (x[starts] + x[ends - 1])
    desired = np.clip(np.rint(midpoint * MAX_CODE), 0, MAX_CODE).astype(int)
    mapped = np.empty(len(desired), dtype=np.int16)
    previous = 0
    for index, value in enumerate(desired):
        lower = max(previous if index else 0, MAX_CODE - (len(desired) - 1 - index))
        upper = min(MAX_CODE, previous + 1 if index else 0)
        mapped[index] = int(np.clip(value, lower, upper))
        previous = int(mapped[index])
    lut = np.full(1 << (context_bits + N_BITS), -1, dtype=np.int16)
    lut[segment_keys] = mapped
    # Runtime noise can pair a trained high-bit context with an adjacent raw
    # code that a noiseless ramp did not visit.  Fill each observed context by
    # monotonic nearest/interpolated extension; no sine/evaluation data enter.
    contexts = segment_keys >> np.uint32(N_BITS)
    raw = segment_keys & np.uint32(MAX_CODE)
    for context in np.unique(contexts):
        selected = contexts == context
        raw_selected = raw[selected].astype(int)
        mapped_selected = mapped[selected].astype(float)
        order = np.argsort(raw_selected)
        filled = np.rint(
            np.interp(
                np.arange(MAX_CODE + 1),
                raw_selected[order],
                mapped_selected[order],
                left=mapped_selected[order][0],
                right=mapped_selected[order][-1],
            )
        ).astype(np.int16)
        start = int(context) << N_BITS
        lut[start : start + MAX_CODE + 1] = filled
    return lut


def decode_context_transition_lut(
    decisions: np.ndarray,
    raw_codes: Sequence[float],
    lut: np.ndarray,
    *,
    context_bits: int = 7,
) -> np.ndarray:
    bits = np.asarray(decisions, dtype=np.bool_)
    codes = np.asarray(raw_codes, dtype=int)
    if bits.ndim != 2 or codes.shape != (len(bits),):
        raise ValueError("invalid context-LUT evaluation record")
    context = pack_decisions(bits[:, :context_bits]).astype(np.uint32)
    keys = (context << np.uint32(N_BITS)) | codes.astype(np.uint32)
    table = np.asarray(lut)
    if int(np.max(keys)) >= len(table):
        raise ValueError("context-LUT key is out of range")
    corrected = table[keys]
    # Extremely narrow redundant contexts may be absent from a finite ramp.
    # Fall back to the already calibrated raw code for only those keys; this is
    # conservative and avoids inventing a correction from evaluation data.
    corrected = np.where(corrected < 0, codes, corrected)
    return corrected.astype(float)


def folded_harmonic_bin(harmonic: int, fundamental_bin: int, sample_count: int) -> int:
    residue = (harmonic * fundamental_bin) % sample_count
    return min(residue, sample_count - residue)


def dynamic_metrics(codes: Sequence[float], tone_bin: int, *, max_harmonic: int = 10) -> DynamicMetrics:
    y = np.asarray(codes, dtype=float)
    if y.ndim != 1 or len(y) % 2 or not np.all(np.isfinite(y)):
        raise ValueError("codes must be a finite, even-length record")
    n_samples = len(y)
    if tone_bin <= 0 or tone_bin >= n_samples // 2 or math.gcd(n_samples, tone_bin) != 1:
        raise ValueError("dynamic hard gate requires a coherent coprime tone bin")
    clip_count = int(np.count_nonzero((y <= 0.0) | (y >= MAX_CODE)))
    centered = y - float(np.mean(y))
    spectrum = np.fft.rfft(centered)
    power = np.abs(spectrum) ** 2
    if len(power) > 2:
        power[1:-1] *= 2.0
    fundamental = float(power[tone_bin])
    all_non_dc = float(np.sum(power[1:]))
    noise_and_distortion = all_non_dc - fundamental
    if fundamental <= 0.0 or noise_and_distortion <= 0.0:
        raise ValueError("degenerate spectrum")
    sndr_db = 10.0 * math.log10(fundamental / noise_and_distortion)

    spur_power = power.copy()
    spur_power[0] = 0.0
    spur_power[tone_bin] = 0.0
    sfdr_db = 10.0 * math.log10(fundamental / float(np.max(spur_power)))
    harmonic_bins = {
        folded_harmonic_bin(h, tone_bin, n_samples)
        for h in range(2, max_harmonic + 1)
    }
    harmonic_bins.discard(0)
    harmonic_bins.discard(tone_bin)
    harmonic_power = float(sum(power[index] for index in harmonic_bins))
    thd_db = -math.inf if harmonic_power == 0.0 else 10.0 * math.log10(harmonic_power / fundamental)

    sample_index = np.arange(n_samples, dtype=float)
    phase = 2.0 * np.pi * tone_bin * sample_index / n_samples
    sin_wave = np.sin(phase)
    cos_wave = np.cos(phase)
    dc = float(np.mean(y))
    sin_coefficient = 2.0 * float(np.dot(y, sin_wave)) / n_samples
    cos_coefficient = 2.0 * float(np.dot(y, cos_wave)) / n_samples
    fit = dc + sin_coefficient * sin_wave + cos_coefficient * cos_wave
    signal_power = float(np.mean((fit - np.mean(fit)) ** 2))
    residual_power = float(np.mean((y - fit) ** 2))
    time_sndr_db = 10.0 * math.log10(signal_power / residual_power)
    return DynamicMetrics(
        sndr_db=sndr_db,
        enob=(sndr_db - 1.76) / 6.02,
        sfdr_db=sfdr_db,
        thd_db=thd_db,
        time_domain_sndr_db=time_sndr_db,
        clip_count=clip_count,
        fundamental_bin=tone_bin,
        sample_count=n_samples,
    )


def static_metrics(codes: Sequence[float]) -> StaticMetrics:
    integer_codes = np.asarray(codes, dtype=int)
    if integer_codes.ndim != 1 or len(integer_codes) < 16 * (1 << N_BITS):
        raise ValueError("static ramp needs at least 16 samples per nominal code")
    steps = np.diff(integer_codes)
    counts = np.bincount(integer_codes, minlength=1 << N_BITS).astype(float)
    interior = counts[1:-1]
    mean_width = float(np.mean(interior))
    dnl = interior / mean_width - 1.0
    inl = np.cumsum(dnl)
    inl -= np.linspace(float(inl[0]), float(inl[-1]), len(inl))
    first = int(np.flatnonzero(integer_codes > 0)[0])
    last = int(np.flatnonzero(integer_codes < MAX_CODE)[-1])
    nominal_width = len(integer_codes) / (1 << N_BITS)
    return StaticMetrics(
        monotonic_violations=int(np.count_nonzero(steps < 0)),
        worst_code_backstep=int(min(0, int(np.min(steps)))),
        missing_codes=int(np.count_nonzero(interior == 0.0)),
        dnl_min_lsb=float(np.min(dnl)),
        dnl_max_lsb=float(np.max(dnl)),
        inl_peak_lsb=float(np.max(np.abs(inl))),
        offset_error_lsb=float(first / nominal_width - 0.5),
        gain_error_lsb=float((last - first + 1) / nominal_width - (MAX_CODE - 1)),
    )


def enob_to_sinad_db(enob: float) -> float:
    return 1.76 + 6.02 * enob
