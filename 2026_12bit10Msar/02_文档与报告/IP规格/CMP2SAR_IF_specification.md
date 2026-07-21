---
title: CMP2SAR_IF 模块 IP 规格与维护说明
aliases:
  - CMP2SAR_IF
  - Comparator-to-SAR Interface
  - DEC_N 接口
tags:
  - IP规格
  - SAR_ADC
  - Comparator
  - VerilogA
  - DEC_N
created: 2026-06-01
updated: 2026-06-01
---

# CMP2SAR_IF 模块 IP 规格与维护说明

## 1. 模块定位

`CMP2SAR_IF` 是比较器到 SAR 逻辑之间的安全判决接口。它把动态比较器的双端输出：

```text
COMP / COMN
```

转换成原 `SAR_LOGIC` 可以读取的单端、低有效、安全判决信号：

```text
DEC_N
```

当前建议的系统连接为：

```text
COM_IAZ.COMP/COMN
        ↓
CMP2SAR_IF
        ↓
DEC_N
        ↓
SAR_LOGIC 原 COMN 输入端
```

源码位置：

```text
10_项目区/2026_12bit10Msar/04_辅助工具/veriloga_models/CMP2SAR_IF.va
```

相关方案分析：

```text
10_项目区/2026_12bit10Msar/03_实验记录/报告/20260601_CMP2SAR_valid_gated_DEC_N接口方案分析.md
```

## 2. 要解决的问题

当前 PMOS / IAZ 动态比较器在 reset、autozero 或未判决阶段可能出现：

```text
COMP = 0
COMN = 0
```

而原 `SAR_LOGIC` 对输入低电平敏感。当前网表中 `DFF` 的 `COMN` 端接入 PMOS 支路，`COMN=0` 会打开对应通路，因此裸接 `COMN` 有可能把比较器 reset 态误读成有效判决。

`CMP2SAR_IF` 的保护规则是：

```text
比较器无效时：
    DEC_N = 1

比较器有效，且 COMP/COMN 形成指定互补判决时：
    DEC_N = 0

其他状态：
    DEC_N = 1
```

它不是简单地把 `COMP/COMN` 合成一个信号，而是给原 SAR 增加一个有效判决协议。

## 3. Verilog-A 原型

```verilog
module CMP2SAR_IF(COMP, COMN, CLK, RST, PRST, DGND, DVDD, DEC_N);
```

| 端口 | 方向 | 类型 | 含义 |
| --- | --- | --- | --- |
| `COMP` | input | electrical | 比较器正输出 |
| `COMN` | input | electrical | 比较器负输出 |
| `CLK` | input | electrical | 比较器 evaluate 时钟，对应当前 `COM_IAZ.CLK` |
| `RST` | input | electrical | 比较器/模拟 reset，高有效 |
| `PRST` | input | electrical | SAR logic pre-reset，高有效 |
| `DGND` | inout | electrical | 数字地 |
| `DVDD` | inout | electrical | 数字电源 |
| `DEC_N` | output | electrical | 送给原 `SAR_LOGIC.COMN` 的低有效安全判决信号 |

重要约束：

```text
CLK 是比较器 evaluate 时钟。
CCLK 是 SAR_LOGIC 采样/推进时钟。
不要把 CLK 和 CCLK 接反。
```

## 4. 顶层接线

当前顶层网表中比较器实例为：

```spectre
I28 (AGND AVDD CLK RST N P COMN COMP) COM_IAZ
```

因此 `CMP2SAR_IF` 推荐实例为：

```spectre
I_IF (COMP COMN CLK RST PRST DGND DVDD DEC_N) CMP2SAR_IF
```

原 SAR 实例中：

```spectre
I15 (... CCLK COMN DGND DVDD PRST SET<0> ... SET<12>) SAR_LOGIC
```

应改为：

```spectre
I15 (... CCLK DEC_N DGND DVDD PRST SET<0> ... SET<12>) SAR_LOGIC
```

如果在 Spectre netlist 中直接 include 行为模型，可加入：

```spectre
ahdl_include "10_项目区/2026_12bit10Msar/04_辅助工具/veriloga_models/CMP2SAR_IF.va"
```

实际 ADE 中建议用 cellview 管理 Verilog-A model，避免每次导出网表后手动补 include。

## 5. 参数定义

源码参数为：

```verilog
parameter real td_valid = 5e-10;
parameter real td_out   = 1e-11;
parameter real tr       = 1e-11;
parameter real tf       = 1e-11;
parameter integer pol_sel = 0;
```

