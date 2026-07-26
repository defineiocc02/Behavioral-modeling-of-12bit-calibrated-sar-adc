# 硬件资源与 Verilog-A 移植方案

## 1. 模拟部分

每个差分侧：

| 项目 | 数量 |
|---|---:|
| high-segment unit capacitance | 71 Cu |
| bridge | 2 Cu |
| low-segment unit capacitance | 65 Cu |
| total | 138 Cu |
| independently switched groups | 14 |

P/N 总计 276 Cu。若 `Cu=4 fF`，主阵列总名义电容为 `1.104 pF`，每侧
`552 fF`。这不包含 sampling switch、comparator input 和 routing parasitic。

只需要一个主 comparator。v3.1 不增加 auxiliary calibration comparator、
calibration sub-DAC、LUT SRAM 或 CAM。

## 2. 正常转换数字资源规划

以下是由 Python 行为模型推导的资源规划。当前 `rtl/` 只实现并综合了前景
校准控制器和 lower-SAR 子转换器，尚未包含完整 normal-conversion SAR
sequencer、Q2 weighted decoder 或 ADC 顶层。因此不能把校准 RTL 综合结果
表述为“完整 ADC RTL 已可流片”。

- 15-state asynchronous SAR sequencer；
- 14 对 P/N bottom-plate controls；
- 7 个 P-side 和 7 个 N-side calibrated high-weight registers；
- 低段 7 个 nominal constants 与 1 个 terminal constant；
- 一个约 24-bit signed Q8 normal-conversion accumulator；
- 一个 common normalization reciprocal/multiplier；
- 14-bit unsigned Q2 output (`12 integer + 2 fractional`)。

当前可综合校准接口采用 unsigned Q8、12 个整数位，每个 20 bits，
14 个 P/N 高段寄存器共 280 bits。低段常数可综合为连线常量。
每个目标完成后立即截断回 Q8；Python 采用相同逐目标 Q8 格点，不保留
RTL 中不存在的递归额外小数精度。

## 3. 校准数字资源

校准硬件可与正常 decoder 复用：

- 一个 target counter（7 states）；
- 一个 pair counter（7 bits，0..127）；
- P0/P1/N0/N1 四状态控制；
- 两个 32-bit signed accumulation registers（当前 P/N 并行实现）；
- 四个 24-bit signed Q8 lower-SAR result registers；
- target validation comparator；
- 280-bit high-weight register bank。

总校准工作为 3584 个 lower-SAR sub-conversions。
校准是前景启动流程，不影响每次 normal conversion 的 15-comparison 延迟。
递归量尺不是固定标称值：校准 H2..H32 时，lower-SAR 会读取此前写入的
P/N Q8 高段权重；低段与 terminal 继续使用标称常数。

当前 Vivado 2018.3 综合（`xc7z020clg400-1`，100 MHz 约束）结果为：

- 449 LUT、595 registers、0 DSP、0 BRAM；
- setup WNS `+0.298 ns`、TNS `0 ns`、0/2101 failing endpoints；
- hold WHS `-0.147 ns`、THS `-0.436 ns`、4/2101 failing endpoints；
- pulse-width slack `+4.500 ns`，0/596 failing endpoints；
- `check_timing` 为 0 no-clock、0 constant-clock、0 unconstrained internal
  endpoints、0 missing input/output delay、0 combinational loop；
- 342/125 bonded IOB，即 273.60%。

三条 hold failure 从 `start` 到 target-index registers，另一条从 `cmp_out`
到 accumulator。它们是 raw FPGA I/O timing model 的 input-to-register
端点，不是内部 register-to-register setup failure，但意味着不能把
`+0.298 ns` 单独表述成“100 MHz 时序通过”。同时，当前顶层把 ASIC 内部
switch buses 和全部校准权重暴露成 parallel package pins，导致 IOB 超用，
无法直接 place-and-route。FPGA 原型必须先加 serialized/packed wrapper，
再做 implementation、hold repair 和 post-route timing。

两组 XSIM 自检分别覆盖校准平均/写入顺序，以及递归 P/N Q8 量尺读取。
上述数字只对应 calibration/lower-SAR RTL，不代表完整 ADC 数字顶层，
也不替代目标 standard-cell library 下的 ASIC synthesis、CTS 与 signoff STA。

## 4. Verilog-A 端口

推荐模拟模块只描述物理 CDAC 与 comparator-facing top plates：

```text
electrical VINP, VINN, VREFP, VREFN, VCM
electrical VTOP_P, VTOP_N
input SAMPLE
electrical VBOT_P[13:0]
electrical VBOT_N[13:0]
```

stage 到电容组：

```text
0 H32, 1 H16, 2 H8-A, 3 H8-R, 4 H4, 5 H2, 6 H1,
7 L32, 8 L16, 9 L8, 10 L4, 11 L2-A, 12 L2-R, 13 L1
```

采样相位，P 侧所有 14 个 bottom plates 接 VINP，N 侧接 VINN，只有
`VTOP_P/VTOP_N` 钳到 VCM。`VBRIDGE` 保持内部浮动并由 bridge/low 段
电容分压决定，不增加 bridge-node 采样开关。转换相位由 BITP/BITN 选择
VCM 或 VREFP。bridge 是内部 `VTOP ↔ VBRIDGE` 电容，没有数字
bottom-plate port。

## 5. 失配映射

不要给一个 32-Cu group 直接施加 `0.5%` group sigma。正确方法是：

```text
C_group = Cu × sum_{k=1..N}(1 + epsilon_k)
epsilon_k ~ Normal(0, 0.005)
```

因此 group relative sigma 自动按 `0.5%/sqrt(N)` 缩小。P/N 两侧独立生成，
bridge 的两个 unit cells 也独立生成。

`va/cdac_behavioral.va` 不在模型内部随机抽取失配；`P_MC_*`/`N_MC_*`
参数是外部已经实现的 group 倍率。驱动 Verilog-A Monte Carlo 时，应由
testbench/PDK 按上述 unit-cell 求和生成这些倍率。若直接给每个 group
同一个 0.5% sigma，就会退化成错误的 flat PER-CAP 压力模型。

## 6. 移植顺序

1. 先在 Verilog-A 中复现理想 15-decision trace；
2. 对四个代表输入比较 Python 与 VA 的每 stage `VTOP_P-VTOP_N`；
3. 加入 unit-cell mismatch 并比对 physical oracle weights；
4. 接入数字校准寄存器与 Q8 accumulator；
5. 使用同一 `N=4096, k=1019, -0.5 dBFS, rectangular` FFT 协议；
6. 最后才进入 Spectre PVT、settling、reference droop 和 parasitic 验证。

当前 `va/cdac_behavioral.va` 已实现独立 P/N bottom-plate 端口和 SAMPLE
下降沿电荷捕获；`va/strongarm_cmp.va` 已统一时钟阈值、逻辑摆幅和 ready
延迟。当前文件已在隔离 VM 沙箱通过 Spectre standalone smoke；CDAC 保留4条
`VACOMP-1116` 连续信号 `transition()` 警告。这些文件仍只是模块级运行完成、
待 full-ADC AMS 与逐 stage 波形交叉验证的移植模型，不是晶体管级签核。
