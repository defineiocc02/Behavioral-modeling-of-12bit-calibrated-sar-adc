from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


HOST = "meow@192.168.38.128"
REMOTE_ROOT = "/home/meow/jxy/codex_sandbox/sar0716_calibration_20260717/dec_onehot"
SPECTRE = "/opt/cadence/SPECTRE231/bin/spectre"


def run(command: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )


def ssh(command: str, *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", HOST, command],
        timeout=timeout,
    )


def scp_to(local: Path, remote: str) -> None:
    run(["scp", "-q", str(local), f"{HOST}:{remote}"])


def scp_from(remote: str, local: Path) -> None:
    local.parent.mkdir(parents=True, exist_ok=True)
    run(["scp", "-q", f"{HOST}:{remote}", str(local)])


def parse_codes(log_path: Path) -> list[int]:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return [int(value) for value in re.findall(r"DEC_MON sample=\d+ code=(\d+)", text)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DEC_CAL_PHY physical-bit one-hot tests.")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--corrected", type=Path, required=True)
    args = parser.parse_args()

    project = args.project.resolve()
    tb = project / "testbenches" / "tb_dec_onehot.scs"
    monitor = project / "testbenches" / "DEC_MON.va"
    result_root = project / "results" / "dec_onehot"
    expected_original = [1, 2, 4, 8, 12, 20, 32, 48, 128, 256, 256, 512, 1024, 2048]
    expected_corrected = [2048, 1024, 512, 256, 256, 128, 48, 32, 20, 12, 8, 4, 2, 1]

    variants = (
        ("vm_original", args.original.resolve(), expected_original),
        ("0716_corrected", args.corrected.resolve(), expected_corrected),
    )

    ssh(f"mkdir -p '{REMOTE_ROOT}/vm_original' '{REMOTE_ROOT}/0716_corrected'")

    failed = False
    for name, decoder, expected in variants:
        remote_dir = f"{REMOTE_ROOT}/{name}"
        local_dir = result_root / name
        local_dir.mkdir(parents=True, exist_ok=True)

        scp_to(tb, f"{remote_dir}/tb_dec_onehot.scs")
        scp_to(monitor, f"{remote_dir}/DEC_MON.va")
        scp_to(decoder, f"{remote_dir}/DEC.va")

        spectre_command = (
            "source /home/meow/.cshrc; "
            f"cd {remote_dir}; "
            "rm -f spectre.out; "
            f"{SPECTRE} -64 tb_dec_onehot.scs +log spectre.out -format psfxl -raw psf"
        )
        command = f"csh -fc \"{spectre_command}\""
        try:
            completed = ssh(command, timeout=180)
            (local_dir / "remote_stdout.txt").write_text(
                completed.stdout + completed.stderr, encoding="utf-8"
            )
        except subprocess.CalledProcessError as exc:
            (local_dir / "remote_stdout.txt").write_text(
                (exc.stdout or "") + (exc.stderr or ""), encoding="utf-8"
            )
            failed = True

        scp_from(f"{remote_dir}/spectre.out", local_dir / "spectre.out")
        codes = parse_codes(local_dir / "spectre.out")
        passed = codes == expected
        failed = failed or not passed
        summary = (
            f"variant={name}\n"
            f"decoder={decoder}\n"
            f"expected={expected}\n"
            f"observed={codes}\n"
            f"pass={passed}\n"
        )
        (local_dir / "summary.txt").write_text(summary, encoding="utf-8")
        print(summary, end="")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
