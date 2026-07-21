from __future__ import annotations

import argparse
import json
import math
import random
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Capacitor:
    instance: str
    branch: str
    units: float


CAPACITORS = (
    Capacitor("C143", "C12_P", 16.0),
    Capacitor("C156", "C12_N", 16.0),
    Capacitor("C141", "C11_P", 8.0),
    Capacitor("C154", "C11_N", 8.0),
    Capacitor("C142", "C10_P", 4.0),
    Capacitor("C155", "C10_N", 4.0),
    Capacitor("C139", "C9_P", 2.0),
    Capacitor("C152", "C9_N", 2.0),
    Capacitor("C248", "CR_P", 2.0),
    Capacitor("C249", "CR_N", 2.0),
    Capacitor("C140", "C8_P", 1.0),
    Capacitor("C153", "C8_N", 1.0),
    Capacitor("C138", "C7_P", 24.0),
    Capacitor("C151", "C7_N", 24.0),
    Capacitor("C137", "C6_P", 16.0),
    Capacitor("C150", "C6_N", 16.0),
    Capacitor("C136", "C5_P", 10.0),
    Capacitor("C149", "C5_N", 10.0),
    Capacitor("C132", "C4_P", 6.0),
    Capacitor("C157", "C4_N", 6.0),
    Capacitor("C135", "C3_P", 4.0),
    Capacitor("C148", "C3_N", 4.0),
    Capacitor("C134", "C2_P", 2.0),
    Capacitor("C147", "C2_N", 2.0),
    Capacitor("C133", "C1_P", 1.0),
    Capacitor("C146", "C1_N", 1.0),
    Capacitor("C144", "BRIDGE_P", 1.0),
    Capacitor("C145", "BRIDGE_N", 1.0),
)

HIGH3_BRANCHES = {"C12_P", "C12_N", "C11_P", "C11_N", "C10_P", "C10_N"}
PAPER_KC_FRACTION_SQRT_FF = {
    "vertical": 0.0014,
    "lateral": 0.0020,
}


def cdac_bounds(text: str) -> tuple[int, int]:
    start_marker = "subckt CDAC_0716 "
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError("CDAC_0716 subcircuit was not found")
    end = text.find("ends CDAC_0716", start)
    if end < 0:
        raise RuntimeError("CDAC_0716 end statement was not found")
    return start, end


def replace_capacitor(cdac: str, capacitor: Capacitor, multiplier: float) -> str:
    pattern = re.compile(
        rf"^(\s*{re.escape(capacitor.instance)}\s+\([^\n]+\)\s+capacitor\s+c=)"
        rf"(?:[-+0-9.eE]+\*)?C[ \t]*$",
        flags=re.MULTILINE,
    )
    replacement = rf"\g<1>{multiplier:.9f}*C"
    updated, count = pattern.subn(replacement, cdac, count=1)
    if count != 1:
        raise RuntimeError(f"Expected one {capacitor.instance} capacitor, found {count}")
    return updated


def extract_multiplier(cdac: str, instance: str) -> float:
    match = re.search(
        rf"^\s*{re.escape(instance)}\s+\([^\n]+\)\s+capacitor\s+c="
        rf"(?:(?P<mult>[-+0-9.eE]+)\*)?C[ \t]*$",
        cdac,
        flags=re.MULTILINE,
    )
    if match is None:
        raise RuntimeError(f"Cannot read {instance} multiplier")
    return float(match.group("mult") or "1")


