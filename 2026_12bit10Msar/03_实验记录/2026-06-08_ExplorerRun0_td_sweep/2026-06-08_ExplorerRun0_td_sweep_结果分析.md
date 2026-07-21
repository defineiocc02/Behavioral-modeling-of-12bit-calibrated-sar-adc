# 2026-06-08 ExplorerRun.0 td sweep 结果分析

> 数据源：VM 最新完成 run，`/home/meow/jxy/simulation/12bit_50M_SAR/test_12bit50MSAR_AMS_final/maestro/results/maestro/ExplorerRun.0`。本地归档见 `raw/` 和 `figures/`。

## 先给结论

这次找对的“刚刚跑完结果”是 `ExplorerRun.0`，不是旧的大目录。证据是 `ExplorerRun.0.log` 记录本次从 VM 时间 `2026-06-08 09:04:17 -0400` 开始，到 `10:14:43 -0400` 完成；换算香港时间约为 `2026-06-08 21:04:17` 到 `22:14:43`。`ExplorerRun.0.rdb` 修改时间是 `10:14:44`，`maestro.sdb` 修改时间是 `10:14:45`。

这组仿真实际是 `td` 三点扫描：`24.05n / 26n / 28n`，每点跑 `tt/ff/ss/sf/fs` 五个 corner，共 `15` 个 Spectre run。15 个 run 均有 `.simDone`，数据库 `testStatus` 均为 `done`，Spectre 均为 `0 errors`；每个点有 `2 warnings`，主要是线程限制提示和 `CCLK` save statement 找不到。

从性能看，`td=24.05ns` 明显偏早，ENOB 只有 `8.665-8.874 bit`。`td=26ns` 是关键跃迁点，worst-corner ENOB 到 `10.109 bit`，worst-corner SNR 到 `62.61 dB`。`td=28ns` 在 worst-corner ENOB/SNR 上又小幅提升，但 ff/ss/fs 等 corner 有局部回落，且功耗继续上升。我的建议是：当前若要一个稳妥工作点，先把 `td=26ns` 当 baseline；如果追求 worst-case ENOB/SNR，可以在 `26-28ns` 之间加密扫点，比如 `26.5ns/27ns/27.5ns`。

## 本次结果完整性

- VM 状态：Virtuoso 仍打开；检查时没有正在运行的 `spectre` 进程。
- 磁盘：`/home/meow` 所在分区 `139G`，已用 `83G`，可用 `57G`，使用率 `60%`。
- 当前 run 本体大小：`ExplorerRun.0` 约 `2.5G`。
- 当前测试目录总大小：`test_12bit50MSAR_AMS_final` 约 `7.2G`，其中另有 `Interactive.13` 约 `4.7G`，不属于本次刚完成的 ExplorerRun.0。
- 运行耗时：每个 point 约 `22.8-23.9 min`，峰值内存约 `284-321 MB`。

## 汇总表

表中格式为 `min/avg/max`；功耗单位为 `uW`。

| DP | td | ENOB bit | SNR dB | SFDR dB | Power uW | ENOB worst | Power max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 24.05n | 8.665/8.752/8.874 | 53.71/54.34/55.49 | 66.30/66.69/67.33 | 255.4/294.5/340.9 | sf | ff |
| 2 | 26n | 10.109/10.340/10.599 | 62.61/63.91/65.49 | 74.35/75.89/77.26 | 262.1/303.7/352.9 | sf | ff |
| 3 | 28n | 10.231/10.348/10.688 | 63.15/63.96/65.94 | 74.46/75.67/77.46 | 265.6/307.8/357.0 | ff | ff |

## 全部 corner 数据

| DP | td | corner | pointID | status | ENOB | SNR dB | SFDR dB | Power uW | COM uW | SW uW | SR uW |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 24.05n | tt | 5 | done | 8.697 | 53.82 | 67.12 | 289.82 | 158.84 | 73.92 | 11.78 |
| 1 | 24.05n | ff | 1 | done | 8.809 | 54.68 | 67.33 | 340.85 | 202.15 | 79.23 | 12.04 |
| 1 | 24.05n | ss | 4 | done | 8.874 | 55.49 | 66.36 | 255.44 | 130.71 | 70.23 | 11.45 |
| 1 | 24.05n | sf | 3 | done | 8.665 | 53.71 | 66.30 | 301.68 | 171.54 | 74.34 | 11.62 |
| 1 | 24.05n | fs | 2 | done | 8.717 | 53.99 | 66.33 | 284.70 | 152.72 | 74.41 | 11.81 |
| 2 | 26n | tt | 10 | done | 10.599 | 65.49 | 77.26 | 298.81 | 167.57 | 73.92 | 11.75 |
| 2 | 26n | ff | 6 | done | 10.407 | 64.39 | 76.84 | 352.88 | 213.66 | 79.23 | 12.04 |
| 2 | 26n | ss | 9 | done | 10.443 | 64.37 | 75.90 | 262.06 | 137.12 | 70.24 | 11.40 |
| 2 | 26n | sf | 8 | done | 10.109 | 62.72 | 74.35 | 311.35 | 180.50 | 74.35 | 11.62 |
| 2 | 26n | fs | 7 | done | 10.142 | 62.61 | 75.09 | 293.19 | 161.22 | 74.41 | 11.78 |
| 3 | 28n | tt | 15 | done | 10.688 | 65.94 | 77.46 | 303.08 | 171.87 | 73.93 | 11.76 |
| 3 | 28n | ff | 11 | done | 10.231 | 63.51 | 75.11 | 356.95 | 218.18 | 79.24 | 12.07 |
| 3 | 28n | ss | 14 | done | 10.242 | 63.23 | 74.46 | 265.64 | 140.80 | 70.24 | 11.40 |
| 3 | 28n | sf | 13 | done | 10.341 | 63.96 | 76.48 | 316.22 | 184.73 | 74.35 | 11.65 |
| 3 | 28n | fs | 12 | done | 10.241 | 63.15 | 74.83 | 297.19 | 165.42 | 74.40 | 11.78 |

