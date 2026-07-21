from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SRC = Path(r"C:\Users\Administrator\Desktop\ExplorerRun.0.csv")
FIG_DIR = ROOT / "figures"
REPORT_DIR = ROOT / "reports"
FIG_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

OUT_FIG = FIG_DIR / "2026-06-12_NF10_新结构_SNR变化规律.png"
OUT_REPORT = REPORT_DIR / "2026-06-12_NF10_新结构_SNR变化规律分析.md"


def setup_font() -> None:
    for candidate in [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]:
        if Path(candidate).exists():
            font_manager.fontManager.addfont(candidate)
            plt.rcParams["font.sans-serif"] = [font_manager.FontProperties(fname=candidate).get_name()]
            break
    plt.rcParams["axes.unicode_minus"] = False


def parse_params(text: str) -> dict[str, str]:
    params: dict[str, str] = {}
    for item in text.replace("Parameters:", "").split(","):
        if "=" in item:
            key, value = item.strip().split("=", 1)
            params[key] = value
    return params


def parse_numeric_with_unit(value: str) -> float:
    match = re.fullmatch(r"([0-9.]+)([a-zA-Z]*)", value.strip())
    if not match:
        return float(value)
    number = float(match.group(1))
    unit = match.group(2)
    if unit == "n":
        return number * 1e3
    if unit == "u":
        return number * 1e6
    if unit == "p":
        return number
    return number


def load_snr_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current_params: dict[str, str] = {}
    with SRC.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            point = row.get("Point", "")
            if point.startswith("Parameters:"):
                current_params = parse_params(point)
                continue
            if row.get("Output") != "SNR":
                continue
            wk1 = current_params["WK1"]
            fsr = int(current_params["FSR"])
            tdel = current_params["TDELCLKFIA"]
            rows.append(
                {
                    "point": int(row["Point"]),
                    "WK1": wk1,
                    "WK1_numeric": parse_numeric_with_unit(wk1),
                    "FSR": fsr,
                    "TDEL": tdel,
                    "TDEL_ps": parse_numeric_with_unit(tdel),
                    "SNR": float(row["Nominal"]),
                }
            )
    return rows


def avg(values: list[float]) -> float:
    return sum(values) / len(values)


