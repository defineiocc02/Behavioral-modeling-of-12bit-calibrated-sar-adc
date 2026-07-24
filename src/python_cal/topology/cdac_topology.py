"""Physical two-segment integer-capacitor CDAC topology."""

from dataclasses import dataclass, field

from python_cal import config as cfg
from .capacitor import Capacitor

CU = cfg.CU
VREF = cfg.VREF
VREFN_ = cfg.VREFN
VCM = cfg.VCM
N_STAGES = cfg.N_STAGES
N_PHYSICAL = cfg.N_PHYSICAL
N_BITS = cfg.N_BITS


@dataclass(frozen=True)
class CDACTopology:
    capacitors: tuple[Capacitor, ...]
    low_capacitors: tuple[Capacitor, ...] = field(init=False)
    bridge_capacitor: Capacitor = field(init=False)
    high_capacitors: tuple[Capacitor, ...] = field(init=False)
    c_low_total: float = field(init=False)
    c_high_total: float = field(init=False)
    c_bridge: float = field(init=False)

    def __post_init__(self):
        low = tuple(c for c in self.capacitors if c.name.startswith("low_"))
        high = tuple(c for c in self.capacitors if c.name.startswith("high_"))
        bridge = next(c for c in self.capacitors if c.name == "bridge")
        object.__setattr__(self, "low_capacitors", low)
        object.__setattr__(self, "high_capacitors", high)
        object.__setattr__(self, "bridge_capacitor", bridge)
        object.__setattr__(self, "c_low_total", sum(c.capacitance_f for c in low))
        object.__setattr__(self, "c_high_total", sum(c.capacitance_f for c in high))
        object.__setattr__(self, "c_bridge", bridge.capacitance_f)

    @property
    def total_capacitance(self) -> float:
        return self.c_low_total + self.c_bridge + self.c_high_total

    def get_cap_by_name(self, name: str) -> Capacitor:
        for capacitor in self.capacitors:
            if capacitor.name == name:
                return capacitor
        raise KeyError(f"Capacitor {name!r} not found")

    def get_cap_by_stage(self, stage: int) -> Capacitor | None:
        for capacitor in self.capacitors:
            if capacitor.stage == stage:
                return capacitor
        return None


CAP_ORDER = tuple(cfg.ALL_CAP_NAMES)
STAGE_MAP = {
    name: stage
    for stage, name in {
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
    }.items()
}
STAGE_MAP["bridge"] = None


def build_cdac_topology(
    side: str,
    mismatch: tuple[float, ...] | None = None,
    caps_override: dict | None = None,
) -> CDACTopology:
    """Build one side of the active 71-Cu/2-Cu/65-Cu CDAC."""

    top_node = f"VTOP_{side}"
    bridge_node = f"VBRIDGE_{side}"
    if caps_override is not None:
        cap_values = dict(caps_override)
    else:
        high_names = [
            "high_1c", "high_2c", "high_4c", "high_8c_a",
            "high_8c_r", "high_16c", "high_32c",
        ]
        factors = (1.0,) * len(high_names) if mismatch is None else mismatch
        if len(factors) != len(high_names):
            raise ValueError("high-segment mismatch must contain 7 factors")
        cap_values = {
            name: count * CU for name, count in cfg.CAP_NOMINAL_CU.items()
        }
        for name, factor in zip(high_names, factors):
            cap_values[name] *= float(factor)

    missing = set(CAP_ORDER).difference(cap_values)
    if missing:
        raise ValueError(f"caps_override missing {sorted(missing)}")

    capacitors = []
    for name in CAP_ORDER:
        capacitor_top = (
            bridge_node
            if name.startswith("low_") or name == "bridge"
            else top_node
        )
        capacitors.append(
            Capacitor(
                name=name,
                capacitance_f=float(cap_values[name]),
                top_node=capacitor_top,
                bottom_node=f"BOT_{side}_{name}",
                stage=STAGE_MAP[name],
            )
        )
    return CDACTopology(tuple(capacitors))


def build_differential_topology(md=None, mu=None, p_caps=None, n_caps=None):
    return (
        build_cdac_topology("P", mismatch=md, caps_override=p_caps),
        build_cdac_topology("N", mismatch=mu, caps_override=n_caps),
    )
