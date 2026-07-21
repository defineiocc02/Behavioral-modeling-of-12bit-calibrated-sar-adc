# 12-bit 50 MS/s SAR ADC 带噪声前仿真结果分析报告

生成日期：2026-06-03  
数据来源：`data/ExplorerRun.0.csv`  
测试名：`12bit_50M_SAR_test_12bit50MSAR_AMS_final_1`  
分析对象：12-bit、50 MS/s SAR ADC，带噪声前仿真，PVT corner sweep

## 1. 结论摘要

本次 CSV 结果包含两个时序参数点：`td=24.05n` 和 `td=28n`。每个参数点均覆盖 15 个 PVT/温度角落，包含 `tt/ff/ss/sf/fs` 与 `-40/27/85 °C` 组合。有效动态指标包括 `ENOB`、`SNR`、`SFDR`，有效功耗指标包括 `SWITCHESPOWER`、`COMPOWER`、`LOGICPOWER`、`SYNCPOWER`、`SRPOWER` 与总 `Power`。

综合判断：

| 判断项 | 结论 |
|---|---|
| 推荐参数点 | 推荐优先采用 `td=28n` |
| 动态性能 | `td=28n` 全角落 ENOB 最差为 `11.14 bit`，平均 `11.53 bit`，作为 12-bit SAR ADC 的带噪声前仿真结果，可以认为动态性能初步可接受 |
| 功耗代价 | `td=28n` 平均总功耗约 `335.8 uW`，比 `td=24.05n` 高约 `11.7 uW`，但换来约 `0.20 bit` 平均 ENOB 提升 |
| 最差角落 | 动态性能最差主要集中在 `FF, 85 °C`，需要作为后续优化和后仿重点角落 |
| 当前最大问题 | `PREWOCM` 在所有角落均为 `eval err`，说明该测量表达式或节点引用失败，必须修复 |
| 是否能最终签核 | 不能仅凭此表最终签核。还缺少 `SNDR/SINAD`、`THD`、`DNL/INL`、missing code、offset/gain error、Monte Carlo、post-layout parasitic/noise 等关键验证 |

如果设计规格是“12-bit ADC，动态 ENOB 全角落大于 11 bit”，本次 `td=28n` 结果可以接受并进入下一阶段。如果规格要求“ENOB 全角落大于 11.5 bit”或“接近理想 12-bit 动态性能”，当前结果仍不够，主要受 `FF, 85 °C` 最差角落限制。

## 2. 数据结构与角落定义

原始 CSV 的有效表头从 `Point, Test, Output, Spec, Weight, Pass/Fail, Min, Max, tt_0...fs_2` 开始。前 5 行定义了 PVT corner 信息，后续数据分为两个参数点：

| Point | 参数 | 说明 |
|---:|---|---|
| 1 | `td=24.05n` | 原始较短 delay 点 |
| 2 | `td=28n` | 较长 delay 点，动态性能更好 |

15 个角落对应关系如下：

| 列名 | Process | Temperature |
|---|---|---:|
| `tt_0` | TT | -40 °C |
| `tt_1` | TT | 27 °C |
| `tt_2` | TT | 85 °C |
| `ff_0` | FF | -40 °C |
| `ff_1` | FF | 27 °C |
| `ff_2` | FF | 85 °C |
| `ss_0` | SS | -40 °C |
| `ss_1` | SS | 27 °C |
| `ss_2` | SS | 85 °C |
| `sf_0` | SF | -40 °C |
| `sf_1` | SF | 27 °C |
| `sf_2` | SF | 85 °C |
| `fs_0` | FS | -40 °C |
| `fs_1` | FS | 27 °C |
| `fs_2` | FS | 85 °C |

## 3. 动态指标总览

12-bit ADC 理想满幅正弦量化 SNR 约为：

`SNR_ideal = 6.02 * 12 + 1.76 = 74.0 dB`

本次仿真 SNR 最好接近 `73.11 dB`，但最差为 `69.87 dB`。这说明设计已经具备超过 11-bit 的有效动态分辨率，但还没有达到理想 12-bit 的余量。对于前仿真而言，这个结果不差；对于最终规格签核而言，还需要更完整的指标证明。

图 1 给出了两个 `td` 参数点在 15 个角落下的 ENOB 变化。可以看到 `td=28n` 在几乎所有角落均优于 `td=24.05n`，且全角落均高于 11 bit。

