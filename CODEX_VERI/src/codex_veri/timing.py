"""Counting oracle; it does not model analog time or claim completion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimingCount:
    targets: int
    pairs: int
    directions: int
    frames: int
    maximum_decisions: int
    frame_slot_time_us: float


def legacy_direct_count(pairs: int = 32, frame_period_ns: float = 150.0) -> TimingCount:
    frames = 7 * pairs * 2
    decisions = 2 * pairs * sum(range(7, 14))
    return TimingCount(7, pairs, 2, frames, decisions, frames * frame_period_ns / 1000.0)


def centered_candidate_count(pairs: int = 32, frame_period_ns: float = 150.0) -> TimingCount:
    frames = 7 * pairs * 2
    # Maximum path: one SIGN, six physical trials, one terminal decision.
    decisions = frames * 8
    return TimingCount(7, pairs, 2, frames, decisions, frames * frame_period_ns / 1000.0)
