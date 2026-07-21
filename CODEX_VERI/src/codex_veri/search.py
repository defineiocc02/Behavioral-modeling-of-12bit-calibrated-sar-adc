"""Explicit trial/terminal policy model for directed boundary tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class TrialStep:
    weight: float
    before: float
    trial: float
    decision: str


@dataclass(frozen=True)
class SearchTrace:
    target: float
    accepted: float
    output: float
    exact_trial: bool
    terminal_reached: bool
    terminal_zero: bool
    terminal_one: int
    steps: tuple[TrialStep, ...]


def magnitude_search(
    target: float,
    trial_weights: Sequence[float],
    *,
    terminal_tie: str = "lower",
    exact_trial_stop: bool = True,
) -> SearchTrace:
    """Search a nonnegative magnitude with explicit exact and terminal paths.

    The terminal is a digital 1-LSB append decision, not a paper-defined Huang
    operation.  This model exists to test the project's implementation policy.
    """
    if target < 0:
        raise ValueError("magnitude target must be nonnegative")
    if terminal_tie not in {"lower", "upper"}:
        raise ValueError("terminal_tie must be lower or upper")
    accepted = 0.0
    steps: list[TrialStep] = []
    eps = 1e-12
    for weight in trial_weights:
        trial = accepted + float(weight)
        if abs(target - trial) <= eps:
            steps.append(TrialStep(float(weight), accepted, trial, "exact"))
            accepted = trial
            if exact_trial_stop:
                return SearchTrace(target, accepted, accepted, True, False, False, 0, tuple(steps))
        elif target > trial:
            steps.append(TrialStep(float(weight), accepted, trial, "keep"))
            accepted = trial
        else:
            steps.append(TrialStep(float(weight), accepted, trial, "discard"))

    residual = target - accepted
    terminal_zero = abs(residual) <= eps
    if terminal_zero:
        terminal_one = 1 if terminal_tie == "upper" else 0
    else:
        terminal_one = 1 if residual > 0 else 0
    return SearchTrace(
        target=target,
        accepted=accepted,
        output=accepted + terminal_one,
        exact_trial=False,
        terminal_reached=True,
        terminal_zero=terminal_zero,
        terminal_one=terminal_one,
        steps=tuple(steps),
    )


def signed_search(value: float, trial_weights: Sequence[float], **kwargs: object) -> SearchTrace:
    trace = magnitude_search(abs(value), trial_weights, **kwargs)
    if value >= 0:
        return trace
    return SearchTrace(
        target=value,
        accepted=-trace.accepted,
        output=-trace.output,
        exact_trial=trace.exact_trial,
        terminal_reached=trace.terminal_reached,
        terminal_zero=trace.terminal_zero,
        terminal_one=trace.terminal_one,
        steps=trace.steps,
    )
