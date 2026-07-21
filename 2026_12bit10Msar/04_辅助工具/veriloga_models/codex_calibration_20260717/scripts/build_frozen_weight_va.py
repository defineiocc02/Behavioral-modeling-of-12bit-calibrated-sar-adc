from __future__ import annotations

import argparse
import json
from pathlib import Path


NOMINAL_LSB = (2048, 1024, 512, 256, 256, 128, 48, 32, 20, 12, 8, 4, 2, 1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze measured Huang calibration weights into a test-only decoder VA."
    )
    parser.add_argument("--source-va", type=Path, required=True)
    parser.add_argument("--calibration-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = args.source_va.resolve()
    summary_path = args.calibration_summary.resolve()
    output = args.output.resolve()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not summary.get("complete"):
        raise RuntimeError("Calibration summary is incomplete")

    weights = summary["weights"]
    frac_bits = int(weights["frac_bits"])
    values_q = [int(value) for value in weights["values_q"]]
    if frac_bits != 6:
        raise RuntimeError(f"Expected Q6 Huang weights, got Q{frac_bits}")
    if len(values_q) != len(NOMINAL_LSB):
        raise RuntimeError(f"Expected {len(NOMINAL_LSB)} weights, got {len(values_q)}")

    text = source.read_text(encoding="utf-8", errors="strict")
    for index, (nominal, measured_q) in enumerate(zip(NOMINAL_LSB, values_q)):
        old = f"w{index} = q_scale;" if nominal == 1 else f"w{index} = {nominal}*q_scale;"
        count = text.count(old)
        if count != 3:
            raise RuntimeError(f"Expected three nominal assignments for w{index}, found {count}")
        text = text.replace(old, f"w{index} = {measured_q};")

    banner = (
        "// TEST-ONLY FROZEN HUANG WEIGHTS.\n"
        f"// Source calibration: {summary_path}\n"
        "// Do not deploy this file as the foreground calibration implementation.\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(banner + text, encoding="utf-8", newline="\n")
    print(output)


if __name__ == "__main__":
    main()
