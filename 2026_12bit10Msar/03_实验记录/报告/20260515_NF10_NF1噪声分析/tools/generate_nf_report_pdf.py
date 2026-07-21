from __future__ import annotations

import csv
import math
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String


ROOT = Path(__file__).resolve().parent
PDF_PATH = ROOT / "NF10_NF1_combined_analysis_20260515.pdf"
CALC_CSV = ROOT / "NF10_NF1_noise_calculated_20260515.csv"

CORNERS = ["Nominal", "C0", "C1", "fs", "sf"]
TDS = ["24.05n", "25n", "26n", "27n"]
MODE_LABEL = {
    "sampling_noise_only": "NF=10 sample-noise stress",
    "full_noise": "NF=1 full-noise",
}
MODE_SHORT = {
    "sampling_noise_only": "NF=10",
    "full_noise": "NF=1",
}
MODE_COLOR = {
    "sampling_noise_only": colors.HexColor("#d95f02"),
    "full_noise": colors.HexColor("#1f77b4"),
}


def fnum(value: str | float) -> float:
    return float(value)


def fmt(value: str | float, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"


def sci(value: str | float, digits: int = 3) -> str:
    return f"{float(value):.{digits}e}"


def read_rows() -> list[dict[str, str]]:
    with CALC_CSV.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["delta_td_ns_num"] = fnum(row["delta_td_ns"])
        row["snr_num"] = fnum(row["snr_db"])
        row["enob_num"] = fnum(row["enob"])
        row["sfdr_num"] = fnum(row["sfdr_db"])
        row["excess_noise_log"] = math.log10(fnum(row["excess_noise_power_v2"]))
    return rows


ROWS = read_rows()


def get_row(mode: str, corner: str, td: str) -> dict[str, str]:
    for row in ROWS:
        if row["mode"] == mode and row["corner"] == corner and row["td"] == td:
            return row
    raise KeyError((mode, corner, td))


def best_by_snr(mode: str, corner: str) -> dict[str, str]:
    rows = [r for r in ROWS if r["mode"] == mode and r["corner"] == corner]
    return max(rows, key=lambda r: fnum(r["snr_db"]))


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(doc.leftMargin, 0.28 * inch, "NF=10 / NF=1 noise simulation report")
    canvas.drawRightString(
        doc.pagesize[0] - doc.rightMargin,
        0.28 * inch,
        f"Page {doc.page}",
    )
    canvas.restoreState()


def base_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "Small",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            "Note",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=10.5,
            textColor=colors.HexColor("#444444"),
        )
    )
    return styles


def best_table() -> Table:
    data = [
        [
            "Corner",
            "NF=10 best td",
            "NF=10 SNR",
            "NF=10 ENOB",
            "NF=10 SFDR",
            "NF=1 best td",
            "NF=1 SNR",
            "NF=1 ENOB",
            "NF=1 SFDR",
        ]
    ]
    for corner in CORNERS:
        nf10 = best_by_snr("sampling_noise_only", corner)
        nf1 = best_by_snr("full_noise", corner)
        data.append(
            [
                corner,
                nf10["td"],
                fmt(nf10["snr_db"]),
                fmt(nf10["enob"]),
                fmt(nf10["sfdr_db"]),
                nf1["td"],
                fmt(nf1["snr_db"]),
                fmt(nf1["enob"]),
                fmt(nf1["sfdr_db"]),
            ]
        )
    table = Table(data, repeatRows=1)
    table.setStyle(common_table_style(header_bg="#e8eef3"))
    return table


def common_table_style(header_bg="#f1f4f6") -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#222222")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.6),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfcfcf")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fbfbfb")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )


