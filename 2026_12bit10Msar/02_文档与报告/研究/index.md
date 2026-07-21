---
title: 研究报告 — 目录说明
aliases: [研究报告目录]
tags: [type/moc, topic/sar-adc]
created: 2026-05-11
updated: 2026-05-11
---

# 研究报告 — 研究报告与图表

## 内容

| 文件 / 文件夹 | 说明 |
|:---|:---|
| `研究报告.md` | 研究报告 Markdown 主版本 |
| `研究报告.tex` | LaTeX 版本（~30 页） |
| `研究报告.pdf` | PDF 输出 |
| `reference.bib` | 参考文献 |
| `figures/` | 6 张学术级图表（Fig4–Fig8，PNG+PDF 双格式） |
| `scripts/` | 绘图脚本与 CSV 数据 |
| `scripts/generate_figures.py` | Python 绘图主脚本（最新 v3） |
| `scripts/Plot_JSSC_Final.m` | MATLAB JSSC 标准绘图脚本 |
| `scripts/Plot_TCAS_II.m` | MATLAB TCAS-II 标准绘图脚本 |
| `scripts/data/` | 仿真 CSV 数据（enob, noise_breakdown, offset_sensitivity） |
| `参考论文/` | 相关参考文献 PDF |

## 说明

- `01_论文/tvlsi_paper.tex` 通过 `\graphicspath` 引用本目录下的 `figures/`
- 绘图脚本 `generate_figures.py` 为当前唯一活跃版本（v3），旧版已移至 `_archive/scripts/`
