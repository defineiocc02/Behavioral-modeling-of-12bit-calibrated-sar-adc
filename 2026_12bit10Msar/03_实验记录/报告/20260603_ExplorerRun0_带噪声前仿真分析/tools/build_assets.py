import csv
import html
import json
import math
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = PACKAGE_DIR / "data" / "ExplorerRun.0.csv"
ASSET_DIR = PACKAGE_DIR / "figures"
SUMMARY_PATH = PACKAGE_DIR / "data" / "summary.json"

CORNER_ORDER = [
    "tt_0", "tt_1", "tt_2",
    "ff_0", "ff_1", "ff_2",
    "ss_0", "ss_1", "ss_2",
    "sf_0", "sf_1", "sf_2",
    "fs_0", "fs_1", "fs_2",
]
CORNER_LABELS = [
    "TT -40", "TT 27", "TT 85",
    "FF -40", "FF 27", "FF 85",
    "SS -40", "SS 27", "SS 85",
    "SF -40", "SF 27", "SF 85",
    "FS -40", "FS 27", "FS 85",
]
TEMPS = [-40, 27, 85]
PROCS = ["tt", "ff", "ss", "sf", "fs"]


def parse_csv(path):
    rows = list(csv.reader(path.open(newline="", encoding="utf-8-sig")))
    header_idx = next(i for i, row in enumerate(rows) if row and row[0] == "Point")
    header = rows[header_idx]
    current_td = None
    data = {}
    test_name = ""
    for row in rows[header_idx + 1:]:
        if not row:
            continue
        if row[0].startswith("Parameters:"):
            current_td = row[0].replace("Parameters:", "").strip()
            data[current_td] = {}
            continue
        if current_td is None or len(row) < len(header):
            continue
        test_name = test_name or row[1]
        output = row[2].strip()
        if not output or output.startswith("/"):
            continue
        values = {}
        for idx, corner in enumerate(CORNER_ORDER, start=8):
            raw = row[idx].strip()
            if not raw:
                continue
            if raw.lower() == "eval err":
                values[corner] = raw
            else:
                try:
                    values[corner] = float(raw)
                except ValueError:
                    values[corner] = raw
        if values:
            data[current_td][output] = values
    return {"test_name": test_name, "data": data}


def numeric_values(data, td, metric):
    vals = []
    by_corner = data[td][metric]
    for corner in CORNER_ORDER:
        value = by_corner.get(corner)
        if isinstance(value, (int, float)):
            vals.append(float(value))
    return vals


def stats(vals):
    return {
        "min": min(vals),
        "max": max(vals),
        "mean": sum(vals) / len(vals),
    }


def metric_stats(parsed):
    data = parsed["data"]
    out = {}
    for td in data:
        out[td] = {}
        for metric, values_by_corner in data[td].items():
            vals = [v for v in values_by_corner.values() if isinstance(v, (int, float))]
            eval_err = sum(1 for v in values_by_corner.values() if v == "eval err")
            if vals:
                min_v = min(vals)
                max_v = max(vals)
                min_corner = next(k for k in CORNER_ORDER if values_by_corner.get(k) == min_v)
                max_corner = next(k for k in CORNER_ORDER if values_by_corner.get(k) == max_v)
                out[td][metric] = {
                    "min": min_v,
                    "max": max_v,
                    "mean": sum(vals) / len(vals),
                    "min_corner": min_corner,
                    "max_corner": max_corner,
                    "eval_err": eval_err,
                    "count": len(vals),
                }
            else:
                out[td][metric] = {
                    "eval_err": eval_err,
                    "count": 0,
                }
    return out


def esc(s):
    return html.escape(str(s), quote=True)


def svg_text(x, y, text, size=12, fill="#233", anchor="middle", weight="400", rotate=None):
    transform = f' transform="rotate({rotate} {x} {y})"' if rotate else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial, Microsoft YaHei, sans-serif" '
        f'font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}"{transform}>'
        f"{esc(text)}</text>"
    )


def save_svg(name, body, width=980, height=540):
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" fill="#fbfcfd"/>'
        f"{body}</svg>"
    )
    (ASSET_DIR / name).write_text(svg, encoding="utf-8")


