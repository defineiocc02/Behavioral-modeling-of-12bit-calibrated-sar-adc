"""Exact deterministic decision-tree audit for the active SAR conversion path.

Unlike per-code bisection, this module does not assume that the decoded output
is monotonic.  For a fixed SAR decision prefix the comparator residue is affine
in differential input, so each prefix partitions one input interval at most
once.  Recursing over those physical comparator partitions enumerates every
reachable final decision word and its input interval.

This is a behavioral L2 static verifier.  Comparator noise, metastability,
settling error and transistor-level parasitics require separate robustness
verification.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from python_cal.decode.sar_decoder import SARDecoder
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.topology.cdac_topology import N_STAGES, VCM
from python_cal.topology.switching_policy import DifferentialSwitchingPolicy


@dataclass(frozen=True)
class ReachableLeaf:
    """One reachable final decision word and its open input interval."""

    v_lo: float
    v_hi: float
    decisions: tuple[int, ...]

    @property
    def width_v(self) -> float:
        return self.v_hi - self.v_lo


def _trial_vdiff(
    cdac: DifferentialCDAC,
    policy: DifferentialSwitchingPolicy,
    prefix: tuple[int, ...],
    vin_diff: float,
) -> float:
    """Evaluate the next comparator input for one valid decision prefix."""

    vinp = VCM + vin_diff / 2.0
    vinn = VCM - vin_diff / 2.0
    cdac.sample(vinp, vinn, policy.sampling_state(vinp, vinn), VCM)
    committed = policy.reset_state()
    cdac.apply_switch_state(committed)

    for stage, decision in enumerate(prefix):
        trial = policy.trial_state(stage, committed)
        committed = policy.commit_state(
            stage,
            committed,
            trial,
            comparator_output=decision,
        )
        cdac.apply_switch_state(committed)

    stage = len(prefix)
    trial = policy.trial_state(stage, committed)
    cdac.apply_switch_state(trial)
    return float(cdac.solve_current().differential_input)


def enumerate_reachable_leaves(
    cdac: DifferentialCDAC,
    *,
    v_lo: float = -2.0,
    v_hi: float = 2.0,
    root_tol_v: float = 1e-13,
) -> list[ReachableLeaf]:
    """Enumerate all deterministic final decision intervals.

    The returned leaves are sorted by input voltage and cover ``[v_lo, v_hi]``
    up to floating-point boundary tolerance.
    """

    if not np.isfinite(v_lo) or not np.isfinite(v_hi) or v_lo >= v_hi:
        raise ValueError("require finite v_lo < v_hi")
    policy = DifferentialSwitchingPolicy()
    leaves: list[ReachableLeaf] = []

    def walk(prefix: tuple[int, ...], lo: float, hi: float) -> None:
        if len(prefix) == N_STAGES:
            leaves.append(ReachableLeaf(lo, hi, prefix))
            return

        span = hi - lo
        inset = min(max(span * 1e-10, root_tol_v), span * 0.25)
        x_lo = lo + inset
        x_hi = hi - inset
        f_lo = _trial_vdiff(cdac, policy, prefix, x_lo)
        f_hi = _trial_vdiff(cdac, policy, prefix, x_hi)

        slope = (f_hi - f_lo) / (x_hi - x_lo)
        if abs(slope) < 1e-18:
            mid = 0.5 * (lo + hi)
            decision = int(
                _trial_vdiff(cdac, policy, prefix, mid) > 0.0
            )
            walk(prefix + (decision,), lo, hi)
            return

        root = x_lo - f_lo / slope
        if root <= lo + root_tol_v or root >= hi - root_tol_v:
            mid = 0.5 * (lo + hi)
            decision = int(
                _trial_vdiff(cdac, policy, prefix, mid) > 0.0
            )
            walk(prefix + (decision,), lo, hi)
            return

        left_mid = 0.5 * (lo + root)
        right_mid = 0.5 * (root + hi)
        left_decision = int(
            _trial_vdiff(cdac, policy, prefix, left_mid) > 0.0
        )
        right_decision = int(
            _trial_vdiff(cdac, policy, prefix, right_mid) > 0.0
        )
        if left_decision == right_decision:
            # A numerical root outside the valid prefix region must not invent
            # an unreachable branch.
            walk(prefix + (left_decision,), lo, hi)
            return
        walk(prefix + (left_decision,), lo, root)
        walk(prefix + (right_decision,), root, hi)

    walk((), float(v_lo), float(v_hi))
    leaves.sort(key=lambda leaf: leaf.v_lo)
    return leaves


def audit_reachable_codebook(
    cdac: DifferentialCDAC,
    decoder: SARDecoder,
    *,
    v_lo: float = -2.0,
    v_hi: float = 2.0,
    leaves: list[ReachableLeaf] | None = None,
) -> dict:
    """Audit monotonicity and missing integer output codes without assumptions."""

    if leaves is None:
        leaves = enumerate_reachable_leaves(cdac, v_lo=v_lo, v_hi=v_hi)
    codes_float = np.array(
        [decoder.decode_float(leaf.decisions) for leaf in leaves],
        dtype=np.float64,
    )
    codes_int = np.array(
        [decoder.decode(leaf.decisions) for leaf in leaves],
        dtype=np.int32,
    )
    float_steps = np.diff(codes_float)
    int_steps = np.diff(codes_int)
    prior_float_max = np.maximum.accumulate(codes_float)
    prior_integer_max = np.maximum.accumulate(codes_int)
    float_violation = codes_float < prior_float_max - 1e-12
    integer_violation = codes_int < prior_integer_max
    interval_widths = np.asarray(
        [leaf.width_v for leaf in leaves],
        dtype=np.float64,
    )
    input_span = float(leaves[-1].v_hi - leaves[0].v_lo)

    represented = np.zeros(decoder.max_code + 1, dtype=bool)
    represented[np.clip(codes_int, 0, decoder.max_code)] = True
    missing = np.flatnonzero(~represented)
    backstep_idx = np.flatnonzero(float_steps < -1e-12)

    result = {
        "method": "exact reachable decision-tree partition",
        "v_lo": float(v_lo),
        "v_hi": float(v_hi),
        "n_reachable_leaves": len(leaves),
        "n_unique_integer_codes": int(np.count_nonzero(represented)),
        "n_missing_codes": int(len(missing)),
        "missing_codes": missing[:32].astype(int).tolist(),
        "n_float_backsteps": int(len(backstep_idx)),
        "worst_float_step_lsb": (
            float(np.min(float_steps)) if len(float_steps) else 0.0
        ),
        "n_integer_backsteps": int(np.count_nonzero(int_steps < 0)),
        "max_float_rollback_lsb": float(
            np.max(prior_float_max - codes_float)
        ),
        "max_integer_rollback_lsb": int(
            np.max(prior_integer_max - codes_int)
        ),
        "float_nonmonotonic_input_fraction": float(
            np.sum(interval_widths[float_violation]) / input_span
        ),
        "integer_nonmonotonic_input_fraction": float(
            np.sum(interval_widths[integer_violation]) / input_span
        ),
        "max_integer_jump": (
            int(np.max(int_steps)) if len(int_steps) else 0
        ),
        "backstep_examples": [
            {
                "leaf_index": int(index),
                "v_boundary": float(leaves[index].v_hi),
                "code_before": float(codes_float[index]),
                "code_after": float(codes_float[index + 1]),
                "step_lsb": float(float_steps[index]),
                "decisions_before": list(leaves[index].decisions),
                "decisions_after": list(leaves[index + 1].decisions),
            }
            for index in backstep_idx[:16]
        ],
    }
    if result["n_missing_codes"] == 0:
        result.update(
            _histogram_linearity(leaves, codes_int, decoder.max_code)
        )
    else:
        result.update({
            "dnl_peak_lsb": None,
            "dnl_rms_lsb": None,
            "inl_peak_lsb": None,
            "inl_rms_lsb": None,
            "linearity_note": (
                "undefined until missing codes and integer backsteps are zero"
            ),
        })
    return result


def _histogram_linearity(
    leaves: list[ReachableLeaf],
    codes: np.ndarray,
    max_code: int,
) -> dict:
    """Exact code-density DNL/INL from reachable interval widths.

    A redundant SAR may give one integer code several disjoint input
    intervals.  Summing those widths is the deterministic limit of the
    slow-ramp histogram method used for measured DNL/INL.  Saturated end bins
    are excluded.  Formal local backsteps remain reported separately and are
    never hidden by this metric.
    """

    widths = np.zeros(max_code + 1, dtype=np.float64)
    for leaf, code in zip(leaves, codes):
        widths[int(code)] += leaf.width_v
    internal = widths[1:max_code]
    ideal_lsb = float(np.mean(internal))
    if ideal_lsb <= 0.0:
        raise RuntimeError("non-positive internal code width")
    dnl = internal / ideal_lsb - 1.0
    inl = np.cumsum(dnl)
    # Endpoint removal suppresses numerical accumulation at the final bin.
    inl -= np.linspace(inl[0], inl[-1], len(inl))
    return {
        "dnl_peak_lsb": float(np.max(np.abs(dnl))),
        "dnl_rms_lsb": float(np.sqrt(np.mean(dnl ** 2))),
        "inl_peak_lsb": float(np.max(np.abs(inl))),
        "inl_rms_lsb": float(np.sqrt(np.mean(inl ** 2))),
        "linearity_note": (
            "exact reachable code-density widths; saturated end bins "
            "excluded; formal local backsteps reported separately"
        ),
    }
