from __future__ import annotations

import argparse
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an isolated full-ADC Spectre netlist variant.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cal-bypass", type=int, choices=(0, 1), required=True)
    parser.add_argument("--stop", default="25u")
    parser.add_argument("--save-raw", action="store_true")
    parser.add_argument(
        "--minimal-save",
        action="store_true",
        help="Save only calibration observability nodes to limit PSF size.",
    )
    parser.add_argument(
        "--fft-save",
        action="store_true",
        help="Save only OUT/SOUT and calibration status for dynamic testing.",
    )
    parser.add_argument("--va", help="Optional differential half-amplitude netlist value, e.g. 800m")
    parser.add_argument(
        "--noisefmin",
        help="Optional fixed transient-noise lower bound, e.g. 100k; use the same value for A/B.",
    )
    parser.add_argument(
        "--disable-tran-noise",
        action="store_true",
        help="Remove transient-noise controls while retaining the transistor-level comparator.",
    )
    parser.add_argument("--normalize-range", type=int, choices=(0, 1), default=1)
    parser.add_argument(
        "--avg-pairs-log2",
        type=int,
        choices=range(0, 9),
        default=0,
        help="Positive/negative calibration pair count as log2; 0 for behavioral, 5 for paper.",
    )
    args = parser.parse_args()
    if args.minimal_save and args.fft_save:
        parser.error("--minimal-save and --fft-save are mutually exclusive")

    source = args.source.resolve()
    output = args.output.resolve()
    text = source.read_text(encoding="utf-8", errors="strict")

    if args.va is not None:
        text, count = re.subn(r"\bva=[^ ]+", f"va={args.va}", text, count=1)
        if count != 1:
            raise RuntimeError("Expected exactly one va design parameter")

    if args.noisefmin is not None:
        text, count = re.subn(
            r"\bnoisefmin=[^\s]+",
            f"noisefmin={args.noisefmin}",
            text,
            count=1,
        )
        if count != 1:
            raise RuntimeError("Expected exactly one noisefmin transient parameter")

    if args.disable_tran_noise:
        if args.noisefmin is not None:
            parser.error("--disable-tran-noise and --noisefmin are mutually exclusive")
        text, count = re.subn(
            r"\b(?:noisefmax|noisefmin|noiseseed|noisescale)=[^\s]+[ \t]*",
            "",
            text,
        )
        if count != 4:
            raise RuntimeError(f"Expected four transient-noise controls, removed {count}")

    text, count = re.subn(r"CAL_BYPASS=\d+", f"CAL_BYPASS={args.cal_bypass}", text, count=1)
    if count != 1:
        raise RuntimeError("Expected exactly one CAL_BYPASS instance parameter")

    # Keep deprecated CDF parameters parse-compatible, but disable every
    # pre-Huang estimator hook in generated netlists.
    text, count = re.subn(
        r"UPDATE_DEADBAND_LSB=[^\s]+(?:[ \t]+HIGH_WEIGHT_UPDATE_DEADBAND_LSB=[^\s]+)?",
        "UPDATE_DEADBAND_LSB=0 HIGH_WEIGHT_UPDATE_DEADBAND_LSB=0",
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError("Expected exactly one UPDATE_DEADBAND_LSB instance parameter")
    text, count = re.subn(r"APPLY_BIN_MIDPOINT=[^\s]+", "APPLY_BIN_MIDPOINT=0", text, count=1)
    if count != 1:
        raise RuntimeError("Expected exactly one APPLY_BIN_MIDPOINT instance parameter")

    def set_or_insert_parameter(name: str, value: str, anchor: str) -> None:
        nonlocal text
        pattern = rf"{name}=[^\s]+"
        text, found = re.subn(pattern, f"{name}={value}", text, count=1)
        if found == 0:
            if anchor not in text:
                raise RuntimeError(f"Cannot insert {name}; anchor {anchor} was not found")
            text = text.replace(anchor, f"{anchor} {name}={value}", 1)

    set_or_insert_parameter("AUTO_BIN_MIDPOINT", "0", "APPLY_BIN_MIDPOINT=0")
    set_or_insert_parameter("FRAC_BITS", "6", "DEBUG=1")
    set_or_insert_parameter("AVG_PAIRS_LOG2", str(args.avg_pairs_log2), "FRAC_BITS=6")
    set_or_insert_parameter(
        "NORMALIZE_REDUNDANT_RANGE",
        str(args.normalize_range),
        "AUTO_BIN_MIDPOINT=0",
    )
    set_or_insert_parameter("REMOVE_REDUNDANCY_OFFSET", "1", "CAL_BYPASS=" + str(args.cal_bypass))

    text, count = re.subn(r"tran tran stop=[^ ]+", f"tran tran stop={args.stop}", text, count=1)
    if count != 1:
        raise RuntimeError("Expected exactly one transient analysis")

    old_switch = 'ahdl_include "/home/meow/jxy/12bit_50M_SAR/SWITCH_CAL/veriloga/veriloga.va"'
    old_decoder = 'ahdl_include "/home/meow/jxy/12bit_50M_SAR/DEC_CAL_PHY/veriloga/veriloga.va"'
    if old_switch not in text or old_decoder not in text:
        raise RuntimeError("Frozen AHDL include paths were not found")
    text = text.replace(old_switch, 'ahdl_include "SWITCH_CAL_original.va"', 1)
    text = text.replace(old_decoder, 'ahdl_include "DEC_CAL_PHY_FRAME_SYNC.va"', 1)

    if args.minimal_save:
        text, count = re.subn(
            r"^save CLK[\s\S]*?^saveOptions options",
            "save CLK COMN COMP RST1 P N CAL DONE ERR\nsaveOptions options",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise RuntimeError("Frozen multiline save statement was not found")
    elif args.fft_save:
        fft_nodes = ["OUT", "SOUT", "CAL", "DONE", "ERR"]
        if args.save_raw:
            fft_nodes += [f"BP\\<{index}\\>" for index in range(14)]
            fft_nodes += [f"Bit\\<{index}\\>" for index in range(12)]
        text, count = re.subn(
            r"^save CLK[\s\S]*?^saveOptions options",
            "save " + " ".join(fft_nodes) + "\nsaveOptions options",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise RuntimeError("Frozen multiline save statement was not found")
    else:
        save_anchor = "save CLK COMN COMP RST1 RST VIP CLK00 PRST OUT"
        if save_anchor not in text:
            raise RuntimeError("Frozen save statement was not found")
        save_replacement = "save CLK COMN COMP RST1 RST VIP CLK00 PRST OUT SOUT CAL DONE ERR"
        if args.save_raw:
            raw_nodes = [f"BP\\<{index}\\>" for index in range(14)]
            raw_nodes += [f"Bit\\<{index}\\>" for index in range(12)]
            save_replacement += " " + " ".join(raw_nodes)
        text = text.replace(save_anchor, save_replacement, 1)

    header = (
        f"// CODEX_SANDBOX_VARIANT cal_bypass={args.cal_bypass} stop={args.stop} "
        f"save_raw={int(args.save_raw)} minimal_save={int(args.minimal_save)} "
        f"fft_save={int(args.fft_save)} "
        f"va={args.va or 'frozen'} "
        f"normalize_range={args.normalize_range} "
        f"avg_pairs_log2={args.avg_pairs_log2} "
        f"tran_noise={'off' if args.disable_tran_noise else 'on'} "
        f"noisefmin={'disabled' if args.disable_tran_noise else (args.noisefmin or 'frozen')}\n"
        f"// FROZEN_SOURCE={source}\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(header + text, encoding="utf-8", newline="\n")
    print(output)


if __name__ == "__main__":
    main()