| 参数 | 默认值 | 含义 | 维护建议 |
| --- | ---: | --- | --- |
| `td_valid` | `5e-10` | `CLK` 上升后等待多久才相信比较器输出 | 优先扫参，建议 200 ps、500 ps、800 ps、1 ns |
| `td_out` | `1e-11` | `DEC_N` 输出传播延迟 | 通常保持 10 ps |
| `tr` | `1e-11` | `DEC_N` 输出上升时间 | 收敛困难时可加到 50 ps 或 100 ps |
| `tf` | `1e-11` | `DEC_N` 输出下降时间 | 收敛困难时可加到 50 ps 或 100 ps |
| `pol_sel` | `0` | 比较器输出极性选择 | 若 SAR 输出方向反了，先改这个，不要先改 SAR 主逻辑 |

### 5.1 `td_valid`

`td_valid` 是最关键的调试参数。它决定 `CLK` 上升后等待多久才认为 `COMP/COMN` 可以被相信，也就是比较器 evaluate 后多久打开 valid window。

当前源码用延迟时钟实现：

```verilog
clk_dly_v = absdelay(V(CLK, DGND), td_valid);
cmp_valid = clk_bit && clk_dly_bit && (!rst_bit) && (!prst_bit);
```

逻辑上等价于另一种写法：

```verilog
@(cross(V(CLK, DGND) - 0.5 * V(DVDD, DGND), +1)) begin
    valid_time = $abstime + td_valid;
end

cmp_valid = clk_bit && ($abstime >= valid_time) && (!rst_bit) && (!prst_bit);
```

两种写法的目标一致：

```text
CLK 上升
→ 等 td_valid
→ cmp_valid 才允许变成 1
→ 接口才开始读取 COMP/COMN
```

如果以后改成 `cross + valid_time` 版本，要注意初始化 `valid_time`，并确认 reset/CLK 下降后 valid 不会残留到下一 bit。

若 `td_valid` 太小：

```text
比较器还没再生完成，CMP_VALID 已经打开，DEC_N 可能跟随中间态或毛刺。
```

典型表现：

```text
PMOS 比较器 reset 态仍然污染 SAR；
某些 bit 提前动作；
DEC_N 在 COMP/COMN 半有效状态下乱跳；
输出码不稳定；
SFDR/SNDR 异常。
```

若 `td_valid` 太大：

```text
比较器已经判完，但接口迟迟不放行，DEC_N 可能来不及在 CCLK 采样前稳定。
```

典型表现：

```text
SAR 采样不到正确判决；
某些 bit 保持默认值；
输出码卡住或偏移；
有效转换速度不够。
```

第一轮建议扫：

```text
td_valid = 2e-10
td_valid = 5e-10
td_valid = 8e-10
td_valid = 1e-9
```

第一轮只扫 `td_valid`，先固定：

```text
td_out = 1e-11
tr     = 1e-11
tf     = 1e-11
```

### 5.2 `td_out`

`td_out` 是 `DEC_N` 输出传播延时，默认 10 ps。它不是比较器有效窗口延时，而是：

```text
内部 low_event 变化
→ 等 td_out
→ DEC_N 输出开始变化
```

它和 `td_valid` 的区别是：

| 参数 | 作用 |
| --- | --- |
| `td_valid` | 决定什么时候相信比较器输出 |
| `td_out` | 决定 `DEC_N` 输出变化前的传播延时 |

`td_out` 一般保持较小：

```text
td_out = 10 ps ~ 50 ps
```

如果 `td_out` 太大，即使 `cmp_valid` 和 `low_event` 已经正确生成，`DEC_N` 也可能赶不上 `CCLK` 采样。

### 5.3 `tr`

`tr` 是 `DEC_N` 从低到高的上升时间，默认 10 ps。

`DEC_N` 上升代表接口回到安全态，通常发生在：

```text
比较器进入无效期；
low_event 消失；
RST/PRST 重新有效；
CLK evaluate 窗口结束。
```

如果 `tr` 太大，上一 bit 的低有效状态可能恢复太慢，污染下一 bit：

```text
上一 bit DEC_N = 0
下一 bit 开始前 DEC_N 还没回到 1
→ 下一 bit 可能继承错误低电平
```

如果 `tr` 太小，边沿太硬，Spectre 可能需要很小 timestep，仿真变慢或更难收敛。10 ps 是合理起点，收敛困难时可尝试 50 ps。

### 5.4 `tf`

`tf` 是 `DEC_N` 从高到低的下降时间，默认 10 ps。

`DEC_N` 下降代表检测到有效低事件：

```text
CMP_VALID = 1
COMP/COMN = 指定互补态
→ DEC_N: 1 → 0
```

如果 `tf` 太大，`CCLK` 采样时 `DEC_N` 可能仍在中间电平，原 SAR DFF 看到的逻辑状态会不确定。

如果 `tf` 太小，也可能引起收敛压力。因此建议先用 10 ps；若收敛不好，再试：

```text
tr = 5e-11
tf = 5e-11
```

