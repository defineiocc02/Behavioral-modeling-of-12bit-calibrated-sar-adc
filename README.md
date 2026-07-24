# 12-bit calibrated asynchronous SAR ADC behavioral model

[![Version](https://img.shields.io/badge/version-3.0.0-0072B2)](VERSION)
[![Tests](https://img.shields.io/badge/tests-63%20passing-009E73)](src/python_cal/tests)
[![FFT](https://img.shields.io/badge/FFT-coherent%20rectangular-009E73)](docs/MODELING_GUIDE.md)

这是当前仓库唯一有效的 Python 行为级版本。它实现了全差分、异步、
split-CDAC SAR ADC，包含电荷守恒求解、P/N 独立电容失配、前景权重校准、
普通加权解码、完整可达码本审计与相干 FFT。旧 Verilog-A、旧 RTL、旧
Python 实验和被否决的 LUT/DP 方案不在活动目录中。

> 证据等级：Python behavioral L2。结果不是晶体管级 PVT、版图后仿或硅片
> 测量结论。

![Model architecture](docs/assets/figures/fig01_model_architecture.png)

## 锁定的 v3.0 CDAC

每侧只使用整数单位电容：

```text
High segment: 32, 16, 8, 8, 4, 2, 1 Cu   = 71 Cu
Bridge:                                  2 Cu
Low segment:  32, 16, 8, 4, 2, 2, 1 Cu  = 65 Cu
Total:                                  138 Cu / side
```

桥接后的标称有效权重为：

```text
2144, 1072, 536, 536, 268, 134, 67,
  64,   32,  16,   8,   4,   4,  2, 1 terminal
```

- 所有 14 个高、低段电容都在正常转换时采样输入；低段没有接死 VCM。
- 14 个物理 trial/compare/commit 加 1 个 comparator-only terminal，共
  15 次比较。
- 高段重复 8 Cu 提供大范围冗余，低段重复 2 Cu 提供细粒度覆盖。
- 解码只有 P/N 校准权重加和与 Q2 舍入，没有 LUT、DP、异常表或状态式钳位。

![CDAC topology](docs/assets/figures/fig02_cdac_topology.png)

## 为什么不用旧 95 Cu 方案

旧结构

```text
Low: 1, 2, 4, 6, 10, 16, 24 Cu
Bridge: 1 Cu
High: 1, 2, 4, 8, 16 Cu
```

虽然面积小，但在相同 `0.5%` unit-cap mismatch 的 1000-seed 可达码本实验中：

- 缺码 P50 = 22，最坏 = 84；
- 最大跳码最坏 = 9；
- 不能作为 12-bit 静态签核结构。

v3.0 的 138 Cu 结构在相同物理-oracle 审计中为 1000/1000 零缺码，
最大跳码始终为 1。它把电容从 95 Cu 增至 138 Cu，但避免了额外校正
LUT 和复杂解码器。

![Old versus v3.0 CDAC audit](docs/assets/figures/fig09_cdac_candidate_comparison.png)

## v3.0 发布结果

正式 100-seed 运行（`0.5%` unit-cap mismatch、512 pairs、1 mV RMS
calibration noise）给出：

| 指标 | 校准前 | 校准后 Q2 | 物理 oracle |
|---|---:|---:|---:|
| SNDR P50 | 66.62 dB | 74.48 dB | 74.67 dB |
| ENOB P50 | — | 12.08 bit | 12.11 bit |

- 100/100 校准有效，负收益 0/100；
- oracle gap P50/P95 = `0.156/0.412 dB`；
- 100/100 零缺码且最大跳码为 1；
- DNL/INL peak P95 = `0.8663/0.9234 LSB`；
- integer-12 diagnostic 的 SNDR/ENOB P50 只有 `71.15 dB/11.53 bit`，
  证明此前“只有 11 位”的主因是校准权重又被整数输出重量化，不是输入幅度
  或理想 12-bit CDAC 本身的上限。

完整证据见 [v3.0 发布结果](docs/RELEASE_RESULTS_V3.md)。

## 校准

低段完整参与采样，但作为 `131 Q0` 的匹配基准尺，不使用主比较器递归
自校最低几位。原因是最低位只有 `3 Q0` 左右的 backend margin，无法可靠
覆盖 3 mV 级 comparator offset；强行校准反而会饱和。

前景校准从 H1 开始，顺序为：

```text
H1 -> H2 -> H4 -> H8-R -> H8-A -> H16 -> H32
```

每个目标执行 P0/P1/N0/N1 四次 lower-SAR 子转换，并用半差得到 P/N
权重。`512` pairs 时总校准工作量为 `7 × 4 × 512 = 14336` 次子转换，
与旧版本相同，没有增加校准周期总量。

## 静态指标的两个口径

本仓库同时报告两种互不替代的结果：

1. **论文/硅片常用 code-density 口径**：把同一输出码的所有可达输入区间
   宽度相加，报告 missing code、DNL、INL 和最大跳码。
2. **更强的形式化口径**：检查任意相邻可达区间是否存在局部回退。

非二进制冗余允许一个输出码有多个输入表示，因此可能出现窄于 1 LSB 的
局部重叠。它不等于缺码，也不应从报告中隐藏。v3.0 的发布门以
`零缺码 + max jump <= 1 + DNL/INL <= 1 LSB` 为静态验收；形式化回退数
保留为独立诊断，不宣称严格数学单调。

![Static signoff](docs/assets/figures/fig06_static_signoff.png)

## FFT 协议

正式指标路径统一为：

| 参数 | 值 |
|---|---:|
| FFT 点数 | 4096 |
| 相干 bin | 127 |
| 相位 | 0.123 rad |
| 输入幅度 | -0.5 dBFS |
| VFS | 每个 seed 动态测量 |
| 窗 | rectangular |
| clipping | 每次运行显式检查 |

相干采样时矩形窗的 ENBW 为 1 bin，不需要把主瓣扩展到多个 bin。Blackman
适合未知频率或非相干诊断，但不能与本项目的单-bin 相干 SNDR 混用。

## 快速复现

```powershell
python -m pip install -e ".[dev,docs]"
python -m pytest src/python_cal/tests -q

$env:PYTHONPATH = "src"
$env:SAR_MC_SEEDS = "100"
$env:SAR_AVG_PAIRS = "512"
python src/python_cal/run_final_calibration_pipeline.py

python docs/figures/generate_modeling_figures.py
```

发布结果位于
[`src/python_cal/validation_results/final_pipeline`](src/python_cal/validation_results/final_pipeline)，
图表位于 [`docs/assets/figures`](docs/assets/figures)。

## 目录

```text
src/python_cal/
  topology/        integer CDAC and explicit switch states
  physical/        charge-conservation solver and P/N oracle
  comparator/      dynamic comparator model
  async_control/   asynchronous SAR handshake
  calibration/     active force-0/force-1 calibration only
  decode/          plain weighted-sum decoder
  validation/      FFT and exact reachable-codebook audits
  tests/           regression suite
docs/
  MODELING_GUIDE.md
  VALIDATION_STATUS.md
  FIGURE_CATALOG.md
  ARCHIVE_POLICY.md
```

进一步说明见 [建模指南](docs/MODELING_GUIDE.md)、
[验证状态](docs/VALIDATION_STATUS.md) 和
[图表目录](docs/FIGURE_CATALOG.md)。
论文使用边界见 [Chen 2024 参考说明](docs/REFERENCE_NOTES.md)。
硬件资源和移植接口见
[Hardware and Verilog-A port plan](docs/HARDWARE_AND_VERILOGA_PORT.md)。
