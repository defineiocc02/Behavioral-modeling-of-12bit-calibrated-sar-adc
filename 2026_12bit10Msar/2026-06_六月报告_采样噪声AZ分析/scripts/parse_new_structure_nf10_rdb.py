from __future__ import annotations

import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw_data" / "2026-06-11_NF10_新结构_最新结果"
RDB = RAW_DIR / "ExplorerRun.0.rdb"
TABLE_DIR = ROOT / "tables"

METRICS = [
    "ENOB",
    "SNR",
    "SFDR",
    "Power",
    "COMPOWER",
    "SRPOWER",
    "SWITCHESPOWER",
    "LOGICPOWER",
    "SYNCPOWER",
]
POWER_METRICS = {"Power", "COMPOWER", "SRPOWER", "SWITCHESPOWER", "LOGICPOWER", "SYNCPOWER"}
PARAMS = ["td", "WK1", "WK2", "caz", "caz1", "cb", "cbin", "RON", "IB", "temperature"]
CORNER_ORDER = {"tt": 0, "ff": 1, "ss": 2, "sf": 3, "fs": 4}


def value_to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def avg(values):
    nums = [v for v in values if v is not None]
    return sum(nums) / len(nums) if nums else None


def fmt(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return value


def metric_column(metric: str) -> str:
    return f"{metric}_uW" if metric in POWER_METRICS else metric


def main() -> None:
    TABLE_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(RDB)
    cur = con.cursor()

    result_id = {name: rid for rid, name in cur.execute("select resultID, name from result")}
    param_id = {name: pid for pid, name in cur.execute("select parameterID, name from parameter")}
    corner_name = {cid: name for cid, name in cur.execute("select cornerID, name from corner")}
    status_by_point = {
        point_id: status
        for point_id, status in cur.execute("select pointID, statusCode from testStatus")
    }

    rows = []
    points = cur.execute(
        "select pointID, designPointNumber, cornerID from point order by designPointNumber, cornerID"
    ).fetchall()
    for point_id, design_point, corner_id in points:
        row = {
            "dataset": "2026-06-11_NF10_新结构_最新结果",
            "identity": "新结构 NF=10 取出结果",
            "design_point": design_point,
            "point_id": point_id,
            "corner": corner_name.get(corner_id, str(corner_id)),
            "status_code": status_by_point.get(point_id, ""),
        }
        for name in PARAMS:
            pid = param_id.get(name)
            val = None
            if pid is not None:
                rec = cur.execute(
                    "select value from parameterValue where pointID=? and parameterID=?",
                    (point_id, pid),
                ).fetchone()
                if rec is not None:
                    val = rec[0]
            row[name] = val if val is not None else ""

        for metric in METRICS:
            rid = result_id.get(metric)
            val = err = None
            if rid is not None:
                rec = cur.execute(
                    "select value, errorID from resultValue where pointID=? and resultID=?",
                    (point_id, rid),
                ).fetchone()
                if rec is not None:
                    val, err = rec
            num = value_to_float(val)
            if num is not None and metric in POWER_METRICS:
                num *= 1e6
            row[metric_column(metric)] = num
            row[f"{metric}_errorID"] = "" if err is None else err
        rows.append(row)

    metric_path = TABLE_DIR / "new_structure_nf10_metrics.csv"
    metric_fields = [
        "dataset",
        "identity",
        "design_point",
        "point_id",
        "corner",
        "status_code",
        *PARAMS,
    ]
    for metric in METRICS:
        metric_fields.extend([metric_column(metric), f"{metric}_errorID"])
    with metric_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=metric_fields)
        writer.writeheader()
        for row in sorted(rows, key=lambda r: (int(r["design_point"]), CORNER_ORDER.get(r["corner"], 99))):
            writer.writerow({k: fmt(row.get(k, "")) for k in metric_fields})

    aggregates = []
    for design_point in sorted({int(r["design_point"]) for r in rows}):
        group = [r for r in rows if int(r["design_point"]) == design_point]
        first = group[0]
        agg = {
            "dataset": "2026-06-11_NF10_新结构_最新结果",
            "identity": "新结构 NF=10 取出结果",
            "design_point": design_point,
            "corner_count": len(group),
            "done_count": sum(1 for r in group if r["status_code"] == 3),
        }
        for name in PARAMS:
            agg[name] = first.get(name, "")
        for metric in METRICS:
            col = metric_column(metric)
            values = [r[col] for r in group]
            nums = [v for v in values if v is not None]
            agg[f"{col}_avg"] = avg(values)
            agg[f"{col}_min"] = min(nums) if nums else None
            agg[f"{col}_max"] = max(nums) if nums else None
            agg[f"{col}_valid_count"] = len(nums)
        aggregates.append(agg)

    agg_path = TABLE_DIR / "new_structure_nf10_aggregate.csv"
    agg_fields = [
        "dataset",
        "identity",
        "design_point",
        "corner_count",
        "done_count",
        *PARAMS,
    ]
    for metric in METRICS:
        col = metric_column(metric)
        agg_fields.extend([f"{col}_avg", f"{col}_min", f"{col}_max", f"{col}_valid_count"])
    with agg_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=agg_fields)
        writer.writeheader()
        for row in aggregates:
            writer.writerow({k: fmt(row.get(k, "")) for k in agg_fields})

    best = max(aggregates, key=lambda r: r["SNR_avg"] if r["SNR_avg"] is not None else -1e9)
    summary = [
        "# 2026-06-11 NF10 新结构最新结果解析摘要",
        "",
        "数据身份：新结构 NF=10 取出结果。",
        "",
        f"- RDB：`{RDB}`",
        "- 结构：9 个 design point，每个 design point 5 个 corner，共 45 个点。",
        f"- 完成状态：{sum(r['done_count'] for r in aggregates)} / {sum(r['corner_count'] for r in aggregates)} 个点 statusCode=3。",
        f"- Sweep 变量：`WK1` x `WK2` = 3 x 3。",
        f"- 最高平均 SNR：design point {best['design_point']}，WK1={best['WK1']}，WK2={best['WK2']}，SNR_avg={best['SNR_avg']:.4f} dB。",
        f"- 对应 ENOB_avg={best['ENOB_avg']:.4f} bit，SFDR_avg={best['SFDR_avg']:.4f} dB，Power_uW_avg={best['Power_uW_avg']:.4f} uW。",
        "",
        "输出表格：",
        "",
        f"- `{metric_path.relative_to(ROOT)}`",
        f"- `{agg_path.relative_to(ROOT)}`",
    ]
    (RAW_DIR / "parsed_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    con.close()
    print(metric_path)
    print(agg_path)
    print(RAW_DIR / "parsed_summary.md")
    print(f"best_design_point={best['design_point']} WK1={best['WK1']} WK2={best['WK2']} SNR_avg={best['SNR_avg']:.4f}")


if __name__ == "__main__":
    main()
