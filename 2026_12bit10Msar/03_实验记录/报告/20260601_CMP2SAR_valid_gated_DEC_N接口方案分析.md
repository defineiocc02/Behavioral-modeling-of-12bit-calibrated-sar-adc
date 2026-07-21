---
date: 2026-06-01
project: 2026_12bit10Msar
topic: COM_IAZ 到 SAR_LOGIC 的 valid-gated DEC_N 接口
source_netlist: 10_项目区/2026_12bit10Msar/03_实验记录/网表/netlist.txt
tags:
  - SAR_ADC
  - Comparator
  - COM_IAZ
  - SAR_LOGIC
  - DEC_N
---

# CMP2SAR valid-gated DEC_N 接口方案分析

## 1. 结论

我建议采用方案二：

```text
COM_IAZ 的 COMP/COMN
        ↓
CMP2SAR_IF：valid-gated differential-to-single decision interface
        ↓
DEC_N
        ↓
原 SAR_LOGIC 的 COMN 输入端
```

这个方案和当前工程的结构匹配。它的核心价值是：不重画、不重构原来的 `SAR_LOGIC`，只在比较器和 `SAR_LOGIC` 之间插入一个“有效窗口保护 + 差分转单端 + 低有效输出”的接口。这样可以避免 `COM_IAZ` 在 reset、autozero 或未再生完成时出现 `COMP=0, COMN=0`，被原 SAR DFF 当成有效低电平判决。

当前最应该先做的是静态门级验证版：

```text
DEC_N = ~(CMP_VALID & COMP & ~COMN)
```

如果后续确认比较器极性相反，再改为：

```text
DEC_N = ~(CMP_VALID & COMN & ~COMP)
```

正式版本可以加 `POL_SEL`，但第一轮不建议把问题复杂化。先把 `DEC_N` 的安全态、有效态和采样时序跑通。

## 2. 当前网表证据

本分析基于当前导出的网表：

```text
10_项目区/2026_12bit10Msar/03_实验记录/网表/netlist.txt
```

### 2.1 COM_IAZ 端口

当前 `COM_IAZ` 的子电路端口为：

```spectre
subckt COM_IAZ AGND AVDD CLK RST VIN VIP VON VOP
```

顶层实例为：

```spectre
I28 (AGND AVDD CLK RST N P COMN COMP) COM_IAZ
```

所以当前连接关系是：

| COM_IAZ 端口 | 顶层网络 |
| --- | --- |
| `VIN` | `N` |
| `VIP` | `P` |
| `VON` | `COMN` |
| `VOP` | `COMP` |
| `CLK` | `CLK` |
| `RST` | `RST` |

也就是说，顶层已经有差分比较器输出 `COMN/COMP`，只是现在没有经过保护，直接把 `COMN` 送进了 SAR。

### 2.2 SAR_LOGIC 端口

当前 `SAR_LOGIC` 子电路端口中只有一个比较器决策输入：

```spectre
subckt SAR_LOGIC ... CCLK COMN DGND DVDD PRST SET<0> ... SET<12>
```

顶层实例目前是：

```spectre
I15 (... BITP<1> BITP<0> CCLK COMN DGND DVDD PRST SET<0> ... SET<12>) SAR_LOGIC
```

因此方案二的实际改动点非常明确：把这行实例里的 `COMN` 改成 `DEC_N`，而 `SAR_LOGIC` 子电路本身先不动。

### 2.3 原 DFF 确实对 COMN 低电平敏感

`DFF` 子电路端口为：

```spectre
subckt DFF CCLK CLK1 COMN D DGND DVDD N P Q
```

其中 `COMN` 出现在 PMOS 串联支路中：

```spectre
M7 (net3 COMN net4 DVDD) pch ...
```

PMOS gate 为低时导通，因此 `COMN=0` 会打开该支路。也就是说，原 `SAR_LOGIC` 的比较器输入确实带有低有效触发特征。这个结构解释了为什么比较器 reset 态如果输出 `00`，裸接 `COMN` 会有误判风险。

