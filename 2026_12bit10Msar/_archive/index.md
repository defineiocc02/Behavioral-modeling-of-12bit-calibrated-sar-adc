---
title: _archive — 历史文件归档
aliases: [归档]
tags: [type/moc, archive]
created: 2026-05-11
updated: 2026-05-13
---

# 📦 _archive — 历史文件归档

> 存放项目的历史版本、旧版报告、废弃脚本和早期草稿。
> 当前版本的文件在项目根目录下各对应文件夹中。

---

## 📁 归档目录结构

```
_archive/
├── 📄 index.md                       本文件
│
├── 📁 20260512_CSV旧导出/            ← 旧版 CSV 数据（已被新导出替换）
│   ├── 20260512_NF10_td24.csv       NF=10, td=24ns
│   └── 20260512_NF10_td26.csv       NF=10, td=26ns
│
├── 📁 20260512_旧版仿真报告/          ← 旧版仿真报告
│   ├── simulation_report.pdf
│   └── simulation_report.tex
│
├── 📁 20260513_报告快照/              ← 修订前的原版快照
│   ├── full_report_原版.tex
│   ├── 研究报告_原版.tex
│   ├── 研究报告_原版.md
│   └── tvlsi_paper_原版.tex
│
├── 📁 paper_draft_v0/                 ← 论文初版草稿
│   ├── paper_IEEEtran.tex/.pdf
│   └── references.bib
│
├── 📁 old_figures/                    ← 旧版配图
├── 📁 scripts/                        ← 旧版绘图脚本
```

---

## 🗺️ 版本对照

| 文档 | 归档版本 | 当前版本 |
|------|---------|---------|
| 仿真报告 | `20260512_旧版仿真报告/` | `04_实验记录/报告/full_report.pdf` |
| 研究报告 | `20260513_报告快照/` | `05_研究报告/研究报告.pdf` |
| TVLSI 论文 | `paper_draft_v0/` | `01_论文/tvlsi_paper.pdf` |
| NF=10 旧 CSV | `20260512_CSV旧导出/` | `04_实验记录/仿真数据/20260512_NF10.csv` |
