from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures"
REPORT_DIR = ROOT / "reports"
FIG_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

OUT_NOISE = FIG_DIR / "2026-06-09_NF10_三方案_噪声功率消除百分比.png"
OUT_SNR = FIG_DIR / "2026-06-09_NF10_三方案_SNR_corner对比.png"
OUT_NOISE_ASCII = FIG_DIR / "2026-06-09_nf10_three_scheme_noise_power_reduction.png"
OUT_SNR_ASCII = FIG_DIR / "2026-06-09_nf10_three_scheme_snr_corner_compare.png"
OUT_PDF = REPORT_DIR / "2026-06-09_NF10_仅采样噪声_三方案KT_C_可视化总结.pdf"

FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
]
FONT_PATH = next((p for p in FONT_CANDIDATES if p.exists()), None)


def font(size: int) -> ImageFont.FreeTypeFont:
    path = FONT_PATH or Path(r"C:\Windows\Fonts\arial.ttf")
    return ImageFont.truetype(str(path), size=size, index=0)


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_center(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, fnt, fill) -> None:
    w, h = text_size(draw, text, fnt)
    draw.text((xy[0] - w / 2, xy[1] - h / 2), text, font=fnt, fill=fill)


def rounded(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, width=1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def make_noise_chart() -> None:
    width, height = 1800, 1200
    img = Image.new("RGB", (width, height), "#f7f8fb")
    d = ImageDraw.Draw(img)
    navy = "#172033"
    grey = "#667085"
    blue = "#2f6fdd"
    teal = "#0f9f9a"
    green = "#16a36a"
    amber = "#f59e0b"
    red = "#e5484d"
    border = "#d9dee8"

    d.text((90, 70), "采样噪声功率相对于原本基准的变化", font=font(52), fill=navy)
    d.text(
        (92, 138),
        "基准：昨天 FIA，td=24.05n / AZ 约 0.05ns，NOISEFACTOR=10，仅采样噪声",
        font=font(27),
        fill=grey,
    )

    data = [
        ("原本基准", 100.00, 0.00, "#98a2b3"),
        ("FIA / 方案 A", 10.92, 89.08, blue),
        ("电流型 KT/C 无 FIA", 10.78, 89.22, teal),
        ("电压型 KT/C", 6.55, 93.45, green),
    ]
    x0, y0 = 390, 255
    bar_w, bar_h = 1000, 84
    gap = 102

    for i, (name, remain, removed, color) in enumerate(data):
        y = y0 + i * (bar_h + gap)
        d.text((90, y + 23), name, font=font(32), fill=navy)
        rounded(d, (x0, y, x0 + bar_w, y + bar_h), 22, "#e8ecf3")
        rem_w = max(4, bar_w * remain / 100)
        removed_w = bar_w - rem_w
        if removed_w > 0:
            rounded(d, (x0, y, x0 + removed_w, y + bar_h), 22, color)
        d.rounded_rectangle(
            (x0 + removed_w, y, x0 + bar_w, y + bar_h),
            radius=22,
            fill=amber if name == "原本基准" else red,
        )
        if name == "原本基准":
            draw_center(d, (x0 + bar_w / 2, y + bar_h / 2), "原本采样噪声功率 = 100%", font(31), "white")
        else:
            d.text((x0 + 30, y + 24), f"已消除 {removed:.2f}%", font=font(30), fill="white")
            d.text((x0 + bar_w + 32, y + 15), f"剩余 {remain:.2f}%", font=font(34), fill=red)
            d.text((x0 + bar_w + 36, y + 56), "越小越好", font=font(21), fill=grey)

    rounded(d, (95, 970, 1705, 1125), 28, "white", border, 2)
    d.text((135, 1000), "读图结论", font=font(32), fill=navy)
    d.text(
        (135, 1046),
        "电流型无 FIA 与 FIA 的消除幅度几乎相同，均约 89%；电压型 KT/C 进一步把剩余采样噪声压到约 6.55%。",
        font=font(28),
        fill=grey,
    )
    d.text(
        (135, 1086),
        "因此电流型无 FIA 是一个有效对比点，但不是比电压型更强的采样噪声压低方案。",
        font=font(28),
        fill=grey,
    )

    img.save(OUT_NOISE, quality=96)
    img.save(OUT_NOISE_ASCII, quality=96)


def make_snr_chart() -> None:
    width, height = 1800, 1200
    img = Image.new("RGB", (width, height), "#f7f8fb")
    d = ImageDraw.Draw(img)
    navy = "#172033"
    grey = "#667085"
    grid = "#d9dee8"
    blue = "#2f6fdd"
    teal = "#0f9f9a"
    green = "#16a36a"

    d.text((90, 70), "最终三组方案的 SNR 对比", font=font(52), fill=navy)
    d.text((92, 138), "对比点：td=28n / AZ 约 4ns，NOISEFACTOR=10，仅采样噪声", font=font(27), fill=grey)

    corners = ["tt", "ff", "ss", "sf", "fs", "avg"]
    fia = [65.9413, 63.5149, 63.2268, 63.9569, 63.1473, 63.9574]
    current_no_fia = [63.3285, 64.1136, 63.3537, 64.1105, 65.1685, 64.0150]
    voltage = [66.1321, 68.1704, 64.0304, 65.7646, 66.7739, 66.1743]

    x0, y0, x1, y1 = 135, 255, 1395, 850
    ymin, ymax = 60, 69
    for tick in range(ymin, ymax + 1):
        y = y1 - (tick - ymin) / (ymax - ymin) * (y1 - y0)
        d.line((x0, y, x1, y), fill=grid, width=2 if tick % 2 == 0 else 1)
        d.text((80, y - 14), f"{tick}", font=font(22), fill=grey)
    d.text((55, 215), "SNR / dB", font=font(24), fill=grey)

    group_w = (x1 - x0) / len(corners)
    bar_w = 38
    series = [
        ("FIA / 方案 A", fia, blue, -50),
        ("电流型无 FIA", current_no_fia, teal, 0),
        ("电压型 KT/C", voltage, green, 50),
    ]
    for i, corner in enumerate(corners):
        cx = x0 + group_w * i + group_w / 2
        for _, values, color, offset in series:
            val = values[i]
            top = y1 - (val - ymin) / (ymax - ymin) * (y1 - y0)
            rounded(d, (cx + offset - bar_w / 2, top, cx + offset + bar_w / 2, y1), 10, color)
            draw_center(d, (cx + offset, top - 20), f"{val:.1f}", font(18), navy)
        draw_center(d, (cx, y1 + 36), corner, font(26), navy)

    rounded(d, (1435, 285, 1715, 520), 24, "white", "#d9dee8", 2)
    legend_y = 320
    for label, _, color, _ in series:
        d.rectangle((1470, legend_y + 8, 1515, legend_y + 34), fill=color)
        d.text((1535, legend_y), label, font=font(24), fill=navy)
        legend_y += 60

    rounded(d, (1435, 570, 1715, 805), 24, "#ffffff", "#d9dee8", 2)
    draw_center(d, (1575, 620), "平均 SNR", font(28), navy)
    d.text((1485, 670), "FIA：63.9574 dB", font=font(23), fill=blue)
    d.text((1485, 710), "电流无 FIA：64.0150 dB", font=font(23), fill=teal)
    d.text((1485, 750), "电压型：66.1743 dB", font=font(23), fill=green)

    rounded(d, (95, 945, 1705, 1115), 28, "white", "#d9dee8", 2)
    d.text((135, 980), "读图结论", font=font(32), fill=navy)
    d.text(
        (135, 1026),
        "电流型无 FIA 的平均 SNR 只比 FIA 高 0.0576 dB，属于非常接近；电压型比电流型无 FIA 高 2.1593 dB。",
        font=font(28),
        fill=grey,
    )
    d.text(
        (135, 1066),
        "电压型优势主要来自 ff、fs 等角；电流型无 FIA 的意义更偏向“无 FIA 电流消除路线”的控制对照。",
        font=font(28),
        fill=grey,
    )

    img.save(OUT_SNR, quality=96)
    img.save(OUT_SNR_ASCII, quality=96)


def register_pdf_font() -> str:
    if FONT_PATH:
        pdfmetrics.registerFont(TTFont("ReportCN", str(FONT_PATH), subfontIndex=0))
        return "ReportCN"
    return "Helvetica"


def add_wrapped(c, text, x, y, max_chars, leading, font_name, size, color):
    c.setFont(font_name, size)
    c.setFillColor(color)
    line = ""
    for ch in text:
        trial = line + ch
        if len(trial) > max_chars and line:
            c.drawString(x, y, line)
            y -= leading
            line = ch
        else:
            line = trial
    if line:
        c.drawString(x, y, line)
        y -= leading
    return y


def make_pdf() -> None:
    font_name = register_pdf_font()
    c = canvas.Canvas(str(OUT_PDF), pagesize=A4)
    w, h = A4
    margin = 42

    c.setFillColor("#172033")
    c.setFont(font_name, 22)
    c.drawString(margin, h - 55, "NF10 仅采样噪声：三方案 KT/C 消除可视化总结")
    c.setFont(font_name, 11.5)
    c.setFillColor("#667085")
    c.drawString(margin, h - 78, "基准为昨天 FIA td=24.05n / AZ 约 0.05ns；当前正式比较点为 td=28n / AZ 约 4ns")

    y = h - 115
    bullets = [
        "FIA / 方案 A：平均 SNR 63.9574 dB，采样噪声功率剩余约 10.92%，即降低约 89.08%。",
        "电流型 KT/C 无 FIA：平均 SNR 64.0150 dB，采样噪声功率剩余约 10.78%，即降低约 89.22%。",
        "电压型 KT/C：平均 SNR 66.1743 dB，采样噪声功率剩余约 6.55%，即降低约 93.45%。",
        "当前新增电流型无 FIA 方案与 FIA 非常接近；电压型 KT/C 的噪声压低更强，但功耗也明显更高。",
    ]
    for b in bullets:
        c.setFillColor("#172033")
        c.setFont(font_name, 12.0)
        c.drawString(margin, y, "-")
        y = add_wrapped(c, b, margin + 16, y, 41, 17, font_name, 12.0, "#172033")
        y -= 2

    img1 = ImageReader(str(OUT_NOISE))
    img_w = w - 2 * margin
    img_h = img_w * 1200 / 1800
    c.drawImage(img1, margin, y - img_h - 10, width=img_w, height=img_h, preserveAspectRatio=True, mask="auto")
    c.showPage()

    c.setFillColor("#172033")
    c.setFont(font_name, 19)
    c.drawString(margin, h - 55, "SNR 与方案取舍")
    img2 = ImageReader(str(OUT_SNR))
    c.drawImage(img2, margin, h - 85 - img_h, width=img_w, height=img_h, preserveAspectRatio=True, mask="auto")

    c.setFillColor("#172033")
    c.setFont(font_name, 13)
    c.drawString(margin, 126, "简要判断")
    c.setFillColor("#667085")
    c.setFont(font_name, 11.2)
    c.drawString(margin, 105, "电流型 KT/C 无 FIA 是有效对比方案，但它与 FIA 在采样噪声消除百分比和平均 SNR 上几乎贴近。")
    c.drawString(margin, 88, "电压型 KT/C 在采样噪声压低上最强，适合强调 KT/C 消除能力；最终取舍需同时报告功耗代价。")
    c.setFillColor("#98a2b3")
    c.setFont(font_name, 9)
    c.drawRightString(w - margin, 38, "数据来源：项目 tables/ 当前有效 CSV；2026-06-09 三方案口径")
    c.save()


def main() -> None:
    make_noise_chart()
    make_snr_chart()
    make_pdf()
    print(str(OUT_NOISE))
    print(str(OUT_SNR))
    print(str(OUT_PDF))


if __name__ == "__main__":
    main()
