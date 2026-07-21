> 命名更正：这组数据是“对比方案B”，不是正式方案。正式阅读入口请看 `2026-06-09_对比方案B_NOISEFACTOR10采样噪声综合对比报告.md`。

# 2026-06-09 正式方案：NOISEFACTOR=10 仅采样噪声综合对比报告

## 数据来源与状态

- 正式方案原始数据：`raw_data/2026-06-09_sampling_only_NOISEFACTOR10_formal_scheme/ExplorerRun.0.rdb`
- 对比方案归档：`raw_data/2026-06-09_sampling_only_NOISEFACTOR10_comparison_scheme/ExplorerRun.0.rdb`
- 正式方案运行时间：Tue Jun  9 01:39:00 2026 -> Tue Jun  9 02:20:40 2026
- 完成状态：`Number of points completed = 1`，`Number of simulation errors = 0`。
- 本轮正式方案为 `NOISEFACTOR=10`、仅采样噪声打开，RDB 中只有 `td=28n` 一个 design point，对应 AZ 约 `4ns`。
- 说明：上一轮被我临时称为“新方案”的数据已更正为“对比方案”，本报告中的“正式方案”指当前这轮从 VM 时间 `01:39` 开始、`02:20` 完成的结果。

## 正式方案结果

| corner | ENOB | SNR | SFDR | Power | COMPOWER | SYNCPOWER |
| --- | --- | --- | --- | --- | --- | --- |
| tt | 10.6604 | 66.1321 dB | 76.5424 dB | 431.27 uW | 228.70 uW | 25.06 uW |
| ff | 11.0333 | 68.1704 dB | 80.5808 dB | 448.22 uW | 232.92 uW | 26.00 uW |
| ss | 10.3497 | 64.0304 dB | 76.6686 dB | 439.70 uW | 246.24 uW | 24.33 uW |
| sf | 10.6180 | 65.7646 dB | 77.5001 dB | 446.40 uW | 244.19 uW | 25.06 uW |
| fs | 10.7424 | 66.7739 dB | 78.2783 dB | 433.53 uW | 229.39 uW | 25.15 uW |

汇总：平均 ENOB `10.6807 bit`，平均 SNR `66.1743 dB`，平均 SFDR `77.9141 dB`，平均总功耗 `439.82 uW`。Worst corner 仍为 `ss`，但正式方案的 `ss` 已提升到 SNR `64.03 dB`、ENOB `10.3497`。

## 与对比方案比较

| corner | SNR 对比方案 | SNR 正式方案 | ΔSNR | ENOB 对比方案 | ENOB 正式方案 | ΔENOB | Power Δ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tt | 64.1950 | 66.1321 | +1.9371 dB | 10.3134 | 10.6604 | +0.3470 | +90.22 uW |
| ff | 67.1753 | 68.1704 | +0.9951 dB | 10.8302 | 11.0333 | +0.2031 | +81.01 uW |
| ss | 61.2752 | 64.0304 | +2.7552 dB | 9.8994 | 10.3497 | +0.4502 | +101.94 uW |
| sf | 63.9503 | 65.7646 | +1.8143 dB | 10.3069 | 10.6180 | +0.3111 | +90.04 uW |
| fs | 64.7527 | 66.7739 | +2.0212 dB | 10.3883 | 10.7424 | +0.3541 | +91.96 uW |

正式方案相对对比方案的平均提升：SNR `+1.9046 dB`，ENOB `+0.3331 bit`，SFDR `+1.9495 dB`。代价是平均总功耗增加 `+91.03 uW`，主要来自 COMPOWER 增加 `+91.12 uW`。

## 与昨天 NOISEFACTOR=10 td=28n 比较

