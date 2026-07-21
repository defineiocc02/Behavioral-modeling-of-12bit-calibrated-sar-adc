from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, r"D:\ReedZhao\vm-remote")
from vm_base import VMConnection  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "raw_data" / "2026-06-09_NF10_仅采样噪声_电流型KT_C_无FIA_正式对比"

REMOTE_RDB = (
    "/home/meow/jxy/12bit_50M_SAR/test_12bit50MSAR_AMS_final/"
    "maestro/results/maestro/ExplorerRun.0.rdb"
)
REMOTE_SDB = (
    "/home/meow/jxy/12bit_50M_SAR/test_12bit50MSAR_AMS_final/"
    "maestro/maestro.sdb"
)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    status_cmd = f"""
printf 'REMOTE_RDB=%s\\n' '{REMOTE_RDB}'
printf 'REMOTE_SDB=%s\\n' '{REMOTE_SDB}'
printf '\\n[stat]\\n'
stat -c '%y %s %n' '{REMOTE_RDB}' '{REMOTE_SDB}' 2>&1
printf '\\n[process]\\n'
ps -eo pid,etime,cmd | egrep 'virtuoso|spectre|aps|maestro|ocean' | grep -v egrep || true
"""
    with VMConnection() as vm:
        vm.download(REMOTE_RDB, str(OUTDIR / "ExplorerRun.0.rdb"))
        vm.download(REMOTE_SDB, str(OUTDIR / "maestro.sdb"))
        status = vm.run(status_cmd, timeout=120)
        (OUTDIR / "remote_status.txt").write_text(
            status.stdout + ("\nSTDERR:\n" + status.stderr if status.stderr else ""),
            encoding="utf-8",
        )
    (OUTDIR / "README.md").write_text(
        "# 原始数据归档说明\n\n"
        "- 身份：无 FIA 电流型 KT/C 消除方案。\n"
        "- 归档来源：VM 最新 `ExplorerRun.0.rdb` 与 `maestro.sdb`，远端路径见 `remote_status.txt`。\n"
        "- 操作边界：归档时 VM 上 Virtuoso/Spectre 仍显示运行中；本脚本只读取和下载，不修改 VM。\n"
        "- 路径规范：正文写 `KT/C`，目录名写 `KT_C`。\n",
        encoding="utf-8",
    )
    print(OUTDIR)


if __name__ == "__main__":
    main()
