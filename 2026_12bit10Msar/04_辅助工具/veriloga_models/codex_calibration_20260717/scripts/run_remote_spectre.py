from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


HOST = "meow@192.168.38.128"
REMOTE_ROOT = "/home/meow/jxy/codex_sandbox/sar0716_calibration_20260717"
SPECTRE = "/opt/cadence/SPECTRE231/bin/spectre"


def run(command: list[str], *, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one isolated Spectre netlist in the VM sandbox.")
    parser.add_argument("--case", required=True)
    parser.add_argument("--netlist", type=Path, required=True)
    parser.add_argument("--include", type=Path, action="append", default=[])
    parser.add_argument(
        "--include-as", nargs=2, action="append", default=[], metavar=("LOCAL", "REMOTE_NAME")
    )
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument(
        "--multithread",
        action="store_true",
        help="Enable Spectre's +mt mode; still launches only one Spectre process.",
    )
    parser.add_argument(
        "--preset-cx",
        action="store_true",
        help="Use the same +preset=cx acceleration selected by the ADE testbench.",
    )
    args = parser.parse_args()

    netlist = args.netlist.resolve()
    includes = [path.resolve() for path in args.include]
    include_aliases = [(Path(local).resolve(), remote) for local, remote in args.include_as]
    result_dir = args.result_dir.resolve()
    result_dir.mkdir(parents=True, exist_ok=True)
    remote_dir = f"{REMOTE_ROOT}/{args.case}"

    run(["ssh", "-o", "BatchMode=yes", HOST, f"mkdir -p '{remote_dir}'"])
    run(["scp", "-q", str(netlist), f"{HOST}:{remote_dir}/{netlist.name}"])
    for include in includes:
        run(["scp", "-q", str(include), f"{HOST}:{remote_dir}/{include.name}"])
    for include, remote_name in include_aliases:
        if "/" in remote_name or "\\" in remote_name:
            raise ValueError(f"REMOTE_NAME must be a basename: {remote_name}")
        run(["scp", "-q", str(include), f"{HOST}:{remote_dir}/{remote_name}"])

    spectre_command = (
        "source /home/meow/.cshrc; "
        f"cd {remote_dir}; "
        "rm -f spectre.out; "
        f"{SPECTRE} -64 {netlist.name} +log spectre.out -format psfxl -raw psf"
        f"{' +mt' if args.multithread else ''}"
        f"{' +preset=cx' if args.preset_cx else ''}"
    )
    command = ["ssh", "-o", "BatchMode=yes", HOST, f"csh -fc \"{spectre_command}\""]
    try:
        completed = run(command, timeout=args.timeout)
        return_code = 0
        output = completed.stdout + completed.stderr
    except subprocess.CalledProcessError as exc:
        return_code = exc.returncode
        output = (exc.stdout or "") + (exc.stderr or "")

    (result_dir / "remote_stdout.txt").write_text(output, encoding="utf-8")
    run(["scp", "-q", f"{HOST}:{remote_dir}/spectre.out", str(result_dir / "spectre.out")])
    print(result_dir / "spectre.out")
    if return_code:
        raise SystemExit(return_code)


if __name__ == "__main__":
    main()
