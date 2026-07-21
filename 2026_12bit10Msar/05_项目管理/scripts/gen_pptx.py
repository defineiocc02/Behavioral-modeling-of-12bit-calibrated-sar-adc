#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate visually appealing Nature-style PPTX for CAAZ SAR ADC report."""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
import os

# === Color palette ===
BLUE   = RGBColor(0, 82, 136)
BLUE_L = RGBColor(220, 235, 250)
BLUE_D = RGBColor(0, 55, 100)
TEAL   = RGBColor(0, 128, 128)
TEAL_L = RGBColor(220, 245, 245)
WHITE  = RGBColor(255, 255, 255)
DGRAY  = RGBColor(50, 50, 50)
MGRAY  = RGBColor(140, 140, 140)
LGRAY  = RGBColor(235, 235, 240)
GREEN  = RGBColor(0, 130, 50)
GREEN_L= RGBColor(220, 245, 220)
ORANGE = RGBColor(220, 120, 20)
RED    = RGBColor(200, 50, 50)

FIGS = "D:/ReedZhao/Document/Obsidian/日常/10_项目区/2026_12bit50Msar/05_研究报告/figures"
OUT  = "D:/ReedZhao/Document/Obsidian/日常/10_项目区/2026_12bit50Msar/07_项目管理"

prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)
W = prs.slide_width
H = prs.slide_height

