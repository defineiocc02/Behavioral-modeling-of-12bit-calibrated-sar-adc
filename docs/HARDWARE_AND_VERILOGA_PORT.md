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

只需要一个主 comparator。v3.0 不增加 auxiliary calibration comparator、
calibration sub-DAC、LUT SRAM 或 CAM。

## 2. 正常转换数字资源

- 15-state asynchronous SAR sequencer；
- 14 对 P/N bottom-plate controls；
- 7 个 P-side 和 7 个 N-side calibrated high-weight registers；
- 低段 7 个 nominal constants 与 1 个 terminal constant；
- 一个约 20-bit signed Q6 accumulator；
- 一个 common normalization reciprocal/multiplier；
- 14-bit unsigned Q2 output (`12 integer + 2 fractional`)。

若 high-weight register 采用 unsigned Q6、12 个整数位，每个 18 bits，
14 个寄存器共 252 bits。低段常数可综合为连线常量。

## 3. 校准数字资源

校准硬件可与正常 decoder 复用：

- 一个 target counter（7 states）；
- 一个 pair counter（9 bits，0..511）；
- P0/P1/N0/N1 四状态控制；
- 一个约 30-bit signed accumulation register，可分时复用；
- target validation comparator；
- 252-bit high-weight register bank。

总校准工作为 14336 个 lower-SAR sub-conversions，与退役版本相同。
校准是前景启动流程，不影响每次 normal conversion 的 15-comparison 延迟。

## 4. Verilog-A 端口

推荐模拟模块只描述物理 CDAC 与 comparator-facing top plates：

```text
electrical VINP, VINN, VREFP, VREFN, VCM
electrical VTOP_P, VTOP_N
input SAMPLE
input [13:0] BITP
input [13:0] BITN
```

stage 到电容组：

```text
0 H32, 1 H16, 2 H8-A, 3 H8-R, 4 H4, 5 H2, 6 H1,
7 L32, 8 L16, 9 L8, 10 L4, 11 L2-A, 12 L2-R, 13 L1
```

采样相位，P 侧所有 14 个 bottom plates 接 VINP，N 侧接 VINN。转换相位
由 BITP/BITN 选择 VCM 或 VREFP。bridge 是内部 `VTOP ↔ VBRIDGE` 电容，
没有数字 bottom-plate port。

## 5. 失配映射

不要给一个 32-Cu group 直接施加 `0.5%` group sigma。正确方法是：

```text
C_group = Cu × sum_{k=1..N}(1 + epsilon_k)
epsilon_k ~ Normal(0, 0.005)
```

因此 group relative sigma 自动按 `0.5%/sqrt(N)` 缩小。P/N 两侧独立生成，
bridge 的两个 unit cells 也独立生成。

## 6. 移植顺序

1. 先在 Verilog-A 中复现理想 15-decision trace；
2. 对四个代表输入比较 Python 与 VA 的每 stage `VTOP_P-VTOP_N`；
3. 加入 unit-cell mismatch 并比对 physical oracle weights；
4. 接入数字校准寄存器与 Q6 accumulator；
5. 使用同一 `N=4096, k=127, -0.5 dBFS, rectangular` FFT 协议；
6. 最后才进入 Spectre PVT、settling、reference droop 和 parasitic 验证。

这份文档是端口和资源规划，不是已完成的晶体管级或 Verilog-A 签核。