def line_chart(parsed, metric, title, y_label, y_min=None, y_max=None, ref_lines=None, filename=None):
    data = parsed["data"]
    tds = list(data.keys())
    series = {td: numeric_values(data, td, metric) for td in tds}
    vals = [v for arr in series.values() for v in arr]
    if y_min is None:
        y_min = math.floor((min(vals) - 0.1) * 2) / 2
    if y_max is None:
        y_max = math.ceil((max(vals) + 0.1) * 2) / 2
    width, height = 1080, 560
    ml, mr, mt, mb = 78, 32, 62, 108
    pw, ph = width - ml - mr, height - mt - mb
    colors = {"td=24.05n": "#2b6cb0", "td=28n": "#d9480f"}
    def sx(i):
        return ml + i * pw / (len(CORNER_ORDER) - 1)
    def sy(v):
        return mt + (y_max - v) * ph / (y_max - y_min)
    pieces = []
    pieces.append(svg_text(width / 2, 30, title, 20, "#14213d", weight="700"))
    pieces.append(svg_text(18, mt + ph / 2, y_label, 13, "#334", rotate=-90))
    pieces.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#8795a1" stroke-width="1"/>')
    pieces.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#8795a1" stroke-width="1"/>')
    ticks = 6
    for t in range(ticks + 1):
        v = y_min + (y_max - y_min) * t / ticks
        y = sy(v)
        pieces.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml+pw}" y2="{y:.1f}" stroke="#e6ebf0" stroke-width="1"/>')
        pieces.append(svg_text(ml - 10, y + 4, f"{v:.1f}", 11, "#5d6b78", anchor="end"))
    if ref_lines:
        for label, value, color in ref_lines:
            if y_min <= value <= y_max:
                y = sy(value)
                pieces.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml+pw}" y2="{y:.1f}" stroke="{color}" stroke-width="1.5" stroke-dasharray="6 5"/>')
                pieces.append(svg_text(ml + pw - 4, y - 6, label, 11, color, anchor="end", weight="700"))
    for i, label in enumerate(CORNER_LABELS):
        x = sx(i)
        pieces.append(f'<line x1="{x:.1f}" y1="{mt+ph}" x2="{x:.1f}" y2="{mt+ph+5}" stroke="#8795a1"/>')
        pieces.append(svg_text(x, mt + ph + 22, label, 10, "#425466", rotate=-35))
    legend_x = ml + 8
    for idx, td in enumerate(tds):
        color = colors.get(td, "#333")
        ly = 48 + idx * 22
        pieces.append(f'<line x1="{legend_x}" y1="{ly}" x2="{legend_x + 28}" y2="{ly}" stroke="{color}" stroke-width="3"/>')
        pieces.append(svg_text(legend_x + 36, ly + 4, td, 12, "#233", anchor="start", weight="700"))
    for td in tds:
        vals_td = series[td]
        color = colors.get(td, "#333")
        points = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(vals_td))
        pieces.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.6"/>')
        min_v = min(vals_td)
        max_v = max(vals_td)
        for i, v in enumerate(vals_td):
            radius = 4.0 if v in (min_v, max_v) else 3.2
            pieces.append(f'<circle cx="{sx(i):.1f}" cy="{sy(v):.1f}" r="{radius}" fill="#fbfcfd" stroke="{color}" stroke-width="2"/>')
        min_i = vals_td.index(min_v)
        pieces.append(svg_text(sx(min_i), sy(min_v) + 18, f"min {min_v:.2f}", 10, color, weight="700"))
    save_svg(filename or f"{metric.lower()}_corners.svg", "".join(pieces), width, height)


def grouped_bar_chart(parsed):
    data = parsed["data"]
    tds = list(data.keys())
    metrics = ["SWITCHESPOWER", "COMPOWER", "LOGICPOWER", "SYNCPOWER", "SRPOWER"]
    display = ["Switch", "Comparator", "Logic", "Sync", "SR"]
    means = {
        td: [stats(numeric_values(data, td, m))["mean"] * 1e6 for m in metrics]
        for td in tds
    }
    width, height = 920, 520
    ml, mr, mt, mb = 74, 40, 64, 78
    pw, ph = width - ml - mr, height - mt - mb
    y_max = math.ceil(max(v for arr in means.values() for v in arr) / 25) * 25
    colors = {"td=24.05n": "#2b6cb0", "td=28n": "#d9480f"}
    pieces = [svg_text(width / 2, 31, "Average Power Breakdown Across PVT", 20, "#14213d", weight="700")]
    pieces.append(svg_text(20, mt + ph / 2, "Power (uW)", 13, "#334", rotate=-90))
    pieces.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#8795a1"/>')
    pieces.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#8795a1"/>')
    for t in range(6):
        v = y_max * t / 5
        y = mt + (y_max - v) * ph / y_max
        pieces.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml+pw}" y2="{y:.1f}" stroke="#e6ebf0"/>')
        pieces.append(svg_text(ml - 8, y + 4, f"{v:.0f}", 11, "#5d6b78", anchor="end"))
    group_w = pw / len(metrics)
    bar_w = group_w * 0.26
    for i, label in enumerate(display):
        gx = ml + i * group_w + group_w / 2
        pieces.append(svg_text(gx, mt + ph + 28, label, 12, "#233", weight="700"))
        for j, td in enumerate(tds):
            val = means[td][i]
            x = gx + (j - 0.5) * bar_w * 1.35
            h = val * ph / y_max
            y = mt + ph - h
            pieces.append(f'<rect x="{x - bar_w/2:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{colors[td]}" rx="3"/>')
            pieces.append(svg_text(x, y - 7, f"{val:.1f}", 10, colors[td], weight="700"))
    lx = ml + pw - 180
    for j, td in enumerate(tds):
        y = 46 + j * 22
        pieces.append(f'<rect x="{lx}" y="{y-10}" width="18" height="10" fill="{colors[td]}"/>')
        pieces.append(svg_text(lx + 26, y, td, 12, "#233", anchor="start", weight="700"))
    save_svg("power_breakdown.svg", "".join(pieces), width, height)


