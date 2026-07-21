---
title: 12-bit 50MS/s SAR ADC with CAAZ — 项目 MOC
aliases: [MOC, 项目地图, 总索引]
tags: [type/moc, topic/sar-adc, project]
created: 2026-03-25
updated: 2026-06-03
---

# 🗺️ 12-bit 50MS/s SAR ADC with CAAZ — 项目知识地图

> 异步 SAR + 电流域 kT/C 噪声消除（CAAZ），TSMC 18RF 工艺。

---

## 🎯 核心指标

| 参数 | 目标 | 仿真结果 (TT) | 状态 |
|:---|:---|:---|:---:|
| ENOB | > 11 bit | **11.61 bit** | 🟢 |
| SNR | > 70 dB | **71.81 dB** | 🟢 |
| SFDR | > 75 dB | **84.01 dB** | 🟢 |
| CAAZ η | > 85% | **87.9%** | 🟢 |
| 功耗 | < 1 mW | **720 µW** | 🟢 |

---

## 📁 目录结构

```
2026_12bit10Msar/
│
├── 📁 01_论文/                   IEEE TVLSI 投稿
│   ├── tvlsi_paper.tex/.pdf/.md
│   ├── IEEEtran.cls
│   └── reference.bib
│
├── 📁 02_文档与报告/             ← 设计 + IP + 研究（合并）
│   ├── 📁 设计/                  设计指南 + 仿真流程
│   ├── 📁 IP规格/                子模块规格
│   └── 📁 研究/                  研究总报告 + figures + scripts
│       ├── 研究报告.tex/.pdf/.md
│       ├── figures/              全部配图 (28 文件)
│       ├── scripts/              绘图 & 分析
│       ├── references/           .bib
│       └── 参考论文/             外部 PDF
│
├── 📁 03_实验记录/               ⭐ 仿真数据 & 分析
│   ├── 📁 仿真数据/              CSV + MD 解读
│   ├── 📁 报告/                  full_report.pdf/.tex/.md + 专题报告包
│   │   └── 20260603_ExplorerRun0_带噪声前仿真分析/
│   ├── 📁 数据分析/              模块专题
│   ├── 📁 实验记录归档/
│   └── 📁 网表/
│
├── 📁 04_辅助工具/               第三方工具（ADCToolbox, EVAS, gm/id...）
│
├── 📁 05_项目管理/               
│   ├── 📄 MOC_12bit50M_SAR.md   ← 你在这里
│   ├── 流片就绪度检查清单.md
│   ├── 📁 组会PPT/
│   ├── 📁 论文审查/
│   └── 📁 scripts/              gen_pptx.py
│
├── 📁 06_工作记录/               会议 · 周记 · 待办
│
└── 📁 _archive/                  📦 历史版本
    ├── 20260512_CSV旧导出/
    ├── 20260512_旧版仿真报告/
    ├── 20260513_报告快照/
    ├── paper_draft_v0/
    ├── old_figures/
    └── scripts/
```

---

## 🔍 快速跳转

| 找什么 | 路径 |
|--------|------|
| **最新仿真数据** | `03_实验记录/仿真数据/20260512_全数据对比分析.md` |
| **最新带噪声前仿真报告** | `03_实验记录/报告/20260603_ExplorerRun0_带噪声前仿真分析/20260603_ExplorerRun0_带噪声前仿真分析报告.md` |
| **完整仿真报告** | `03_实验记录/报告/full_report.pdf` |
| **研究总报告** | `02_文档与报告/研究/研究报告.pdf` |
| **TVLSI 论文** | `01_论文/tvlsi_paper.pdf` |
| **组会 PPT** | `05_项目管理/组会PPT/` |
| **配图** | `02_文档与报告/研究/figures/` |
| **CAAZ 原理** | `03_实验记录/数据分析/CAAZ_噪声消除_数据分析.md` |
| **SAR_LOGIC 分析** | `03_实验记录/数据分析/SAR_LOGIC_SYNC_分析.md` |
| **流片检查清单** | `05_项目管理/流片就绪度检查清单.md` |
| **历史版本** | `_archive/` |

---

## 📊 数据流

```
VM 仿真 (192.168.38.128)
    │ scp ExplorerRun.0.csv
    ▼
03_实验记录/仿真数据/*.csv
    │
    ▼
02_文档与报告/研究/scripts/figures/*.py  →  figures/  (配图)
    │
    ├──→ 03_实验记录/报告/full_report.pdf
    ├──→ 02_文档与报告/研究/研究报告.pdf
    └──→ 01_论文/tvlsi_paper.pdf
```

---

## 🔗 关联系统

| 系统 | 命令 |
|------|------|
| VM 仿真 | `ssh meow@192.168.38.128` |
| 拉取 CSV | `scp meow@192.168.38.128:/home/meow/jxy/simulation/ExplorerRun.0.csv ./` |
| 编译报告 | `xelatex`（两次） |
| Claude Skills | `~/.claude/skills/`（42 个） |
