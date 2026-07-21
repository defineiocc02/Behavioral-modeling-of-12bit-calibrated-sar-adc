from __future__ import annotations

import csv
import math
from pathlib import Path


MODE_LABELS = {
    "sampling_noise_only": "NF=10 / noisescale=10",
    "full_noise": "NF=1 / noisescale=1",
}

CORNERS = ["Nominal", "C0", "C1", "fs", "sf"]
MODES = ["sampling_noise_only", "full_noise"]


def fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def tex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("$", r"\$")
        .replace("#", r"\#")
        .replace("_", r"\_")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("~", r"\textasciitilde{}")
        .replace("^", r"\textasciicircum{}")
    )


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def frow(row: dict[str, str], key: str) -> float:
    return float(row[key])


def sort_key(row: dict[str, str]) -> tuple[int, int, float]:
    return (
        MODES.index(row["mode"]),
        CORNERS.index(row["corner"]),
        frow(row, "delta_td_ns"),
    )


def best_rows(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    best: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["mode"], row["corner"])
        if key not in best or frow(row, "snr_db") > frow(best[key], "snr_db"):
            best[key] = row
    return best


def coord_series(
    rows: list[dict[str, str]],
    mode: str,
    corner: str,
    metric: str,
    scale: float = 1.0,
) -> str:
    selected = [
        row
        for row in rows
        if row["mode"] == mode and row["corner"] == corner
    ]
    selected.sort(key=lambda row: frow(row, "delta_td_ns"))
    return " ".join(
        f"({fmt(frow(row, 'delta_td_ns'), 2)},{fmt(frow(row, metric) * scale, 3)})"
        for row in selected
    )


def plot_axis(
    rows: list[dict[str, str]],
    mode: str,
    metric: str,
    ylabel: str,
    scale: float,
    ymin: float | None = None,
) -> str:
    ymin_opt = f", ymin={ymin}" if ymin is not None else ""
    lines = [
        r"\begin{tikzpicture}",
        r"\begin{axis}[",
        r"width=\linewidth, height=0.32\textheight,",
        r"xlabel={$\Delta t_d$ (ns)},",
        f"ylabel={{{ylabel}}},",
        r"xmin=0, xmax=3.1,",
        r"grid=both,",
        r"legend style={font=\scriptsize, cells={anchor=west}},",
        r"legend pos=south east,",
        r"tick label style={font=\scriptsize},",
        r"label style={font=\small},",
        r"title style={font=\small},",
        f"title={{{MODE_LABELS[mode]}}}{ymin_opt}",
        r"]",
    ]
    for corner in CORNERS:
        coords = coord_series(rows, mode, corner, metric, scale)
        lines.append(f"\\addplot+[mark=*] coordinates {{{coords}}};")
        lines.append(f"\\addlegendentry{{{tex_escape(corner)}}}")
    lines.extend([r"\end{axis}", r"\end{tikzpicture}"])
    return "\n".join(lines)


def plot_pair(
    rows: list[dict[str, str]],
    metric: str,
    ylabel: str,
    caption: str,
    scale: float = 1.0,
    ymin: float | None = None,
) -> str:
    left = plot_axis(rows, "sampling_noise_only", metric, ylabel, scale, ymin)
    right = plot_axis(rows, "full_noise", metric, ylabel, scale, ymin)
    return "\n".join(
        [
            r"\begin{figure}[H]",
            r"\centering",
            r"\begin{minipage}{0.49\linewidth}",
            left,
            r"\end{minipage}\hfill",
            r"\begin{minipage}{0.49\linewidth}",
            right,
            r"\end{minipage}",
            f"\\caption{{{caption}}}",
            r"\end{figure}",
        ]
    )


def best_table(rows: list[dict[str, str]]) -> str:
    best = best_rows(rows)
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Best $t_d$ by corner using SNR as the selection criterion.}",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Corner & NF10 $t_d$ & NF10 SNR & NF10 ENOB & NF1 $t_d$ & NF1 SNR & NF1 ENOB \\",
        r"\midrule",
    ]
    for corner in CORNERS:
        nf10 = best[("sampling_noise_only", corner)]
        nf1 = best[("full_noise", corner)]
        lines.append(
            f"{tex_escape(corner)} & {tex_escape(nf10['td'])} & {fmt(frow(nf10, 'snr_db'))} "
            f"& {fmt(frow(nf10, 'enob'))} & {tex_escape(nf1['td'])} & "
            f"{fmt(frow(nf1, 'snr_db'))} & {fmt(frow(nf1, 'enob'))} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def corner_table(rows: list[dict[str, str]], corner: str) -> str:
    by_mode_td = {
        (row["mode"], row["td"]): row
        for row in rows
        if row["corner"] == corner
    }
    tds = sorted(
        {row["td"] for row in rows if row["corner"] == corner},
        key=lambda td: frow(by_mode_td[("sampling_noise_only", td)], "delta_td_ns"),
    )
    lines = [
        f"\\subsection*{{{tex_escape(corner)}}}",
        r"{\tiny\setlength{\tabcolsep}{2.5pt}",
        r"\begin{longtable}{lrrrrrrrrrr}",
        r"\toprule",
        (
            r"$t_d$ & $\Delta t_d$ ns & NF10 SNR & NF10 ENOB & NF10 SFDR "
            r"& NF10 $V_{ex}$ uV & NF1 SNR & NF1 ENOB & NF1 SFDR & NF1 $V_{ex}$ uV & $\Delta$SNR \\"
        ),
        r"\midrule",
        r"\endhead",
    ]
    for td in tds:
        nf10 = by_mode_td[("sampling_noise_only", td)]
        nf1 = by_mode_td[("full_noise", td)]
        delta_snr = frow(nf1, "snr_db") - frow(nf10, "snr_db")
        lines.append(
            f"{tex_escape(td)} & {fmt(frow(nf10, 'delta_td_ns'))} & "
            f"{fmt(frow(nf10, 'snr_db'))} & {fmt(frow(nf10, 'enob'))} & {fmt(frow(nf10, 'sfdr_db'))} & "
            f"{fmt(frow(nf10, 'excess_noise_rms_v') * 1e6, 1)} & "
            f"{fmt(frow(nf1, 'snr_db'))} & {fmt(frow(nf1, 'enob'))} & {fmt(frow(nf1, 'sfdr_db'))} & "
            f"{fmt(frow(nf1, 'excess_noise_rms_v') * 1e6, 1)} & {fmt(delta_snr)} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{longtable}", r"}"])
    return "\n".join(lines)