![ENOB Across PVT Corners](enob_corners.svg)

图 2 给出了 SNR 结果。`td=28n` 的 SNR 平均值为 `71.48 dB`，相比 `td=24.05n` 的 `70.20 dB` 提升约 `1.28 dB`。虚线为理想 12-bit ADC 的约 `74 dB` 参考线。

![SNR Across PVT Corners](snr_corners.svg)

图 3 给出了 SFDR 结果。`td=28n` 的平均 SFDR 约为 `81.90 dB`，整体优于 `td=24.05n`，但最差角落仍下降到 `76.14 dB`。

![SFDR Across PVT Corners](sfdr_corners.svg)

### 3.1 动态指标统计

| td | ENOB min | ENOB avg | ENOB max | SNR min | SNR avg | SNR max | SFDR min | SFDR avg | SFDR max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `td=24.05n` | 11.08 | 11.34 | 11.60 | 68.61 dB | 70.20 dB | 71.49 dB | 77.60 dB | 80.76 dB | 83.12 dB |
| `td=28n` | 11.14 | 11.53 | 11.84 | 69.87 dB | 71.48 dB | 73.11 dB | 76.14 dB | 81.90 dB | 85.73 dB |

### 3.2 最差角落定位

| td | 指标 | 最差值 | 最差角落 | 说明 |
|---|---|---:|---|---|
| `td=24.05n` | ENOB | 11.08 bit | `ff_2`, FF 85 °C | 动态分辨率最差 |
| `td=24.05n` | SNR | 68.61 dB | `ff_2`, FF 85 °C | 噪声表现最差 |
| `td=24.05n` | SFDR | 77.60 dB | `fs_2`, FS 85 °C | 杂散最差 |
| `td=28n` | ENOB | 11.14 bit | `ff_2`, FF 85 °C | 全角落仍高于 11 bit |
| `td=28n` | SNR | 69.87 dB | `ff_2`, FF 85 °C | 较 `td=24.05n` 最差值提升 1.26 dB |
| `td=28n` | SFDR | 76.14 dB | `ff_2`, FF 85 °C | SFDR 最差值略低于 `td=24.05n` |

从最差角落看，`FF, 85 °C` 是核心风险角落。它同时压低 ENOB、SNR，并在 `td=28n` 下成为 SFDR 最差点。这个现象通常提示：高速、高温角落下，比较器再生过程、DAC settling、kickback、参考缓冲或数字耦合对频谱结果更敏感。仅凭 CSV 不能判断主因，但后续应优先在 `ff_2` 下保存 transient 波形、残差、比较器输入差分、CDAC settling 轨迹和 FFT spectrum。

图 4 是 `td=28n` 的 ENOB 热力图。颜色越偏暖代表 ENOB 越低，可以直观看到 `FF, 85 °C` 是最低点。

![ENOB Heatmap td=28n](enob_heatmap_td28n.svg)

### 3.3 两个 td 参数点对比

![td Dynamic Comparison](td_dynamic_comparison.svg)

| 比较项 | `td=24.05n` | `td=28n` | 变化 |
|---|---:|---:|---:|
| ENOB 平均值 | 11.34 bit | 11.53 bit | +0.20 bit |
| ENOB 最差值 | 11.08 bit | 11.14 bit | +0.06 bit |
| SNR 平均值 | 70.20 dB | 71.48 dB | +1.28 dB |
| SNR 最差值 | 68.61 dB | 69.87 dB | +1.26 dB |
| SFDR 平均值 | 80.76 dB | 81.90 dB | +1.13 dB |
| SFDR 最差值 | 77.60 dB | 76.14 dB | -1.46 dB |

`td=28n` 的总体优势明确：ENOB 与 SNR 均提升，平均 SFDR 也提升。唯一需要注意的是 SFDR 的最差值从 `77.60 dB` 降到 `76.14 dB`，说明较长 delay 虽改善噪声或 settling margin，但并不保证所有杂散项同步改善。该点需要检查 `ff_2` 角落 FFT 频谱，确认最大 spur 的频率位置与来源。

## 4. 角落明细表

下面给出 15 个角落下的 ENOB/SNR/SFDR 明细，便于复核。

