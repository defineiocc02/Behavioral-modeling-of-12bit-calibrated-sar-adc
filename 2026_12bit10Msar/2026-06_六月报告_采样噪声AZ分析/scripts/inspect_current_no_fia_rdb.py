from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RDB = ROOT / "raw_data" / "2026-06-09_NF10_仅采样噪声_电流型KT_C_无FIA_正式对比" / "ExplorerRun.0.rdb"


def main() -> None:
    con = sqlite3.connect(RDB)
    cur = con.cursor()
    print("RDB", RDB)
    print("tables", cur.execute("select name from sqlite_master where type='table' order by name").fetchall())
    for table in [
        "result",
        "point",
        "pointIDMap",
        "corner",
        "cornerResultValue",
        "parameter",
        "parameterValue",
        "resultValue",
    ]:
        print(f"\n-- {table} --")
        try:
            print(cur.execute(f"pragma table_info({table})").fetchall())
            for row in cur.execute(f"select * from {table} limit 12").fetchall():
                print(row)
        except Exception as exc:
            print(type(exc).__name__, exc)
    con.close()


if __name__ == "__main__":
    main()
