from __future__ import annotations

import argparse
from pathlib import Path


def extract_subckt(lines: list[str], name: str) -> list[str]:
    start = next(i for i, line in enumerate(lines) if line.startswith(f"subckt {name} "))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == f"ends {name}")
    return lines[start : end + 1]


def nodes(prefix: str, start: int, stop: int) -> str:
    return " ".join(f"{prefix}{index}" for index in range(start, stop + 1))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build real-CDAC/ideal-comparator calibration testbench.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    lines = source.read_text(encoding="utf-8", errors="strict").splitlines()
    generated = [
        "// Real frozen CDAC and SWITCH with an ideal clocked comparator.",
        "simulator lang=spectre",
        "global 0",
        "parameters vdd=1.8 C=4f",
        "",
        *extract_subckt(lines, "CDAC_0716"),
        "",
        "VAGND (AGND 0) vsource dc=0 type=dc",
        "VDGND (DGND 0) vsource dc=0 type=dc",
        "VAVDD (AVDD AGND) vsource dc=vdd type=dc",
        "VDVDD (DVDD DGND) vsource dc=vdd type=dc",
        "VVCM (VCM AGND) vsource dc=vdd/2 type=dc",
        "VREFP_SRC (VREFP AGND) vsource dc=vdd type=dc",
        "VREFN_SRC (VREFN AGND) vsource dc=0 type=dc",
        "VVIP (VIP AGND) vsource dc=vdd/2 type=dc",
        "VVIN (VIN AGND) vsource dc=vdd/2 type=dc",
        "VRST (RST AGND) vsource type=pulse val0=0 val1=vdd period=100n delay=100p rise=10p fall=10p width=18n",
        "VRST1 (RST1 AGND) vsource type=pulse val0=0 val1=vdd period=100n delay=100p rise=10p fall=10p width=14n",
        "VCALRST (CAL_RST DGND) vsource type=pulse val0=0 val1=vdd period=150u delay=1n rise=10p fall=10p width=2n",
        "VCALCLK (CAL_CLK DGND) vsource type=pulse val0=0 val1=vdd period=10n delay=10p rise=10p fall=10p width=5n",
        "VSOUT (SOUT DGND) vsource dc=0 type=dc",
        "VCLKSAR (CLK_SAR DGND) vsource dc=0 type=dc",
        "VCLK00 (CLK00 DGND) vsource dc=0 type=dc",
    ]

    for index in range(14):
        generated.append(f"VBP{index} (BP{index} DGND) vsource dc=0 type=dc")
        generated.append(f"VBITN{index} (BITN{index} AGND) vsource dc=0 type=dc")
        generated.append(f"VBITP{index} (BITP{index} AGND) vsource dc=0 type=dc")
    for index in range(13):
        generated.append(f"VSET{index} (SET{index} AGND) vsource dc=0 type=dc")

    generated.extend(
        [
            "",
            f"XSW (AGND AVDD {nodes('BITD', 1, 13)} {nodes('BITN', 0, 13)} {nodes('BITP', 0, 13)} "
            f"{nodes('BITU', 1, 13)} N P RST RST1 {nodes('SET', 0, 12)} VCM VIN VIP VREFN VREFP "
            f"{nodes('BITD_CAL', 0, 12)} {nodes('BITU_CAL', 0, 12)} CAL CAL_CLK) SWITCH_CAL "
            "RON_SAMPLE=5 RON_REF=10 RON_TOP=5 ROFF=1e15 TD_RSTT=200p TD_RST11=200p NORMAL_REF_SWAP=1",
            f"XCDAC ({nodes('BITD', 1, 13)} {nodes('BITU', 1, 13)} N P) CDAC_0716",
            "XCOMP (CLK P N COMP COMN DGND DVDD) IDEAL_COMP",
            f"XDEC ({' '.join(f'Bit{index}' for index in range(11, -1, -1))} {nodes('BP', 0, 13)} "
            f"DGND DVDD SOUT COMP COMN RST1 CAL_RST CLK_SAR CLK00 CLK "
            f"{nodes('BITD_CAL', 0, 12)} {nodes('BITU_CAL', 0, 12)} CAL DONE ERR CAL_CLK) DEC_CAL_PHY "
            "TD_CAL=200p TD_CMP_CAL=2n CMP_SWAP=1 CMP_VALID_FRACTION=0.2 MAX_INVALID=3 "
            "ZERO_ON_INVALID_PHASE0=1 ZERO_ON_INVALID_PHASE1=1 WEIGHT_TOL=0.25 "
            "REMOVE_REDUNDANCY_OFFSET=1 DEBUG=1 FRAC_BITS=6 "
            "AVG_PAIRS_LOG2=0 CAL_BYPASS=0",
            "tran tran stop=1.3u maxstep=100p annotate=status",
            "save P N CLK CAL DONE ERR",
            "saveOptions options save=selected",
            'ahdl_include "SWITCH_CAL_original.va"',
            'ahdl_include "DEC_CAL_PHY_FRAME_SYNC.va"',
            'ahdl_include "IDEAL_COMP.va"',
            "",
        ]
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(generated), encoding="utf-8", newline="\n")
    print(output)


if __name__ == "__main__":
    main()
