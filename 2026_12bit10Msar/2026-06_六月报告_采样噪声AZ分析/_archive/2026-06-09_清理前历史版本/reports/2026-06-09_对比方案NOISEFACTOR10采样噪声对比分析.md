# 2026-06-09 对比方案：NOISEFACTOR=10 仅采样噪声结果对比分析

## 数据来源

- 当前对比方案原始数据：`raw_data/2026-06-09_sampling_only_NOISEFACTOR10_comparison_scheme/ExplorerRun.0.rdb`
- 当前对比方案日志：`raw_data/2026-06-09_sampling_only_NOISEFACTOR10_comparison_scheme/ExplorerRun.0.log`
- 运行时间：Tue Jun  9 00:38:33 2026 -> Tue Jun  9 01:30:01 2026
- 完成状态：`Number of points completed = 1`，`Number of simulation errors = 0`。
- 本轮只有一个 design point，RDB 中 `td=28n`，对应 AZ 约 `4ns`。
- 本轮为 `NOISEFACTOR=10`、仅采样噪声打开的压力测试。`SRPOWER` 表达式仍然报 evaluation error，但 `Power` 总功耗、`COMPOWER`、`LOGICPOWER`、`SYNCPOWER` 均有有效值。

## 对比方案 td=28n 结果

| corner | ENOB | SNR | SFDR | Power | COMPOWER | SYNCPOWER |
| --- | --- | --- | --- | --- | --- | --- |
| tt | 10.3134 | 64.1950 dB | 75.5682 dB | 341.06 uW | 138.83 uW | 25.08 uW |
| ff | 10.8302 | 67.1753 dB | 78.5854 dB | 367.22 uW | 151.91 uW | 26.04 uW |
| ss | 9.8994 | 61.2752 dB | 73.6704 dB | 337.75 uW | 144.20 uW | 24.34 uW |
| sf | 10.3069 | 63.9503 dB | 76.7070 dB | 356.36 uW | 154.12 uW | 25.07 uW |
| fs | 10.3883 | 64.7527 dB | 75.2920 dB | 341.58 uW | 136.77 uW | 25.19 uW |

汇总：平均 ENOB `10.3476 bit`，平均 SNR `64.2697 dB`，平均 SFDR `75.9646 dB`，平均总功耗 `348.79 uW`。Worst corner 为 `ss`：ENOB `9.8994 bit`、SNR `61.2752 dB`。

## 和昨天 NOISEFACTOR=10 采样噪声结果比较

下面是同样 `td=28n/AZ≈4ns` 条件下，对比方案相对昨天结果的变化：

| corner | SNR 昨天 | SNR 对比方案 | ΔSNR | ENOB 昨天 | ENOB 对比方案 | ΔENOB |
| --- | --- | --- | --- | --- | --- | --- |
| tt | 65.9413 | 64.1950 | -1.7463 dB | 10.6877 | 10.3134 | -0.3743 |
| ff | 63.5149 | 67.1753 | +3.6604 dB | 10.2305 | 10.8302 | +0.5997 |
| ss | 63.2268 | 61.2752 | -1.9516 dB | 10.2421 | 9.8994 | -0.3427 |
| sf | 63.9569 | 63.9503 | -0.0066 dB | 10.3411 | 10.3069 | -0.0342 |
| fs | 63.1473 | 64.7527 | +1.6054 dB | 10.2405 | 10.3883 | +0.1478 |

平均值对比：

- 昨天 `td=28n`：平均 ENOB `10.3484`，平均 SNR `63.9574 dB`，平均 SFDR `75.6688 dB`。
- 对比方案 `td=28n`：平均 ENOB `10.3476`，平均 SNR `64.2697 dB`，平均 SFDR `75.9646 dB`。
- 平均 ENOB 基本不变，差值 `-0.0008 bit`；平均 SNR 提高 `+0.3123 dB`。
- 但是 corner 分布变了：`ff` 明显改善 `+3.66 dB`，`fs` 改善 `+1.61 dB`；`ss` 下降 `-1.95 dB`，`tt` 下降 `-1.75 dB`。所以平均值看起来类似，但 worst-case 变差。

## 以昨天 24.05n 为基准折算采样噪声消除

本轮只有 `td=28n`，没有同时跑 `td=24.05n` 基准点。因此这里采用昨天 `NOISEFACTOR=10`、`td=24.05n/AZ≈0.05ns` 作为未充分 AZ 消除的基准，按 `10^(-ΔSNR/10)` 折算采样噪声功率剩余。这个折算用于横向参考，严格性略低于同一轮内同时跑 baseline。

