---
title: CDAC 校准解码 Verilog-A 集成与时序说明
created: 2026-07-14
updated: 2026-07-14
tags:
  - VerilogA
  - SAR_ADC
  - CDAC
  - calibration
  - integration
---

# CDAC 校准解码 Verilog-A 集成与时序说明

## 1. 交付内容与模型边界

本次交付包括：

- `04_辅助工具/veriloga_models/DEC_CAL.va`
- `04_辅助工具/veriloga_models/tb_DEC_CAL.scs`

`DEC_CAL` 的作用是：

1. 使用已知的 `ACT_W0~ACT_W11` 模拟真实 CDAC 判决权重；
2. 通过差分双相残差递推恢复 `cw0~cw11`；
3. 在现有 `SOUT` 上升沿锁存 `BP<12:0>`；
4. 使用校准权重产生 12-bit offset-binary 输出；
5. 提供校准状态、输出有效脉冲和权重模拟监控。

该模块仍是 golden behavioral model。它没有物理比较器判决输入，也没有 CDAC 校准切换控制输出，因此不能单独从未知晶体管级 CDAC 中测量权重。真正闭环时还需增加校准模式 MUX、CDAC 强制切换控制和 comparator residue-search 模块。

## 2. 当前全电路逻辑

当前顶层 `test_12bit50MSAR_AMS_final` 的主要信号链为：

```text
VIP/VIN
  |
  v
BS + SWITCH + CDAC ---- P/N ----> COM_IAZ
                                  |
                                  | COMP/COMN
                                  v
                             SYNC_asnyc
                                  |
                                  | DEC_N, CCLK, CLK
                                  v
                              SAR_LOGIC
                                  |
                                  | BITP<12:0>, BITN<12:0>
                                  v
                               PN_BUF
                                  |
                                  | BP<12:0>, BN<12:0>
                                  v
                                 DEC
                                  |
                                  | Bit<11:0>
                                  v
                              SNDR_DAC
                                  |
                                  v
                                 OUT
```

`PN_BUF` 对每个 `BITP/BITN` 使用两级反相器，因此 `BP` 与 `BITP` 同极性，`BN` 与 `BITN` 同极性。现有 `DEC` 读取的是 `BP<0:12>`，校准解码模块也应读取 `BP`，避免直接加载 SAR 锁存器输出。

## 3. 为什么数字判决权重不是物理电容标签

物理 CDAC 电容为：

```text
子阵列：1C, 2C, 4C, 6C, 10C, 16C, 24C
主阵列：1C, 2C, 4C, 8C, 16C
桥接电容：1C
```

桥接标称衰减为 1/64，因此物理有效权重为：

```text
1, 2, 4, 6, 10, 16, 24, 64, 128, 256, 512, 1024
```

但 SAR 在切换最大电容前先进行一次比较。判决和电容切换的对应关系为：

| 判决 | 随后控制的物理电容 | 物理有效权重 | 数字判决权重 |
| --- | --- | ---: | ---: |
| `BP<12>` | BIT12 | 1024 | 2048（最终 MSB） |
| `BP<11>` | BIT11 | 512 | 1024 |
| `BP<10>` | BIT10 | 256 | 512 |
| `BP<9>` | BIT9 | 128 | 256 |
| `BP<8>` | BIT8 | 64 | 128 |
| `BP<7>` | BIT7 | 24 | 48 |
| `BP<6>` | BIT6 | 16 | 32 |
| `BP<5>` | BIT5 | 10 | 20 |
| `BP<4>` | BIT4 | 6 | 12 |
| `BP<3>` | BIT3 | 4 | 8 |
| `BP<2>` | BIT2 | 2 | 4 |
| `BP<1>` | BIT1 | 1 | 2 |
| `BP<0>` | 无后续电容 | - | 1（终止量化位） |

因此原 DEC 实际数学关系为：

```text
CODE = 2048*BP12
     + 1024*BP11 + 512*BP10 + 256*BP9 + 128*BP8
     + 48*BP7 + 32*BP6 + 20*BP5 + 12*BP4
     + 8*BP3 + 4*BP2 + 2*BP1 + BP0
```

校准解码模块采用完全相同的 nominal decoder 权重：

```text
{W0..W11} = {1,2,4,8,12,20,32,48,128,256,512,1024}
```

## 4. `DEC_CAL` 端口映射

### 4.1 电源和校准控制