### 2.4 当前时钟和 reset 线

顶层激励中：

```spectre
V7  (RST  AGND) pulse val0=0 val1=vdd period=100n delay=100p width=td
V13 (PRST AGND) pulse val0=0 val1=vdd period=100n delay=-2n  width=30n
V40 (CLK00 AGND) pulse val0=0 val1=vdd period=100n delay=30n width=69n
```

`SYNC` 产生 `CCLK` 和 `CLK`：

```spectre
I21 (CCLK CLK CLK00 DGND DVDD SET<12>) SYNC
```

`COM_IAZ` 的 `CLK` 端由顶层 `CLK` 驱动。网表中 `COM_IAZ` 有：

```spectre
M9  (DP CLK AVDD AVDD) pch ...
M26 (DN CLK AVDD AVDD) pch ...
M23 (net7 CLK AGND AGND) nch ...
```

这说明 `CLK=0` 时 `DP/DN` 被 PMOS 预充，`CLK=1` 时 NMOS tail 打开，更像是 `CLK=1` evaluate。但是这仍然要用一次单步瞬态波形确认，不要只凭名字决定最终时序。

## 3. 原始问题

现在的结构近似是：

```text
COM_IAZ.COMN → SAR_LOGIC.COMN
```

风险状态是：

```text
reset / 未判决 / 再生未完成：
COMP = 0
COMN = 0
```

由于原 `SAR_LOGIC` 的 `COMN` 输入低有效，`COMN=0` 可能被当成一次真实判决，使某些 `BITP/BITN/SET` 支路提前翻转。这个错误如果落在采样边沿附近，就会表现为：

1. 单次码错误；
2. bit 周期之间的状态继承；
3. 对整机 FFT/SFDR 产生离散杂散；
4. 在 FF、FS、低裕量输入或边沿不对齐时更明显。

因此接口的第一目标不是“放大”或“锁存”比较器输出，而是：

```text
比较器无效时，强制送给 SAR 的输入为安全高电平 1。
比较器有效且方向满足低有效事件时，才允许 DEC_N=0。
```

## 4. DEC_N 定义

`DEC_N` 是送给原 `SAR_LOGIC.COMN` 端口的新单端信号。

| `DEC_N` | 对原 SAR_LOGIC 的含义 |
| ---: | --- |
| `1` | 安全态，不触发低有效判决 |
| `0` | 有效低电平判决，允许原 DFF 采样 |

如果比较器极性为：

```text
P > N → COMP=1, COMN=0
P < N → COMP=0, COMN=1
```

并且希望：

```text
P > N → DEC_N=0
P < N → DEC_N=1
```

则：

```text
LOW_EVENT = CMP_VALID & COMP & ~COMN
DEC_N     = ~LOW_EVENT
```

即：

```text
DEC_N = ~(CMP_VALID & COMP & ~COMN)
```

真值表如下：

| 状态 | COMP | COMN | CMP_VALID | LOW_EVENT | DEC_N |
| --- | ---: | ---: | ---: | ---: | ---: |
| reset / 未判决 | 0 | 0 | 0 | 0 | 1 |
| reset 输出仍为 00，但 valid 错误拉高 | 0 | 0 | 1 | 0 | 1 |
| 非法同高态 | 1 | 1 | 1 | 0 | 1 |
| 有效判决 P>N | 1 | 0 | 1 | 1 | 0 |
| 有效判决 P<N | 0 | 1 | 1 | 0 | 1 |

这个表说明：`00` 和 `11` 都不会产生低有效事件，只有 `COMP=1, COMN=0, CMP_VALID=1` 同时成立时，原 SAR 才会看到低电平。

## 5. 极性问题

必须注意，当前网表的端口名不能完全替代极性验证。当前实例是：

