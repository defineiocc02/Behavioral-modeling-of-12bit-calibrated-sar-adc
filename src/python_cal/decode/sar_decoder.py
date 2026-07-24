"""Ordinary calibrated weighted-sum decoder.

There is no decision-word LUT, dynamic-programming remap, exception table, or
stateful monotonic clamp.  Calibration updates only the per-stage weights.
"""

from dataclasses import dataclass
import math

import numpy as np

from python_cal import config as cfg


@dataclass(frozen=True)
class DecodeResult:
    code: int
    code_float: float
    clip_low: bool
    clip_high: bool
    raw_sum: float


class SARDecoder:
    def __init__(
        self,
        weights_p=None,
        weights_n=None,
        max_code=(1 << cfg.N_BITS) - 1,
        weights=None,
    ):
        if weights is not None:
            if weights_p is not None or weights_n is not None:
                raise ValueError("use either weights or weights_p/weights_n")
            weights_p = weights
            weights_n = weights
        nominal = list(cfg.NOMINAL_WEIGHTS_Q0)
        self.weights_p = (
            list(weights_p) if weights_p is not None else nominal.copy()
        )
        self.weights_n = (
            list(weights_n) if weights_n is not None else nominal.copy()
        )
        if len(self.weights_p) != cfg.N_STAGES:
            raise ValueError(f"expected {cfg.N_STAGES} P-side weights")
        if len(self.weights_n) != cfg.N_STAGES:
            raise ValueError(f"expected {cfg.N_STAGES} N-side weights")
        self.max_code = int(max_code)
        self.signal_stages = list(cfg.SIGNAL_STAGES)
        self.aux_stages = list(cfg.AUX_STAGES)
        self.signal_p = sum(self.weights_p[i] for i in self.signal_stages)
        self.signal_n = sum(self.weights_n[i] for i in self.signal_stages)
        self.weights = [
            (wp + wn) / 2.0
            for wp, wn in zip(self.weights_p, self.weights_n)
        ]
        self.signal_weight = sum(
            self.weights[i] for i in self.signal_stages
        )
        self.aux_weight = sum(self.weights[i] for i in self.aux_stages)
        self.aux_offset = self.aux_weight / 2.0

    def update_weights(self, new_weights):
        self.__init__(
            weights_p=new_weights,
            weights_n=new_weights,
            max_code=self.max_code,
        )

    def update_weights_per_side(self, weights_p, weights_n):
        self.__init__(
            weights_p=weights_p,
            weights_n=weights_n,
            max_code=self.max_code,
        )

    def _decode_code_float(self, decisions) -> tuple[float, float]:
        if len(decisions) != cfg.N_STAGES:
            raise ValueError(
                f"expected {cfg.N_STAGES} decisions, got {len(decisions)}"
            )
        signed_sum = 0.0
        for decision, wp, wn in zip(
            decisions, self.weights_p, self.weights_n
        ):
            if decision == 0:
                signed_sum += wp
            elif decision == 1:
                signed_sum -= wn
            else:
                raise ValueError(f"decision must be 0 or 1, got {decision!r}")

        total_range = self.signal_p + self.signal_n
        if total_range <= 0.0:
            raise ValueError("decoder signal range must be positive")

        # P/N weight asymmetry creates a constant offset.  The physically
        # centered differential reconstruction uses half of the combined
        # signal range, not either side alone.
        center = total_range / 2.0
        code_float = (signed_sum + center) * self.max_code / total_range
        return float(code_float), float(signed_sum)

    def decode(self, decisions, clip=True) -> int:
        result = self.decode_detailed(decisions)
        return (
            max(0, min(self.max_code, result.code))
            if clip else result.code
        )

    def decode_float(self, decisions, clip=True) -> float:
        value, _ = self._decode_code_float(decisions)
        return (
            max(0.0, min(float(self.max_code), value))
            if clip else float(value)
        )

    def decode_q(self, decisions, fractional_bits=2, clip=True) -> int:
        if fractional_bits < 0:
            raise ValueError("fractional_bits must be non-negative")
        scale = 1 << fractional_bits
        value, _ = self._decode_code_float(decisions)
        code_q = int(math.floor(value * scale + 0.5))
        return (
            max(0, min(self.max_code * scale, code_q))
            if clip else code_q
        )

    def decode_fixed(self, decisions, fractional_bits=2, clip=True) -> float:
        scale = 1 << fractional_bits
        return self.decode_q(decisions, fractional_bits, clip) / scale

    def decode_detailed(self, decisions) -> DecodeResult:
        code_float, signed_sum = self._decode_code_float(decisions)
        code = int(math.floor(code_float + 0.5))
        return DecodeResult(
            code=code,
            code_float=code_float,
            clip_low=code < 0,
            clip_high=code > self.max_code,
            raw_sum=signed_sum,
        )

    def decode_batch(self, decisions_array):
        return np.asarray(
            [self.decode(list(decisions)) for decisions in decisions_array],
            dtype=np.int32,
        )
