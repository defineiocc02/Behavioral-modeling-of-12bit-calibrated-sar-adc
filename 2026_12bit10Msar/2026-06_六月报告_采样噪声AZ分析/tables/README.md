# tables 说明

本目录保存当前有效的 CSV 计算结果。正文统一写 `KT/C`，文件名统一写 `KT_C`。

## 主要入口

| 文件 | 内容 |
| --- | --- |
| `sampling_nf10_scheme_summary.csv` | A/B/C 三方案核心汇总，优先引用 |
| `td_sweep_metrics.csv` | A 方案 FIA td sweep 逐点逐 corner 原始指标 |
| `td_sweep_aggregate.csv` | A 方案 FIA td sweep 聚合指标 |
| `sampling_noise_cancellation_percent.csv` | A 方案相对 `td=24.05n` 的采样噪声消除百分比 |
| `sampling_nf10_voltage_offset_KT_C_metrics.csv` | B 方案电压失调 KT/C 逐 corner 指标 |
| `sampling_nf10_voltage_offset_KT_C_aggregate.csv` | B 方案聚合指标 |
| `sampling_nf10_voltage_offset_KT_C_cancellation_using_yesterday_baseline.csv` | B 方案相对 A 基准的采样噪声消除百分比 |
| `sampling_nf10_current_offset_KT_C_no_FIA_metrics.csv` | C 方案电流型 KT/C 无 FIA 逐 corner 指标 |
| `sampling_nf10_current_offset_KT_C_no_FIA_aggregate.csv` | C 方案聚合指标 |
| `sampling_nf10_current_offset_KT_C_no_FIA_cancellation_using_yesterday_baseline.csv` | C 方案相对 A 基准的采样噪声消除百分比 |
| `new_structure_nf10_metrics.csv` | 新结构 NF=10 取出结果，逐 design point / corner 指标 |
| `new_structure_nf10_aggregate.csv` | 新结构 NF=10 取出结果，按 design point 聚合指标 |

## 对比表

| 文件 | 内容 |
| --- | --- |
| `sampling_nf10_voltage_offset_KT_C_vs_yesterday_td28_comparison.csv` | B 方案 vs A 方案 `td=28n` |
| `sampling_nf10_current_offset_KT_C_no_FIA_vs_FIA_td28_comparison.csv` | C 方案 vs A 方案 `td=28n` |
| `sampling_nf10_current_offset_KT_C_no_FIA_vs_voltage_offset_KT_C_td28_comparison.csv` | C 方案 vs B 方案 |
| `sampling_nf10_voltage_offset_KT_C_vs_full_noise_td28_comparison.csv` | B 方案 vs 全噪声参考 |
| `noisefactor10_vs_full_noise_comparison.csv` | NF10 仅采样噪声与全噪声口径对照 |

## 全噪声参考

| 文件 | 内容 |
| --- | --- |
| `full_noise_nominal_metrics.csv` | 完整噪声打开、未调整 `NOISEFACTOR` 的逐 corner 指标 |
| `full_noise_nominal_aggregate.csv` | 全噪声标称聚合指标 |
| `full_noise_equiv_total_noise_change.csv` | 全噪声标称条件下的等效噪声变化估算 |

## 计算公式

采样噪声功率百分比统一按平均 SNR 相对 A 方案 `td=24.05n` 基准折算：

```text
剩余噪声功率百分比 = 100 * 10^(-(SNR_after - SNR_baseline)/10)
噪声功率消除百分比 = 100 - 剩余噪声功率百分比
```

其中 `SNR_baseline = 54.3396 dB`。

## 最新三方案数值

| 方案 | SNR avg / dB | Power avg / uW | 采样噪声剩余 | 采样噪声降低 |
| --- | ---: | ---: | ---: | ---: |
| A：FIA 基础电流失调 KT/C | 63.9574 | 307.8167 | 10.92% | 89.08% |
| C：电流型 KT/C 无 FIA | 64.0150 | 351.5700 | 10.78% | 89.22% |
| B：电压失调 KT/C | 66.1743 | 439.8245 | 6.55% | 93.45% |

## 新结构 NF10 最新读取

新结构 NF=10 取出结果位于：

- `new_structure_nf10_metrics.csv`
- `new_structure_nf10_aggregate.csv`

该组为独立新结构记录，不直接并入旧结构 A/B/C 三方案的采样噪声消除百分比结论。

当前聚合表中最高平均 SNR 为 design point 1：`WK1=300n`、`WK2=300n`，`SNR_avg=65.6137 dB`，`Power_uW_avg=209.3673 uW`。