### 5.5 四个延时的时序关系

低有效判决路径可近似理解为：

```text
CLK 上升
↓
等待 td_valid
↓
CMP_VALID = 1
↓
根据 COMP/COMN 生成 low_event
↓
等待 td_out
↓
DEC_N 开始下降
↓
经过 tf
↓
DEC_N 稳定为低
↓
CCLK 采样
```

因此低判决路径大概是：

```text
t_DEC_N_valid ≈ t_CLK_rise + td_valid + td_out + tf
```

采样约束为：

```text
t_CCLK_sample > t_CLK_rise + td_valid + td_out + tf + t_setup
```

如果是 `DEC_N` 回到安全高电平，则重点看：

```text
td_out + tr
```

能否保证下一 bit 开始前恢复到 `DEC_N=1`。

### 5.6 和 `tdac/tdel` 的关系

当前工程网表里还有：

```text
tdac = 2 ns
tdel = 4.5 ns
```

这两个属于原 SAR/SYNC 时序，不是 `CMP2SAR_IF` 的输出延时。

| 参数 | 位置 | 作用 |
| --- | --- | --- |
| `tdac` | SAR/SYNC 逻辑 | DAC settling 和采样/比较触发之间的时序关系 |
| `tdel` | SAR/SYNC 逻辑 | 每 bit token/转换步进间隔 |
| `td_valid` | `CMP2SAR_IF` | `CLK` 上升后多久认为比较器输出有效 |
| `td_out` | `CMP2SAR_IF` | `DEC_N` 输出传播延时 |
| `tr/tf` | `CMP2SAR_IF` | `DEC_N` 输出边沿斜率 |

新增接口必须嵌入原时序：

```text
CLK 上升
→ td_valid 后 DEC_N 才可能有效
→ CCLK 采样 DEC_N
→ 下一 bit
```

所以 `td_valid` 不能大于 `CCLK` 给出的可用窗口。

### 5.7 `pol_sel`

默认：

```text
pol_sel = 0
```

对应：

```text
COMP=1, COMN=0, cmp_valid=1 → DEC_N=0
```

反向：

```text
pol_sel = 1
```

对应：

```text
COMN=1, COMP=0, cmp_valid=1 → DEC_N=0
```

如果换比较器以后输出极性变化，只改 `pol_sel`，不要重画 `SAR_LOGIC`。

## 6. 内部逻辑

### 6.1 电源跟随阈值

源码中：

```verilog
vdd_now = V(DVDD, DGND);
vth = 0.5 * vdd_now;
```

逻辑判断阈值不是写死 0.9 V，而是跟随当前 `DVDD`。在 `DVDD=1.8V` 时：

```text
vth = 0.9 V
```

### 6.2 延迟 evaluate 时钟

源码中：

```verilog
clk_dly_v = absdelay(V(CLK, DGND), td_valid);
```

等价于：

```text
CLK_DLY = delay(CLK, td_valid)
```

### 6.3 模拟电压转逻辑位

源码中把各端口电压转换成 0/1 逻辑：

```verilog
clk_bit     = (V(CLK, DGND)  > vth);
clk_dly_bit = (clk_dly_v     > vth);
rst_bit     = (V(RST, DGND)  > vth);
prst_bit    = (V(PRST, DGND) > vth);
comp_bit    = (V(COMP, DGND) > vth);
comn_bit    = (V(COMN, DGND) > vth);
```

### 6.4 valid window

核心保护逻辑为：

```verilog
cmp_valid = clk_bit && clk_dly_bit && (!rst_bit) && (!prst_bit);
```

等价于：

```text
CMP_VALID = CLK & delay(CLK) & ~RST & ~PRST
```

这意味着：

```text
CLK 刚上升时，不相信 COMP/COMN；
RST 或 PRST 为高时，不相信 COMP/COMN；
只有 evaluate 持续超过 td_valid 后，才允许比较器结果影响 DEC_N。
```

### 6.5 low event

默认极性：

```verilog
low_event = cmp_valid && comp_bit && (!comn_bit);
```

反向极性：

```verilog
low_event = cmp_valid && comn_bit && (!comp_bit);
```

因此 `COMP/COMN=00` 和 `COMP/COMN=11` 都会被过滤，不会让 `DEC_N` 拉低。

### 6.6 DEC_N 输出

```verilog
dec_bit = low_event ? 0 : 1;
V(DEC_N, DGND) <+ transition(dec_bit ? vdd_now : 0.0, td_out, tr, tf);
```

即：

```text
DEC_N = ~low_event
```

`DEC_N` 默认高电平，只有在有效低事件出现时才变低。

## 7. 真值表

假设：

```text
pol_sel = 0
```