## 关键观察

1. `td=24.05ns` 不建议作为最终点。所有 corner 的 ENOB 都在 `8.7 bit` 左右，SNR 只有 `53.7-55.5 dB`；与后两个点相比差距约 `1.4-1.9 bit`。
2. `td=26ns` 是最明显的有效边界。相对 `24.05ns`，worst-corner ENOB 提升 `1.444 bit`，SFDR 从最低 `66.30 dB` 提到 `74.35 dB`，同时平均总功耗约 `303.7 uW`。
3. `td=28ns` 对 `tt` 最好：`ENOB=10.688 bit`，`SNR=65.94 dB`，`SFDR=77.46 dB`。但它不是所有 corner 都单调更好，例如 ff corner 从 `td=26ns` 的 `ENOB=10.407` 降到 `10.231`。
4. 功耗随 `td` 增大基本单调增加，主要由 `COMPOWER` 拉升。`td=28ns` 相比 `26ns` 平均总功耗增加约 `4.2 uW`，提升幅度不大，但也没有免费收益。
5. ADE 显示 `Best design point: 1` 不应作为性能排序依据。数据库里 `point.merit` 全是 `0`，没有 spec 表约束；数值结果明显显示 DP1 不是最优性能点。

## 需要注意的问题

`LOGICPOWER` 和 `SYNCPOWER` 在 15 个点全部求值失败，但这不是 Spectre 仿真失败，而是 ADE 输出表达式失败：

- `LOGICPOWER = average(IT("/I15/DVDD")) * 1.8`
- `SYNCPOWER = average(IT("/I21/DVDD")) * 1.8`
- 错误原因：`IT(...)` 返回 nil，随后 `nil * 1.8` 失败。

相关日志还出现 `WIA-1006 Unable to plot expression <IT("/I21/DVDD")>`、`<IT("/I15/DVDD")>`，以及 `ADE-3022 Cannot create valid save statement`。下一次建议检查这两个电源电流的层级路径是否仍然正确，并在 Outputs/Save 设置里重新选取对应 supply pin current，而不是沿用旧表达式。

`SPECTRE-8281` 还提示 `CCLK` save statement 找不到。这个节点未必影响 ENOB/SNR/SFDR 计算，但说明输出设置里至少有一个旧节点名需要清理。

## 图形归档

![summary_montage](10_项目区/2026_12bit10Msar/03_实验记录/2026-06-08_ExplorerRun0_td_sweep/figures/summary_montage.png)

关键图：

- ENOB: `figures/dsImg_window_374.3.png`
- SNR: `figures/dsImg_window_374.4.png`
- SFDR: `figures/dsImg_window_374.5.png`
- Total Power: `figures/dsImg_window_374.7.png`
- COMPOWER: `figures/dsImg_window_374.2.png`

## 原始文件

- `raw/ExplorerRun.0.rdb`: ADE SQLite 结果数据库。
- `raw/ExplorerRun.0.log`: ADE Explorer run 文本摘要。
- `raw/maestro.sdb`: ADE session 数据。
- `td_sweep_metrics.csv`: 从 rdb 提取的逐 corner 指标。
- `td_sweep_aggregate.csv`: 从 rdb 提取的逐 design point 汇总。

## 下一步建议

1. 在 `td=26-28ns` 间加密扫描：`26.5ns / 27ns / 27.5ns`，判断 ff/ss/fs 的回落是偶然 FFT/窗口效应还是真实时序边界。
2. 修复 `LOGICPOWER/SYNCPOWER` 的电流表达式后重跑一次小规模验证；否则当前功耗拆分不完整。
3. 清理 ADE Outputs 里失效的 `CCLK`、`/I21/*`、`/I15/*` save/plot 表达式，减少下次 run 的无效 warning/error。
4. 如果论文需要 quote 指标，建议先用 `td=26ns` 的 worst-corner 作为保守口径，用 `td=28ns@tt` 作为典型最好值，两者分开叙述。