```spectre
I28 (AGND AVDD CLK RST N P COMN COMP) COM_IAZ
```

也就是：

```text
VIN=N
VIP=P
VON=COMN
VOP=COMP
```

但 `COM_IAZ` 是 PMOS 输入对 + 动态再生结构，最终 `P>N` 时到底是 `COMP=1, COMN=0`，还是 `COMP=0, COMN=1`，应该通过固定差分输入的瞬态仿真确认。

若实测极性相反，即：

```text
P > N → COMN=1, COMP=0
P < N → COMN=0, COMP=1
```

则接口应改为：

```text
LOW_EVENT = CMP_VALID & COMN & ~COMP
DEC_N     = ~LOW_EVENT
```

正式兼容版本为：

```text
LOW0 = CMP_VALID & COMP & ~COMN
LOW1 = CMP_VALID & COMN & ~COMP

LOW_EVENT = POL_SEL ? LOW1 : LOW0
DEC_N     = ~LOW_EVENT
```

其中：

| `POL_SEL` | 低有效事件 |
| ---: | --- |
| `0` | `COMP & ~COMN` |
| `1` | `COMN & ~COMP` |

但是第一轮验证不建议直接上 `POL_SEL`。先用最小版本减少变量，把波形和时序问题看清楚。

## 6. CMP_VALID 生成

`CMP_VALID` 不应该从 `COMP/COMN` 自己组合出来，因为 reset 的 `00`、非法态的 `11`、以及再生中间态都可能误导逻辑。`CMP_VALID` 应该来自比较器 evaluate 时钟。

结合当前网表，初始建议为：

```text
CLK_DLY   = delay(CLK)
CMP_VALID = CLK & CLK_DLY & ~RST & ~PRST
```

含义：

1. `CLK=1` 后认为比较器进入 evaluate；
2. 通过 `CLK_DLY` 等待再生过程完成一段时间；
3. `RST=1` 或 `PRST=1` 时强制无效；
4. `CLK` 下降后 `CMP_VALID` 立即关闭，让 `DEC_N` 回到安全高电平。

如果瞬态确认 `COM_IAZ` 实际是 `CLK=0` evaluate，则要整体改成：

```text
CLK_EVAL  = ~CLK
CLK_DLY   = delay(CLK_EVAL)
CMP_VALID = CLK_EVAL & CLK_DLY & ~RST & ~PRST
```

当前从 PMOS 预充和 NMOS tail 的连接看，`CLK=1` evaluate 的可能性更高，但最终仍以波形为准。

## 7. 第一版门级实现

当前网表里已有 2 输入 `NAND1`、`NOR1`、`INVX2/3/4/5/6/7`，没有直接看到 3 输入 NAND。因此最小静态版本可以用 2 输入 NAND 组合实现：

```text
COMN_B    = ~COMN
CLK_DLY   = delay(CLK)
CLK_VALID = CLK & CLK_DLY
RST_VALID = ~RST & ~PRST
CMP_VALID = CLK_VALID & RST_VALID

AB        = CMP_VALID & COMP
DEC_N     = ~(AB & COMN_B)
```

等价于：

```text
DEC_N = ~(CMP_VALID & COMP & ~COMN)
```

### 7.1 可用于临时网表验证的子电路草案

下面这个版本只适合快速 transient 验证。正式设计应回到 schematic 中画 `CMP2SAR_IF`，再重新导出网表。

