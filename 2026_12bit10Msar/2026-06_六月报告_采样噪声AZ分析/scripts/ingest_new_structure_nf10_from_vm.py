from __future__ import annotations

from pathlib import Path
import sys


VM_REMOTE_ROOT = Path(r"D:\ReedZhao\vm-remote")
if str(VM_REMOTE_ROOT) not in sys.path:
    sys.path.insert(0, str(VM_REMOTE_ROOT))

from vm_base import VMConnection  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "raw_data" / "2026-06-11_NF10_新结构_最新结果"

REMOTE_RDB = "/home/meow/jxy/12bit_50M_SAR/test_12bit50MSAR_AMS_final/maestro/results/maestro/ExplorerRun.0.rdb"
REMOTE_SDB = "/home/meow/jxy/12bit_50M_SAR/test_12bit50MSAR_AMS_final/maestro/maestro.sdb"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with VMConnection() as vm:
        def capture(command: str, filename: str) -> str:
            report = vm.run_to_file(command, filename=filename, timeout=120)
            return vm.read_file(report).strip()

        nf_hits = capture(
            r"find /home/meow/jxy/simulation/12bit_50M_SAR/test_12bit50MSAR_AMS_final/maestro/results/maestro/ExplorerRun.0 "
            r"-path '*/netlist/input.scs' -exec grep -HinE 'NOISEFACTOR|noisefactor|noise factor|NF=|nf=' {} \; 2>/dev/null | head -120",
            "new_structure_nf10_nf_search.txt",
        )
        if not nf_hits:
            nf_hits = "no explicit NOISEFACTOR/NF string found in latest input.scs files; identity retained from user-provided run condition."

        status_parts = [
            f"source_rdb={REMOTE_RDB}",
            capture(f"stat -c 'rdb_mtime_vm=%y\nrdb_size_bytes=%s' '{REMOTE_RDB}'", "new_structure_nf10_rdb_stat.txt"),
            f"source_sdb={REMOTE_SDB}",
            capture(f"stat -c 'sdb_mtime_vm=%y\nsdb_size_bytes=%s' '{REMOTE_SDB}'", "new_structure_nf10_sdb_stat.txt"),
            "process_state=",
            capture("ps -eo pid,cmd | grep -E 'virtuoso|spectre' | grep -v grep", "new_structure_nf10_process_state.txt"),
            "nf_search=",
            nf_hits,
        ]
        status_text = "\n".join(part for part in status_parts if part) + "\n"
        (OUT_DIR / "remote_status.txt").write_text(status_text, encoding="utf-8")
        vm.download(REMOTE_RDB, str(OUT_DIR / "ExplorerRun.0.rdb"))
        vm.download(REMOTE_SDB, str(OUT_DIR / "maestro.sdb"))

    readme = f"""# 2026-06-11 NF10 新结构最新结果

本目录保存最新读取的“新结构 NF=10”仿真结果。

- 数据身份：新结构 NF=10 取出结果。
- VM 源 RDB：`{REMOTE_RDB}`
- VM 源 maestro：`{REMOTE_SDB}`
- 本地文件：`ExplorerRun.0.rdb`、`maestro.sdb`
- 读取方式：只读下载；未修改 VM 仿真状态。
- 状态备注：下载时 VM 中 Virtuoso/Spectre 仍在运行，因此本目录记录的是当时最新可读的 RDB/SDB 快照。

详细源文件时间、大小和进程状态见 `remote_status.txt`。
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    print(OUT_DIR)


if __name__ == "__main__":
    main()
