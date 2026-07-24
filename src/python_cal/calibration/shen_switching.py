"""Switch-state helpers owned exclusively by the active Shen calibration path.

This module intentionally contains no calDAC search, wall-state, or legacy
D+/D- helper. Stage 13 is absent because it is a comparator-only terminal
decision and therefore has no capacitor field.
"""

from __future__ import annotations

from python_cal.topology.switch_state import (
    DifferentialSwitchState,
    Rail,
    SideSwitchState,
)


STAGE_TO_CAP = {
    0: "high_32c",
    1: "high_16c",
    2: "high_8c",
    3: "high_4c",
    4: "high_2c",
    5: "high_1c_r",
    6: "high_1c_a",
    7: "low_32c",
    8: "low_16c",
    9: "low_8c",
    10: "low_4c",
    11: "low_2c",
    12: "low_1c",
}


def _require_physical_stage(stage: int) -> str:
    try:
        return STAGE_TO_CAP[stage]
    except KeyError as exc:
        if stage == 13:
            raise ValueError(
                "stage 13 is a digital terminal decision, not a capacitor"
            ) from exc
        raise ValueError(f"unknown physical SAR stage: {stage}") from exc


def build_force_p_state(stage: int, rail: Rail) -> DifferentialSwitchState:
    """Force one P-side target capacitor while keeping the N side at VCM."""
    if rail not in (Rail.VREFN, Rail.VREFP):
        raise ValueError("force rail must be VREFN or VREFP")
    cap_name = _require_physical_stage(stage)
    return DifferentialSwitchState(
        p_side=SideSwitchState.all_vcm().with_rail(cap_name, rail),
        n_side=SideSwitchState.all_vcm(),
    )


def build_force_n_state(stage: int, rail: Rail) -> DifferentialSwitchState:
    """Force one N-side target capacitor while keeping the P side at VCM."""
    if rail not in (Rail.VREFN, Rail.VREFP):
        raise ValueError("force rail must be VREFN or VREFP")
    cap_name = _require_physical_stage(stage)
    return DifferentialSwitchState(
        p_side=SideSwitchState.all_vcm(),
        n_side=SideSwitchState.all_vcm().with_rail(cap_name, rail),
    )
