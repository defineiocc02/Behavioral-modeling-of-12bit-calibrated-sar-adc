from __future__ import annotations

import csv
import math
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "tables"
RAW = ROOT / "raw_data" / "2026-06-09_NF10_仅采样噪声_电流型KT_C_无FIA_正式对比"
RDB = RAW / "ExplorerRun.0.rdb"
CASE = "2026-06-09_NF10_仅采样噪声_电流型KT_C_无FIA_正式对比"
PREFIX = "sampling_nf10_current_offset_KT_C_no_FIA"

CORNER_ORDER = ["tt", "ff", "ss", "sf", "fs"]
METRICS = [
    "SWITCHESPOWER",
    "COMPOWER",
    "ENOB",
    "SNR",
    "SFDR",
    "LOGICPOWER",
    "SYNCPOWER",
    "SRPOWER",
    "Power",
]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def f4(x: float) -> str:
    return f"{x:.4f}"


def f6(x: float) -> str:
    return f"{x:.6f}"


def pct_residual(delta_snr_db: float) -> float:
    return 100.0 * 10 ** (-delta_snr_db / 10.0)


def load_rdb_metrics() -> list[dict[str, object]]:
    con = sqlite3.connect(RDB)
    cur = con.cursor()
    result_ids = {
        name: rid
        for rid, name in cur.execute("select resultID,name from result").fetchall()
        if name in METRICS
    }
    rows = []
    for point_id, corner in cur.execute(
        "select p.pointID,c.name from point p join corner c on c.cornerID=p.cornerID"
    ).fetchall():
        values: dict[str, object] = {}
        errors: dict[str, object] = {}
        for name, rid in result_ids.items():
            value, error_id = cur.execute(
                "select value,errorID from resultValue where pointID=? and resultID=?",
                (point_id, rid),
            ).fetchone()
            values[name] = value
            errors[name] = error_id
        rows.append(
            {
                "case": CASE,
                "td": "28n",
                "AZ_time_ns_equiv": "4.00",
                "corner": corner,
                "pointID": point_id,
                "statusCode": "3",
                "statusMessage": "done",
                "ENOB_bits": values["ENOB"],
                "SNR_dB": values["SNR"],
                "SFDR_dB": values["SFDR"],
                "SWITCHESPOWER_uW": values["SWITCHESPOWER"] * 1e6,
                "COMPOWER_uW": values["COMPOWER"] * 1e6,
                "LOGICPOWER_uW": values["LOGICPOWER"] * 1e6,
                "SYNCPOWER_uW": values["SYNCPOWER"] * 1e6,
                "SRPOWER_uW": "" if values["SRPOWER"] == "" else values["SRPOWER"] * 1e6,
                "SRPOWER_error": "yes" if errors["SRPOWER"] else "",
                "Power_uW": values["Power"] * 1e6,
            }
        )
    con.close()
    rows.sort(key=lambda r: CORNER_ORDER.index(str(r["corner"])))
    return rows


def make_aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    def vals(key: str) -> list[float]:
        return [float(r[key]) for r in rows]

    enob = vals("ENOB_bits")
    snr = vals("SNR_dB")
    sfdr = vals("SFDR_dB")
    power = vals("Power_uW")
    compower = vals("COMPOWER_uW")
    sync = vals("SYNCPOWER_uW")
    return {
        "case": CASE,
        "td": "28n",
        "AZ_time_ns_equiv": "4.0000",
        "corner_count": len(rows),
        "ENOB_min": f4(min(enob)),
        "ENOB_avg": f4(sum(enob) / len(enob)),
        "ENOB_max": f4(max(enob)),
        "ENOB_worst_corner": rows[enob.index(min(enob))]["corner"],
        "ENOB_best_corner": rows[enob.index(max(enob))]["corner"],
        "SNR_min": f4(min(snr)),
        "SNR_avg": f4(sum(snr) / len(snr)),
        "SNR_max": f4(max(snr)),
        "SNR_worst_corner": rows[snr.index(min(snr))]["corner"],
        "SNR_best_corner": rows[snr.index(max(snr))]["corner"],
        "SFDR_min": f4(min(sfdr)),
        "SFDR_avg": f4(sum(sfdr) / len(sfdr)),
        "SFDR_max": f4(max(sfdr)),
        "SFDR_worst_corner": rows[sfdr.index(min(sfdr))]["corner"],
        "SFDR_best_corner": rows[sfdr.index(max(sfdr))]["corner"],
        "Power_uW_min": f4(min(power)),
        "Power_uW_avg": f4(sum(power) / len(power)),
        "Power_uW_max": f4(max(power)),
        "Power_uW_max_corner": rows[power.index(max(power))]["corner"],
        "COMPOWER_uW_avg": f4(sum(compower) / len(compower)),
        "SYNCPOWER_uW_avg": f4(sum(sync) / len(sync)),
    }


