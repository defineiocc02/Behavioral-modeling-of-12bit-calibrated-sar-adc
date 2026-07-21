---
title: SAR_LOGIC 与 SYNC 模块深度分析
aliases: [SAR逻辑分析, SYNC分析, 时序分析]
tags: [type/note, topic/sar-adc]
created: 2026-05-12
updated: 2026-05-12
---

# SAR_LOGIC 与 SYNC 模块深度分析

> 数据来源：VM netlist `input.scs`，2026-05-12
> 设计库: `12bit_50M_SAR`, cell: `test_12bit50MSAR_AMS_final`, view: `schematic`

---

## 一、系统级信号流

```
CLK00 (10MHz) ──→┐
                  │
              ┌───┴───┐
              │ SYNC  ├──→ CLK ──→ COM_IAZ (比较器)
              │       ├──→ CCLK ─→ SAR_LOGIC (13个DFF)
              └───┬───┘
                  │
            SET<12> (来自 SAR_LOGIC, 转换完成信号)
```

```
PRST ──────→┐
             │
         ┌───┴──────┐
         │ SAR_LOGIC ├──→ BITP<12:0>, BITN<12:0> ──→ CDAC + SWITCH
         │           ├──→ SET<12> ──→ SYNC (停止CCLK)
         └───────────┘
```

---

## 二、SYNC 模块 — 异步 CCLK 发生器

### 2.1 拓扑结构

SYNC 本质上是一个 **CLK00 边沿触发的单次脉冲发生器**，带有 **SET<12> 使能抑制**。

```
CLK00 ──→ I33(NAND) ──→ EN ──→ I67(INVX4) ──→ net5
              ↑                         │
              │                         ▼
          SET<12>──I32(INVX2)→net9   net5 ──→ I72(not_gate, tdel/2) ──→ net1
                                              │
                                              ▼
                                          I68(NAND) ──→ net10
                                              │
                                  ┌───────────┘
                                  ▼
              ┌── I70(NAND) ←── A ←── I7(not_gate, tdel) ←── PCLK
              │       │
              ▼       ▼
          I69(NAND) ──→ net6 ──→ M12+M13(inv) ──→ PCLK
                                      │
                                      ├──→ I50/I51/I52/I35 → CCLK
                                      └──→ I79/I82 → CLK
```

### 2.2 工作模式

**转换中 (SET<12>=0):**
- EN = NOT(CLK00) → net5 = CLK00
- 每个 CLK00 下降沿，net1 (tdel/2 延迟取反) 与 net5 在 **I68 NAND** 中产生一个负脉冲 net10
- 该脉冲触发 I70/I69/M12-M13 构成的 **异步锁存反馈环**
- PCLK 产生一个与 tdel 等宽的正脉冲
- PCLK 经四级缓冲 (I50→I51→I52→I35) → **CCLK**
- PCLK 经两级缓冲 (I79→I82) → **CLK** (送比较器)

**转换完成 (SET<12>=1):**
- EN = 1 (固定) → net5 = 0
- I68 输出 net10 = 1 (锁死)
- 反馈环停振，CCLK 保持为 0

### 2.3 关键时序参数

| 参数 | 值 | 作用 |
|------|-----|------|
| `tdel` | **4.5 ns** | I7 not_gate 延迟；决定 CCLK 脉冲宽度 |
| `tdel/2` | **2.25 ns** | I72 not_gate 延迟；边缘检测窗口 |
| `CLK00` | **10 MHz** (100 ns) | 主时钟；每周期生产一个 CCLK 脉冲 |

CCLK 脉冲宽度 ≈ `tdel` + NAND环反馈延迟 + 缓冲链延迟 ≈ **~5-6 ns**。

### 2.4 CCLK 缓冲链驱动强度

```
PCLK ──→ I50(INVX4, Wp=4u) ──→ I51(INVX5, Wp=8u) ──→ I52(INVX6, Wp=16u) ──→ I35(INVX6, Wp=16u) ──→ CCLK
```

扇出：13 个 DFF + 顶层布线，总负载约 **50-80 fF**。四级锥形缓冲（4u→8u→16u→16u）提供充足的驱动，每级反相器尺寸逐级翻倍，上升/下降时间控制在 **~100 ps**。