```spectre
subckt CMP2SAR_IF COMP COMN CLK RST PRST DGND DVDD DEC_N
    // COMN_B = ~COMN
    ICOMN_B (COMN COMN_B DVDD DGND) INVX2

    // CLK_DLY: first-pass physical inverter delay.
    // If delay is too small, increase inverter chain length or use a tunable delay cell.
    ICLK_D0 (CLK CLK_B DVDD DGND) INVX3
    ICLK_D1 (CLK_B CLK_DLY DVDD DGND) INVX3

    // RST_VALID = ~RST & ~PRST
    IRST_B  (RST RST_B DVDD DGND) INVX2
    IPRST_B (PRST PRST_B DVDD DGND) INVX2
    IR0     (RST_B DGND DVDD PRST_B N_RSTV) NAND1
    IR1     (N_RSTV RST_VALID DVDD DGND) INVX2

    // CLK_VALID = CLK & CLK_DLY
    IC0     (CLK DGND DVDD CLK_DLY N_CLKV) NAND1
    IC1     (N_CLKV CLK_VALID DVDD DGND) INVX2

    // CMP_VALID = CLK_VALID & RST_VALID
    IV0     (CLK_VALID DGND DVDD RST_VALID N_VALID) NAND1
    IV1     (N_VALID CMP_VALID DVDD DGND) INVX2

    // DEC_N = ~(CMP_VALID & COMP & ~COMN)
    IA0     (CMP_VALID DGND DVDD COMP N_AB) NAND1
    IA1     (N_AB AB DVDD DGND) INVX2
    IDEC    (AB DGND DVDD COMN_B DEC_N) NAND1
ends CMP2SAR_IF
```

顶层连接改为：

```spectre
I_DEC (COMP COMN CLK RST PRST DGND DVDD DEC_N) CMP2SAR_IF

I15 (... BITP<1> BITP<0> CCLK DEC_N DGND DVDD PRST SET<0> ... SET<12>) SAR_LOGIC
```

对比当前顶层：

```spectre
I15 (... BITP<1> BITP<0> CCLK COMN DGND DVDD PRST SET<0> ... SET<12>) SAR_LOGIC
```

唯一真正改变原 SAR 的地方是把 `COMN` 换成 `DEC_N`。

### 7.2 关于 delay 的实现

上面的 `INVX3 → INVX3` 只是一个初始延迟。更好的验证方法是在 ADE 中把 delay 做成可扫变量，例如：

```text
valid_td = 200 ps
valid_td = 500 ps
valid_td = 800 ps
valid_td = 1 ns
```

如果使用当前网表中的 Verilog-A `not_gate` 做临时延迟，可以做两个反相器保持极性：

```spectre
Ivd0 (CLK CLK_B)   not_gate vlogic_high=vdd vlogic_low=0 vtrans=vdd/2 tdel=valid_td/2 trise=10p tfall=10p
Ivd1 (CLK_B CLK_DLY) not_gate vlogic_high=vdd vlogic_low=0 vtrans=vdd/2 tdel=valid_td/2 trise=10p tfall=10p
```

但 `not_gate` 是 AHDL/行为级单元，只能用于调时序窗口，不应作为最终版版图实现。

## 8. 时序约束

目标时序是：

```text
DAC settle 完成
    ↓
COM_IAZ evaluate
    ↓
COMP/COMN 再生稳定
    ↓
CMP_VALID 拉高
    ↓
DEC_N 根据有效判决更新
    ↓
CCLK 采样 DEC_N
    ↓
CMP_VALID 拉低
    ↓
DEC_N 回到 1，等待下一 bit
```

关键约束为：

```text
t_CCLK_sample > t_CMP_VALID_rise + t_DEC_N_delay + t_setup_SAR
```

并且：

```text
DEC_N 必须在下一 bit 的采样窗口前回到 1。
```

如果 `CMP_VALID` 太早，`DEC_N` 会跟随未完成再生的 `COMP/COMN`，仍然可能误判。如果 `CMP_VALID` 太晚，`CCLK` 采样时 `DEC_N` 还没有稳定，SAR 会丢判决或采到上一状态。

当前 `SYNC` 中有 `tdel=4.5n` 的延迟参数，SAR bit 时钟和比较器 evaluate 的相对位置很可能由这里决定。因此 `CMP_VALID` 的延迟不应独立拍脑袋，需要在同一张 transient 波形里同时看：

