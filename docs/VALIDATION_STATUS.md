# v3.1 验证状态

更新时间：2026-07-26

活动版本：`v3.1.0`

活动分支：`codex/python-cal-validation`

## 结论先行

当前行为级结论围绕“失配是否被校准稳住”，不是围绕噪声性能：

- **理想链路正确**：零失配、零校准扰动时 SNDR 74.643 dB、ENOB
  12.107 bit、无缺码、无局部 backstep；
- **名义失配场景通过**：0.5% PER-UNIT 失配配合 0.3 mV RMS
  calibration-only 比较器扰动，100/100 动态和静态均通过；
- **双倍失配压力点基本稳定但不宣称全通过**：1.0% PER-UNIT 下动态
  100/100，通过校准后的最差 SNDR 仍为 73.641 dB；静态为 98/100，
  两个种子的 INL peak 分别为 1.02918 和 1.00010 LSB；
- **零校准扰动组是机制隔离，不是目标工作模式**：它们揭示重复 lower-SAR
  比较的确定性量化锁定。0.3 mV 不进入正常转换、FFT 或 SNDR 噪声路径。

因此，当前结果支持“0.5% 单位电容失配下，校准能够稳住整体行为级性能”；
它不等同于晶体管级、PVT、版图后仿或硅片签核。

## 失配与扰动定义

正式矩阵统一采用 **PER-UNIT**：

```text
Cunit,i = Cu * (1 + epsilon_i)
epsilon_i ~ Normal(0, sigma_unit^2)
Cgroup   = sum(Cunit,i)
```

P/N 两侧独立抽样，bridge 由两个单位电容组成，失配作用域为 `all`。组电容
相对 sigma 随单位数按 `1/sqrt(N)` 缩小；这不是把同一相对 sigma 平铺到
每个整组电容上的 flat PER-CAP 压力模型。

0.3 mV RMS 的唯一定义是每次 P0/P1/N0/N1 前景校准比较器的输入等效高斯
扰动：

```text
n ~ Normal(0, (0.3 mV RMS)^2)
```

它约为 1.8 V / 4096 条件下的 0.68 LSB。正常转换保持零噪声，且项目没有
额外 dither DAC。

## 冻结的五组正式矩阵

所有失配组均为相同的 100 个种子；ideal 为 1 个确定性样本。校准权重在每个
递归目标完成后立即截断到与 RTL 一致的 Q8，最终输出使用 Q2。

| 场景 | Pre SNDR P50 | Cal SNDR P50 / min | Cal ENOB P50 / min | 动态 | 静态 | 缺码 | 全样本判定 |
|---|---:|---:|---:|---:|---:|---:|---|
| ideal, 0 mV | 74.643 | 74.643 / 74.643 dB | 12.107 / 12.107 | 1/1 | 1/1 | 0 | PASS |
| 0.5% PER-UNIT, 0 mV | 67.506 | 73.249 / 69.857 dB | 11.876 / 11.312 | 95/100 | 40/100 | 1 | FAIL（隔离组） |
| 0.5% PER-UNIT, 0.3 mV | 67.506 | 74.521 / 74.050 dB | 12.087 / 12.008 | 100/100 | 100/100 | 0 | **PASS（名义场景）** |
| 1.0% PER-UNIT, 0 mV | 62.154 | 72.825 / 68.455 dB | 11.805 / 11.079 | 96/100 | 27/100 | 1 | FAIL（隔离组） |
| 1.0% PER-UNIT, 0.3 mV | 62.154 | 74.424 / 73.641 dB | 12.070 / 11.940 | 100/100 | 98/100 | 0 | FAIL（压力点尾部） |

名义场景的 physical-weight oracle gap P50/P95 为 0.135/0.357 dB；
1.0% 压力点为 0.226/0.679 dB。校准后的动态性能已经接近使用真实物理权重
的 oracle。

1.0% 压力点的两个静态失败种子是：