---

## 三、SAR_LOGIC 模块 — 令牌传递状态机

### 3.1 总体架构

```
I48(INVX3) ──→ I49(INVX4) ──→ I50(INVX5)──→ PRST_B
  │               │               │
PRST              │               │
                  ▼               ▼
             用于 I51 NAND   用于 I46.D (令牌初始值)
             (强制归零)        (复位撤除后注入令牌)
```

### 3.2 复位链 (PRST → PRST_B)

```
PRST ──→ I48(INVX3, Wp=2u) ──→ net1 ──→ I49(INVX4, Wp=4u) ──→ net2 ──→ I50(INVX5, Wp=8u) ──→ PRST_B
```

三级递进缓冲，提供复位信号的干净整形和足够的驱动。`PRST_B` 极性为 PRST 的延迟取反。

### 3.3 核心：12+1 位片 (Bit-Slice) 链

整个 SAR 由 **13 个定制 DFF** 构成位移位寄存器：1 个起始位 I46 + 12 个数据位 I47<11:0>。

#### I46（最高位 MSB，起始触发器）

```
I46 (CCLK ST<0> COMN PRST_B DGND DVDD BITN<12> BITP<12> Q<12>) DFF
  └──── Pin: CCLK  CLK1  COMN   D      DGND  DVDD    N        P        Q
```

- **D = PRST_B**: 复位撤除后自动注入令牌（= 1）
- **CLK1 = ST<0>**: 始终活动（ST<0> 由 NOR1 对 PRST 和内部状态生成）
- **Q = Q<12>**: 令牌输出到下一级 I47<11>.D

#### I47<11:0>（常规位片，12个）

```
I47<11>: (CCLK ST<1> COMN Q<12> DGND DVDD BITN<11> BITP<11> QQ<11>) DFF
I47<10>: (CCLK ST<2> COMN Q<11> DGND DVDD BITN<10> BITP<10> QQ<10>) DFF
...
I47<0>:  (CCLK ST<12> COMN Q<1>  DGND DVDD BITN<0>  BITP<0>  QQ<0>)  DFF
```

- **D = Q<上一级>**: 令牌逐级传递
- **CLK1 = ST<i+1>**: 由 ST 信号控制激活
- **QQ = 原始输出**: 直接进入 I51 NAND 路径
- **N/P = BITN/BITP**: 互补输出到 DAC

#### 令牌传递路径

```
PRST_B
   │
I46: D=PRST_B, Q=Q<12>
   │
   ▼
I47<11>: D=Q<12>,  Q->QQ<11> ──→ I51<11>(NAND) + I52<11>(INVX3) ──→ Q<11>
   │     └── BITN<11>/BITP<11> → DAC                                            │
   ▼                                                                              │
I47<10>: D=Q<11>,  Q->QQ<10> ──→ I51<10>(NAND) + I52<10>(INVX3) ──→ Q<10>      │
   │     └── BITN<10>/BITP<10> → DAC                                            │
   ▼                                                                              │
......                                                                            
   │                                                                              │
   ▼                                                                              │
I47<0>:  D=Q<1>,   Q->QQ<0>  ──→ (无 I51/I52, LSB 无后级)
   │     └── BITN<0>/BITP<0> → DAC
   │
   ▼
令牌到达 LSB 后，QQ<0> 悬空 → 链结束
```

### 3.4 I51/I52 — PRST 使能的令牌闸门

```
I51<11>: (PRST_B, QQ<11>) → NOT(PRST_B & QQ<11>) → net3<0>
I52<11>: (net3<0>) → Q<11>
```

**功能**: 当 PRST=1 (复位) 时 PRST_B=0，NAND 输出固定为 1，INVX3 输出 Q=0，强制清零所有中间令牌。复位释放后 PRST_B=1，NAND+INVX3 单纯起缓冲作用：Q = QQ。

```
PRST_B | QQ  →  I51 NAND → I52 INVX3 → Q
  0    |  X  →     1     →     0     → 0    ← 复位
  1    |  0  →     1     →     0     → 0
  1    |  1  →     0     →     1     → 1    ← 正常工作(缓冲)
```

