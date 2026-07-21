"""Parsers for immutable external Spectre evidence."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re
from typing import Iterable


HEADER = re.compile(r"CAL PAIR target=(?P<target>\d+) pair=(?P<pair>\d+)")
VALUES = re.compile(
    r"DPLUS=(?P<dplus>[+-]?(?:\d+(?:\.\d*)?|\.\d+))\s+"
    r"DMINUS=(?P<dminus>[+-]?(?:\d+(?:\.\d*)?|\.\d+))\s+"
    r"DIFF=(?P<diff>[+-]?(?:\d+(?:\.\d*)?|\.\d+))"
)

# The historical log prints DPLUS/DMINUS to three decimals.  DIFF is computed
# internally before those fields are rounded, so a 0.001 LSB discrepancy is
# legitimate; anything larger is internally inconsistent evidence.
PRINTED_DIFF_ABS_TOLERANCE = 1.1e-3


class EvidenceFormatError(ValueError):
    """The immutable evidence is incomplete, duplicated, or inconsistent."""


@dataclass(frozen=True)
class ParsedPair:
    target: int
    pair: int
    d_plus: float
    d_minus: float
    diff: float

    @property
    def estimate(self) -> float:
        return self.diff / 2.0


def parse_cal_pairs(
    path: str | Path,
    *,
    expected_targets: Iterable[int] | None = None,
    expected_pairs_per_target: int | None = None,
) -> tuple[ParsedPair, ...]:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    parsed: list[ParsedPair] = []
    pending: tuple[int, int] | None = None
    for line in lines:
        header = HEADER.search(line)
        if header:
            pending = (int(header.group("target")), int(header.group("pair")))
            values = VALUES.search(line)
            if values:
                parsed.append(_build(pending, values))
                pending = None
            continue
        if pending is not None:
            values = VALUES.search(line)
            if values:
                parsed.append(_build(pending, values))
                pending = None
    result = tuple(parsed)
    if expected_targets is not None or expected_pairs_per_target is not None:
        if expected_targets is None or expected_pairs_per_target is None:
            raise ValueError("expected_targets and expected_pairs_per_target must be specified together")
        validate_pair_coverage(result, expected_targets, expected_pairs_per_target)
    return result


def validate_pair_coverage(
    pairs: Iterable[ParsedPair], expected_targets: Iterable[int], expected_pairs_per_target: int
) -> None:
    """Require one and only one record for every expected (target, pair) key."""

    if expected_pairs_per_target <= 0:
        raise ValueError("expected_pairs_per_target must be positive")
    records = tuple(pairs)
    keys = [(pair.target, pair.pair) for pair in records]
    if len(keys) != len(set(keys)):
        raise EvidenceFormatError("duplicate CAL PAIR target/pair key")
    expected = {
        (int(target), pair_id)
        for target in expected_targets
        for pair_id in range(expected_pairs_per_target)
    }
    actual = set(keys)
    if actual != expected:
        missing = sorted(expected - actual)[:8]
        unexpected = sorted(actual - expected)[:8]
        raise EvidenceFormatError(
            f"CAL PAIR coverage mismatch: missing={missing}, unexpected={unexpected}"
        )


def _build(header: tuple[int, int], values: re.Match[str]) -> ParsedPair:
    d_plus = float(values.group("dplus"))
    d_minus = float(values.group("dminus"))
    diff = float(values.group("diff"))
    if not all(math.isfinite(value) for value in (d_plus, d_minus, diff)):
        raise EvidenceFormatError("non-finite CAL PAIR value")
    if not math.isclose(
        diff, d_plus - d_minus, rel_tol=0.0, abs_tol=PRINTED_DIFF_ABS_TOLERANCE
    ):
        raise EvidenceFormatError(
            f"DIFF mismatch for target={header[0]} pair={header[1]}: "
            f"logged={diff}, d_plus-d_minus={d_plus - d_minus}"
        )
    return ParsedPair(
        target=header[0],
        pair=header[1],
        d_plus=d_plus,
        d_minus=d_minus,
        diff=diff,
    )