def summarize(multipliers: dict[str, float]) -> dict[str, float]:
    def average(p: str, n: str) -> float:
        return 0.5 * (multipliers[p] + multipliers[n])

    return {
        "c12_weight_lsb": 128.0 * average("C143", "C156"),
        "c11_weight_lsb": 128.0 * average("C141", "C154"),
        "c10_weight_lsb": 128.0 * average("C142", "C155"),
        "c9_weight_lsb": 128.0 * average("C139", "C152"),
        "cr_weight_lsb": 128.0 * average("C248", "C249"),
        "c8_weight_lsb": 128.0 * average("C140", "C153"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a deterministic CDAC mismatch campaign."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--unit-sigma",
        type=float,
        default=0.001,
        help="One-sigma relative mismatch of a 1C element; 0.001 is 0.1%%.",
    )
    parser.add_argument(
        "--scope",
        choices=("all", "high3"),
        default="all",
        help="Apply random mismatch to all listed CDAC capacitors or only C12/C11/C10.",
    )
    parser.add_argument(
        "--paper-model",
        choices=tuple(PAPER_KC_FRACTION_SQRT_FF),
        help="Use Omran TCSI 2016 Table II K_C instead of --unit-sigma.",
    )
    parser.add_argument(
        "--unit-cap-ff",
        type=float,
        default=4.0,
        help="Physical unit capacitance used with --paper-model.",
    )
    parser.add_argument(
        "--campaign-mode",
        choices=("sigma-sweep", "monte-carlo"),
        default="sigma-sweep",
        help="Sweep sigma multipliers or draw independent samples at the same sigma.",
    )
    parser.add_argument(
        "--sample-count",
        type=int,
        default=5,
        help="Number of independent samples in monte-carlo mode (default: 5).",
    )
    parser.add_argument(
        "--center",
        choices=("ideal", "source"),
        default="ideal",
        help="Center random mismatch on ideal unit counts or the actual source-netlist values.",
    )
    args = parser.parse_args()
    if args.unit_cap_ff <= 0:
        parser.error("--unit-cap-ff must be positive")

    paper_kc = (
        PAPER_KC_FRACTION_SQRT_FF[args.paper_model] if args.paper_model else None
    )
    unit_sigma = paper_kc / math.sqrt(args.unit_cap_ff) if paper_kc else args.unit_sigma

    source = args.source.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding="utf-8", errors="strict")
    start, end = cdac_bounds(text)
    base_cdac = text[start:end]
    source_multipliers = {
        capacitor.instance: extract_multiplier(base_cdac, capacitor.instance)
        for capacitor in CAPACITORS
    }

    scope_suffix = "" if args.scope == "all" else "_high3"
    model_suffix = f"_paper_{args.paper_model}" if args.paper_model else ""
    if args.campaign_mode == "monte-carlo":
        cases = [("case00_latest_fixed", None, None)] + [
            (f"sample{index:02d}{model_suffix}{scope_suffix}", 1.0, 7100 + index)
            for index in range(1, args.sample_count + 1)
        ]
    else:
        cases = [
            ("case00_latest_fixed", None, None),
            (f"case01_sigma01x{model_suffix}{scope_suffix}", 1.0, 7101),
            (f"case02_sigma03x{model_suffix}{scope_suffix}", 3.0, 7102),
            (f"case03_sigma06x{model_suffix}{scope_suffix}", 6.0, 7103),
            (f"case04_sigma09x{model_suffix}{scope_suffix}", 9.0, 7104),
            (f"case05_sigma12x{model_suffix}{scope_suffix}", 12.0, 7105),
        ]
    manifest: dict[str, object] = {
        "source": str(source),
        "unit_sigma_fraction": unit_sigma,
        "scope": args.scope,
        "campaign_mode": args.campaign_mode,
        "random_center": args.center,
        "paper_model": args.paper_model,
        "paper_reference": (
            "Omran et al., TCSI 2016, Table II and Eq. (6)" if args.paper_model else None
        ),
        "paper_kc_fraction_sqrt_ff": paper_kc,
        "unit_cap_ff": args.unit_cap_ff,
        "scaling_rule": "sigma(C_N)/C_N = scale * unit_sigma / sqrt(N)",
        "cases": [],
    }

    for case_name, scale, seed in cases:
        if scale is None:
            multipliers = dict(source_multipliers)
            injected_errors = {capacitor.instance: 0.0 for capacitor in CAPACITORS}
        else:
            rng = random.Random(seed)
            multipliers = {}
            injected_errors = {}
            for capacitor in CAPACITORS:
                if args.scope == "all" or capacitor.branch in HIGH3_BRANCHES:
                    sigma = scale * unit_sigma / math.sqrt(capacitor.units)
                    relative_error = rng.gauss(0.0, sigma)
                    center_units = (
                        source_multipliers[capacitor.instance]
                        if args.center == "source"
                        else capacitor.units
                    )
                    multipliers[capacitor.instance] = center_units * (1.0 + relative_error)
                    injected_errors[capacitor.instance] = relative_error
                else:
                    multipliers[capacitor.instance] = source_multipliers[capacitor.instance]
                    injected_errors[capacitor.instance] = 0.0

        case_cdac = base_cdac
        cap_records: list[dict[str, object]] = []
        for capacitor in CAPACITORS:
            multiplier = multipliers[capacitor.instance]
            case_cdac = replace_capacitor(case_cdac, capacitor, multiplier)
            cap_records.append(
                {
                    "instance": capacitor.instance,
                    "branch": capacitor.branch,
                    "nominal_units": capacitor.units,
                    "center_units": (
                        source_multipliers[capacitor.instance]
                        if args.center == "source" or scale is None
                        else capacitor.units
                    ),
                    "actual_units": multiplier,
                    "injected_relative_error": injected_errors[capacitor.instance],
                    "total_relative_error_vs_ideal": multiplier / capacitor.units - 1.0,
                    "relative_error": multiplier / capacitor.units - 1.0,
                }
            )

        case_text = text[:start] + case_cdac + text[end:]
        output = output_dir / f"{case_name}_source.scs"
        output.write_text(case_text, encoding="utf-8", newline="\n")
        manifest["cases"].append(
            {
                "name": case_name,
                "scale": scale,
                "seed": seed,
                "source_netlist": str(output),
                "capacitors": cap_records,
                "effective_weights": summarize(multipliers),
            }
        )

    manifest_path = output_dir / "mismatch_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(manifest_path)


if __name__ == "__main__":
    main()