### 3.5 SET 信号生成

SET<i> 在每个位周期结束时，用于将 DAC 强制复位到采样共模。

```
ST<i> ──→┐
          │
         I53(NOR1) ──→ net7<i> ──→ I54(INVX4) ──→ net6<i> ──→ I55(INVX5) ──→ SET<i>
          │
PRST ─────┘
```

**逻辑**: SET<i> = NOT(ST<i> OR PRST) = ST<i>' AND PRST'

SET<i> 仅在 PRST=0（非复位）且 ST<i>=0（该位未激活）时才为 1。这意味着：
- 采样期间 (PRST=1)：SET<i>=0，DAC 采样开关自由
- 转换期间 (PRST=0)：只有非活动位的 SET=1，强制它们停在 VCM

### 3.6 ST 信号生成 (状态指示)

```
ST<12:0> = NOR1(ST<i>, PRST)
```

实际电路：I53<12:0> 将 DFF 的 QQ 输出（或 I46 的 Q）与 PRST 进行 NOR。但等一下——查看实例化：
```
I53<0>: (ST<0> DGND DVDD PRST net7<0>) NOR1
```

NOR1 pins: (A AGND AVDD B VOUT)
所以 A=ST<0>, B=PRST → VOUT=net7<0>
net7<0> = NOT(ST<0> OR PRST)

但 ST<0> 是 NOR1 的输入，而这个 NOR1 的输出 net7<0> 又通过 I54→I55 产生 SET<0>...

这里 ST<0> 实际上是一个**端口**，它是 I46 DFF 的内部状态输出吗？

不，再看 DFF：
```
subckt DFF CCLK CLK1 COMN D DGND DVDD N P Q
```

DFF 没有 ST 输出端口。那么 ST 是从哪来的？

看 I46 的连接：
```
I46 (CCLK ST<0> COMN PRST_B DGND DVDD BITN<12> BITP<12> Q<12>) DFF
```

DFF pins: (CCLK CLK1 COMN D DGND DVDD N P Q)
所以 CLK1 = ST<0>。ST<0> 是 DFF 的 CLK1 输入！

再看 DFF 内部的 CLK1 连接。ST<0> 连接到 CLK1，CLK1 控制 DFF 的预充电/放电。

那么 ST<0> 是从外部什么地方产生的？ST<0> 是 SAR_LOGIC 的一个**输出端口**吗？

检查 SAR_LOGIC 的端口列表：
```
subckt SAR_LOGIC ... SET<0> SET<1> ... SET<12>
```

SET 是端口，但没有 ST 端口。所以 ST 是内部信号。

ST<0> 连接到 I53<0> 的 A 输入和 I46 的 CLK1 输入。I53<0> 的 VOUT 是 net7<0>。但 net7<0> 不是 ST<0>。

那 ST<0> 到底是从哪里驱动的？

啊，我明白了。ST<0> 是一个内部线网，它被多个模块读取（作为 NOR1 的输入、DFF 的 CLK1 输入），但它的驱动源是... 看 DFF 的输出 Q。

等等，不对。I46 的 Q 是 Q<12>，不是 ST<0>。

再查 DFF 内部：
```
M3 (net2 CLK1 DVDD DVDD) pch  -- precharge net2 when CLK1=0
M4 (Q CCLK net2 DVDD) pch     -- Q = net2 when CCLK=0
M5 (Q CLK1 DGND DGND) nch     -- Q = 0 when CLK1=1
...
```

CLK1 在 DFF 内部被大量使用，但 CLK1 本身没有被驱动——它是一个输入端口。

所以 ST<0> 是从外面驱动的。但在 SAR_LOGIC 中没有任何器件驱动 ST<0>。

那么 ST<0> 可能是一个**输出**端口？但 SAR_LOGIC 的端口列表里没有 ST。

除非 ST<0> 是 DFF 内部的一个节点通过某种方式连接到外部... 不对，CLK1 在 DFF 中是输入端口。