| Seed | Cal SNDR | DNL peak | INL peak | Missing code |
|---:|---:|---:|---:|---:|
| 10062 | 73.641 dB | 0.79783 LSB | 1.02918 LSB | 0 |
| 10080 | 74.002 dB | 0.72007 LSB | 1.00010 LSB | 0 |

这里不为把 98/100 改成 100/100 而引入 LUT、排序、CAM 或单调钳位。压力点
如实保留为余量信息。

## 单调性如何使用

局部 backstep 继续记录，但不单独构成当前发布硬门：

- 理想链路 backstep 为 0；
- 失配后冗余 decision word 的相邻可达边界可能出现局部次序交换；
- 若它造成缺码、DNL/INL 超限或 SNDR/ENOB 下降，现有真实性能门会失败；
- 若 code-density 和动态性能均满足目标，则不额外要求每个可达边界严格
  数学单调。

这与“忽略问题”不同：CSV/JSON 保留了 backstep 数、rollback 和影响区间，
但不据此过度设计一套异常映射硬件。

| 正式条件 | 有 backstep seeds | count P50/P95/max | 最大 rollback | 受影响输入宽度 P50/P95/max |
|---|---:|---:|---:|---:|
| 0.5% nominal, 0.3 mV | 99/100 | 157.5 / 747.2 / 991 | 1 LSB | 0.0453% / 0.1152% / 0.1620% |
| 1.0% stress, 0.3 mV | 99/100 | 166.0 / 744.5 / 981 | 1 LSB | 0.0738% / 0.2319% / 0.2989% |

count 很大是因为多个很窄的 decision interval 可以落入同一个输出 code，
因此不能把 count 直接等同于宽范围模拟输入倒退。当前更有工程意义的量是
最大 rollback 只有 1 LSB，nominal 最大受影响输入宽度只有 0.1620%。
若未来应用把 strict monotonicity 写入硬规格，再单独升级为验收门。

## 数字与模型一致性

- Python 校准器按 H1C 至 H32C 递归更新 P/N 两侧权重；
- 每个目标提交后立即向下截断为 Q8，与 `cal_weight_reg.sv` 一致；
- lower-SAR 使用当前已校准的侧独立 Q8 权重；
- 输出重构为 Q2；
- 15 次比较中的最后一次为 comparator-only 终端判决，不增加 CDAC 电容。

Python 回归、XSIM 自检和 Vivado 综合结果在最终 PDF 中作为独立层级列出。
当前 RTL 覆盖校准控制和 lower-SAR 子转换器，不得外推为完整 ADC RTL
signoff。

100 MHz synthesis proxy 的 setup WNS 为 `+0.298 ns`，但 hold WHS 为
`-0.147 ns`，共有 4/2101 failing endpoints；342/125 bonded IOB 也说明
raw parallel `cal_top` 不能直接在该 FPGA package 上实现。因此结论是
“校准子集可综合、setup estimate 通过，但 timing constraints 未全部满足”，
不是“100 MHz 完整时序通过”。详细报告见 `scripts/synth_timing_summary.rpt`、
`scripts/synth_hold.rpt` 和 `scripts/synth_check_timing.rpt`。

## 证据与复现边界

冻结证据位于 `evidence/mismatch_matrix/`。每个场景保留：

- 完整 CSV；
- machine-readable summary；
- `run_manifest.json`；
- 总矩阵中的文件与源码 SHA-256。

当前 pipeline、calibrator 和 config SHA-256 分别为：

```text
58c178a37e8e9151056eb0139da3d9b7c8d094da998e3befcb072bf0ea3c3477
a8972d87e499e5f55315b53d69bfaff39fb9e5f77182dc42082d98427a552545
290b223dc324a8734a8416c2d6cdbcefe567fcd79e82778bf2a267a900dc9c19
```

活动图只能从该冻结目录重绘。`docs/archive/v3.0/` 中的旧图和旧数字不得
进入 v3.1 报告。
