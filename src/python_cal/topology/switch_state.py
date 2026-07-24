"""Explicit bottom-plate switch state for every physical CDAC capacitor."""

from dataclasses import dataclass
from enum import Enum


class Rail(Enum):
    VREFP = "vrefp"
    VREFN = "vrefn"
    VCM = "vcm"
    VINP = "vinp"
    VINN = "vinn"
    FLOAT = "float"

    def voltage(self, vrefp=1.8, vrefn=0.0, vcm=0.9,
                vinp=0.9, vinn=0.9):
        return {
            Rail.VREFP: vrefp,
            Rail.VREFN: vrefn,
            Rail.VCM: vcm,
            Rail.VINP: vinp,
            Rail.VINN: vinn,
        }.get(self, 0.0)


@dataclass(frozen=True)
class SideSwitchState:
    low_1c: Rail = Rail.VCM
    low_2c_a: Rail = Rail.VCM
    low_2c_r: Rail = Rail.VCM
    low_4c: Rail = Rail.VCM
    low_8c: Rail = Rail.VCM
    low_16c: Rail = Rail.VCM
    low_32c: Rail = Rail.VCM

    high_1c: Rail = Rail.VCM
    high_2c: Rail = Rail.VCM
    high_4c: Rail = Rail.VCM
    high_8c_a: Rail = Rail.VCM
    high_8c_r: Rail = Rail.VCM
    high_16c: Rail = Rail.VCM
    high_32c: Rail = Rail.VCM

    STAGE_TO_FIELD = {
        0: "high_32c",
        1: "high_16c",
        2: "high_8c_a",
        3: "high_8c_r",
        4: "high_4c",
        5: "high_2c",
        6: "high_1c",
        7: "low_32c",
        8: "low_16c",
        9: "low_8c",
        10: "low_4c",
        11: "low_2c_a",
        12: "low_2c_r",
        13: "low_1c",
    }

    CAP_NAMES = [
        "low_1c", "low_2c_a", "low_2c_r", "low_4c",
        "low_8c", "low_16c", "low_32c",
        "high_1c", "high_2c", "high_4c", "high_8c_a",
        "high_8c_r", "high_16c", "high_32c",
    ]

    def get_rail(self, cap_name: str) -> Rail:
        return getattr(self, cap_name)

    def with_rail(self, cap_name: str, rail: Rail) -> "SideSwitchState":
        values = {name: getattr(self, name) for name in self.CAP_NAMES}
        values[cap_name] = rail
        return SideSwitchState(**values)

    @classmethod
    def all_vcm(cls):
        return cls()

    @classmethod
    def all_rail(cls, rail: Rail):
        return cls(**{name: rail for name in cls.CAP_NAMES})


@dataclass(frozen=True)
class DifferentialSwitchState:
    p_side: SideSwitchState = SideSwitchState()
    n_side: SideSwitchState = SideSwitchState()

    @classmethod
    def all_vcm(cls):
        return cls(SideSwitchState.all_vcm(), SideSwitchState.all_vcm())