所以 ST<0> 一定是在 SAR_LOGIC 外部有驱动源？但 SAR_LOGIC 被实例化在顶层：
```
I15 (...) SAR_LOGIC
```

在顶层，SAR_LOGIC 的端口连接：
```
I15 (... SET<0> SET<1> ... SET<12>) SAR_LOGIC
```

所以 ST<0> 是 SAR_LOGIC 内部未驱动线网？这不可能通过仿真。

仔细看一下——可能 ST 信号实际上是来自 DFF 内部的某些节点，我漏掉了。

再看 DFF 内部：M0 (CLK1 D DVDD DVDD) pch。gate = D。

当 D=0: PMOS ON → CLK1 = DVDD = 1
当 D=1: PMOS OFF

M1 (CLK1 CCLK net1 DGND) nch: gate=CCLK
M2 (net1 D DGND DGND) nch: gate=D

当 D=1, CCLK=1: M1 ON, M2 ON → CLK1 = net1 = 0

所以 CLK1 是由 DFF 内部电路驱动的 (pre-charge + conditional discharge)。但 CLK1 作为一个 pin，它既是输入又是输出？不，在 Spectre 中，管脚默认是双向的。

实际上，在 SPICE/spectre 中，端口连接只是一个连接点。如果有器件在内部驱动它，它就是输出。如果有器件在外部驱动它，它就是输入。如果同时在内外驱动，就会冲突。

但在 SAR_LOGIC 中，ST<0> 同时被：
1. I46 DFF 内部驱动（CLK1 端口由 M0/M1 内部驱动）
2. I53<0> NOR1 读取（A=ST<0>）
3. I46 本身使用（CLK1=ST<0>）

所以 ST<0> 实际上就是 DFF 的 CLK1 端口的内部节点！DFF 的 CLK1 端口被 DFF 内部的 M0/M1 驱动，然后通过 ST<0> 线网被 I53<0> 读取。

这就对了！ST<0> 本质上是 I46 DFF 的 **内部预充电/放电状态的镜像**。当 DFF 内部 CLK1=0（预充电完成，就绪），ST<0>=0 告诉 NOR1 "此位可活动"。当 CLK1=1（放电完成，token 已传递），ST<0>=1 告诉 NOR1 "此位已结束"。

ST 是一个**双向状态信号**——既被 DFF 驱动来指示状态，又被外部用来控制 NOR1 的置位/使能逻辑。

这就是**位切片架构的精髓**：每个 DFF 把自己的内部节点暴露出来作为状态指示，外部逻辑利用它来生成 SET 信号。每个位片的边界不仅传输数据，还传输状态——这是全定制设计的关键特征，综合工具做不到。

### 3.7 DFF (位片) 晶体管级分析

```
subckt DFF CCLK CLK1 COMN D DGND DVDD N P Q

输入:
  CCLK: 主时钟 (由SYNC产生)
  CLK1: 状态信号 (内部节点外露，双向)
  COMN: 比较器输出 (0=VIP>VIN, 1=VIP<VIN)
  D:    上一级的令牌输入

输出:
  N, P: BITN/BITP (互补DAC控制，P = NOT(N))
  Q:    令牌输出 (到下一级 D 或到 I51)
```

**工作相位：**

**相位 1: 预充电 (CLK1→0)**

令牌传入时，D=0（无令牌）或 D=1（有令牌）：
```
M0: D=0 → PMOS ON → CLK1 充电到 DVDD → CLK1=1  → 禁止进入预充电
M0: D=1 → PMOS OFF → 待定
```

等等，让我重新分析。M0 (CLK1 D DVDD DVDD) pch — 当 gate (D) = 0 时导通，drain (CLK1) 被拉到 source (DVDD)。

当上一级的 Q 输出 = 1（令牌存在）→ D=1 → M0 OFF，CLK1 不被预充电，等待 CCLK 来放电。
当上一级的 Q 输出 = 0（无令牌）→ D=0 → M0 ON，CLK1 = DVDD = 1。

CLK1=1 意味着：
- M9 (P CLK1 DGND): ON → P = 0（BITP 强制为 0）
- M5 (Q CLK1 DGND): ON → Q = 0（令牌输出为 0）
- M3 (net2 CLK1 DVDD): OFF
- M6 (net4 CLK1 DVDD): OFF

