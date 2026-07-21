from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


HOST = "meow@192.168.38.128"
REMOTE_ROOT = "/home/meow/jxy/codex_sandbox/sar0716_calibration_20260717"


def run(command: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )


def safe_name(signal: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", signal.strip("/"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Export selected PSF waveforms through standalone OCEAN.")
    parser.add_argument("--case", required=True)
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--signal", action="append", required=True)
    parser.add_argument("--from-time", help="Optional OCEAN start time, e.g. 12.298505u")
    parser.add_argument("--to-time", help="Optional OCEAN stop time, e.g. 24.998505u")
    parser.add_argument("--step", help="Optional OCEAN resampling step, e.g. 100n")
    args = parser.parse_args()
    grid_values = (args.from_time, args.to_time, args.step)
    if any(value is not None for value in grid_values) and not all(
        value is not None for value in grid_values
    ):
        parser.error("--from-time, --to-time and --step must be provided together")

    result_dir = args.result_dir.resolve()
    result_dir.mkdir(parents=True, exist_ok=True)
    remote_dir = f"{REMOTE_ROOT}/{args.case}"
    remote_export_dir = f"{remote_dir}/exports"
    local_script = result_dir / "export_waveforms.ocn"
    remote_script = f"{remote_dir}/export_waveforms.ocn"

    lines = [
        f'openResults("{remote_dir}/psf")',
        "selectResult('tran)",
    ]
    for signal in args.signal:
        name = safe_name(signal)
        grid = ""
        if args.from_time is not None:
            grid = f"?from {args.from_time} ?to {args.to_time} ?step {args.step} "
        lines.append(
            f'ocnPrint(v("{signal.strip("/")}") ?numberNotation (quote scientific) '
            f'{grid}?numSpaces 1 ?output "{remote_export_dir}/{name}.txt")'
        )
    lines.append("exit()")
    local_script.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")

    run(["ssh", "-o", "BatchMode=yes", HOST, f"mkdir -p '{remote_export_dir}'"])
    run(["scp", "-q", str(local_script), f"{HOST}:{remote_script}"])
    ocean_command = (
        "source /home/meow/.cshrc; "
        f"cd {remote_dir}; "
        "ocean -nograph -restore export_waveforms.ocn"
    )
    completed = run(
        ["ssh", "-o", "BatchMode=yes", HOST, f"csh -fc \"{ocean_command}\""],
        timeout=600,
    )
    (result_dir / "ocean_stdout.txt").write_text(
        completed.stdout + completed.stderr, encoding="utf-8"
    )

    for signal in args.signal:
        name = safe_name(signal)
        run(["scp", "-q", f"{HOST}:{remote_export_dir}/{name}.txt", str(result_dir / f"{name}.txt")])
        print(result_dir / f"{name}.txt")


if __name__ == "__main__":
    main()
