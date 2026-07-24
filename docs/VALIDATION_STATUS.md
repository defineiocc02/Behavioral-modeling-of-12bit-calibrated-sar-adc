# Validation Status — v2.1.0

## 结论

Python 行为模型、Shen-derived 动态校准链和可复现验证基础设施已经完成。
100-seed 动态门通过；完整静态单调性没有通过，因此顶层验收状态仍是
**FAIL**。这是刻意保留的工程事实，不是文档遗漏。

![Status](assets/figures/fig11_completion_status.png)

## 验收矩阵

| ID | 验证项 | 门槛 | 结果 | 状态 | 证据 |
|---|---|---:|---:|---|---|
| B1 | 数学理想量化器 | 接近 12-bit 极限 | 73.592 dB / 11.932 bit | PASS | baseline JSON |
| B2 | 理想物理 CDAC | ENOB ≥ 11.9 | 73.666 dB / 11.944 bit | PASS | baseline JSON |
| D1 | 校准有效率 | 100% | 100/100 | PASS | 100-seed summary |
| D2 | 校准 SNDR P50 | ≥ 70.99 dB | 73.112 dB | PASS | 100-seed summary |
| D3 | 校准 ENOB P50 | ≥ 11.5 bit | 11.852 bit | PASS | 100-seed summary |
| D4 | oracle gap P50 | ≤ 0.5 dB | 0.222 dB | PASS | 100-seed summary |
| D5 | oracle gap P95 | ≤ 2.0 dB | 0.524 dB | PASS | 100-seed summary |
| D6 | 负校准增益 | 0 seeds | 0/100 | PASS | 100-seed summary |
| F1 | FFT clipping | 0 seeds | 0/100 | PASS | pipeline CSV |
| S1 | sampled missing codes | 0 | 0 | CONDITIONAL | 64-code interval only |
| S2 | full-static missing codes | 0 | 2 | **FAIL** | 2048-pair static JSON |
| S3 | full-static backsteps | 0 | 2 | **FAIL** | 2048-pair static JSON |
| A1 | H4 carry margin | >0 | 91/100 negative | **FAIL** | carry audit JSON |
| P1 | paper-exact Shen | implemented | missing major blocks | NOT IMPLEMENTED | model-scope audit |

## 动态校准前后

100 seeds、0.5% unit-cap mismatch、512 calibration pairs、1 mV calibration
noise：

| 指标 | 标称解码 | 校准 Q2 | P/N 物理 Q2 oracle |
|---|---:|---:|---:|
| SNDR P50 | 66.939 dB | 73.112 dB | 73.322 dB |
| ENOB P50 | 10.828 bit | 11.852 bit | 11.887 bit |
| SFDR P50 | 73.309 dB | 92.820 dB | 94.412 dB |

![Dynamic MC](assets/figures/fig06_dynamic_monte_carlo.png)

校准改善不是来自 oracle leakage：

- `ShenCalibrationController` 只调用 comparator 和 lower-SAR；
- 测试会禁止生产校准读取 `get_physical_weights_per_side_q0()`；
- oracle 仅在校准完成后用于离线 gap 计算。

## 输出精度诊断

| 路径 | integer P50 | Q2 P50 | 恢复 |
|---|---:|---:|---:|
| Calibrated | 70.574 dB | 73.112 dB | +2.538 dB |
| Physical oracle | 70.684 dB | 73.322 dB | +2.638 dB |

这证明约 11.4-bit 的旧结果主要来自第二次整数重构，而非输入幅度或物理
CDAC 上限。

## 静态失败解释

2048 pairs、seed 70000 的完整 4094-transition 检查：

| 指标 | 标称 | 校准后 |
|---|---:|---:|
| DNL peak magnitude | 2.596 LSB | 1.000 LSB |
| INL peak | 2.703 LSB | 1.580 LSB |
| Missing codes | 0 | 2 |
| Adjacent backsteps | 0 | 2 |

DNL/INL 幅度改善的同时出现缺码，说明“权重误差更小”与“codebook 严格
单调”不是同一条件。100-seed H4 carry audit 进一步给出：

- minimum = -4.841 Q0；
- P5 = -3.802 Q0；
- P50 = -1.916 Q0；
- 91/100 为负。

## 证据文件

- `src/python_cal/validation_results/baseline_diagnosis/baseline_diagnosis.json`
- `src/python_cal/validation_results/final_pipeline/final_summary_a3330136.json`
- `src/python_cal/validation_results/final_pipeline/final_pipeline_a3330136.csv`
- `src/python_cal/validation_results/srm_off_isolation/high_only_summary.json`
- `src/python_cal/validation_results/static_signoff/full_static_signoff.json`
- `src/python_cal/validation_results/static_signoff_2048/full_static_signoff.json`
- `src/python_cal/validation_results/codebook_margin/h4_carry_margin.json`

## 声明边界

可以声明：

- 完成了可复现的 Python 12-bit 异步 SAR ADC 行为模型；
- 理想物理模型达到接近 12-bit 动态极限；
- Shen-derived 七目标校准在 100-seed 动态 MC 上通过；
- Q2 是当前最小、有效的数字精度方案；
- single-H1R 静态缺陷已被定量定位。

不可以声明：

- 完成了 transistor-level 或 PVT sign-off；
- 当前架构完整复现 Shen 论文；
- sampled static 等价于 full-static；
- 动态 ENOB 通过意味着零缺码；
- 增加 calibration pairs 可以消除现有 carry backstep。