CLK1=1 时，整个 DFF 处于非活动保持状态。

当 CLK1=0（活动态）：
- M3 ON → net2 预充电
- M6 ON → net4 预充电  
- M9 OFF → P 由其他逻辑驱动
- M5 OFF → Q 由其他逻辑驱动

**相位 2: 比较判决 (CCLK 上升沿)**

当 CCLK=1, D=1（且上一级已把 CLK1 放电到 0）：
```
M1 (gate=CCLK=1): ON → CLK1 = net1
M2 (gate=D=1): ON → net1 = 0
→ CLK1 = 0 (保持活动)
```

CLK1 保持 0，DFF 继续活动。

**相位 3: COMN 采样**

COMN 决定 BITP 的值：
```
M6 (gate=CLK1=0): ON → net4 = DVDD
M7 (gate=COMN): 当 COMN=0 → ON → net3 = net4 = DVDD 
M8 (gate=Q): 假设 Q=1 (有令牌) → ON → P = net3 = DVDD = 1
```

当 COMN=1 (VIP<VIN): M7 OFF, net3 不受 net4 影响。P 由其他路径保持。

**相位 4: 令牌传递 (CCLK 下降沿)**

当 CCLK=0:
```
M4 (gate=CCLK=0): ON → Q = net2
```

之前 M3 (gate=CLK1=0): ON → net2 = DVDD
所以 Q = DVDD = 1（令牌传出）

同时 M1 (gate=CCLK=0): OFF → CLK1 浮动 → M0 (D=? ) 

当 DFF 传出令牌后，M0 的 gate 变为 D=1（因为 Q 是 1，但 D 连接的是上一级的 Q=1），所以 M0 OFF，CLK1 浮动。

但实际上 CLK1 的状态由 M1-M2 路径决定。当 CCLK=0，M1 OFF，CLK1 保持上次的值（0 或 1）。

**状态总结:**

| 阶段 | D | CLK1 | CCLK | Q | P/N | 描述 |
|------|---|------|------|---|-----|------|
| 等待 | 0 | 1 | X | 0 | N=1,P=0 | 无令牌，非活动 |
| 令牌到达 | 1 | 0 | 0 | X | N=?,P=? | 预充电进行中 |
| 比较 | 1 | 0 | ↑1 | 1 | P 采样 COMN | 锁存判决 |
| 传递 | 1 | 0 | ↓0 | 1→出 | 保持 | 令牌传到下一级 |
| CCLK 再次↑ | 0 | →1 | ↑1 | X | P=0,N=1 | 下一周期开始 |

这正是环形计数器的逐位传递机制——每个 CCLK 周期处理一位，令牌沿链传递。

---

## 四、时序分析与 CAAZ 关联

### 4.1 完整转换时序

```
TRST ──────┐___________________________
           │
PRST ──┐___┘___________________________
       │
CLK00 ─┤‾‾‾│___│‾‾‾│___│‾‾‾│___│‾‾‾│___
       │
CCLK  _│   ‾‾│___│‾‾│___│‾‾│___│‾‾│___│‾
       │       ↑   ↑   ↑   ↑          ↑
       │       1   2   3   4  ...     13
       │
       │  ┌──────────────────────────────┐
ST<i> │  │ ST<0>=1                      │
       │  │     ST<1>=1                  │
       │  │          ST<2>=1             │
       │  └──────────────────────────────┘
       │
BITP  ─┤    MSB  MSB-1  MSB-2 ... LSB
```

### 4.2 时间预算

| 参数 | 值 | 来源 |
|------|-----|------|
| CLK00 周期 | 100 ns | 固定 (10 MHz) |
| PRST 复位宽度 | 30 ns | 参数 `width=30n` |
| td (采样时间) | **26.5 ns / 24.05 ns** | 参数 `td` |
| tdel (CCLK 脉冲) | **4.5 ns** | 参数 `tdel` |
| 每周期 CCLK 脉冲数 | **13** | 12-bit + 1 EOC |
| 总转换时间 | **13 × 100 ns = 1.3 µs** | 占空比 13% |
| 采样速率等效 SST | **~7.7 MS/s** | 13 周期 × 100ns |