| VA 端口 | 顶层连接 | 说明 |
| --- | --- | --- |
| `DVDD` | `DVDD` | 与现有 DEC 同名，逻辑高和门限由该端口实时计算 |
| `DGND` | `DGND` | 与现有 DEC 同名 |
| `CAL_CLK` | 新增 `CAL_CLK` | 只推进权重校准状态机 |
| `CAL_RST` | 新增 `CAL_RST` | 只允许一次性前台校准复位 |
| `CAL_START` | 新增 `CAL_START` | 一次性启动脉冲 |

不能把 `CAL_RST` 接到当前 `RST/RST1/PRST`。这些信号每 100 ns 重复一次，会反复清除校准结果。

不能把 `CAL_CLK` 接到当前动态比较器 `CLK`。`CLK` 在一次转换中包含多次异步比较脉冲，不是稳定的校准状态机时钟。

### 4.2 判决和输出有效信号

| VA 端口 | 顶层连接 |
| --- | --- |
| `BP<12:0>` | `BP<12:0>`，与原 DEC 网络同名，整组总线直接连接 |
| `SOUT` | `SOUT`，与原 DEC 网络同名 |

`SOUT` 已经是原 DEC 的最终输出锁存时钟。模块在相同上升沿读取稳定的 `BP<12:0>`。

默认参数 `FIRST_INVERT=0`、`RAW_INVERT=0` 对应 BP 总线。如果改接互补 BN 总线，应同时设为 1。

### 4.3 输出端口

| VA 端口 | 推荐新节点 |
| --- | --- |
| `Bit<11:0>` | 替换原 DEC 时接 `Bit<11:0>`；并联验证时接 `Bit_CAL<11:0>` |
| `CAL_DONE` | `CAL_DONE` |
| `CAL_BUSY` | `CAL_BUSY` |
| `CAL_ERR` | `CAL_ERR` |
| `CODE_VALID` | `CODE_VALID` |
| `W_CAL<11:0>` | `W_CAL<11:0>` |

`Bit<0>` 是 LSB，`Bit<11>` 是 MSB。`W_CAL<11:0>` 只用于保存波形，不应连接到数字逻辑。

## 5. 推荐嵌入结构

第一次联合仿真保留原 DEC，增加 `DEC_CAL` 和第二个 SNDR_DAC：

```text
BP<12:0>
  |-- original DEC --> Bit<11:0>     --> original SNDR_DAC --> OUT
  |
  `-- DEC_CAL --------> Bit_CAL<11:0> --> second SNDR_DAC --> CAL_OUT
```

第二个 SNDR_DAC 的数据端口顺序必须为：

```text
AGND, Bit_CAL<11>, Bit_CAL<10>, ..., Bit_CAL<0>, CAL_OUT
```

不要把 `Bit<11:0>` 拆开后按 LSB 优先接到 SNDR_DAC，否则会发生 bit reversal。

## 6. 校准递推逻辑

| 校准目标 | nominal target | wall 组合 |
| --- | ---: | --- |
| W1 | 2 | W0 |
| W2 | 4 | W1+W0 |
| W3 | 8 | W2+W1+W0 |
| W4 | 12 | W3+W2 |
| W5 | 20 | W4+W3 |
| W6 | 32 | W5+W4 |
| W7 | 48 | W6+W4+W2 |
| W8 | 128 | sum(W0..W7) |
| W9 | 256 | sum(W0..W8) |
| W10 | 512 | sum(W0..W9) |
| W11 | 1024 | sum(W0..W10) |

双相测量为：

```text
meas_pos = +(ACT_target - ACT_wall) + offset + pos_error + noise_pos
meas_neg = -(ACT_target - ACT_wall) + offset + neg_error + noise_neg

residual_est = 0.5 * (meas_pos - meas_neg)
candidate = calibrated_wall + residual_est
```

共同的 comparator offset 在相减后消失。每个 `candidate` 必须位于 nominal target 的 `1 +/- WEIGHT_TOL` 范围内，否则置位 `CAL_ERR`。

校准完成后，解码权重默认执行端点增益归一化：

```text
gain_scale = 2047 / sum(cw0..cw11)
decode_weight[i] = cw[i] * gain_scale
```

## 7. 前台校准时序

独立冒烟测试采用：

```text
CAL_RST  : 1 ns 上升，3 ns 下降
CAL_START: 5 ns 上升，7 ns 下降
CAL_CLK  : 10 ns 首次上升，周期 10 ns
```

模块的状态时序为：

```text
CAL_START rise
  -> start_pending=1

