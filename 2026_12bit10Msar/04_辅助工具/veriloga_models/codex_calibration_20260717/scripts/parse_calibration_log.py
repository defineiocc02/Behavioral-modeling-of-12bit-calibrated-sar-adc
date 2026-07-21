from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


WEIGHT = re.compile(
    r"DEC_CAL_PHY weight target=(?P<target>\d+) wall=(?P<wall>-?\d+) "
    r"measured_q=(?P<measured>-?\d+) value_q=(?P<value_q>-?\d+) "
    r"value=(?P<value>[-+0-9.eE]+) pairs=(?P<pairs>\d+) "
    r"residual_sum=(?P<residual_sum>-?\d+) residual_avg=(?P<residual_avg>-?\d+) "
    r"diversity=(?P<diversity>-?\d+) snap=(?P<snap>\d+)"
)
FINISH = re.compile(
    r"DEC_CAL_PHY finish t=(?P<time>[-+0-9.eE]+) done=(?P<done>\d+) err=(?P<err>\d+)"
)
WEIGHTS_Q = re.compile(
    r"DEC_CAL_PHY weights_q=\{(?P<values>[-0-9,]+)\} Q=(?P<frac_bits>\d+) pairs=(?P<pairs>\d+)"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse DEC_CAL_PHY calibration strobes from Spectre output.")
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-measurements", type=int, default=6)
    args = parser.parse_args()

    text = args.log.resolve().read_text(encoding="utf-8", errors="replace")
    measurements = []
    for match in WEIGHT.finditer(text):
        entry = {key: int(value) for key, value in match.groupdict().items() if key != "value"}
        entry["value"] = float(match.group("value"))
        measurements.append(entry)

    finish_matches = list(FINISH.finditer(text))
    weights_matches = list(WEIGHTS_Q.finditer(text))
    result: dict[str, object] = {"measurements": measurements}
    if finish_matches:
        finish = finish_matches[-1]
        result["finish"] = {
            "time_s": float(finish.group("time")),
            "done": int(finish.group("done")),
            "err": int(finish.group("err")),
        }
    if weights_matches:
        weights = weights_matches[-1]
        frac_bits = int(weights.group("frac_bits"))
        values_q = [int(value) for value in weights.group("values").split(",")]
        result["weights"] = {
            "frac_bits": frac_bits,
            "pairs": int(weights.group("pairs")),
            "values_q": values_q,
            "values_lsb": [value / (1 << frac_bits) for value in values_q],
        }

    result["complete"] = bool(
        result.get("finish", {}).get("done") == 1
        and result.get("finish", {}).get("err") == 0
        and len(measurements) == args.expected_measurements
        and "weights" in result
    )
    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output.resolve().write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