| Corner | `td=24.05n` ENOB | `td=24.05n` SNR | `td=24.05n` SFDR | `td=28n` ENOB | `td=28n` SNR | `td=28n` SFDR |
|---|---:|---:|---:|---:|---:|---:|
| TT -40 °C | 11.50 | 71.25 | 83.12 | 11.84 | 73.11 | 85.05 |
| TT 27 °C | 11.25 | 69.81 | 78.79 | 11.48 | 71.41 | 79.99 |
| TT 85 °C | 11.26 | 69.80 | 81.20 | 11.42 | 70.53 | 82.00 |
| FF -40 °C | 11.54 | 71.30 | 83.04 | 11.71 | 72.11 | 83.99 |
| FF 27 °C | 11.41 | 70.32 | 81.37 | 11.47 | 70.72 | 81.75 |
| FF 85 °C | 11.08 | 68.61 | 78.29 | 11.14 | 69.87 | 76.14 |
| SS -40 °C | 11.43 | 71.32 | 81.56 | 11.63 | 72.48 | 82.85 |
| SS 27 °C | 11.39 | 70.72 | 80.85 | 11.56 | 71.87 | 80.17 |
| SS 85 °C | 11.20 | 69.36 | 80.59 | 11.40 | 70.80 | 81.81 |
| SF -40 °C | 11.60 | 71.49 | 82.66 | 11.78 | 72.88 | 85.51 |
| SF 27 °C | 11.23 | 69.28 | 81.31 | 11.66 | 71.75 | 81.98 |
| SF 85 °C | 11.13 | 68.98 | 80.09 | 11.32 | 70.21 | 80.88 |
| FS -40 °C | 11.45 | 70.36 | 81.97 | 11.69 | 71.93 | 85.73 |
| FS 27 °C | 11.27 | 69.94 | 78.99 | 11.48 | 71.24 | 81.12 |
| FS 85 °C | 11.30 | 70.46 | 77.60 | 11.44 | 71.29 | 79.46 |

## 5. 功耗分析

总 `Power` 在 CSV 中为负值，这通常来自仿真中电源电流方向或功率符号约定。工程评估时应使用绝对值表示消耗功耗。

图 5 展示各模块平均功耗。可以看出 comparator 相关功耗 `COMPOWER` 是主要功耗项，也是 `td=28n` 增加功耗的主要来源。

![Power Breakdown](power_breakdown.svg)

### 5.1 功耗统计

| td | Switch avg | Comparator avg | Logic avg | Sync avg | SR avg | Total avg abs | Total worst abs |
|---|---:|---:|---:|---:|---:|---:|---:|
| `td=24.05n` | 80.07 uW | 166.69 uW | 41.74 uW | 14.70 uW | 12.44 uW | 324.05 uW | 380.70 uW |
| `td=28n` | 80.08 uW | 178.39 uW | 41.74 uW | 14.70 uW | 12.44 uW | 335.77 uW | 395.50 uW |

`td=28n` 相比 `td=24.05n`：

| 功耗项 | 增量 |
|---|---:|
| Switch 平均功耗 | +0.01 uW |
| Comparator 平均功耗 | +11.70 uW |
| Logic 平均功耗 | 约 0 uW |
| Sync 平均功耗 | 约 0 uW |
| SR 平均功耗 | 约 0 uW |
| 总平均功耗绝对值 | +11.72 uW |

因此，本次 `td` 调整几乎没有影响数字逻辑、同步、switching 和 SR 部分，主要改变 comparator 相关功耗。换句话说，动态性能改善的主要代价集中在比较器路径上。

## 6. 能效 FoM 估算

假设采样率为 50 MS/s，使用 Walden FoM：

`FoM = Power / (2^ENOB * Fs)`

其中 Power 使用总功耗绝对值，ENOB 使用仿真导出的 ENOB。

![FoM and Power](fom_power.svg)

| td | 平均功耗 | 最差功耗 | 平均 FoM | 最差 FoM |
|---|---:|---:|---:|---:|
| `td=24.05n` | 324.05 uW | 380.70 uW | 2.51 fJ/conv-step | 3.52 fJ/conv-step |
| `td=28n` | 335.77 uW | 395.50 uW | 2.26 fJ/conv-step | 3.51 fJ/conv-step |

尽管 `td=28n` 功耗略高，但由于 ENOB 提升，平均 Walden FoM 反而更好。这说明从“能量换有效位数”的角度看，`td=28n` 是更优选择。最差 FoM 两者几乎相同，说明 `td=28n` 并没有明显恶化最差能效。