| 状态 | CLK | CLK_DLY | RST | PRST | CMP_VALID | COMP | COMN | DEC_N |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 比较器 reset | x | x | 1 | x | 0 | 0 | 0 | 1 |
| SAR pre-reset | x | x | x | 1 | 0 | 0 | 0 | 1 |
| CLK 刚上升 | 1 | 0 | 0 | 0 | 0 | x | x | 1 |
| 未判决 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 1 |
| 非法态 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 1 |
| 有效低事件 | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 |
| 有效非低事件 | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 1 |

最关键行为：

```text
COMP=0, COMN=0 时，DEC_N 必须保持为 1。
```

## 8. 仿真检查流程

加入该模块后，先不要直接看 FFT。先跑短 transient，保存并观察：

```text
CLK
RST
PRST
COMP
COMN
DEC_N
CCLK
SET<12>
BITP<12>
BITN<12>
```

推荐检查顺序：

1. reset 期间 `DEC_N=1`。
2. `CLK` 刚进入 evaluate、`td_valid` 尚未到达时，`DEC_N=1`。
3. `CMP_VALID` 后，`COMP=1, COMN=0` 是否得到 `DEC_N=0`。
4. `CMP_VALID` 后，`COMP=0, COMN=1` 是否得到 `DEC_N=1`。
5. `DEC_N` 的低脉冲是否覆盖 `CCLK` 采样窗口。
6. 下一 bit 到来前，`DEC_N` 是否回到 1。
7. FF、FS、SF、SS、TT 下重复检查 `td_valid` 裕量。

判断表：

| 现象 | 可能原因 | 调整 |
| --- | --- | --- |
| reset 期间 `DEC_N` 掉到 0 | `RST/PRST` 极性或接线错误 | 检查 `cmp_valid` 公式与接线 |
| `DEC_N` 过早变化 | `td_valid` 太小 | 增大 `td_valid` |
| `DEC_N` 在 `CCLK` 前来不及稳定 | `td_valid` 太大 | 减小 `td_valid` |
| 输出码方向明显反了 | 比较器极性相反 | 切换 `pol_sel` |
| 仿真收敛困难 | 输出边沿太理想 | 增大 `tr/tf` 到 50 ps 或 100 ps |

## 9. 使用条件

当前模型默认：

```text
RST 高有效 reset
PRST 高有效 pre-reset
CLK 高电平 evaluate
COMP/COMN 输出接近数字 rail
DVDD/DGND 为 SAR 数字逻辑电源地
```

如果真实电路中某个信号极性不同，需要维护对应逻辑。

例如如果 `RST` 是低有效 reset，则不能继续使用：

```verilog
(!rst_bit)
```

而要改为：

```verilog
rst_bit
```

如果 `CLK` 是低电平 evaluate，则 valid 逻辑也要改成基于 `~CLK` 的窗口。

## 10. 后续晶体管级替换

Verilog-A 验证通过后，建议替换成晶体管级接口。等价逻辑保持不变：

```text
CMP_VALID = CLK & delay(CLK) & ~RST & ~PRST

LOW0 = CMP_VALID & COMP & ~COMN
LOW1 = CMP_VALID & COMN & ~COMP

DEC_N = ~(POL_SEL ? LOW1 : LOW0)
```

推荐晶体管级组成：

```text
COMP/COMN 对称 buffer
CLK delay chain
CMP_VALID logic
polarity select logic
DEC_N output buffer
```

如果最终追求速度和面积，可以做动态预充式版本：

```text
CMP_VALID=0：DEC_N_INT 预充为 1
CMP_VALID=1 且 LOW_EVENT=1：DEC_N_INT 拉低
其他情况：DEC_N_INT 保持高
```

但动态版本必须单独验证 keeper、泄漏、bit 间恢复和 PVT 时序裕量。

## 11. 维护规则

1. 不建议后续再让 `COMN/COMP` 直接进入 `SAR_LOGIC`。
2. 换比较器后先检查 `CLK/RST/PRST` 极性，再检查 `P>N` 对应 `COMP/COMN` 极性。
3. 输出方向反了优先调 `pol_sel`。
4. FF/FS 下 SFDR 异常时，优先检查 `DEC_N` 是否在 reset 或 valid 前出现低脉冲。
5. `td_valid` 应作为正式仿真的 sweep 参数保留。
6. 行为模型用于功能和时序窗口验证，最终版图前应替换为晶体管级逻辑。

## 12. 一句话总结

`CMP2SAR_IF` 给原 SAR logic 增加了一个有效判决协议：

```text
比较器无效时，DEC_N 强制为安全高电平；
只有比较器有效，并且 COMP/COMN 形成指定互补态时，DEC_N 才允许变低。
```

这正是为了适配当前 PMOS / IAZ 比较器可能出现的 `00` reset 态，同时保留原 `SAR_LOGIC` 的单端低有效输入结构。