```text
CLK
RST
PRST
COMP
COMN
CMP_VALID
DEC_N
CCLK
SET<k>
BITP<k>
BITN<k>
```

## 9. 动态预充式版本的判断

GPT 建议的动态 decision latch 思路是合理的：

```text
CMP_VALID=0：DEC_N_INT 被 PMOS 预充为 1
CMP_VALID=1 且 LOW_EVENT=1：DEC_N_INT 被 NMOS stack 拉低
否则保持高
```

这种形式速度快、面积小，也符合你原 SAR 逻辑偏动态的风格。但我不建议第一版就上动态 latch，原因有三点：

1. `DEC_N_INT` 是动态节点，valid 窗口如果错了，会引入保持、泄漏和前一 bit 残留问题；
2. keeper 尺寸不好选，太弱抗泄漏差，太强又拖慢下拉；
3. 现在最需要验证的是逻辑极性和时序窗口，不是极限速度。

推荐顺序是：

```text
第一轮：静态 NAND 版，确认功能和时序。
第二轮：需要兼容多种比较器时，加 POL_SEL。
第三轮：静态版跑通后，再做预充式动态 latch 优化。
```

## 10. 仿真检查清单

### 10.1 极性确认仿真

先不要跑 FFT，先做固定输入差分的 transient：

```text
P = VCM + Δ
N = VCM - Δ
```

观察 evaluate 后：

```text
COMP / COMN 哪个为 1，哪个为 0
```

再反过来：

```text
P = VCM - Δ
N = VCM + Δ
```

确认极性后，再决定用 `COMP & ~COMN` 还是 `COMN & ~COMP` 作为低有效事件。

### 10.2 reset 态检查

在 `RST=1` 或 `PRST=1` 的窗口中，必须满足：

```text
CMP_VALID = 0
DEC_N = 1
```

即使比较器输出为：

```text
COMP = 0
COMN = 0
```

也不允许 `DEC_N` 被拉低。

### 10.3 有效正判决检查

若采用默认极性：

```text
COMP = 1
COMN = 0
CMP_VALID = 1
```

必须得到：

```text
DEC_N = 0
```

并且低脉冲覆盖 `CCLK` 的采样窗口。

### 10.4 有效负判决检查

若采用默认极性：

```text
COMP = 0
COMN = 1
CMP_VALID = 1
```

必须得到：

```text
DEC_N = 1
```

不能出现短暂低脉冲。

### 10.5 bit 间恢复检查

在每一位判决结束后、下一位开始前，必须看到：

```text
CMP_VALID ↓
DEC_N ↑ 到 1
```

如果 `DEC_N` 的低电平拖到下一位，下一位会继承上一位状态，这是非常危险的。

### 10.6 整机指标检查

接口波形确认后再跑整机指标：

1. 对比加入 `CMP2SAR_IF` 前后的输出码序列；
2. 对比 `BITP/BITN/SET` 是否少了 reset 边沿误翻转；
3. 再看 FFT、SNDR、SFDR；
4. 在 TT、FF、SS、FS、SF 下检查 `DEC_N` 是否仍有足够时序裕量。

## 11. 对 FF/FS 下 SFDR 恶化的解释

你之前观察到 FF、FS 下比较器会影响整体 SFDR，这个接口可能正好命中其中一类原因。

在快角或偏斜角下，以下情况更容易发生：

1. `COM_IAZ` reset 后输出节点恢复更快或更不对称；
2. `COMP/COMN` 可能在真正判决前经过短暂 `00`、`11` 或亚稳态；
3. SAR DFF 的低有效支路在快角下更容易被短脉冲打开；
4. `CCLK` 和 `CLK` 的相对位置随工艺角移动，原本侥幸避开的毛刺可能落入采样窗口。

裸 `COMN` 方案的问题是：它把“比较器输出为低”直接等价成“比较器已经有效判决为低”。这在动态比较器里不成立。`CMP2SAR_IF` 的作用是增加一个明确的时间许可：