next CAL_CLK rise
  -> enter CAL
  -> reset cal_idx to 1
  -> no weight is measured on this edge

following 11 CAL_CLK rising edges
  -> measure W1, W2, ... W11

W11 accepted
  -> CAL_BUSY=0
  -> CAL_DONE=1
```

因此 START 后需要 12 个 `CAL_CLK` 上升沿：第一个进入校准状态，后面 11 个分别恢复 W1~W11。

## 8. 当前 ADC 的 100 ns 转换时序

当前顶层时钟周期为 100 ns，即 10 MS/s。

### 8.1 周期边界和预复位

约 `0~20 ns`：

- `RST`、`RST1`、`PRST` 完成比较器、开关和 SAR_LOGIC 复位；
- CDAC 底板进入采样/VCM 初始化状态；
- `CLK0` 控制 bootstrap 采样开关相位；
- 这些信号均为每周期重复控制，不能复位权重校准寄存器。

### 8.2 异步逐次比较

约 `20~98 ns`：

1. COM_IAZ 完成第一次 VCM 比较；
2. SAR_LOGIC 锁存 `BITP/BITN<12>`；
3. `SET<0>` 使 BIT12 电容按第一次判决切换；
4. 残差建立后进行下一次比较，得到 `BITP/BITN<11>`；
5. `SET<1>` 切换 BIT11；
6. 依次执行到 `SET<11>` 和最后的 `BITP/BITN<0>`；
7. PN_BUF 产生同极性的 `BP/BN<12:0>`。

`SET` 与物理电容的关系是：

```text
SET<0>  -> BIT12
SET<1>  -> BIT11
...
SET<11> -> BIT1
```

### 8.3 输出锁存

约 `98~100 ns`：

- `SOUT` 上升；
- 原 DEC 锁存 BP 判决并产生 `Bit<11:0>`；
- `DEC_CAL` 同时读取 `BP<12:0>` 并产生 `Bit_CAL<11:0>`；
- 模块拉高 `CODE_VALID`；
- `SOUT` 下降后，`CODE_VALID` 下降。

校准完成前的 `SOUT` 上升沿不会更新校准输出，也不会产生 `CODE_VALID`。

## 9. ADE 联合仿真设置

建议新增三个一次性/独立源：

```spectre
CAL_RST  : pulse, delay=1n, width=2n, period > tran stop
CAL_START: pulse, delay=5n, width=2n, period > tran stop
CAL_CLK  : pulse, delay=10n, width=5n, period=10n
```

建议保存：

```text
BP<12:0>
SOUT
CAL_RST CAL_START CAL_CLK
CAL_DONE CAL_BUSY CAL_ERR CODE_VALID
Bit_CAL<11:0>
OUT CAL_OUT
W_CAL<11:0>
```

第一轮 nominal 验证要求：

1. `CAL_ERR` 始终为低；
2. START 后第 12 个 CAL_CLK 边沿完成校准；
3. 所有 `W_CAL<11:0>` 等于 nominal 权重乘 `WMON_SCALE`；
4. `OUT` 与 `CAL_OUT` 的转换码一致；
5. `CODE_VALID` 与 SOUT 有效窗口一致；
6. 码流无 bit reversal、无半量程反转。

## 10. 从行为模型进入物理闭环的后续模块

若要让校准算法直接测量未知的物理 CDAC 权重，需要另外增加：

1. `CAL_MODE_MUX`：在 normal SAR 控制与 calibration 强制切换控制之间选择；
2. `CAL_SWITCH_CTRL`：依次构造 target/wall 的正、负两种极性；
3. `CAL_CMP_LATCH`：在指定残差建立时间后锁存 COM_IAZ 判决；
4. `CAL_RESIDUE_SEARCH`：用多次 comparator 决策估算残差，而不是读取 `ACT_W*`；
5. `CAL_WEIGHT_REG`：保存恢复的权重并交给 calibrated decoder；
6. 正常转换屏蔽逻辑：`CAL_BUSY=1` 时禁止输出码被下游采样。

当前 `DEC_CAL` 已经实现第 5 项的行为等价物和最终 calibrated decoder，可作为后续物理闭环的数字参考模型。