### 4.3 CAAZ 时序耦合

CCLK 的脉冲宽度（`tdel=4.5ns`）直接控制 CAAZ 可用建立时间：

```
CLK 上升沿 ──→ 比较器触发
              │
              ├── CAAZ 预放大器建立 (td = 26.5ns → 仿真 SNR 64.4dB)
              │   CAAZ 预放大器建立 (td = 24.05ns → 仿真 SNR 54.4dB)
              │
              ├── 延迟线 ← 由 RST 的宽度参数 td 控制
              │
              └── COMN 有效 → CCLK 上升沿 → 锁存判决
```

CCLK 的 `tdel` + NAND 环延迟决定了比较器触发点到 CCLK 锁存点的时间窗口。在这个窗口内：
- CAAZ 预放大器建立
- 比较器做出判决
- 结果稳定到可锁存

你们仿真中 td=24.05ns 时 ENOB 暴跌，正是因为 **这个时间窗口缩短了 2.45ns**，CAAZ 的建立时间不够，采样噪声残余从 9.2% 升到 100%。

---

## 五、风险与优化建议

### 5.1 已识别风险

| 风险 | 级别 | 位置 | 说明 |
|------|------|------|------|
| CLK1 浮动依赖 | 🔴 | DFF 内部 | M0/M1 动态节点在 CCLK=0 时无静态保持，漏电会导致 CLK1 漂移 |
| ST<0> 双向节点 | 🟡 | 起振位 | ST<0> 同时被 I46 内部和 I53 读取，需确保无驱动冲突 |
| tdel 全局单载 | 🟡 | SYNC.I7 | 只有一个 tdel 控制所有 13 个周期，无法逐位修调 |
| CCLK 扇出 13 | 🟡 | 版图 | 13 个 DFF 共享 CCLK，布局时需 H-tree |
| SET<12> 竞争 | 🟡 | SYNC→复位 | SET<12> 上升沿与最后一个 CCLK 的时序关系 |

### 5.2 优化建议

1. **增加 DFF 内部静态保持**：在每个动态节点（CLK1, net1, net2, net4）上加弱反馈反相器（keeper），防止漏电导致的状态漂移——特别是低速或高温下。

2. **CCLK 版图布线**：使用 H-tree 结构，确保 13 个 DFF 的 CCLK skew < 20 ps。跑 post-layout 仿真验证。

3. **留一个 tdel trim option**：在 I7 旁边预留一个修调电容阵列（几段 50fF MOM），允许流片后微调 CCLK 脉宽——如果 CAAZ 建立不够好，可以增加 tdel 来补偿。

4. **ST<0> 的双向驱动**：确认没有驱动冲突。CLK1 在 DFF 内部被 M0/M1 驱动，同时 ST<0> 被 I53 读取。如果 EDA 工具报 warning，加一个显式 tie。

5. **SET<12> → CCLK 关断时序**：确保 SET<12> 在第 13 个 CCLK 脉冲的 `tdel` 窗口内到达，既不提前（吞掉第 12 个 CCLK），也不延后（产生多余的第 14 个 CCLK）。仿真中检查 timing guardband。

### 5.3 对比原始分析的修正

| 原分析 | 实际电路 | 差异 |
|--------|---------|------|
| CLK00=50MHz？ | CLK00=**10MHz**, 13周期×100ns | 实际转换速度更慢 |
| BITP/BITN=互补 | **两者都是从 DFF 的 N/P 输出**，P=NOT(N) 在 DFF 内部完成 | 确实是互补对 |
| CCLK 来自延迟线 | CCLK 来自 **SYNC 基于 CLK00 的单次发生器**，tdel 控制脉宽 | 归因不同，原理一致 |
| 13 个 CCLK = 12 位 + 1 EOC | ✅ **正确** | — |
| ST 是状态寄存器输出 | ST 实际上是 DFF 的 **CLK1 内部节点外露** | 更精确：双向节点 |