def summary_bar_chart(parsed, summary):
    tds = list(parsed["data"].keys())
    groups = [
        ("Mean ENOB", [summary[td]["ENOB"]["mean"] for td in tds], "bit"),
        ("Worst ENOB", [summary[td]["ENOB"]["min"] for td in tds], "bit"),
        ("Mean SNR", [summary[td]["SNR"]["mean"] for td in tds], "dB"),
        ("Mean SFDR", [summary[td]["SFDR"]["mean"] for td in tds], "dB"),
    ]
    # Normalize each pair to show relative improvement; labels preserve real values.
    width, height = 960, 520
    ml, mr, mt, mb = 74, 42, 70, 72
    pw, ph = width - ml - mr, height - mt - mb
    colors = ["#2b6cb0", "#d9480f"]
    pieces = [svg_text(width / 2, 32, "td Selection: Dynamic Metric Comparison", 20, "#14213d", weight="700")]
    group_w = pw / len(groups)
    baseline_y = mt + ph
    pieces.append(f'<line x1="{ml}" y1="{baseline_y}" x2="{ml+pw}" y2="{baseline_y}" stroke="#8795a1"/>')
    for i, (name, values, unit) in enumerate(groups):
        lo = min(values) * 0.985
        hi = max(values) * 1.01
        if abs(hi - lo) < 1e-9:
            hi = lo + 1
        gx = ml + i * group_w + group_w / 2
        bar_w = group_w * 0.22
        for j, val in enumerate(values):
            normalized = (val - lo) / (hi - lo)
            h = 48 + normalized * (ph - 74)
            x = gx + (j - 0.5) * bar_w * 1.5
            y = baseline_y - h
            pieces.append(f'<rect x="{x - bar_w/2:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{colors[j]}" rx="4"/>')
            pieces.append(svg_text(x, y - 8, f"{val:.2f} {unit}", 11, colors[j], weight="700"))
        pieces.append(svg_text(gx, baseline_y + 28, name, 12, "#233", weight="700"))
    lx = ml + 12
    for j, td in enumerate(tds):
        y = 56 + j * 23
        pieces.append(f'<rect x="{lx}" y="{y-10}" width="18" height="10" fill="{colors[j]}"/>')
        pieces.append(svg_text(lx + 26, y, td, 12, "#233", anchor="start", weight="700"))
    save_svg("td_dynamic_comparison.svg", "".join(pieces), width, height)


def heatmap(parsed, td, metric):
    data = parsed["data"][td][metric]
    vals = [data[f"{p}_{i}"] for p in PROCS for i in range(3)]
    mn, mx = min(vals), max(vals)
    width, height = 720, 420
    ml, mt = 110, 76
    cell_w, cell_h = 120, 62
    pieces = [svg_text(width / 2, 32, f"{metric} Heatmap - {td}", 20, "#14213d", weight="700")]
    for j, temp in enumerate(TEMPS):
        pieces.append(svg_text(ml + j * cell_w + cell_w / 2, mt - 18, f"{temp}C", 13, "#233", weight="700"))
    for i, proc in enumerate(PROCS):
        pieces.append(svg_text(ml - 18, mt + i * cell_h + cell_h / 2 + 5, proc.upper(), 13, "#233", anchor="end", weight="700"))
        for j, temp in enumerate(TEMPS):
            corner = f"{proc}_{j}"
            val = data[corner]
            ratio = (val - mn) / (mx - mn) if mx > mn else 0.5
            # Blue to orange, with higher values cooler/cleaner.
            r = int(217 - ratio * 170)
            g = int(72 + ratio * 78)
            b = int(15 + ratio * 160)
            color = f"#{r:02x}{g:02x}{b:02x}"
            x = ml + j * cell_w
            y = mt + i * cell_h
            pieces.append(f'<rect x="{x}" y="{y}" width="{cell_w-4}" height="{cell_h-4}" fill="{color}" rx="6"/>')
            pieces.append(svg_text(x + cell_w / 2 - 2, y + cell_h / 2 + 5, f"{val:.2f}", 17, "#fff", weight="700"))
    pieces.append(svg_text(width / 2, height - 30, f"Range: {mn:.2f} to {mx:.2f} bit; lower values are warmer/orange.", 12, "#425466"))
    save_svg(f"{metric.lower()}_heatmap_{td.replace('=', '').replace('.', '_')}.svg", "".join(pieces), width, height)