| corner | SNR 昨天 | SNR 正式方案 | ΔSNR | ENOB 昨天 | ENOB 正式方案 | ΔENOB |
| --- | --- | --- | --- | --- | --- | --- |
| tt | 65.9413 | 66.1321 | +0.1908 dB | 10.6877 | 10.6604 | -0.0273 |
| ff | 63.5149 | 68.1704 | +4.6555 dB | 10.2305 | 11.0333 | +0.8028 |
| ss | 63.2268 | 64.0304 | +0.8036 dB | 10.2421 | 10.3497 | +0.1076 |
| sf | 63.9569 | 65.7646 | +1.8077 dB | 10.3411 | 10.6180 | +0.2769 |
| fs | 63.1473 | 66.7739 | +3.6266 dB | 10.2405 | 10.7424 | +0.5019 |

平均上，正式方案比昨天 `td=28n` 高 `+2.2169 dB` SNR、`+0.3323 bit` ENOB。与对比方案不同，正式方案在所有 corner 上都比昨天更高，`ss` 也从昨天的 `63.23 dB` 提高到 `64.03 dB`。

## 采样噪声消除折算

仍以昨天 `td=24.05n/AZ≈0.05ns` 作为未充分 AZ 消除基准，按 SNR 差值折算采样噪声功率剩余：

| corner | ΔSNR vs 昨天24.05n | 噪声功率剩余 | 噪声功率消除 |
| --- | --- | --- | --- |
| tt | +12.3101 dB | 5.87% | 94.13% |
| ff | +13.4915 dB | 4.48% | 95.52% |
| ss | +8.5355 dB | 14.01% | 85.99% |
| sf | +12.0540 dB | 6.23% | 93.77% |
| fs | +12.7825 dB | 5.27% | 94.73% |

逐 corner residual 平均口径：正式方案剩余 `7.17%`，约消除 `92.83%`；对比方案剩余 `11.82%`；昨天 `td=28n` 同口径剩余 `11.53%`。按平均 SNR 折算，正式方案剩余 `6.55%`，约消除 `93.45%`。

## 与全噪声标称 td=28n 比较

正式方案虽然是采样噪声压力测试，但因为方案本身改善明显，已经接近刚刚全噪声标称结果：平均 SNR 比全噪声标称低 `5.1153 dB`，平均 ENOB 低 `0.8063 bit`。不过功耗显著更高：正式方案平均总功耗 `439.82 uW`，全噪声标称 `374.50 uW`，高出 `65.33 uW`。

## 基本结论

1. 当前正式方案不是刚才的对比方案，已单独归档并重新计算。正式方案 `td=28n/AZ≈4ns` 的平均 SNR 为 `66.17 dB`，平均 ENOB 为 `10.6807`。
2. 正式方案相对对比方案和昨天方案均明显改善，尤其 `ss` corner 从对比方案的 `61.28 dB` 提高到 `64.03 dB`。
3. 按采样噪声消除折算，正式方案逐 corner 平均剩余噪声功率约 `7.17%`，即约 `92.83%` 消除；比对比方案和昨天结果更好。
4. 主要代价是功耗：正式方案平均总功耗比对比方案高 `91.03 uW`，比全噪声标称高 `65.33 uW`，主要由比较器功耗增加贡献。

## 输出文件

- `tables/sampling_nf10_formal_scheme_metrics.csv`
- `tables/sampling_nf10_formal_scheme_aggregate.csv`
- `tables/sampling_nf10_formal_vs_yesterday_td28_comparison.csv`
- `tables/sampling_nf10_formal_vs_comparison_scheme_td28_comparison.csv`
- `tables/sampling_nf10_formal_vs_full_noise_td28_comparison.csv`
- `tables/sampling_nf10_formal_scheme_cancellation_using_yesterday_baseline.csv`
- `figures/2026-06-09_sampling_only_NOISEFACTOR10_formal_scheme/formal_vs_prior_nf10_snr_by_corner.png`
- `figures/2026-06-09_sampling_only_NOISEFACTOR10_formal_scheme/td28_all_scheme_snr_by_corner.png`
- `figures/2026-06-09_sampling_only_NOISEFACTOR10_formal_scheme/td28_average_power_comparison.png`