```text
只有 evaluate 后经过足够延迟，且 COMP/COMN 呈互补有效态，才允许 SAR 看见低电平。
```

因此该接口不一定能解决所有 SFDR 问题，但它能显著降低 reset 态、非法态、未完成再生态对 SAR 决策的污染。

## 12. 风险点

### 12.1 CMP_VALID 不是越晚越好

太早会误判，太晚会错过 `CCLK`。最终要靠 sweep 找窗口。

### 12.2 不能只看 COMP/COMN 生成 valid

比如 `COMP=1, COMN=0` 可能只是再生过程中的短暂毛刺，不一定是已经可采样的结果。valid 必须来自时钟域。

### 12.3 PRST/RST 极性要确认

当前激励显示 `RST`、`PRST` 都是高脉冲，因此第一版用 `~RST & ~PRST` 屏蔽 valid 是合理的。但如果 schematic 中有局部反相或后续改动，仍要以波形为准。

### 12.4 数模电源域要注意

当前网表中 `AVDD` 和 `DVDD` 都是 1.8 V，`AGND` 和 `DGND` 都是 0 V。但 `COM_IAZ` 属于模拟域，`SAR_LOGIC` 属于数字域。`CMP2SAR_IF` 放在哪个电源域，要和版图、电源噪声、ESD/隔离策略一致。第一版仿真可用 `DGND/DVDD` 实现接口输入门，但最终版要确认模拟输出驱动数字门不会引入过大回踢或地弹影响。

### 12.5 `not_gate` 只能作为仿真辅助

当前 netlist 已经使用 AHDL `not_gate`，所以临时验证时可以用它做可调 delay。但最终实现应使用真实 transistor-level inverter/delay chain。

## 13. 推荐执行顺序

1. 在 schematic 里新增 `CMP2SAR_IF` cell，第一版只实现默认极性：

```text
DEC_N = ~(CMP_VALID & COMP & ~COMN)
```

2. 顶层增加实例：

```spectre
I_DEC (COMP COMN CLK RST PRST DGND DVDD DEC_N) CMP2SAR_IF
```

3. 把原 `SAR_LOGIC` 实例输入从 `COMN` 改成 `DEC_N`：

```spectre
I15 (... CCLK DEC_N DGND DVDD PRST SET<0> ... SET<12>) SAR_LOGIC
```

4. 保存并导出网表，不建议长期手改导出网表。

5. 先跑短 transient，只看：

```text
CLK RST PRST COMP COMN CMP_VALID DEC_N CCLK SET<12:0> BITP/BITN
```

6. 扫 `valid_td`：

```text
200 ps, 500 ps, 800 ps, 1 ns
```

7. 极性、reset、bit 间恢复都通过后，再跑完整码流和 FFT。

8. 如果后面要在 FIA、StrongARM、NMOS/PMOS 比较器之间切换，再引入 `POL_SEL`。

9. 静态版验证通过后，再考虑做动态预充式 `DEC_N_INT`，并单独优化 keeper 和输出 buffer。

## 14. 我的最终建议

这个方案是可行的，而且很适合你现在的阶段。它不是大改 SAR，而是把原来“不安全的裸 `COMN`”变成“安全、低有效、带 valid 的 `DEC_N`”。从当前网表看，插入点非常清楚，修改范围也小。

但是第一版不要直接做复杂动态 latch，也不要直接加太多可选极性。先做静态 NAND 保护版，把下面三件事确认掉：

```text
1. reset / 未判决时 DEC_N 恒为 1；
2. 有效判决时 DEC_N 极性正确；
3. CCLK 采样时 DEC_N 已经稳定，下一 bit 前又回到 1。
```

只要这三条成立，再去看 SFDR 会更有意义。否则 FFT 上看到的 spur 很可能只是数字决策接口在某些工艺角下被比较器 reset 态污染，而不是 CDAC 或比较器本体线性度的问题。
