from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_SUBCKTS = ("NOR1", "INVX2", "INVX3", "INVX1", "COM_IAZ")


def extract_subckt(lines: list[str], name: str) -> list[str]:
    start = next(i for i, line in enumerate(lines) if line.startswith(f"subckt {name} "))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == f"ends {name}")
    return lines[start : end + 1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a standalone COM_IAZ test from a frozen netlist.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    lines = source.read_text(encoding="utf-8", errors="strict").splitlines()
    parameter_lines = lines[8:13]
    include_lines = [line for line in lines if line.startswith("include ")]

    generated: list[str] = [
        "// Generated mechanically from the frozen Interactive.293 netlist.",
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
            "VSS (AGND 0) vsource dc=0 type=dc",
            "VDD (AVDD AGND) vsource dc=vdd type=dc",
            "VRST (RST AGND) vsource type=pulse val0=0 val1=vdd period=100n delay=100p rise=10p fall=10p width=18n",
            "VCLK (CLK AGND) vsource type=pulse val0=0 val1=vdd period=10n delay=20n rise=10p fall=10p width=4n",
            "VVIP (VIP AGND) vsource type=pwl wave=[0 0.9 19n 0.9 19.01n 0.91 59n 0.91 59.01n 0.89 119n 0.89 119.01n 0.91 159n 0.91]",
            "VVIN (VIN AGND) vsource type=pwl wave=[0 0.9 19n 0.9 19.01n 0.89 59n 0.89 59.01n 0.91 119n 0.91 119.01n 0.89 159n 0.89]",
            "XCOM (AGND AVDD CLK RST VIN VIP VON VOP) COM_IAZ",
            "XMON (CLK RST VIN VIP VON VOP AGND AVDD) COM_MON",
            "tran tran stop=160n maxstep=5p annotate=status",
            "save CLK RST VIN VIP VON VOP XCOM.CLKAZ XCOM.CLKFIA XCOM.CLKB1",
            "saveOptions options save=selected currents=selected",
            'ahdl_include "/opt/cadence/IC618/tools/dfII/samples/artist/ahdlLib/not_gate/veriloga/veriloga.va"',
            'ahdl_include "COM_MON.va"',
            "",
        ]
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(generated), encoding="utf-8", newline="\n")
    print(output)


if __name__ == "__main__":
    main()