def make_cancellation(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    baseline = {
        r["corner"]: r
        for r in read_csv_rows(TABLES / "td_sweep_metrics.csv")
        if r["td_ns"] == "24.05n"
    }
    out = []
    residuals = []
    snr_after = []
    enob_after = []
    for row in rows:
        corner = str(row["corner"])
        b = baseline[corner]
        base_snr = float(b["SNR_dB"])
        snr = float(row["SNR_dB"])
        delta = snr - base_snr
        residual = pct_residual(delta)
        residuals.append(residual)
        snr_after.append(snr)
        enob_after.append(float(row["ENOB_bits"]))
        out.append(
            {
                "corner": corner,
                "baseline_td": "24.05n_yesterday",
                "td": "28n_current_offset_KT_C_no_FIA",
                "baseline_snr_db": f6(base_snr),
                "snr_db": f6(snr),
                "delta_snr_db": f6(delta),
                "residual_noise_power_pct_of_yesterday_24p05n": f6(residual),
                "cancelled_noise_power_pct": f6(100 - residual),
                "baseline_enob": f6(float(b["ENOB_bit"])),
                "enob": f6(float(row["ENOB_bits"])),
                "delta_enob": f6(float(row["ENOB_bits"]) - float(b["ENOB_bit"])),
            }
        )

    avg_base_snr = 54.3396
    avg_snr = sum(snr_after) / len(snr_after)
    avg_delta = avg_snr - avg_base_snr
    avg_residual = pct_residual(avg_delta)
    avg_base_enob = 8.7524
    avg_enob = sum(enob_after) / len(enob_after)
    out.append(
        {
            "corner": "average_by_corner_residual",
            "baseline_td": "24.05n_yesterday",
            "td": "28n_current_offset_KT_C_no_FIA",
            "baseline_snr_db": f6(avg_base_snr),
            "snr_db": f6(avg_snr),
            "delta_snr_db": f6(avg_delta),
            "residual_noise_power_pct_of_yesterday_24p05n": f6(sum(residuals) / len(residuals)),
            "cancelled_noise_power_pct": f6(100 - sum(residuals) / len(residuals)),
            "baseline_enob": f6(avg_base_enob),
            "enob": f6(avg_enob),
            "delta_enob": f6(avg_enob - avg_base_enob),
        }
    )
    out.append(
        {
            "corner": "average_by_avg_SNR",
            "baseline_td": "24.05n_yesterday",
            "td": "28n_current_offset_KT_C_no_FIA",
            "baseline_snr_db": f6(avg_base_snr),
            "snr_db": f6(avg_snr),
            "delta_snr_db": f6(avg_delta),
            "residual_noise_power_pct_of_yesterday_24p05n": f6(avg_residual),
            "cancelled_noise_power_pct": f6(100 - avg_residual),
            "baseline_enob": f6(avg_base_enob),
            "enob": f6(avg_enob),
            "delta_enob": f6(avg_enob - avg_base_enob),
        }
    )
    return out


def make_comparison(
    rows: list[dict[str, object]],
    other_rows: list[dict[str, str]],
    other_label: str,
    other_snr_key: str,
    other_enob_key: str,
    other_sfdr_key: str,
    other_power_key: str,
    out_label: str,
) -> list[dict[str, object]]:
    current = {str(r["corner"]): r for r in rows}
    other = {r["corner"]: r for r in other_rows if r.get("corner") in CORNER_ORDER}
    out = []
    for corner in CORNER_ORDER:
        c = current[corner]
        o = other[corner]
        row = {
            "corner": corner,
            "td": "28n",
            f"ENOB_{other_label}": f6(float(o[other_enob_key])),
            "ENOB_current_no_FIA": f6(float(c["ENOB_bits"])),
            "ENOB_delta_current_no_FIA_minus_" + out_label: f6(float(c["ENOB_bits"]) - float(o[other_enob_key])),
            f"SNR_{other_label}": f6(float(o[other_snr_key])),
            "SNR_current_no_FIA": f6(float(c["SNR_dB"])),
            "SNR_delta_current_no_FIA_minus_" + out_label: f6(float(c["SNR_dB"]) - float(o[other_snr_key])),
            f"SFDR_{other_label}": f6(float(o[other_sfdr_key])),
            "SFDR_current_no_FIA": f6(float(c["SFDR_dB"])),
            "SFDR_delta_current_no_FIA_minus_" + out_label: f6(float(c["SFDR_dB"]) - float(o[other_sfdr_key])),
            f"Power_{other_label}_uW": f6(float(o[other_power_key])),
            "Power_current_no_FIA_uW": f6(float(c["Power_uW"])),
            "Power_delta_current_no_FIA_minus_" + out_label + "_uW": f6(float(c["Power_uW"]) - float(o[other_power_key])),
        }
        if "COMPOWER_uW" in c and ("COMPOWER_uW" in o or "COMPOWER_voltage_offset_KT_C" in o):
            pass
        out.append(row)

    avg_row = {"corner": "average", "td": "28n"}
    for key in list(out[0].keys()):
        if key in ("corner", "td"):
            continue
        avg_row[key] = f6(sum(float(r[key]) for r in out) / len(out))
    out.append(avg_row)
    return out


def make_scheme_summary(rows: list[dict[str, object]]) -> None:
    agg_fia = {r["td"]: r for r in read_csv_rows(TABLES / "td_sweep_aggregate.csv")}
    agg_volt = read_csv_rows(TABLES / "sampling_nf10_voltage_offset_KT_C_aggregate.csv")[0]
    agg_current = make_aggregate(rows)
    schemes = [
        {
            "scheme": "FIA / 方案A",
            "td": "28n",
            "ENOB_avg": agg_fia["28n"]["ENOB_avg"],
            "SNR_avg": agg_fia["28n"]["SNR_avg"],
            "SFDR_avg": agg_fia["28n"]["SFDR_avg"],
            "Power_uW_avg": agg_fia["28n"]["Power_avg"],
            "COMPOWER_uW_avg": agg_fia["28n"]["COMPOWER_avg"],
            "residual_noise_power_pct_vs_original": "10.918253",
            "cancelled_noise_power_pct_vs_original": "89.081747",
        },
        {
            "scheme": "电压型KT_C正式对比",
            "td": "28n",
            "ENOB_avg": agg_volt["ENOB_avg"],
            "SNR_avg": agg_volt["SNR_avg"],
            "SFDR_avg": agg_volt["SFDR_avg"],
            "Power_uW_avg": agg_volt["Power_uW_avg"],
            "COMPOWER_uW_avg": agg_volt["COMPOWER_uW_avg"],
            "residual_noise_power_pct_vs_original": "6.554384",
            "cancelled_noise_power_pct_vs_original": "93.445616",
        },
        {
            "scheme": "电流型KT_C无FIA正式对比",
            "td": "28n",
            "ENOB_avg": agg_current["ENOB_avg"],
            "SNR_avg": agg_current["SNR_avg"],
            "SFDR_avg": agg_current["SFDR_avg"],
            "Power_uW_avg": agg_current["Power_uW_avg"],
            "COMPOWER_uW_avg": agg_current["COMPOWER_uW_avg"],
            "residual_noise_power_pct_vs_original": "",
            "cancelled_noise_power_pct_vs_original": "",
        },
    ]
    current_snr = float(agg_current["SNR_avg"])
    residual = pct_residual(current_snr - 54.3396)
    schemes[2]["residual_noise_power_pct_vs_original"] = f6(residual)
    schemes[2]["cancelled_noise_power_pct_vs_original"] = f6(100 - residual)
    write_csv(
        TABLES / "sampling_nf10_scheme_summary.csv",
        [
            "scheme",
            "td",
            "ENOB_avg",
            "SNR_avg",
            "SFDR_avg",
            "Power_uW_avg",
            "COMPOWER_uW_avg",
            "residual_noise_power_pct_vs_original",
            "cancelled_noise_power_pct_vs_original",
        ],
        schemes,
    )


def main() -> None:
    rows = load_rdb_metrics()
    metric_fields = [
        "case",
        "td",
        "AZ_time_ns_equiv",
        "corner",
        "pointID",
        "statusCode",
        "statusMessage",
        "ENOB_bits",
        "SNR_dB",
        "SFDR_dB",
        "SWITCHESPOWER_uW",
        "COMPOWER_uW",
        "LOGICPOWER_uW",
        "SYNCPOWER_uW",
        "SRPOWER_uW",
        "SRPOWER_error",
        "Power_uW",
    ]
    write_csv(
        TABLES / f"{PREFIX}_metrics.csv",
        metric_fields,
        [
            {
                k: (f6(float(v)) if isinstance(v, float) and k not in ("ENOB_bits", "SNR_dB", "SFDR_dB") else v)
                for k, v in row.items()
            }
            for row in rows
        ],
    )

    agg = make_aggregate(rows)
    write_csv(TABLES / f"{PREFIX}_aggregate.csv", list(agg.keys()), [agg])

    cancellation = make_cancellation(rows)
    write_csv(TABLES / f"{PREFIX}_cancellation_using_yesterday_baseline.csv", list(cancellation[0].keys()), cancellation)

    fia_rows = [r for r in read_csv_rows(TABLES / "td_sweep_metrics.csv") if r["td_ns"] == "28n"]
    voltage_rows = read_csv_rows(TABLES / "sampling_nf10_voltage_offset_KT_C_metrics.csv")
    comp_fia = make_comparison(
        rows,
        fia_rows,
        "FIA",
        "SNR_dB",
        "ENOB_bit",
        "SFDR_dB",
        "Power_uW",
        "FIA",
    )
    write_csv(TABLES / f"{PREFIX}_vs_FIA_td28_comparison.csv", list(comp_fia[0].keys()), comp_fia)
    comp_voltage = make_comparison(
        rows,
        voltage_rows,
        "voltage_offset_KT_C",
        "SNR_dB",
        "ENOB_bits",
        "SFDR_dB",
        "Power_uW",
        "voltage_offset_KT_C",
    )
    write_csv(TABLES / f"{PREFIX}_vs_voltage_offset_KT_C_td28_comparison.csv", list(comp_voltage[0].keys()), comp_voltage)
    make_scheme_summary(rows)

    print("current_no_FIA_avg_SNR", make_aggregate(rows)["SNR_avg"])
    print("current_no_FIA_avg_Power_uW", make_aggregate(rows)["Power_uW_avg"])


if __name__ == "__main__":
    main()