需要强调：FoM 这里是基于 CSV 中总功耗和 ENOB 的估算。若实际采样率、输入频率、输入幅度、FFT 点数或 ENOB 计算方式不同，FoM 应重新计算。

## 7. `PREWOCM eval err` 问题

`PREWOCM` 在两个参数点、全部 15 个角落均为 `eval err`：

| 输出 | `td=24.05n` | `td=28n` | 判断 |
|---|---:|---:|---|
| `PREWOCM` | 15/15 eval err | 15/15 eval err | 测量表达式失败 |

这更像是仿真测量表达式或节点引用问题，而不是直接证明电路功能失败。常见原因包括：

1. 被测节点不存在或保存设置中没有保存该节点。
2. ADE expression 中使用了错误的层级路径。
3. 表达式中依赖的 crossing、average、sample、clip 区间不成立。
4. transient 时间窗口不覆盖目标事件。
5. 某个表达式变量名在 Explorer/Assembler 中没有正确继承。

建议优先修复，因为 `PREWOCM` 很可能与 comparator preamp、precharge、common-mode 或 offset cancellation 相关。如果这个指标本来用于检查预放大器输出共模或比较器输入共模，那么它的失效会降低本次报告的完整性。

## 8. 工程判断：是否可接受

### 8.1 可以接受的口径

如果项目当前阶段是“带噪声前仿真，判断设计是否值得进入下一轮优化、版图或后仿准备”，并且内部目标为：

| 指标 | 建议门槛 | 本次 `td=28n` |
|---|---:|---:|
| ENOB worst | >= 11.0 bit | 11.14 bit |
| SNR worst | >= 68 dB | 69.87 dB |
| SFDR worst | >= 75 dB | 76.14 dB |
| Total power worst | <= 400 uW | 395.50 uW |

则 `td=28n` 可以判为“前仿真阶段可接受”。它已经在全 PVT 下保持超过 11-bit 的有效动态位数，且功耗仍处于约 0.4 mW 以内。

### 8.2 不能接受或需要保留风险的口径

如果项目规格为：

| 规格口径 | 当前问题 |
|---|---|
| ENOB 全角落 >= 11.5 bit | `td=28n` 最差只有 11.14 bit，不满足 |
| SNR 接近理想 12-bit 的 74 dB | `td=28n` 最差 69.87 dB，平均 71.48 dB，仍有明显差距 |
| 严格 12-bit 动态性能 | 最高 ENOB 11.84 bit，最差 11.14 bit，不应称为全角落 12-bit effective |
| 最终签核 | 缺少静态线性、失真、Monte Carlo、post-layout 等必要数据 |

因此，当前更准确的表述是：

> 该设计在 `td=28n` 下表现为“12-bit SAR ADC 架构中约 11.1 到 11.8 ENOB 的带噪声前仿真结果”。它具备进入下一阶段的价值，但还不能作为最终 12-bit ADC sign-off 结论。

## 9. 可能的性能瓶颈推断

结合数据趋势，可以给出以下工程推断。注意这些是从 CSV 结果反推的假设，需要波形和频谱进一步验证。

### 9.1 `FF, 85 °C` 最差

`FF, 85 °C` 同时使 ENOB 与 SNR 最差，说明高速热角落下的误差项更强。可能来源包括：

1. 比较器再生噪声或输入等效噪声上升。
2. CDAC 或参考路径 settling 不充分，尤其在高温与快角落下时序边界变化。
3. 数字开关活动耦合到比较器输入或参考节点。
4. 输入采样网络开关注入或 bootstrap 行为在热角落下变差。
5. 时钟相位非重叠或 reset/precharge 时间不足，导致上一周期残留。

### 9.2 `td=28n` 改善 ENOB/SNR

`td=28n` 相比 `td=24.05n` 的 ENOB 和 SNR 整体更好，表现像是转换或比较过程获得了更多时间裕量。它可能改善了：

1. DAC settling 误差。
2. 比较器输入端建立时间。
3. SAR 决策边界处的亚稳态概率。
4. 时钟相位之间的冲突或电荷注入残留。

但 SFDR 最差点略降，说明某个 spur 可能受时序调整影响而增强。建议保留 `td=28n`，但必须观察 `ff_2` FFT spectrum 中最大 spur 的频点。

### 9.3 Comparator 功耗是优化重点

