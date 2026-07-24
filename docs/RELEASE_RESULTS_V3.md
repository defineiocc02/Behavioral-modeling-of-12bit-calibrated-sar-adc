# v3.0 发布结果

## 运行条件

- run ID: `dbac69f3`
- 100 Monte Carlo seeds，unit-cap mismatch sigma = 0.5%
- 512 calibration pairs，calibration noise = 1 mV RMS
- 4096-point coherent FFT，`k=127`，phase `0.123 rad`
- dynamic VFS，输入 `-0.5 dBFS`，rectangular window
- Q2 calibrated output；integer 12-bit 只作二次量化诊断

## 动态结果

| 指标 | 校准前 | 校准后 Q2 | 物理 oracle |
|---|---:|---:|---:|
| SNDR P50 | 66.616 dB | 74.482 dB | 74.671 dB |
| SNDR min | 59.972 dB | 74.094 dB | 74.435 dB |
| ENOB P50 | — | 12.080 bit | 12.112 bit |
| ENOB min | — | 12.016 bit | 12.072 bit |

- valid calibrations: 100/100
- negative gain: 0/100
- oracle gap P50/P95/max: `0.156/0.412/0.559 dB`
- gap <= 0.5 dB: 98/100；gap <= 1.0 dB: 100/100
- calibrated integer-12 diagnostic P50: `71.149 dB / 11.526 bit`

Q2 与 integer-12 相差约 3.33 dB。这个对照直接说明旧“只有 11 位”现象
主要来自校准后的分数权重再次被整数 12-bit 输出量化，而不是输入摆幅、
电容物理 oracle 或 FFT 窗导致。

## 静态结果

| 指标 | P50 | P95 | max |
|---|---:|---:|---:|
| DNL peak | 0.7500 LSB | 0.8663 LSB | 0.9501 LSB |
| INL peak | 0.8020 LSB | 0.9234 LSB | 0.9572 LSB |
| missing codes | 0 | 0 | 0 |
| maximum integer jump | 1 | 1 | 1 |

发布门以 code-density DNL/INL、缺码和最大整数跳码为准，全部通过。

形式化局部诊断仍记录 27065 个 integer backsteps（100 seeds 合计）。这些
来自冗余决策字在亚 LSB 输入区间的重叠，因此本版本不宣称任意无限小输入
扰动下都严格数学单调。它们没有通过排序、LUT、CAM、DP 或异常表修正。

## 校准误差

| target | absolute error P50/P95 (Q0) | normalized ratio error P50/P95 |
|---|---:|---:|
| H1 | 0.1797 / 0.4788 | 0.000846 / 0.002554 |
| H2 | 0.3014 / 0.8049 | 0.000486 / 0.001256 |
| H4 | 0.5435 / 1.5343 | 0.000346 / 0.000790 |
| H8-R | 1.0448 / 3.0292 | 0.000125 / 0.000297 |
| H8-A | 1.0039 / 3.1613 | 0.000153 / 0.000353 |
| H16 | 1.9804 / 6.2707 | 0.000067 / 0.000194 |
| H32 | 3.8674 / 12.3308 | 0.000061 / 0.000182 |

绝对 Q0 误差随目标权重放大；去除不可观测的全局 scale 后，H32 的比例
误差 P50/P95 仅 `0.0061%/0.0182%`，与 0.156 dB 的动态 oracle gap 一致。

## 机器可读证据

- `src/python_cal/validation_results/final_pipeline/final_pipeline_dbac69f3.csv`
- `src/python_cal/validation_results/final_pipeline/final_summary_dbac69f3.json`
- `src/python_cal/validation_results/final_pipeline/final_report_dbac69f3.md`
- `src/python_cal/validation_results/final_pipeline/run_manifest.json`
- `src/python_cal/validation_results/cdac_design_audit.json`

这些结果是 Python behavioral L2，不代替 Verilog-A、晶体管级 PVT、版图
后仿或硅片 code-density 签核。
