from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_SUBCKTS = ("NOR1", "INVX2", "INVX3", "INVX1", "COM_IAZ", "CDAC_0716")


def extract_subckt(lines: list[str], name: str) -> list[str]:
    start = next(i for i, line in enumerate(lines) if line.startswith(f"subckt {name} "))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == f"ends {name}")
    return lines[start : end + 1]


def nodes(prefix: str, start: int, stop: int) -> str:
    return " ".join(f"{prefix}{index}" for index in range(start, stop + 1))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a real-CDAC/real-COM_IAZ Huang calibration testbench."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stop", default="39u")
    parser.add_argument("--noisefmin", default="100k")
    parser.add_argument("--noisescale", default="1")
    parser.add_argument("--disable-tran-noise", action="store_true")
    parser.add_argument(
        "--log-only-save",
        action="store_true",
        help="Save only CAL/DONE/ERR; calibration weights remain available in the Spectre log.",
    )
    parser.add_argument("--avg-pairs-log2", type=int, choices=range(0, 9), default=0)
    parser.add_argument(
        "--high-weight-deadband-lsb",
        type=float,
        default=0.0,
        help="Keep the nominal upper-bit weight when the Huang result is within this many LSB.",
    )
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    lines = source.read_text(encoding="utf-8", errors="strict").splitlines()
    parameter_lines = lines[8:13]
    include_lines = [line for line in lines if line.startswith("include ")]

    generated: list[str] = [
        "// Real frozen CDAC and COM_IAZ; Huang 64-conversion foreground calibration.",
        f"// Source: {source}",
        "simulator lang=spectre",
        "global 0",
        *parameter_lines,
        *include_lines,
        "",
    ]
    for name in REQUIRED_SUBCKTS:
        generated.extend(extract_subckt(lines, name))
        generated.append("")

    generated.extend(
        [
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
    )

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
            "XCOM (AGND AVDD CLK RST N P COMN COMP) COM_IAZ",
            f"XDEC ({' '.join(f'Bit{index}' for index in range(11, -1, -1))} {nodes('BP', 0, 13)} "
            f"DGND DVDD SOUT COMP COMN RST1 CAL_RST CLK_SAR CLK00 CLK "
            f"{nodes('BITD_CAL', 0, 12)} {nodes('BITU_CAL', 0, 12)} CAL DONE ERR CAL_CLK) DEC_CAL_PHY "
            "TD_CAL=200p TD_CMP_CAL=2n CMP_SWAP=1 CMP_VALID_FRACTION=0.2 MAX_INVALID=3 "
            "ZERO_ON_INVALID_PHASE0=1 ZERO_ON_INVALID_PHASE1=1 WEIGHT_TOL=0.25 "
            f"UPDATE_DEADBAND_LSB=0 HIGH_WEIGHT_UPDATE_DEADBAND_LSB={args.high_weight_deadband_lsb:g} "
            "APPLY_BIN_MIDPOINT=0 AUTO_BIN_MIDPOINT=0 REMOVE_REDUNDANCY_OFFSET=1 "
            f"DEBUG=1 FRAC_BITS=6 AVG_PAIRS_LOG2={args.avg_pairs_log2} CAL_BYPASS=0",
            (
                f"tran tran stop={args.stop} cmin=1.23364538742384a annotate=status"
                if args.disable_tran_noise
                else f"tran tran stop={args.stop} noisefmax=10G noisefmin={args.noisefmin} "
                f"noiseseed=3651246323 noisescale={args.noisescale} "
                "cmin=1.23364538742384a annotate=status"
            ),
            "save CAL DONE ERR" if args.log_only_save else "save CLK COMN COMP RST1 P N CAL DONE ERR",
            "saveOptions options save=selected currents=selected",
            'ahdl_include "/opt/cadence/IC618/tools/dfII/samples/artist/ahdlLib/not_gate/veriloga/veriloga.va"',
            'ahdl_include "SWITCH_CAL_original.va"',
            'ahdl_include "DEC_CAL_PHY_FRAME_SYNC.va"',
            "",
        ]
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(generated), encoding="utf-8", newline="\n")
    print(output)


if __name__ == "__main__":
    main()
