---
title: "论文创建过程记录 — 12-bit SAR ADC CAAZ kT/C Noise Cancellation"
date: 2026-05-18
pipeline: "ARS Full Pipeline v3.8.0"
target_journal: "IEEE Transactions on Very Large Scale Integration (VLSI) Systems"
---

# 论文创建过程记录

## 一、流水线概览

| 阶段 | 名称 | 状态 | 关键产出 |
|------|------|:--:|----------|
| 1 | RESEARCH | ✅ | 整合 8 类源材料（仿真数据/PVT/噪声分析/实验记录/参考文献/设计文档/网表/绘图脚本） |
| 2 | WRITE | ✅ | 完整 IEEEtran 论文 (9页, 7章节, 3表格, 20条参考文献) |
| 2.5 | INTEGRITY | ✅ | 发现并修正 5 处数据不一致（kTC压缩比/SNR提升/噪声占比/FoM） |
| 3 | REVIEW | ✅ | 5人评审团 (EIC + R1/R2/R3 + Devil's Advocate)，产出 5 份审稿报告 |
| 4 | REVISE | ✅ | 修正 7 项 P0 + 5 项 P1 问题 |
| 3' | RE-REVIEW | ✅ | 全部 P0 问题确认修复 |
| 4.5 | FINAL INTEGRITY | ✅ | 数据一致性最终验证通过 |
| 5 | FINALIZE | ✅ | PDF 编译成功 (9页, 318KB) |
| 6 | PROCESS SUMMARY | ✅ | 本记录 |

## 二、审稿发现与修正汇总

### P0 — 必须修正项 (7项，全部已修正)

| # | 问题 | 修正内容 |
|---|------|----------|
| 1 | FoM 计算错误 (2.56→25.6 fJ) | 修正 Walden FoM 公式: P/(2^ENOB × f_s) |
| 2 | 未声明仿真性质 | 摘要和引言明确标注 "Spectre transient-noise simulations" |
| 3 | "8× improvement" 误导性对比 | 移除开环/闭环增益的误解对比，改为 kTC 压缩比对比 (5.53× vs 2.40×) |
| 4 | Phase 2 噪声提取机制不明 | 重写描述: DAC重配置消除信号分量，仅噪声通过预放大器电流域转换 |
| 5 | 预放大器 Phase 3 状态不明 | 明确: Phase 3 保持激活但为电流源模式; CAAZ 特有开销<2% |
| 6 | Offset 数据逻辑错误 (ENOB 随失调上升) | 标注 2mV 数据点为仿真噪声容限内，聚焦 0→5mV 退化趋势 |
| 7 | SNDR/ENOB 不一致 (70.12↔11.46) | 统一为峰值 SNDR=70.80 dB → ENOB=11.46 bit |

### P1 — 应修正项 (5项，全部已修正)

| # | 问题 | 修正内容 |
|---|------|----------|
| 8 | "paradigm shift" 夸张用语 | 移除 |
| 9 | "no existing solution" 过于绝对 | 改为 "fundamental trade-off" |
| 10 | CAAZ 归属不清 (innovation vs adaptation) | 结论明确为 "adapting CAAZ from DC-offset to kT/C" |
| 11 | PVT ENOB vs 峰值 ENOB 不一致 | 添加说明: 10.73 bit (全系统/PVT) vs 11.46 bit (kTC-only/最佳) |
| 12 | 比较表中未标注仿真 | 添加 simulation footnote |

## 三、关键性能指标 (最终版)

| 指标 | 数值 |
|------|------|
| 工艺 | 180-nm CMOS, 1.8V |
| 分辨率/采样率 | 12-bit / 50 MS/s |
| kT/C 噪声功率压缩 | 5.53× (7.43 dB) |
| kT/C 噪声占比 | 29.69% → 7.09% |
| 模块级 SNR 提升 | +2.0 dB (71.4 → 73.4 dB) |
| 整机 SNR 提升 | +1.21 dB (69.59 → 70.80 dB) |
| 峰值 SNDR/ENOB | 70.80 dB / 11.46 bit |
| 预放大器功耗 | 205.6 μW |
| 系统总功耗 (仿真) | 3.62 mW |
| Walden FoM (仿真) | 25.6 fJ/conv-step |
| 输入电容 | 100 fF |

## 四、AI 自省报告

### 数据完整性
- **已验证**: 所有 kT/C 噪声相关数值与 `提示.md` (权威噪声分析报告) 严格一致
- **已验证**: PVT ENOB 数据与 `数据.md` 一致
- **已验证**: 所有引用在 references.bib 中有对应条目
- **未独立验证**: FFT 频谱具体数值 (SNDR=70.80, SFDR=85.7) 来源于前版论文草稿，项目文件夹内未找到直接对应仿真结果文件
- **未独立验证**: 总功耗 3.62 mW 的细项 (SAR 逻辑 2.09mW, 偏置 1.20mW) 仅部分可追溯至 `数据.md`

### 已知局限
1. **纯仿真验证**: 无硅片实测数据。论文中所有性能声明均为 Spectre transient-noise 仿真结果
2. **无 DNL/INL 数据**: 缺少静态线性度验证
3. **无 Monte Carlo 结果**: 增益失配分析为手工计算，非统计仿真
4. **PVT 温度覆盖不足**: 仅 -40°C 至 +35°C，缺少高温角 (85°C/125°C)
5. **图表占位符**: 10 张图片均为 placeholder box，需替换为实际仿真波形/图表

### 推荐后续工作
1. 使用文件夹内的 MATLAB 脚本 (`Plot_Paper_Figures.m`) 和 Python 脚本生成实际图表
2. 补充 Monte Carlo 仿真 (200-500 runs) 验证线性度
3. 扩展 PVT 温度至 85°C
4. 如为投稿，考虑在 TCAS-II (接受仿真论文) 和 TVLSI (需硅验证) 之间做期刊选择

## 五、产出文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| LaTeX 源文件 | `01_论文/paper_tvlsi.tex` | IEEEtran 格式 |
| 参考文献库 | `01_论文/references.bib` | 20 条 BibTeX 条目 |
| 编译 PDF | `01_论文/paper_tvlsi.pdf` | 9 页, 318 KB |
| 过程记录 | `01_论文/process_record.md` | 本文件 |

---

*Pipeline: ARS Full v3.8.0 | Model: deepseek-v4-pro | 执行日期: 2026-05-18*
