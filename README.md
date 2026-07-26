# 12-bit mismatch-calibrated SAR ADC

[![Version](https://img.shields.io/badge/version-3.1.0-0072B2)](VERSION)
[![Python](https://img.shields.io/badge/python-3.10+-0072B2)](https://www.python.org/)
[![Mismatch](https://img.shields.io/badge/mismatch-PER--UNIT-009E73)](docs/VALIDATION_STATUS.md)
[![Decoder](https://img.shields.io/badge/decoder-Q2%20weighted%20sum-D55E00)](docs/MODELING_GUIDE.md)

这是一个以“电容失配如何影响 SAR ADC，以及前景权重校准能否把性能稳住”
为主问题的可复现行为级项目。噪声不是主研究对象；0.3 mV RMS 只在校准
比较器中作为次要扰动，用于检查 lower-SAR 量化锁定，正常转换不注入噪声。

当前工程结论：

- 理想 CDAC、采样、15 次决策和 Q2 解码链路正确；
- 0.5% PER-UNIT 失配是 nominal behavioral acceptance case；
- 1.0% PER-UNIT 失配是 margin stress，不冒充目标 PDK 数据；
- 校准只更新 P/N 分侧权重，不改变物理电容或 comparator decisions；
- 局部 backstep 保留为诊断，不作为当前应用的单独否决门；
- Python/RTL 使用相同的逐目标 Q8 权重格点；
- 当前可继续进入 transistor/AMS 实现，但尚不是 PDK、版图后或硅片签核。

正式数值、逐种子 yield 和 SHA-256 位于
[验证状态](docs/VALIDATION_STATUS.md)与
[`evidence/mismatch_matrix/`](evidence/mismatch_matrix/)；完整分析见
[最终 PDF 报告](docs/final_report.pdf)。

## 架构

每个差分侧使用整数单位电容：

```text
high:   32, 16, 8, 8, 4, 2, 1 Cu   = 71 Cu
bridge: 2 Cu
low:    32, 16, 8, 4, 2, 2, 1 Cu   = 65 Cu
total:                                  138 Cu/side
```

- P/N 两侧各有 14 个物理 bottom-plate groups；
- 所有 high/low 电容在正常采样时参与输入采样；
- 只有 `VTOP_P/VTOP_N` 在采样时钳到 VCM；
- bridge node 保持内部浮动，不增加 bridge-node sampling switch；
- 14 个物理 trial/commit 加 1 个 comparator-only terminal decision；
- 活动 decoder 是普通 P/N 加权和，无 LUT、CAM、异常表或单调 clamp。

名义权重为：

```text
High Q0: 2144, 1072, 536, 536, 268, 134, 67
Low  Q0:   64,   32,  16,   8,   4,   4,  2
Terminal:    1
```

## 失配定义

正式矩阵采用 **PER-UNIT**，不是 flat PER-CAP：

```text
C_group = Cu × Σ(1 + εk),  εk ~ Normal(0, σunit)
```

每个 unit cell 独立抽样后再组成物理 group，因此 N-Cu group 的相对标准差
自然为 `σunit/√N`。P/N 两侧独立，bridge 的两个 units 也独立。

0.5% 和 1.0% 都是单位电容 sigma。它们是行为级研究点，不是某个 foundry
MOMCAP 的已签核失配。

## 校准与 0.3 mV 扰动

七个高段目标按 H1 → H2 → H4 → H8-R → H8-A → H16 → H32 递归校准：

```text
W_P = mean(S_P0 - S_P1) / 2
W_N = mean(S_N1 - S_N0) / 2
```

低段和 terminal 构成 131-Q0 基准尺；后续目标会读取此前写入的 P/N Q8
权重。每个目标完成后立即截断到 Q8，与综合 RTL 的算术右移和寄存器完全
一致。默认 128 pairs，总计 3584 次 lower-SAR sub-conversions。

0.3 mV 的准确含义是：

```text
calibration comparator input noise:
n ~ Normal(0, (0.3 mV RMS)^2)
```

它只进入 P0/P1/N0/N1 校准比较。正常转换、FFT 和 SNDR 仍使用零噪声。
固定 dither 关闭，也没有额外 dither DAC。完全零扰动时重复 128 次可能
得到相同离散 lower-SAR 结果；小幅输入等效扰动让平均获得亚码宽信息。

## 验证矩阵

| Case | 目的 | Seeds |
|---|---|---:|
| ideal, 0 mV | 理想链路自检 | 1 |
| 0.5% mismatch, 0 mV | 隔离纯失配和量化锁定 | 100 |
| 0.5% mismatch, 0.3 mV calibration-only | nominal acceptance | 100 |
| 1.0% mismatch, 0 mV | 压力点的纯失配对照 | 100 |
| 1.0% mismatch, 0.3 mV calibration-only | margin stress | 100 |

三路动态性能使用同一组物理 decisions：

1. nominal Q2 decoder；
2. calibrated Q2 decoder；
3. physical-weight oracle Q2 decoder。

FFT 固定为 4096 点、coherent bin 1019、phase 0.123 rad、−0.5 dBFS、
rectangular window，并按每个 seed 实测 VFS。静态结果由精确可达决策树
计算 missing codes、code-density DNL/INL 和局部 backstep。

## 已实现与未实现

| 层级 | 当前状态 |
|---|---|
| Python behavioral | 完整物理 CDAC、采样、转换、校准、Q2 解码、FFT、静态审计 |
| Calibration RTL | 可综合；P/N Q8 递归量尺；两组 XSIM 自检通过 |
| FPGA synthesis proxy | 449 LUT、595 FF、0 DSP、0 BRAM；100 MHz setup WNS +0.298 ns；hold WHS −0.147 ns、4 个失败端点 |
| Verilog-A CDAC/comparator | 方程与接口已审查，尚未在本机 Spectre 编译 |
| Full ADC RTL | 尚缺 normal SAR sequencer、Q2 normalization/decoder 和 ADC top |
| Transistor/layout signoff | 尚缺目标 PDK、PVT、reference、switch、kickback、PEX 和硅片数据 |

FPGA 数字资源只对应 calibration/lower-SAR RTL，不代表完整 ADC，也不能
外推 ASIC 面积、功耗或时序。当前 raw parallel top 同时需要 342 个 bonded
IOB，而目标器件只有 125 个，因此也不是可直接实现的 FPGA package top；
应先加 serialized/packed prototype wrapper，再做 place-and-route、hold 修复
和 post-route timing。

## 过度设计处理

已移除或明确不实现：

- 512-pair 默认校准；
- calibration sub-DAC 与 auxiliary comparator；
- decision LUT/CAM、异常映射和单调 clamp；
- 额外 dither DAC；
- 重复 comparator Verilog-A；
- 未使用的 RTL accumulator/CDAC 模型；
- bridge-node sampling clamp；
- 无依据的 foundry/面积/良率结论。

Q2、15th terminal、P/N 分侧权重和 Q8 写回均有直接性能或物理依据，因此
保留。128 pairs 是本轮验证共同点，不宣称是所有 PDK 的全局最小值。

## 复现

```powershell
# 测试
$env:PYTHONPATH = (Resolve-Path src).Path
python -m pytest

# 完整五组矩阵
.\scripts\run_mismatch_matrix.ps1 -Seeds 100 -AveragePairs 128

# 汇总并冻结
python -m python_cal.validation.summarize_mismatch_matrix
python scripts\freeze_mismatch_evidence.py
python -m python_cal.validation.summarize_mismatch_matrix `
  --root evidence\mismatch_matrix

# 图表、指标和 PDF
python scripts\generate_report_figures.py `
  --matrix-root evidence\mismatch_matrix
python scripts\generate_report_metrics.py
.\scripts\reproduce.ps1 -BuildPdf
```

## 目录

```text
src/python_cal/       Python 行为模型与测试
rtl/                  calibration/lower-SAR synthesizable RTL
va/                   CDAC 与 comparator Verilog-A
evidence/             冻结 CSV、JSON、manifest 和矩阵摘要
docs/                 建模说明、验证状态与最终 PDF
scripts/              矩阵、冻结、绘图、综合和复现入口
```

活动/冻结/历史/临时产物的边界见
[`docs/VERSION_MANAGEMENT.md`](docs/VERSION_MANAGEMENT.md)。

## English summary

This repository evaluates capacitor mismatch in a 12-bit differential
split-CDAC SAR ADC. Formal Monte Carlo uses independent PER-UNIT mismatch.
The 0.3 mV RMS term is input-referred comparator noise during foreground
calibration only; normal conversions remain noiseless. Python and
synthesizable calibration RTL commit recursive weights on the same Q8
lattice. Results are behavioral evidence, not transistor-, PDK-, layout- or
silicon-level signoff.