def fom_chart(parsed, summary):
    tds = list(parsed["data"].keys())
    fs = 50e6
    avg_fom = []
    worst_fom = []
    avg_power = []
    worst_power = []
    for td in tds:
        p_abs_avg = abs(summary[td]["Power"]["mean"])
        p_abs_max = max(abs(summary[td]["Power"]["min"]), abs(summary[td]["Power"]["max"]))
        avg_power.append(p_abs_avg * 1e6)
        worst_power.append(p_abs_max * 1e6)
        avg_fom.append(p_abs_avg / (2 ** summary[td]["ENOB"]["mean"] * fs) * 1e15)
        worst_fom.append(p_abs_max / (2 ** summary[td]["ENOB"]["min"] * fs) * 1e15)
    width, height = 880, 500
    ml, mr, mt, mb = 74, 42, 66, 72
    pw, ph = width - ml - mr, height - mt - mb
    colors = ["#2b6cb0", "#d9480f"]
    groups = [
        ("Avg FoM", avg_fom, "fJ/conv-step"),
        ("Worst FoM", worst_fom, "fJ/conv-step"),
        ("Avg Power", avg_power, "uW"),
        ("Worst Power", worst_power, "uW"),
    ]
    pieces = [svg_text(width / 2, 31, "Energy Efficiency and Power Cost", 20, "#14213d", weight="700")]
    baseline_y = mt + ph
    pieces.append(f'<line x1="{ml}" y1="{baseline_y}" x2="{ml+pw}" y2="{baseline_y}" stroke="#8795a1"/>')
    group_w = pw / len(groups)
    for i, (name, vals, unit) in enumerate(groups):
        lo, hi = 0, max(vals) * 1.16
        gx = ml + i * group_w + group_w / 2
        bar_w = group_w * 0.22
        for j, val in enumerate(vals):
            h = val / hi * (ph - 20)
            x = gx + (j - 0.5) * bar_w * 1.5
            y = baseline_y - h
            pieces.append(f'<rect x="{x - bar_w/2:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{colors[j]}" rx="4"/>')
            label = f"{val:.2f}" if val < 10 else f"{val:.1f}"
            pieces.append(svg_text(x, y - 8, label, 11, colors[j], weight="700"))
        pieces.append(svg_text(gx, baseline_y + 26, name, 12, "#233", weight="700"))
        pieces.append(svg_text(gx, baseline_y + 45, unit, 10, "#5d6b78"))
    lx = ml + 12
    for j, td in enumerate(tds):
        y = 55 + j * 23
        pieces.append(f'<rect x="{lx}" y="{y-10}" width="18" height="10" fill="{colors[j]}"/>')
        pieces.append(svg_text(lx + 26, y, td, 12, "#233", anchor="start", weight="700"))
    save_svg("fom_power.svg", "".join(pieces), width, height)
    return {
        "avg_fom_fj": dict(zip(tds, avg_fom)),
        "worst_fom_fj": dict(zip(tds, worst_fom)),
        "avg_power_uW": dict(zip(tds, avg_power)),
        "worst_power_uW": dict(zip(tds, worst_power)),
    }


def main():
    parsed = parse_csv(CSV_PATH)
    summary = metric_stats(parsed)
    line_chart(
        parsed, "ENOB", "ENOB Across PVT Corners", "ENOB (bit)",
        y_min=10.9, y_max=12.0,
        ref_lines=[("11-bit floor", 11.0, "#6a737d")],
        filename="enob_corners.svg",
    )
    line_chart(
        parsed, "SNR", "SNR Across PVT Corners", "SNR (dB)",
        y_min=68.0, y_max=74.5,
        ref_lines=[("Ideal 12-bit SNR ~74 dB", 74.0, "#6a737d")],
        filename="snr_corners.svg",
    )
    line_chart(
        parsed, "SFDR", "SFDR Across PVT Corners", "SFDR (dB)",
        y_min=75.0, y_max=87.0,
        ref_lines=None,
        filename="sfdr_corners.svg",
    )
    grouped_bar_chart(parsed)
    summary_bar_chart(parsed, summary)
    heatmap(parsed, "td=28n", "ENOB")
    fom = fom_chart(parsed, summary)
    result = {
        "test_name": parsed["test_name"],
        "summary": summary,
        "fom": fom,
        "corners": CORNER_LABELS,
    }
    SUMMARY_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
