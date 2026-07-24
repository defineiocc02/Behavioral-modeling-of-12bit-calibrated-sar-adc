# 12-bit Asynchronous SAR ADC Python Behavioral Model

[![Version](https://img.shields.io/badge/version-2.1.0-0072B2)](VERSION)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-3776AB)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-60%20passing-009E73)](src/python_cal/tests)
[![Dynamic gate](https://img.shields.io/badge/dynamic%20gate-PASS-009E73)](docs/VALIDATION_STATUS.md)
[![Static sign-off](https://img.shields.io/badge/static%20sign--off-FAIL-D55E00)](docs/VALIDATION_STATUS.md)

一个可复现、物理路径与数字校准路径严格分离的 12 位全差分异步
SAR ADC Python 行为模型。项目包括 split-CDAC 电荷守恒求解、P/N
独立失配、动态比较器、异步逐次逼近、Shen-derived 前景权重校准、
Q2 数字重构、相干 FFT、Monte Carlo 和完整静态 codebook 审计。

> 当前版本完成了 Python 行为级模型和动态校准验证，但没有声称完成
> 晶体管级/PVT/硅片签核，也没有把 single-H1R 架构包装成 Shen 论文的
> paper-exact 实现。

![Python behavioral model architecture](docs/assets/figures/fig01_model_architecture.png)

## 当前完成情况

| 验证项 | 结果 | 定量证据 |
|---|---|---:|
| 理想物理 CDAC 动态基线 | **PASS** | 73.666 dB SNDR / 11.944 bit |
| 100-seed 校准动态门 | **PASS** | P50 73.112 dB / 11.852 bit |
| 校准到 P/N 物理 oracle | **PASS** | gap P50 0.222 dB，P95 0.524 dB |
| 校准有效率 | **PASS** | 100/100，负增益 0/100 |
| 完整静态单调性 | **FAIL** | 2048 pairs 时 2 缺码、2 回退 |
| Shen paper-exact 架构 | **未实现** | 缺三冗余、reservoir、LSB repeat、SRM、flash 前端 |

![Verified completion status](docs/assets/figures/fig11_completion_status.png)

详细验收边界见 [Validation Status](docs/VALIDATION_STATUS.md)，根因推导见
[12-bit Shen 校准根因报告](src/python_cal/review/2026-07-24_12bit_shen_root_cause_report.md)。

## 为什么过去看起来只有 11 位

不是输入幅度，也不是理想 CDAC 的物理上限。旧链路在 SAR 比较器已经完成
一次量化以后，又将分数校准重构码舍入成整数 12-bit，相当于加入第二份
量化噪声：

- calibrated integer P50：70.574 dB；
- calibrated Q2 P50：73.112 dB；
- 保留两个小数位恢复约 **2.54 dB**；
- physical oracle 同样恢复约 **2.64 dB**。

Q2 仅增加数字累加器和输出的两个小数位，不增加 CDAC 电容、比较次数或
普通转换周期。

![Q2 output precision](docs/assets/figures/fig07_q2_output_precision.png)

旧固定 `0.45 × VREF` 激励会损失约 1.01 dB，但理想物理模型仍能达到
72.657 dB / 11.777 bit，因此它不是“只有 11 位”的主要原因。

## 模型与校准方案

### 物理转换

1. 全差分输入由 bottom-plate sampling 进入 P/N 两侧 split CDAC。
2. 电荷守恒求解器根据真实 P/N 电容和 bridge 求解顶板电压。
3. stages 0–12 执行真实电容 trial/compare/commit。
4. stage 13 是 comparator-only terminal decision，不存在虚构的
   `low_term` 物理电容。
5. 数字 decoder 不反馈到物理 decision 路径。

![Decision weights](docs/assets/figures/fig02_cdac_decision_weights.png)

### Shen-derived 校准

每个目标分别在 P/N 侧执行 VREFN/VREFP force：

```text
W_P = mean(S_P0 - S_P1) / 2
W_N = mean(S_N1 - S_N0) / 2
```

固定对称 dither 防止比较器锁码，半差结构抵消恒定 comparator offset。
校准顺序为 H1R → H1A → H2 → H4 → H8 → H16 → H32，已校准低位递归构成
下一目标的 ruler。

![Shen-derived calibration flow](docs/assets/figures/fig04_shen_calibration_flow.png)

完整数学与代码映射见 [Modeling Guide](docs/MODELING_GUIDE.md)。

## 100-seed 动态结果

验证条件：

- 0.5% unit-cap mismatch，P/N 独立；
- 512 calibration pairs；
- 1 mV RMS calibration noise；
- 4096-point coherent FFT，`k=127`；
- `-0.5 dBFS`，动态测量 VFS，带 clipping guard。

![100-seed dynamic Monte Carlo](docs/assets/figures/fig06_dynamic_monte_carlo.png)

校准前 SNDR P50 为 66.939 dB，校准后为 73.112 dB，P/N 物理 oracle 为
73.322 dB。94/100 样本与 oracle 相差不超过 0.5 dB，99/100 不超过
1.0 dB。

## 已确认的静态限制

动态通过不等于 codebook 单调。当前 single-H1R 冗余简化在 H4 carry
边界没有确定性裕量：

- 100 个真实 P/N 权重样本中 91 个 carry margin 为负；
- margin P50 = -1.916 Q0；
- 2048 calibration pairs 虽降低权重误差，仍出现 2 缺码和 2 回退；
- 继续增加平均次数不能修复架构性 codebook 问题。

![Static codebook risk](docs/assets/figures/fig10_static_codebook_risk.png)

若要求零缺码和严格单调，需要重新分配可观测冗余，或增加
monotonic LUT/codebook 校准；不能只调平均次数或固定减小 H1R。

## 快速开始

```powershell
git clone https://github.com/defineiocc02/Behavioral-modeling-of-12bit-calibrated-sar-adc.git
cd Behavioral-modeling-of-12bit-calibrated-sar-adc

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,docs]"

python -m pytest
python docs\figures\generate_modeling_figures.py
```

一键执行基础复现：

```powershell
.\scripts\reproduce.ps1
```

执行快速 8-seed 动态 pipeline：

```powershell
.\scripts\reproduce.ps1 -RunPipeline -Seeds 8
```

完整 100-seed pipeline 需要更长时间：

```powershell
$env:PYTHONPATH = "src"
$env:SAR_MC_SEEDS = "100"
python src\python_cal\run_final_calibration_pipeline.py
```

## 仓库结构

```text
src/python_cal/
  topology/             split-CDAC、电容和开关状态
  physical/             电荷守恒与 P/N 物理权重 oracle
  comparator/           动态比较器
  async_control/        异步握手与 SAR FSM
  conversion/           顶层行为模型
  calibration/          Shen-derived 生产校准与 deprecated 旧入口
  decode/               P/N 分侧 float / int12 / Q2 decoder
  validation/           统一 FFT 协议
  validation_results/   提交的 JSON/CSV 验证证据
  tests/                58 项回归测试

docs/
  MODELING_GUIDE.md      建模原理和代码映射
  VALIDATION_STATUS.md   验收矩阵与限制
  FIGURE_CATALOG.md      11 组图的来源和解释
  figures/               可复现图表脚本
  assets/figures/        PNG / SVG / PDF
```

## 文档入口

- [完整建模方案](docs/MODELING_GUIDE.md)
- [验证状态和验收边界](docs/VALIDATION_STATUS.md)
- [图表目录与数据来源](docs/FIGURE_CATALOG.md)
- [外部校准代码审查回应](docs/REVIEW_RESPONSE_2026-07-24.md)
- [根因分析报告](src/python_cal/review/2026-07-24_12bit_shen_root_cause_report.md)
- [版本变更记录](CHANGELOG.md)

## 许可

仓库当前没有声明开源许可证。代码公开可见不等于自动授予复制、修改或
再分发权利；如需公开协作，应由仓库所有者另行选择并添加 LICENSE。