| corner | ΔSNR vs 昨天24.05n | 采样噪声功率剩余 | 采样噪声功率消除 |
| --- | --- | --- | --- |
| tt | +10.3730 dB | 9.18% | 90.82% |
| ff | +12.4964 dB | 5.63% | 94.37% |
| ss | +5.7803 dB | 26.42% | 73.58% |
| sf | +10.2397 dB | 9.46% | 90.54% |
| fs | +10.7613 dB | 8.39% | 91.61% |

按逐 corner residual 简单平均，对比方案 `td=28n` 的采样噪声功率剩余约 `11.82%`，消除约 `88.18%`；昨天 `td=28n` 用同一口径对应平均剩余约 `11.53%`，消除约 `88.47%`。如果按平均 SNR 直接折算，对比方案剩余约 `10.16%`，消除约 `89.84%`；昨天报告里约 `10.92%` 剩余、`89.08%` 消除采用的就是这个平均 SNR 口径。

结论是：平均意义上，对比方案和昨天 `td=28n` 很接近，甚至平均 SNR 略好；但它的 corner 分布更不均匀，`ss` corner 是主要风险。

## 和刚刚全噪声标称 td=28n 比较

| corner | SNR 全噪声标称 | SNR 新NF10采样噪声 | 差值 | ENOB 全噪声标称 | ENOB 新NF10采样噪声 | 差值 |
| --- | --- | --- | --- | --- | --- | --- |
| tt | 71.5006 | 64.1950 | -7.3056 dB | 11.5830 | 10.3134 | -1.2696 |
| ff | 71.6000 | 67.1753 | -4.4247 dB | 11.4759 | 10.8302 | -0.6457 |
| ss | 70.4047 | 61.2752 | -9.1295 dB | 11.3878 | 9.8994 | -1.4884 |
| sf | 71.4701 | 63.9503 | -7.5198 dB | 11.4948 | 10.3069 | -1.1879 |
| fs | 71.4728 | 64.7527 | -6.7201 dB | 11.4935 | 10.3883 | -1.1053 |

平均上，对比方案 `NOISEFACTOR=10` 采样噪声压力测试比全噪声标称 `td=28n` 低 `-7.0199 dB` SNR、低 `-1.1394 bit` ENOB。这和昨天压力测试的判断一致：`NOISEFACTOR=10` 会把采样噪声人为推成主导项，不能直接代表正常全噪声规格，但很适合看 AZ 对采样噪声本身的处理能力。

## 基本结论

1. 对比方案这轮 `td=28n/AZ≈4ns` 的平均 ENOB/SNR 与昨天 `td=28n` 基本一致：平均 ENOB 几乎不变，平均 SNR 略高约 `0.3123 dB`。
2. 对比方案的 corner 分布更偏：`ff/fs` 改善，`ss/tt` 变差，其中 `ss` 是 worst-case，SNR 只有 `61.28 dB`。
3. 以昨天 `td=24.05n` 作为基准折算，对比方案采样噪声功率逐 corner 平均剩余 `11.82%`，约消除 `88.18%`；与昨天 `4ns` 的 `11.53%` 剩余相比，平均水平非常接近。
4. 和刚刚全噪声标称相比，对比方案仍低约 `7.02 dB` SNR，说明 `NOISEFACTOR=10` 采样噪声压力测试仍是主导噪声验证，不应直接当正常全噪声规格。

## 输出文件

- `tables/sampling_nf10_comparison_scheme_metrics.csv`
- `tables/sampling_nf10_comparison_scheme_aggregate.csv`
- `tables/sampling_nf10_comparison_vs_yesterday_td28_comparison.csv`
- `tables/sampling_nf10_comparison_scheme_cancellation_using_yesterday_baseline.csv`
- `tables/sampling_nf10_comparison_vs_full_noise_td28_comparison.csv`
- `figures/2026-06-09_sampling_only_NOISEFACTOR10_comparison_scheme/new_scheme_vs_yesterday_snr_by_corner.png`
- `figures/2026-06-09_sampling_only_NOISEFACTOR10_comparison_scheme/td28_three_scheme_snr_by_corner.png`
- `figures/2026-06-09_sampling_only_NOISEFACTOR10_comparison_scheme/new_scheme_residual_noise_by_corner.png`