def render(rows: list[dict[str, str]]) -> str:
    rows = sorted(rows, key=sort_key)
    return "\n\n".join(
        [
            r"\documentclass[11pt]{article}",
            r"\usepackage[margin=0.7in]{geometry}",
            r"\usepackage{amsmath,booktabs,longtable,float,hyperref,siunitx}",
            r"\usepackage{xcolor}",
            r"\usepackage{pgfplots}",
            r"\pgfplotsset{compat=1.18}",
            r"\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=blue}",
            r"\title{NF=10 / NF=1 Noise Simulation Combined Report}",
            r"\author{Codex analysis}",
            r"\date{2026-05-15 HKT}",
            r"\begin{document}",
            r"\maketitle",
            r"\section*{Executive Summary}",
            (
                "Both raw result sets are captured and archived: NF=10 / noisescale=10 "
                "sampling-noise stress mode and NF=1 / noisescale=1 full-noise mode. "
                "Each data set contains 20 completed points across four $t_d$ settings "
                "and five process corners. All Spectre points completed with 0 errors. "
                "The analysis below is corner-by-corner; averages are not used as the "
                "primary conclusion."
            ),
            r"\section*{Noise Calculation}",
            (
                r"Assume $V_{FS}=V_{ref}=1$ Vpp and 12 bits:"
                "\n"
                r"\begin{align*}"
                "\n"
                r"LSB &= V_{FS}/2^{12}=244.141\,\mu V \\"
                "\n"
                r"V_{q,rms} &= LSB/\sqrt{12}=70.477\,\mu V \\"
                "\n"
                r"P_q &= 4.967054\times10^{-9}\,V^2 \\"
                "\n"
                r"P_{sig} &= (V_{FS}/(2\sqrt{2}))^2=0.125000\,V^2 \\"
                "\n"
                r"P_{total} &= P_{sig}/10^{SNR/10} \\"
                "\n"
                r"P_{excess} &= \max(P_{total}-P_q,0)"
                "\n"
                r"\end{align*}"
                "\n"
                r"If $V_{FS}=2V_{ref}$ is used, RMS values scale by 2 and powers by 4; "
                r"$t_d$ trends are unchanged."
            ),
            best_table(rows),
            r"\section*{Figures}",
            plot_pair(rows, "snr_db", "SNR (dB)", r"SNR versus $\Delta t_d$ by corner.", ymin=50),
            plot_pair(rows, "enob", "ENOB (bit)", r"ENOB versus $\Delta t_d$ by corner.", ymin=8),
            plot_pair(rows, "sfdr_db", "SFDR (dB)", r"SFDR versus $\Delta t_d$ by corner.", ymin=60),
            plot_pair(
                rows,
                "excess_noise_rms_v",
                r"$V_{ex,rms}$ ($\mu$V)",
                r"Inferred non-quantization noise RMS versus $\Delta t_d$ by corner.",
                scale=1e6,
                ymin=0,
            ),
            r"\clearpage",
            r"\section*{Corner-by-Corner Data}",
            "\n\n".join(corner_table(rows, corner) for corner in CORNERS),
            r"\section*{Engineering Readout}",
            (
                "NF=10 stress mode confirms that $t_d$ is a meaningful sampling-noise "
                "cancellation knob. The optimum is corner-dependent: Nominal, C1, and sf "
                "favor 27 ns by SNR, while C0 and fs favor 26 ns. NF=1 full-noise mode "
                "is cleaner in absolute SNR because it uses noisescale=1, while NF=10 "
                "intentionally stresses the selected sampling-noise contribution. Use "
                "the limiting corner, not an average, to choose the production $t_d$ target."
            ),
            r"\end{document}",
        ]
    )


def main() -> None:
    root = Path(__file__).resolve().parent
    csv_path = root / "NF10_NF1_noise_calculated_20260515.csv"
    out_path = root / "NF10_NF1_combined_analysis_20260515.tex"
    rows = load_rows(csv_path)
    out_path.write_text(render(rows), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
