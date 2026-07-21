"""Read key error sections from a VM-side Cadence/Spectre log.

Usage:
    python read_vm_log_errors.py /home/meow/jxy/logs_meow/logs0/Job557.log
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


VM_TOOLKIT = Path(os.environ.get("VM_TOOLKIT", r"D:\ReedZhao\vm-remote"))
sys.path.insert(0, str(VM_TOOLKIT))

from vm_base import VMConnection  # noqa: E402


def shell_quote(path: str) -> str:
    return "'" + path.replace("'", "'\"'\"'") + "'"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log_path", help="VM-side absolute log path")
    parser.add_argument("--lines", type=int, default=240)
    args = parser.parse_args()

    log_path = shell_quote(args.log_path)
    grep_limit = int(args.lines)
    tail_limit = int(args.lines)

    cmd = "\n".join(
        [
            f"LOG={log_path}",
            "echo '--- file ---'",
            'if [ -f "$LOG" ]; then ls -lh "$LOG"; else echo "MISSING: $LOG"; exit 2; fi',
            "echo '--- first error-like lines ---'",
            (
                "grep -nEi "
                "'(^|[^a-z])(error|fatal|failed|cannot|can not|unable|undefined|"
                "unbound|exception|traceback|segmentation|permission|denied|syntax|"
                "parse|netlist|hnl|auCdl|spectre|verilog|ahdl|vams|CDF|instantiat|"
                "terminal|pin|view|switch|stop)([^a-z]|$)' "
                '"$LOG" | head -'
                + str(grep_limit)
            ),
            "echo '--- tail ---'",
            f'tail -{tail_limit} "$LOG"',
        ]
    )

    with VMConnection() as vm:
        out_path = vm.run_to_file(cmd, filename="vm_log_diag.txt", timeout=60)
        print(vm.read_file(out_path))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