# === Helper functions ===
def add_rect(slide, l, t, w, h, color, alpha=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape

def add_textbox(slide, l, t, w, h, text, size=18, bold=False, color=DGRAY, align=PP_ALIGN.LEFT, name=""):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = text
    p.font.size = Pt(size); p.font.bold = bold; p.font.color.rgb = color; p.alignment = align
    return tb

def add_bullets(slide, l, t, w, h, items, size=16):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    for i, (txt, lvl) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = txt; p.font.size = Pt(size - lvl*2)
        p.font.color.rgb = DGRAY; p.level = lvl; p.space_after = Pt(3)
    return tb

def add_fig(slide, path, l, t, w, h=None):
    if os.path.exists(path):
        img = slide.shapes.add_picture(path, Inches(l), Inches(t), Inches(w))
        if h: img.height = Inches(h)
        return img
    return None

def add_metric_box(slide, l, t, w, h, label, value, color=BLUE):
    """A colored box with a big metric value and label underneath."""
    add_rect(slide, l, t, w, h, color)
    add_textbox(slide, l+0.15, t+0.1, w-0.3, 0.5, value, size=28, bold=True, color=WHITE)
    add_textbox(slide, l+0.15, t+0.55, w-0.3, 0.4, label, size=11, color=WHITE)

# ========================================================================
# SLIDE 1: Title Slide (bold blue gradient + key metrics)
# ========================================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_rect(slide, 0, 0, 13.333, 7.5, BLUE_D)
add_rect(slide, 0, 0, 10.5, 7.5, BLUE)

add_textbox(slide, 0.8, 1.2, 10, 0.4, "12-bit 50MS/s SAR ADC with CAAZ", size=40, bold=True, color=WHITE)
add_textbox(slide, 0.8, 1.8, 10, 0.4, "完整仿真报告 · 组会汇报", size=24, color=RGBColor(180, 215, 255))
add_rect(slide, 0.8, 2.3, 4, Pt(3), WHITE)

# Key metric boxes
add_metric_box(slide, 0.8, 3.0, 2.3, 1.1, "ENOB (TT, 26ns)", "11.61 bit", TEAL)
add_metric_box(slide, 3.3, 3.0, 2.3, 1.1, "SNR (TT, 26ns)", "71.81 dB", GREEN)
add_metric_box(slide, 5.8, 3.0, 2.3, 1.1, "CAAZ η (TT)", "87.9%", ORANGE)
add_metric_box(slide, 8.3, 3.0, 2.3, 1.1, "Total Power", "720 µW", RGBColor(100, 60, 160))

add_textbox(slide, 0.8, 4.5, 10, 0.3, "TSMC 18RF · Cadence Spectre 231 · 全 PVT 角 · 跨批次验证", size=14, color=RGBColor(160, 200, 240))
add_textbox(slide, 0.8, 5.0, 10, 0.3, "HUST-SAR-2026-002  |  2026-05-13  |  Rev.2.0", size=11, color=MGRAY)

# ========================================================================
# SLIDE 2: Outline
# ========================================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_rect(slide, 0, 0, 0.12, 7.5, BLUE)
add_textbox(slide, 1.0, 0.5, 6, 0.6, "汇报提纲", size=32, bold=True, color=BLUE)
add_rect(slide, 1.0, 1.1, 3, Pt(3), BLUE)

sections = [
    ("01", "设计目标与仿真环境"),
    ("02", "NF=1 基线性能 — PVT 全角"),
    ("03", "td 对比 — 24.05ns vs 26.0ns"),
    ("04", "CAAZ 噪声消除效率 η"),
    ("05", "跨批次数据验证"),
    ("06", "功耗与 SFDR 分析"),
    ("07", "风险评估与优化方向"),
    ("08", "总结与建议"),
]
for i, (num, title) in enumerate(sections):
    y = 1.6 + i * 0.65
    add_rect(slide, 1.0, y, 0.5, 0.45, BLUE if i%2==0 else TEAL)
    add_textbox(slide, 1.0, y+0.03, 0.5, 0.4, num, size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_textbox(slide, 1.7, y+0.05, 8, 0.4, title, size=17, color=DGRAY)

# ========================================================================
# SLIDE 3: Design Targets
# ========================================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_rect(slide, 0, 0, 0.12, 7.5, BLUE)
add_textbox(slide, 1.0, 0.5, 8, 0.6, "设计目标与达标情况", size=32, bold=True, color=BLUE)
add_rect(slide, 1.0, 1.1, 3, Pt(3), BLUE)

# Table
rows, cols = 6, 4
tbl_shape = slide.shapes.add_table(rows, cols, Inches(1.0), Inches(1.6), Inches(8.5), Inches(2.8))
tbl = tbl_shape.table
headers = ["指标", "目标值", "仿真结果 (TT, 26ns)", "结论"]
data = [
    ["ENOB",    "> 11 bit",  "11.61 bit",    "✅ 超额完成"],
    ["SNR",     "> 70 dB",   "71.81 dB",     "✅"],
    ["SFDR",    "> 75 dB",   "84.01 dB",     "✅ 超额完成"],
    ["总功耗",   "< 1 mW",    "720 µW",       "✅"],
    ["CAAZ η",  "> 85%",     "87.9%",        "✅"],
]
# header row
for j, h in enumerate(headers):
    c = tbl.cell(0, j); c.text = h
    c.fill.solid(); c.fill.fore_color.rgb = BLUE
    for p in c.text_frame.paragraphs:
        p.font.color.rgb = WHITE; p.font.bold = True; p.font.size = Pt(16)
# data rows
for i, row in enumerate(data):
    for j, val in enumerate(row):
        c = tbl.cell(i+1, j); c.text = val
        c.fill.solid()
        c.fill.fore_color.rgb = RGBColor(240,245,252) if i%2==0 else WHITE
        for p in c.text_frame.paragraphs:
            p.font.size = Pt(15); p.font.color.rgb = DGRAY
            if "✅" in str(val):
                p.font.color.rgb = GREEN; p.font.bold = True

# Highlight banner
add_rect(slide, 1.0, 4.8, 8.5, 0.7, BLUE_L)
add_textbox(slide, 1.2, 4.9, 8, 0.5,
            "✦ 全 corners ENOB > 11.4 bit  ·  ENOB 极差仅 0.14 bit  ·  SFDR > 81 dB",
            size=16, bold=True, color=BLUE, align=PP_ALIGN.CENTER)

# Key insight boxes
add_rect(slide, 1.0, 5.8, 2.5, 0.8, GREEN_L)
add_textbox(slide, 1.2, 5.9, 2.2, 0.6, "🎯 ENOB目标\n均已达成", size=14, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
add_rect(slide, 3.7, 5.8, 2.5, 0.8, TEAL_L)
add_textbox(slide, 3.9, 5.9, 2.2, 0.6, "📈 SFDR\n84 dB 超额", size=14, bold=True, color=TEAL, align=PP_ALIGN.CENTER)
add_rect(slide, 6.4, 5.8, 3.1, 0.8, RGBColor(255,235,220))
add_textbox(slide, 6.6, 5.9, 2.8, 0.6, "⚡ 功耗 720 µW\n< 1 mW 目标达成", size=14, bold=True, color=ORANGE, align=PP_ALIGN.CENTER)

# ========================================================================
# SLIDE 4: PVT Performance (full-width figure)
# ========================================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_rect(slide, 0, 0, 0.12, 7.5, BLUE)
add_textbox(slide, 1.0, 0.3, 8, 0.5, "NF=1 基线性能 — PVT 全角", size=28, bold=True, color=BLUE)
add_textbox(slide, 1.0, 0.8, 8, 0.3, "td=26.0 ns  |  TT/FF/SS/SF/FS  |  NF=1（无噪声注入）", size=13, color=MGRAY)
add_fig(slide, f"{FIGS}/Fig1_PVT_Performance.png", 0.3, 1.3, 12.5)

# ========================================================================
# SLIDE 5: td Comparison
# ========================================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_rect(slide, 0, 0, 0.12, 7.5, BLUE)
add_textbox(slide, 1.0, 0.3, 8, 0.5, "td 对比 — CAAZ 建立时间优化", size=28, bold=True, color=BLUE)

add_fig(slide, f"{FIGS}/Fig4_td_Sweep_SNR.png", 0.3, 1.2, 6.8)

# Right side: key findings cards
findings = [
    ("🔥 高温角收益最大", "SS/SF (85°C) SNR +1.8 dB", GREEN_L, GREEN),
    ("❄️ 低温角无变化", "FF/FS (-40°C)  gm 大, 24ns 已充分", TEAL_L, TEAL),
    ("✅ 结论", "26.0 ns 为最优设计点", BLUE_L, BLUE),
]
for i, (title, desc, bg, fg) in enumerate(findings):
    y = 1.3 + i * 1.5
    add_rect(slide, 7.6, y, 5, 1.2, bg)
    add_textbox(slide, 7.8, y+0.1, 4.5, 0.4, title, size=18, bold=True, color=fg)
    add_textbox(slide, 7.8, y+0.5, 4.5, 0.5, desc, size=13, color=DGRAY)

# ========================================================================
# SLIDE 6: CAAZ Eta
# ========================================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_rect(slide, 0, 0, 0.12, 7.5, BLUE)
add_textbox(slide, 1.0, 0.3, 8, 0.5, "CAAZ 噪声消除效率 η", size=28, bold=True, color=BLUE)
add_textbox(slide, 1.0, 0.8, 8, 0.3, "NF=10（100× 噪声注入）| 两批次跨验证", size=13, color=MGRAY)

add_fig(slide, f"{FIGS}/Fig2_CAAZ_Eta.png", 0.3, 1.3, 7.0)

# Right panel: eta values
add_rect(slide, 7.8, 1.3, 5, 5.0, BLUE_L)
add_textbox(slide, 8.0, 1.4, 4.5, 0.4, "η 各角汇总", size=18, bold=True, color=BLUE)
eta_data = [
    ("TT", "87.9%", "✅ 达标", GREEN),
    ("FF", "89.4%", "✅", GREEN),
    ("SS", "83.9%", "⚠️ 接近", ORANGE),
    ("SF", "79.7%", "⚠️ 最差", RED),
    ("FS", "91.2%", "✅ 最优", GREEN),
]
for i, (corner, val, status, clr) in enumerate(eta_data):
    y = 2.0 + i * 0.75
    add_textbox(slide, 8.0, y, 1.0, 0.4, corner, size=16, bold=True, color=BLUE)
    add_textbox(slide, 9.0, y, 1.5, 0.4, val, size=20, bold=True, color=clr)
    add_textbox(slide, 10.5, y, 2, 0.4, status, size=14, color=clr)

add_textbox(slide, 8.0, 5.8, 4.5, 0.4, "跨批次 η 偏差 < 1.4 p.p.", size=14, bold=True, color=BLUE)
add_textbox(slide, 8.0, 6.2, 4.5, 0.3, "结论跨批次稳健", size=12, color=MGRAY)

# ========================================================================
# SLIDE 7: Cross-batch Verification
# ========================================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_rect(slide, 0, 0, 0.12, 7.5, BLUE)
add_textbox(slide, 1.0, 0.5, 8, 0.6, "跨批次数据验证", size=32, bold=True, color=BLUE)
add_rect(slide, 1.0, 1.1, 3, Pt(3), BLUE)

# Left: consistent metrics
add_rect(slide, 1.0, 1.5, 5.5, 2.5, GREEN_L)
add_textbox(slide, 1.3, 1.6, 5, 0.4, "✅ 跨批次一致的指标", size=18, bold=True, color=GREEN)
consist = [
    ("COMPOWER 偏差", "< 3 µW"),
    ("η 偏差", "< 1.4 p.p."),
    ("ENOB 偏差", "< 0.2 bit"),
    ("SNR 偏差", "< 0.8 dB"),
    ("数字功耗偏差", "< 0.5 µW"),
]
for i, (label, val) in enumerate(consist):
    add_textbox(slide, 1.3, 2.1+i*0.35, 3, 0.35, label, size=13, color=DGRAY)
    add_textbox(slide, 4.3, 2.1+i*0.35, 2, 0.35, val, size=13, bold=True, color=GREEN)

# Right: discrepancy
add_rect(slide, 7.0, 1.5, 5.5, 2.5, RGBColor(255,235,235))
add_textbox(slide, 7.3, 1.6, 5, 0.4, "⚠️ 需关注的差异", size=18, bold=True, color=RED)
disc = [
    ("SWITCHPOWER", "+15% 系统性偏高"),
    ("→ 原因", "CSV 导出表达式差异"),
    ("→ 不影响", "COMPOWER/数字功耗"),
    ("FF 角 SFDR", "−3.52 dB 跨批次"),
]
for i, (label, val) in enumerate(disc):
    add_textbox(slide, 7.3, 2.1+i*0.4, 2.5, 0.35, label, size=13, color=DGRAY)
    add_textbox(slide, 9.8, 2.1+i*0.4, 2.5, 0.35, val, size=13, bold=True, color=RED)

# Bottom: conclusion
add_rect(slide, 1.0, 4.5, 11.5, 1.0, BLUE_L)
add_textbox(slide, 1.3, 4.6, 11, 0.7,
            "💡 结论：η 跨批次偏差 <1.4 p.p.，CAAZ 效率定性结论稳健，不受批次影响。"
            "建议在 Cadence 中确认 SWITCHPOWER 的 Calculator 表达式定义。",
            size=15, bold=False, color=BLUE)

# ========================================================================
# SLIDE 8: Power & SFDR
# ========================================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_rect(slide, 0, 0, 0.12, 7.5, BLUE)
add_textbox(slide, 1.0, 0.3, 8, 0.5, "功耗与 SFDR 分析", size=28, bold=True, color=BLUE)

add_fig(slide, f"{FIGS}/Fig3_Power_Breakdown.png", 0.2, 1.2, 8.5)

# Right: SFDR summary
add_rect(slide, 9.0, 1.2, 4, 5.5, RGBColor(245,245,250))
add_textbox(slide, 9.2, 1.3, 3.5, 0.4, "SFDR 汇总", size=18, bold=True, color=BLUE)
sfdr_data = [
    ("NF=1, 24ns", "77-81 dB"),
    ("NF=1, 26ns", "81-84 dB ✅"),
    ("NF=10, 26ns", "72-77 dB"),
]
for i, (cond, val) in enumerate(sfdr_data):
    add_textbox(slide, 9.2, 1.8+i*0.5, 3, 0.35, cond, size=13, color=MGRAY)
    add_textbox(slide, 9.2, 2.15+i*0.5, 3, 0.35, val, size=16, bold=True, color=DGRAY)

add_textbox(slide, 9.2, 3.6, 3.5, 0.5, "功耗优化重点:", size=14, bold=True, color=DGRAY)
opts = [
    ("PREWOCM: 299 µW (41%)", "🔧 最大优化空间"),
    ("预放大器电流可缩小", ""),
]
for i, (label, icon) in enumerate(opts):
    add_textbox(slide, 9.2, 4.1+i*0.4, 3.5, 0.35, f"{icon} {label}", size=13, color=DGRAY)

# SFDR worst corner
add_rect(slide, 9.2, 5.0, 3.5, 0.6, RGBColor(255,240,240))
add_textbox(slide, 9.4, 5.05, 3, 0.5, "⚠️ SFDR 最差: SS/SF\n85°C 下仅 72 dB", size=12, bold=True, color=RED)

# ========================================================================
# SLIDE 9: Risk Assessment
# ========================================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_rect(slide, 0, 0, 0.12, 7.5, BLUE)
add_textbox(slide, 1.0, 0.5, 8, 0.6, "风险评估与优化方向", size=32, bold=True, color=BLUE)
add_rect(slide, 1.0, 1.1, 3, Pt(3), BLUE)

risks = [
    ("P0", "SWITCHPOWER 表达式", "跨批次 +15% 偏差", RED),
    ("P0", "DFF 动态节点 keeper", "CLK1/net2 漏电风险", RED),
    ("P1", "预放大器电流优化", "PREWOCM 占 41%，可缩小", ORANGE),
    ("P1", "SF 角深度分析", "η=79.7%, SFDR=72.57 dB", ORANGE),
    ("P1", "CCLK H-tree 布局", "验证 skew <20 ps", ORANGE),
    ("P2", "PEX 反标验证", "版图后必须进行", BLUE),
    ("P2", "低频 1/f 噪声排查", "N=5 比 N=61 退化 ~0.3 bit", BLUE),
]
for i, (prio, title, desc, clr) in enumerate(risks):
    y = 1.5 + i * 0.75
    # Priority tag
    add_rect(slide, 1.0, y, 0.7, 0.55, clr)
    add_textbox(slide, 1.0, y+0.07, 0.7, 0.4, prio, size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    # Content
    add_textbox(slide, 1.9, y+0.02, 3, 0.35, title, size=16, bold=True, color=clr)
    add_textbox(slide, 5.2, y+0.05, 6, 0.35, desc, size=14, color=DGRAY)

# ========================================================================
# SLIDE 10: Conclusions
# ========================================================================
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_rect(slide, 0, 0, 13.333, 7.5, BLUE_D)
add_rect(slide, 0, 0, 10.5, 7.5, BLUE)

add_textbox(slide, 0.8, 0.5, 8, 0.6, "总结与建议", size=36, bold=True, color=WHITE)
add_rect(slide, 0.8, 1.1, 3, Pt(3), WHITE)

conclusions = [
    ("✅", "设计全面达标", "ENOB>11.4, SNR>70dB, SFDR>81dB, CAAZ η=87.9%"),
    ("⚡", "td=26.0ns 最优", "高温角 SNR+1.8dB, 26.5ns 无额外收益, 功耗不变"),
    ("🛡️", "CAAZ 全角有效", "η 跨批次偏差 <1.4 p.p., SF 角 79.7% 为瓶颈"),
    ("📊", "功耗 ~720µW", "模拟 65% / 数字 35%, 预放 41% 可优化"),
    ("📋", "数据跨批次可靠", "COMPOWER/η/ENOB 偏差可控, SWITCHPOWER 表达式待对齐"),
]
for i, (icon, title, desc) in enumerate(conclusions):
    y = 1.5 + i * 1.1
    add_rect(slide, 0.8, y, 9, 0.9, RGBColor(20,60,110))
    add_textbox(slide, 1.0, y+0.05, 0.5, 0.4, icon, size=24, color=WHITE)
    add_textbox(slide, 1.6, y+0.05, 3, 0.4, title, size=20, bold=True, color=WHITE)
    add_textbox(slide, 4.8, y+0.08, 5, 0.4, desc, size=15, color=RGBColor(180,210,240))

add_textbox(slide, 0.8, 6.5, 10, 0.4, "下一步：PEX 验证 → 低频噪声排查 → 预放电流优化", size=16, bold=True, color=TEAL_L)

prs.save(os.path.join(OUT, "CAAZ_SAR_ADC_Simulation_Report.pptx"))
print(f"[OK] PPTX saved ({len(prs.slides)} slides)")