def line_chart(metric: str, title: str, y_label: str, y_fmt, transform=lambda r: None) -> Drawing:
    width, height = 760, 420
    left, right, top, bottom = 62, 26, 45, 34
    panel_gap = 10
    panel_h = (height - top - bottom - panel_gap * (len(CORNERS) - 1)) / len(CORNERS)
    plot_w = width - left - right
    vals = [transform(row) for row in ROWS]
    ymin, ymax = min(vals), max(vals)
    pad = (ymax - ymin) * 0.12 or 1
    ymin -= pad
    ymax += pad
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#fbfbf8"), strokeColor=None))
    drawing.add(String(left, height - 24, title, fontName="Helvetica-Bold", fontSize=14, fillColor=colors.HexColor("#222222")))
    legend_y = height - 28
    drawing.add(Circle(width - 250, legend_y + 4, 3, fillColor=MODE_COLOR["sampling_noise_only"], strokeColor=None))
    drawing.add(String(width - 242, legend_y, "NF=10 stress", fontName="Helvetica", fontSize=8))
    drawing.add(Circle(width - 145, legend_y + 4, 3, fillColor=MODE_COLOR["full_noise"], strokeColor=None))
    drawing.add(String(width - 137, legend_y, "NF=1 full", fontName="Helvetica", fontSize=8))

    def x_pos(delta):
        return left + delta / 3.1 * plot_w

    for idx, corner in enumerate(CORNERS):
        y0 = height - top - (idx + 1) * panel_h - idx * panel_gap
        drawing.add(String(8, y0 + panel_h / 2 - 4, corner, fontName="Helvetica-Bold", fontSize=9, fillColor=colors.HexColor("#333333")))
        drawing.add(Rect(left, y0, plot_w, panel_h, fillColor=colors.white, strokeColor=colors.HexColor("#dddddd"), strokeWidth=0.4))
        for g in range(5):
            yy = y0 + g * panel_h / 4
            val = ymin + g * (ymax - ymin) / 4
            drawing.add(Line(left, yy, left + plot_w, yy, strokeColor=colors.HexColor("#e9e9e9"), strokeWidth=0.35))
            drawing.add(String(left - 6, yy - 3, y_fmt(val), textAnchor="end", fontName="Helvetica", fontSize=6.5, fillColor=colors.HexColor("#666666")))
        for xt in [0, 1, 2, 3]:
            xx = x_pos(xt)
            drawing.add(Line(xx, y0, xx, y0 + panel_h, strokeColor=colors.HexColor("#f0f0f0"), strokeWidth=0.3))
            if idx == len(CORNERS) - 1:
                drawing.add(String(xx, bottom - 16, str(xt), textAnchor="middle", fontName="Helvetica", fontSize=7))

        def y_pos(val):
            return y0 + (val - ymin) / (ymax - ymin) * panel_h

        for mode in ["sampling_noise_only", "full_noise"]:
            pts = []
            for td in TDS:
                row = get_row(mode, corner, td)
                pts.append((x_pos(fnum(row["delta_td_ns"])), y_pos(transform(row))))
            for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
                drawing.add(Line(x1, y1, x2, y2, strokeColor=MODE_COLOR[mode], strokeWidth=1.5))
            for xx, yy in pts:
                drawing.add(Circle(xx, yy, 2.5, fillColor=MODE_COLOR[mode], strokeColor=colors.white, strokeWidth=0.6))
    drawing.add(String(width / 2, 8, "Delta td from 24 ns (ns)", textAnchor="middle", fontName="Helvetica", fontSize=8))
    drawing.add(String(4, height / 2, y_label, textAnchor="middle", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#333333"), transform=[0, 1, -1, 0, 4, height / 2]))
    return drawing


def heatmap(mode: str, title: str) -> Drawing:
    width, height = 760, 270
    left, top = 92, 52
    cell_w, cell_h = 142, 34
    vals = [math.log10(fnum(r["excess_noise_power_v2"])) for r in ROWS if r["mode"] == mode]
    vmin, vmax = min(vals), max(vals)
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#fbfbf8"), strokeColor=None))
    drawing.add(String(left, height - 25, title, fontName="Helvetica-Bold", fontSize=13, fillColor=colors.HexColor("#222222")))
    for j, td in enumerate(TDS):
        drawing.add(String(left + j * cell_w + cell_w / 2, height - top + 12, td, textAnchor="middle", fontName="Helvetica-Bold", fontSize=8))
    for i, corner in enumerate(CORNERS):
        y = height - top - (i + 1) * cell_h
        drawing.add(String(left - 8, y + cell_h / 2 - 3, corner, textAnchor="end", fontName="Helvetica-Bold", fontSize=8))
        for j, td in enumerate(TDS):
            row = get_row(mode, corner, td)
            lv = math.log10(fnum(row["excess_noise_power_v2"]))
            t = 0 if vmax == vmin else (lv - vmin) / (vmax - vmin)
            c0 = (246, 239, 247)
            c1 = (49, 130, 189)
            rgb = [int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3)]
            fill = colors.Color(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
            x = left + j * cell_w
            drawing.add(Rect(x, y, cell_w - 4, cell_h - 4, fillColor=fill, strokeColor=colors.white, strokeWidth=0.6))
            drawing.add(String(x + cell_w / 2 - 2, y + cell_h / 2 - 4, sci(row["excess_noise_power_v2"], 2), textAnchor="middle", fontName="Helvetica", fontSize=7, fillColor=colors.black))
    return drawing


def delta_bar_chart() -> Drawing:
    width, height = 760, 300
    left, right, top, bottom = 60, 20, 44, 48
    plot_w, plot_h = width - left - right, height - top - bottom
    vals = []
    for corner in CORNERS:
        for td in TDS:
            nf10 = get_row("sampling_noise_only", corner, td)
            nf1 = get_row("full_noise", corner, td)
            vals.append((corner, td, fnum(nf1["snr_db"]) - fnum(nf10["snr_db"])))
    ymin = math.floor(min(v[2] for v in vals) - 1)
    ymax = math.ceil(max(v[2] for v in vals) + 1)
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#fbfbf8"), strokeColor=None))
    drawing.add(String(left, height - 23, "NF=1 minus NF=10 SNR by Corner and td", fontName="Helvetica-Bold", fontSize=13))

    def y_pos(val):
        return bottom + (val - ymin) / (ymax - ymin) * plot_h

    drawing.add(Rect(left, bottom, plot_w, plot_h, fillColor=colors.white, strokeColor=colors.HexColor("#dddddd"), strokeWidth=0.4))
    for g in range(6):
        val = ymin + g * (ymax - ymin) / 5
        yy = y_pos(val)
        drawing.add(Line(left, yy, left + plot_w, yy, strokeColor=colors.HexColor("#e8e8e8"), strokeWidth=0.35))
        drawing.add(String(left - 6, yy - 3, fmt(val, 1), textAnchor="end", fontName="Helvetica", fontSize=7))
    group_w = plot_w / len(CORNERS)
    td_colors = [colors.HexColor("#8dd3c7"), colors.HexColor("#80b1d3"), colors.HexColor("#fdb462"), colors.HexColor("#b3de69")]
    bar_w = (group_w - 24) / len(TDS) - 3
    for i, corner in enumerate(CORNERS):
        gx = left + i * group_w + 12
        drawing.add(String(gx + group_w / 2 - 12, 20, corner, textAnchor="middle", fontName="Helvetica-Bold", fontSize=8))
        for j, td in enumerate(TDS):
            val = [v[2] for v in vals if v[0] == corner and v[1] == td][0]
            x = gx + j * (bar_w + 3)
            y0 = y_pos(0)
            y1 = y_pos(val)
            drawing.add(Rect(x, min(y0, y1), bar_w, abs(y1 - y0), fillColor=td_colors[j], strokeColor=colors.white, strokeWidth=0.5))
    for j, td in enumerate(TDS):
        drawing.add(Rect(left + j * 76, 2, 8, 8, fillColor=td_colors[j], strokeColor=None))
        drawing.add(String(left + j * 76 + 12, 2, td, fontName="Helvetica", fontSize=7))
    return drawing


def corner_table(corner: str) -> Table:
    data = [
        [
            "td",
            "dtd ns",
            "NF10 SNR",
            "NF10 ENOB",
            "NF10 SFDR",
            "NF10 Pexcess",
            "NF1 SNR",
            "NF1 ENOB",
            "NF1 SFDR",
            "NF1 Pexcess",
        ]
    ]
    for td in TDS:
        nf10 = get_row("sampling_noise_only", corner, td)
        nf1 = get_row("full_noise", corner, td)
        data.append(
            [
                td,
                fmt(nf10["delta_td_ns"], 2),
                fmt(nf10["snr_db"], 2),
                fmt(nf10["enob"], 2),
                fmt(nf10["sfdr_db"], 2),
                sci(nf10["excess_noise_power_v2"], 2),
                fmt(nf1["snr_db"], 2),
                fmt(nf1["enob"], 2),
                fmt(nf1["sfdr_db"], 2),
                sci(nf1["excess_noise_power_v2"], 2),
            ]
        )
    table = Table(data, repeatRows=1)
    table.setStyle(common_table_style())
    return table


def build_pdf():
    styles = base_styles()
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=landscape(A4),
        leftMargin=0.45 * inch,
        rightMargin=0.45 * inch,
        topMargin=0.42 * inch,
        bottomMargin=0.45 * inch,
        title="NF10 NF1 Noise Simulation Report",
    )
    story = []
    story.append(Paragraph("NF=10 / NF=1 Noise Simulation Combined Report", styles["Title"]))
    story.append(Paragraph("Generated 2026-05-15 HKT. Current Maestro ExplorerRun.0 only; older Interactive runs excluded.", styles["Small"]))
    story.append(Spacer(1, 0.12 * inch))
    story.append(Paragraph("<b>Executive Summary</b>", styles["Heading2"]))
    story.append(Paragraph("NF=10 / noisescale=10 is the user-defined sampling-noise stress mode. NF=1 / noisescale=1 is the user-defined full-noise mode. Both have 20 completed points and all Spectre runs completed with 0 errors.", styles["Small"]))
    story.append(Paragraph("The analysis is intentionally per-corner: Nominal, C0, C1, fs, and sf. Averages are not used as the decision basis.", styles["Small"]))
    story.append(Paragraph("Because the two modes use different noise scales, compare td trends and stress gap per corner rather than treating absolute SNR as a direct physical ranking of all noise sources.", styles["Small"]))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph("<b>Noise Calculation</b>", styles["Heading2"]))
    story.append(Paragraph("Assume VFS = Vref = 1 Vpp and 12-bit ADC. LSB = 244.141 uV, Vq,rms = 70.477 uV, Pq = 4.967054e-9 V^2, Psig = 0.125 V^2. For each SNR: Ptotal = Psig / 10^(SNR/10), Pexcess = max(Ptotal - Pq, 0). If using differential full-scale VFS = 2*Vref, RMS values scale by 2 and powers by 4; td trends do not change.", styles["Small"]))
    story.append(Paragraph("<b>Best td by corner</b>", styles["Heading2"]))
    story.append(best_table())
    story.append(PageBreak())
    story.append(Paragraph("SNR and ENOB Trends", styles["Heading2"]))
    story.append(line_chart("snr_num", "SNR vs Delta td by Corner", "SNR (dB)", lambda v: fmt(v, 1), lambda r: fnum(r["snr_db"])))
    story.append(Spacer(1, 0.05 * inch))
    story.append(line_chart("enob_num", "ENOB vs Delta td by Corner", "ENOB (bits)", lambda v: fmt(v, 2), lambda r: fnum(r["enob"])))
    story.append(PageBreak())
    story.append(Paragraph("SFDR and Noise Trends", styles["Heading2"]))
    story.append(line_chart("sfdr_num", "SFDR vs Delta td by Corner", "SFDR (dB)", lambda v: fmt(v, 1), lambda r: fnum(r["sfdr_db"])))
    story.append(Spacer(1, 0.05 * inch))
    story.append(line_chart("excess_noise_log", "Inferred Excess Noise Power vs Delta td by Corner", "log10 Pexcess", lambda v: fmt(v, 2), lambda r: fnum(r["excess_noise_log"])))
    story.append(PageBreak())
    story.append(Paragraph("Mode Difference and Heatmaps", styles["Heading2"]))
    story.append(delta_bar_chart())
    story.append(Spacer(1, 0.08 * inch))
    story.append(heatmap("sampling_noise_only", "NF=10 Sample-Noise Stress: Excess Noise Power Heatmap"))
    story.append(Spacer(1, 0.05 * inch))
    story.append(heatmap("full_noise", "NF=1 Full-Noise: Excess Noise Power Heatmap"))
    story.append(PageBreak())
    story.append(Paragraph("Corner-by-Corner Data", styles["Heading2"]))
    for corner in CORNERS:
        nf10 = best_by_snr("sampling_noise_only", corner)
        nf1 = best_by_snr("full_noise", corner)
        story.append(Paragraph(corner, styles["Heading3"]))
        story.append(corner_table(corner))
        story.append(Paragraph(f"NF=10 best SNR is {fmt(nf10['snr_db'])} dB at {nf10['td']}. NF=1 best SNR is {fmt(nf1['snr_db'])} dB at {nf1['td']}. Treat this as the corner-specific td preference; do not replace it with a global average.", styles["Note"]))
        story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph("<b>Engineering Readout</b>", styles["Heading2"]))
    story.append(Paragraph("NF=10 stress mode confirms td is a meaningful sampling-noise cancellation knob. Nominal, C1, and sf favor 27 ns by SNR in the stressed run, while C0 and fs favor 26 ns. NF=1 full-noise mode is cleaner in absolute SNR because it uses noisescale=1; the NF=10 run deliberately stresses sampling noise with noisescale=10. Choose td by the limiting corner, not by a global average.", styles["Small"]))
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)


if __name__ == "__main__":
    build_pdf()
    print(PDF_PATH)