功耗增量几乎全部来自 `COMPOWER`。如果后续需要压低功耗，优先检查：

1. comparator/preamp bias 是否随 `td` 配置变化。
2. auto-zero 或 precharge 阶段是否存在额外静态电流。
3. `td=28n` 是否导致某些动态节点保持导通更久。
4. comparator 的 reset、latch、preamp 阶段是否可以分相降低重叠电流。

## 10. 后续验证建议

为了把“前仿真可接受”推进到“设计可签核”，建议按以下优先级补充验证。

### 10.1 立即修复

1. 修复 `PREWOCM` 的 `eval err`。
2. 保存 `ff_2, td=28n` 下关键 transient 波形：`VIP/VIN`、CDAC top plate、comparator input、comparator output、reference node、SAR decision bits。
3. 保存 `ff_2, td=28n` 的 FFT spectrum，定位最大 spur 频率。

### 10.2 动态性能补充

| 项目 | 目的 |
|---|---|
| `SNDR/SINAD` | 用于严格计算 ENOB，避免只看 SNR |
| `THD` | 判断失真是否成为 SFDR/SNDR 限制因素 |
| FFT spur table | 定位最大 spur 来源 |
| input frequency sweep | 检查 Nyquist 附近性能退化 |
| input amplitude sweep | 检查接近满幅时失真与 clipping |
| coherent sampling 设置复核 | 防止 FFT leakage 影响 SNR/SFDR |

### 10.3 静态线性验证

| 项目 | 目的 |
|---|---|
| DNL | 检查 missing code 风险 |
| INL | 检查 capacitor mismatch、reference settling 和 comparator offset 的综合影响 |
| offset error | 检查输入零点偏移 |
| gain error | 检查参考、电容阵列比例和采样网络误差 |
| code histogram | 补充噪声和码宽一致性判断 |

### 10.4 鲁棒性验证

| 项目 | 目的 |
|---|---|
| Monte Carlo mismatch | 检查电容 mismatch、比较器 offset、开关 mismatch |
| supply variation | 检查 AVDD/DVDD/ref sensitivity |
| clock jitter | 检查高输入频率下 aperture uncertainty |
| reference buffer loading | 检查 CDAC switching 对 reference 的扰动 |
| post-layout RC extraction | 检查寄生电容、电阻、coupling 后性能 |

## 11. 推荐决策

建议当前决策如下：

| 决策项 | 建议 |
|---|---|
| `td` 选择 | 采用 `td=28n` 作为下一轮主分析点 |
| 是否继续推进 | 可以推进，但必须带着 `ff_2` 最差角落风险继续 |
| 是否需要重新优化 | 若目标只是 ENOB > 11 bit，全角落暂不需要大改；若目标是 ENOB > 11.5 bit，需要优化最差角落 |
| 下一步最重要工作 | 修复 `PREWOCM`，补 SNDR/THD/DNL/INL，检查 `ff_2` FFT spur |
| 报告状态 | 本报告适合作为前仿真阶段评审材料，不适合作为最终 sign-off 报告 |

最终建议：

> 选择 `td=28n` 继续推进。当前带噪声前仿真显示该 12-bit 50 MS/s SAR ADC 在全 PVT 下至少达到约 11-bit 以上 ENOB，功耗约 0.34 mW，整体表现可接受。但必须修复 `PREWOCM eval err`，并补齐 SNDR/THD/静态线性/Monte Carlo/后仿验证后，才能确认其是否真正满足 12-bit ADC 的完整规格。

## 12. 附录：原始有效输出项清单

| 输出项 | 状态 | 说明 |
|---|---|---|
| `SWITCHESPOWER` | 有效 | CDAC/switching 相关功耗 |
| `COMPOWER` | 有效 | comparator/preamp 相关功耗，主导功耗变化 |
| `PREWOCM` | 失败 | 全角落 `eval err` |
| `ENOB` | 有效 | 有效位数，当前最重要动态指标 |
| `SNR` | 有效 | 噪声相关动态指标 |
| `SFDR` | 有效 | 最大杂散相关指标 |
| `LOGICPOWER` | 有效 | 数字逻辑功耗 |
| `SYNCPOWER` | 有效 | 同步相关功耗 |
| `SRPOWER` | 有效 | SR latch 或相关模块功耗 |
| `Power` | 有效 | 总功耗，符号为负，评估时取绝对值 |
