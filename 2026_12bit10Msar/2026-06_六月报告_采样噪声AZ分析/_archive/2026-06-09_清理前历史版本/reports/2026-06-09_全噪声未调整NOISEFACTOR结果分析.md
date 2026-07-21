# 2026-06-09 全噪声打开、NOISEFACTOR 未放大结果分析

## 数据来源

- 本地归档目录：`D:\ReedZhao\Document\Obsidian\日常\10_项目区\2026_12bit10Msar\2026-06_六月报告_采样噪声AZ分析`
- 最新原始数据：`raw_data/2026-06-09_full_noise_nominal/ExplorerRun.0.rdb`
- 最新日志：`raw_data/2026-06-09_full_noise_nominal/ExplorerRun.0.log`
- 本轮设置：完整噪声打开，未对 `NOISEFACTOR` 做 10 倍电压放大/100 倍功率放大。
- Sweep 点：`td=24.05n` 与 `td=28n`。按前一轮定义，二者可等效为 AZ 时间约 `0.05ns` 与 `4ns`。
- 日志状态：Run time window: Mon Jun  8 22:01:03 2026 -> Mon Jun  8 23:08:16 2026; Number of points completed: 2; Number of simulation errors: 0

## 最新全噪声结果汇总

| td | AZ 等效时间 | ENOB min/avg/max | SNR min/avg/max | SFDR min/avg/max | Power avg/max |
| --- | --- | --- | --- | --- | --- |
| 24.05n | 0.05 ns | 11.2469 / 11.3548 / 11.4730 | 69.6147 / 70.3257 / 70.8711 dB | 80.1116 / 81.4859 / 82.7412 dB | 361.31 / 413.04 uW |
| 28n | 4.00 ns | 11.3878 / 11.4870 / 11.5830 | 70.4047 / 71.2896 / 71.6000 dB | 80.3479 / 81.5728 / 83.6625 dB | 374.50 / 428.88 uW |

## 按 corner 的全噪声结果

| corner | td=24.05n ENOB/SNR | td=28n ENOB/SNR | SNR 提升 | 等效总噪声功率剩余 | 总功耗变化 |
| --- | --- | --- | --- | --- | --- |
| tt | 11.4333 / 70.6838 dB | 11.5830 / 71.5006 dB | +0.8167 dB | 82.86% | +13.37 uW (+3.76%) |
| ff | 11.2841 / 70.2336 dB | 11.4759 / 71.6000 dB | +1.3664 dB | 73.01% | +15.84 uW (+3.84%) |
| ss | 11.4730 / 70.8711 dB | 11.3878 / 70.4047 dB | -0.4664 dB | 111.34% | +10.43 uW (+3.28%) |
| sf | 11.3367 / 70.2254 dB | 11.4948 / 71.4701 dB | +1.2447 dB | 75.08% | +13.64 uW (+3.69%) |
| fs | 11.2469 / 69.6147 dB | 11.4935 / 71.4728 dB | +1.8581 dB | 65.19% | +12.64 uW (+3.60%) |

这里的“等效总噪声功率剩余”是用 `10^(-ΔSNR/10)` 从 SNR 差值换算得到的。因为本轮不是只打开采样噪声，而是完整噪声都打开，所以这个百分比不能直接解释成“纯采样噪声还剩多少”，更准确的说法是：在同一信号幅度近似不变时，`td=28n` 相对 `td=24.05n` 的总噪声/失真等效功率变化。

平均意义下，`td=28n` 相对 `td=24.05n`：

- ENOB 从 `11.3548 bit` 提高到 `11.4870 bit`，增加 `0.1322 bit`。
- SNR 从 `70.3257 dB` 提高到 `71.2896 dB`，增加 `0.9639 dB`。
- 按平均 SNR 换算，总噪声等效功率剩余约 `80.10%`，即降低约 `19.90%`。
- 逐 corner 百分比再平均，总噪声等效功率剩余约 `81.49%`，即降低约 `18.51%`。
- 平均总功耗从 `361.31 uW` 增加到 `374.50 uW`，增加 `13.18 uW`，约 `3.65%`。

## 关键判断

1. 全噪声、NOISEFACTOR 未放大时，`td=24.05n` 已经达到平均 ENOB `11.3548 bit`、平均 SNR `70.3257 dB`，性能显著高于昨天 `NOISEFACTOR=10` 的采样噪声强化压力测试。
2. 把 `td` 拉到 `28n` 仍然有收益，平均 SNR 提升约 `0.96 dB`，但收益不像昨天的采样噪声强化场景那样巨大。这说明在正常 NOISEFACTOR 下，采样噪声不再是压倒性主导项。
3. `ss` corner 在 `td=28n` 的 SNR 反而比 `td=24.05n` 低约 `-0.47 dB`，这是本轮最需要复查的 corner。它可能来自统计/FFT窗口/瞬态收敛差异，也可能说明 `4ns` AZ 时间并非所有 corner 都单调更优。
4. 这次 `LOGICPOWER` 与 `SYNCPOWER` 都有有效数值，功耗拆分比昨天完整；平均总功耗约 `361.31 uW` 到 `374.50 uW`。

## 输出文件

- `tables/full_noise_nominal_metrics.csv`
- `tables/full_noise_nominal_aggregate.csv`
- `tables/full_noise_equiv_total_noise_change.csv`
- `figures/2026-06-09_full_noise_nominal/full_noise_enob_by_corner.png`
- `figures/2026-06-09_full_noise_nominal/full_noise_snr_by_corner.png`
- `figures/2026-06-09_full_noise_nominal/full_noise_equiv_total_noise_residual.png`