def main() -> None:
    setup_font()
    rows = load_snr_rows()
    wk1_levels = ["300n", "600n", "800n", "1u", "2u", "5u"]
    fsr_levels = [1, 3, 5, 7]
    tdel_levels = [10, 50, 100, 200]
    colors = {1: "#64748b", 3: "#2f6fdd", 5: "#0f9f9a", 7: "#16a36a"}

    by_combo = {(r["WK1"], r["FSR"], r["TDEL_ps"]): r["SNR"] for r in rows}
    best = max(rows, key=lambda r: r["SNR"])
    worst = min(rows, key=lambda r: r["SNR"])

    by_fsr: dict[int, list[float]] = defaultdict(list)
    by_tdel: dict[int, list[float]] = defaultdict(list)
    by_wk1: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        by_fsr[r["FSR"]].append(r["SNR"])
        by_tdel[r["TDEL_ps"]].append(r["SNR"])
        by_wk1[r["WK1"]].append(r["SNR"])

    fig = plt.figure(figsize=(18, 11), dpi=180)
    gs = fig.add_gridspec(3, 4, width_ratios=[1, 1, 1, 1.08], height_ratios=[1, 1, 1], wspace=0.34, hspace=0.42)
    axes = [fig.add_subplot(gs[i // 3, i % 3]) for i in range(6)]
    ax_summary = fig.add_subplot(gs[:, 3])

    for ax, wk1 in zip(axes, wk1_levels):
        for fsr in fsr_levels:
            y = [by_combo[(wk1, fsr, t)] for t in tdel_levels]
            ax.plot(tdel_levels, y, marker="o", linewidth=2.2, markersize=5.2, color=colors[fsr], label=f"FSR={fsr}")
        ax.set_title(f"WK1 = {wk1}", fontsize=12, fontweight="bold")
        ax.set_xticks(tdel_levels)
        ax.set_ylim(63, 74)
        ax.grid(True, alpha=0.22)
        ax.set_xlabel("TDELCLKFIA / ps")
        ax.set_ylabel("SNR / dB")
        if wk1 == best["WK1"]:
            ax.scatter([best["TDEL_ps"]], [best["SNR"]], s=120, facecolor="none", edgecolor="#dc2626", linewidth=2.6, zorder=5)
            ax.annotate(
                f"最高 {best['SNR']:.2f} dB\nFSR={best['FSR']}, {best['TDEL']}",
                xy=(best["TDEL_ps"], best["SNR"]),
                xytext=(best["TDEL_ps"] + 16, best["SNR"] - 1.25),
                arrowprops={"arrowstyle": "->", "color": "#dc2626", "lw": 1.5},
                fontsize=9.2,
                color="#991b1b",
            )

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.43, 0.965), fontsize=10.5)

    ax_summary.axis("off")
    ax_summary.set_title("SNR 变化状态与原因", fontsize=15, fontweight="bold", loc="left", pad=10)
    summary_lines = [
        f"数据规模：{len(rows)} 点 = 6 个 WK1 × 4 个 FSR × 4 个 TDEL",
        "",
        f"最高点：Point {best['point']}",
        f"  WK1={best['WK1']}, FSR={best['FSR']}, TDEL={best['TDEL']}",
        f"  SNR={best['SNR']:.2f} dB",
        "",
        f"最低点：Point {worst['point']}",
        f"  WK1={worst['WK1']}, FSR={worst['FSR']}, TDEL={worst['TDEL']}",
        f"  SNR={worst['SNR']:.2f} dB",
        "",
        "平均趋势：",
        f"  FSR=1 → 7: {avg(by_fsr[1]):.2f} → {avg(by_fsr[7]):.2f} dB",
        f"  TDEL=10p → 200p: {avg(by_tdel[10]):.2f} → {avg(by_tdel[200]):.2f} dB",
        f"  最佳 WK1 平均：1u = {avg(by_wk1['1u']):.2f} dB",
        f"  最差 WK1 平均：5u = {avg(by_wk1['5u']):.2f} dB",
        "",
        "原因判断：",
        "1. FSR 增大后输入动态范围/有效信号摆幅更大，",
        "   信号功率占比提高，因此 SNR 整体上升。",
        "2. TDELCLKFIA 延迟变大后，FIA/比较器相关时序偏离",
        "   最优采样/再生窗口，平均 SNR 逐步下降。",
        "3. WK1 过小或过大都不是绝对最优；600n~1u",
        "   附近平均较高，5u 会带来更明显的负载/时序代价。",
    ]
    y = 0.98
    for line in summary_lines:
        size = 10.2
        weight = "bold" if line.endswith("：") or line.startswith("最高") or line.startswith("最低") else "normal"
        ax_summary.text(0.0, y, line, transform=ax_summary.transAxes, fontsize=size, fontweight=weight, va="top", color="#172033")
        y -= 0.044 if line else 0.032

    fig.suptitle("新结构 NF=10：SNR 随 WK1 / FSR / TDELCLKFIA 的变化规律", fontsize=20, fontweight="bold", x=0.43, y=0.995)
    fig.text(0.055, 0.025, "来源：C:/Users/Administrator/Desktop/ExplorerRun.0.csv；SNR = ADE Explorer 导出 Nominal 列", fontsize=9.5, color="#667085")
    fig.savefig(OUT_FIG, bbox_inches="tight")
    plt.close(fig)

    ranking = sorted(rows, key=lambda r: r["SNR"], reverse=True)
    report = [
        "# 2026-06-12 NF10 新结构 SNR 变化规律分析",
        "",
        "数据来源：`C:/Users/Administrator/Desktop/ExplorerRun.0.csv`。",
        "",
        f"输出图片：`{OUT_FIG.relative_to(ROOT)}`",
        "",
        "## 核心判断",
        "",
        f"- 最高 SNR：Point {best['point']}，WK1={best['WK1']}，FSR={best['FSR']}，TDELCLKFIA={best['TDEL']}，SNR={best['SNR']:.2f} dB。",
        f"- 最低 SNR：Point {worst['point']}，WK1={worst['WK1']}，FSR={worst['FSR']}，TDELCLKFIA={worst['TDEL']}，SNR={worst['SNR']:.2f} dB。",
        f"- FSR 从 1 到 7 时，平均 SNR 从 {avg(by_fsr[1]):.2f} dB 提升到 {avg(by_fsr[7]):.2f} dB，是最清晰的正相关因素。",
        f"- TDELCLKFIA 从 10p 到 200p 时，平均 SNR 从 {avg(by_tdel[10]):.2f} dB 降到 {avg(by_tdel[200]):.2f} dB，说明延迟增大整体不利。",
        f"- WK1 平均最优在 1u 附近，平均 SNR={avg(by_wk1['1u']):.2f} dB；5u 平均最低，平均 SNR={avg(by_wk1['5u']):.2f} dB。",
        "",
        "## 前 10 个 SNR 点",
        "",
        "| Rank | Point | WK1 | FSR | TDELCLKFIA | SNR / dB |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for i, r in enumerate(ranking[:10], start=1):
        report.append(f"| {i} | {r['point']} | {r['WK1']} | {r['FSR']} | {r['TDEL']} | {r['SNR']:.2f} |")
    report.extend(
        [
            "",
            "## 原因分析",
            "",
            "1. `FSR` 增大时，输入有效信号幅度/动态范围增加，信号功率相对噪声功率提高，因此 SNR 整体升高。",
            "2. `TDELCLKFIA` 增大时，FIA/比较器前后级时序更容易偏离最佳采样、复位或再生窗口，因此平均 SNR 呈下降趋势。",
            "3. `WK1` 存在中间最优区。过小可能驱动或开关导通不足，过大则引入更高负载和寄生，导致速度、建立和噪声表现变差；本次 sweep 中 600n~1u 区间整体最好，5u 明显劣化。",
        ]
    )
    OUT_REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")

    print(OUT_FIG)
    print(OUT_REPORT)
    print(f"best_point={best['point']} WK1={best['WK1']} FSR={best['FSR']} TDEL={best['TDEL']} SNR={best['SNR']:.2f}")


if __name__ == "__main__":
    main()
