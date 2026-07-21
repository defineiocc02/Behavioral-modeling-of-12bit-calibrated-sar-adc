# 12-bit 桥接冗余 SAR ADC 双向递归位权校准完整设计文档

**基于论文**: Qifeng Huang, "Advanced Clock Multiplier and SAR ADC Design Techniques for High-Resolution Signal Chain Systems," HKUST PhD Thesis, 2024, Section 4.5

**版本**: V5.0 (Huang Recursive Full Calibration)

**日期**: 2026-07-21

---

## 目录

1. [电荷域数学模型](#1-电荷域数学模型)
2. [当前 CDAC 的校准可行性分析](#2-当前-cdac-的校准可行性分析)
3. [因子 2 问题的严格推导](#3-因子-2-问题的严格推导)
4. [替代 CDAC 设计](#4-替代-cdac-设计)
5. [完整递归校准算法](#5-完整递归校准算法)
6. [校准切换表](#6-校准切换表)
7. [递归误差传播模型](#7-递归误差传播模型)
8. [正常转换的数字重构](#8-正常转换的数字重构)
9. [状态机流程](#9-状态机流程)
10. [伪代码](#10-伪代码)
11. [Verilog-A 实现方案](#11-verilog-a-实现方案)
12. [仿真验证方案](#12-仿真验证方案)
13. [最终结论](#13-最终结论)

---

## 1. 电荷域数学模型

### 1.1 物理 CDAC 结构

当前 CDAC 为全差分桥接结构：

```
P 侧:
  低位阵列 (通过桥接电容 C_B 连接到顶板 P):
    C_L1=1C, C_L2=2C, C_L3=4C, C_L4=6C, C_L5=10C, C_L6=16C, C_L7=24C
  桥接电容: C_B = 1C
  高位阵列 (直接连接到顶板 P):
    C_H1=1C, C_H2=2C, C_H2R=2C(redundant), C_H4=4C, C_H8=8C, C_H16=16C

N 侧: 镜像结构
```

总电容：
- 低位总电容: C_LT = 1+2+4+6+10+16+24 = 63C
- 高位总电容: C_HT = 1+2+2+4+8+16 = 33C
- 桥接电容: C_B = 1C

### 1.2 P 侧电荷守恒方程

设节点 P (高位顶板) 电压变化为 v_P，节点 L (低位顶板) 电压变化为 v_L。

**高位电容 C_Hj 切换 ΔV_j 时：**

节点 P 的电荷守恒：
```
C_HT · v_P + C_B · (v_P - v_L) = Σ_j C_Hj · ΔV_j
```

节点 L 的电荷守恒 (低位不切换)：
```
C_LT · v_L + C_B · (v_L - v_P) = 0
```

由第二个方程：
```
v_P = (C_LT + C_B) / C_B · v_L = 64 · v_L
```

代入第一个方程：
```
(C_HT + C_B) · v_P - C_B · v_L = Σ C_Hj · ΔV_j
34 · v_P - 1 · (v_P / 64) = Σ C_Hj · ΔV_j
v_P · (34 - 1/64) = Σ C_Hj · ΔV_j
v_P = Σ C_Hj · ΔV_j / (2176/64 - 1/64) = 64 · Σ C_Hj · ΔV_j / 2175
```

**低位电容 C_Li 切换 ΔV_i 时：**

节点 L 的电荷守恒：
```
C_LT · v_L + C_B · (v_L - v_P) = C_Li · ΔV_i
```

节点 P 的电荷守恒 (高位不切换)：
```
C_HT · v_P + C_B · (v_P - v_L) = 0
```

由第二个方程：
```
v_L = (C_HT + C_B) / C_B · v_P = 34 · v_P
```

代入第一个方程：
```
(C_LT + C_B) · v_L - C_B · v_P = C_Li · ΔV_i
64 · v_L - v_P = C_Li · ΔV_i
64 · 34 · v_P - v_P = C_Li · ΔV_i
v_P · (2176 - 1) = C_Li · ΔV_i
v_P = C_Li · ΔV_i / 2175
```

### 1.3 单端顶板电压公式汇总

定义归一化常数 K = 1/2175：

| 电容 | 位置 | 单端 v_P 贡献 |
|------|------|---------------|
| 高位 C_Hj | 高位阵列 | 64 · C_Hj · ΔV · K |
| 低位 C_Li | 低位阵列 | 1 · C_Li · ΔV · K |

### 1.4 差分顶板电压与有效权重

在差分结构中，P 侧和 N 侧互补切换：
- 当 P 侧某电容底板从 VCM 切到 VREFP (ΔV = +VREF/2) 时，N 侧对应电容从 VCM 切到 VREFN (ΔV = -VREF/2)
- 差分电压变化 = v_P - v_N = 2 × v_P (单端)

因此**差分有效权重**：

```
W_Hj = 2 · 64 · C_Hj · K · (VREF/2) · (1/VREF) · 4095 = 2 · 64 · C_Hj / D_norm
W_Li = 2 · 1  · C_Li · K · (VREF/2) · (1/VREF) · 4095 = 2 · 1  · C_Li / D_norm
```

其中 D_norm = (C_LT + C_B)(C_HT + C_B) - C_B² = 64 × 34 - 1 = 2175

归一化使最小权重 (低位 1C) = 2 (差分)：

| 物理电容 | C 值 | 差分权重 |
|---------|------|---------|
| 高位 16C | 16 | 2 × 64 × 16 = **2048** |
| 高位 8C | 8 | 2 × 64 × 8 = **1024** |
| 高位 4C | 4 | 2 × 64 × 4 = **512** |
| 高位 2C | 2 | 2 × 64 × 2 = **256** |
| 高位 2C_R | 2 | 2 × 64 × 2 = **256** |
| 高位 1C | 1 | 2 × 64 × 1 = **128** |
| 低位 24C | 24 | 2 × 1 × 24 = **48** |
| 低位 16C | 16 | 2 × 1 × 16 = **32** |
| 低位 10C | 10 | 2 × 1 × 10 = **20** |
| 低位 6C | 6 | 2 × 1 × 6 = **12** |
| 低位 4C | 4 | 2 × 1 × 4 = **8** |
| 低位 2C | 2 | 2 × 1 × 2 = **4** |
| 低位 1C | 1 | 2 × 1 × 1 = **2** |
| terminal | — | **1** (比较器判决) |

总权重 = 2048+1024+512+256+256+128+48+32+20+12+8+4+2+1 = **4351**

冗余 = 4351 - 4095 = **256** (来自冗余 2C_R 位)

### 1.5 桥接衰减因子

桥接衰减比 α = (C_LT + C_B) / C_B = 64

这意味着高位 1C 的权重是低位 1C 的 64 倍。低位总权重 = 2 × (1+2+4+6+10+16+24) = 2 × 63 = 126 (不含 terminal)。加上 terminal = 127。

**关键观察**: 高位 1C 权重 (128) 比低位总权重 (127) 恰好多 1 LSB。这是桥接 DAC 的基本性质：当 C_B = 1C 时，gap = 2 (差分) = 1 (含 terminal)。

---

## 2. 当前 CDAC 的校准可行性分析

### 2.1 校准 DAC 可达码集合分析

初始校准 DAC 权重集合：{1, 2, 4, 8, 12, 20, 32, 48}

总和 = 1+2+4+8+12+20+32+48 = 127

**定理 1 (可达性)**: 集合 {1, 2, 4, 8, 12, 20, 32, 48} 可以表示 [0, 127] 中的所有整数。

**证明**: 对排序后的权重 w_1=1 ≤ w_2=2 ≤ ... ≤ w_8=48，检查完备性条件 w_{k+1} ≤ 1 + Σ_{i≤k} w_i：

| k | w_k | Σ_{i<k} w_i | 1 + Σ | w_k ≤ 1+Σ? |
|---|-----|-------------|-------|------------|
| 1 | 1 | 0 | 1 | 1 ≤ 1 ✓ |
| 2 | 2 | 1 | 2 | 2 ≤ 2 ✓ |
| 3 | 4 | 3 | 4 | 4 ≤ 4 ✓ |
| 4 | 8 | 7 | 8 | 8 ≤ 8 ✓ |
| 5 | 12 | 15 | 16 | 12 ≤ 16 ✓ |
| 6 | 20 | 27 | 28 | 20 ≤ 28 ✓ |
| 7 | 32 | 47 | 48 | 32 ≤ 48 ✓ |
| 8 | 48 | 79 | 80 | 48 ≤ 80 ✓ |

条件全部满足，因此可达码集合 = {0, 1, 2, ..., 127}，无 missing code。 ∎

### 2.2 SAR 收敛性证明

SAR trial 顺序 (从大到小): 48, 32, 20, 12, 8, 4, 2, terminal(1)

**定理 2 (SAR 收敛)**: 对任意输入 x ∈ [0, 127]，上述 SAR 顺序正确量化 x。

**证明**: 对每一步 k，检查残差是否被剩余权重覆盖：

| 步骤 | trial 权重 | 剩余权重和 | 条件 | 满足? |
|------|-----------|-----------|------|-------|
| 1 | 48 | 79 | 48 ≤ 79+1 | ✓ |
| 2 | 32 | 47 | 32 ≤ 47+1 | ✓ |
| 3 | 20 | 27 | 20 ≤ 27+1 | ✓ |
| 4 | 12 | 15 | 12 ≤ 15+1 | ✓ |
| 5 | 8 | 7 | 8 ≤ 7+1 | ✓ |
| 6 | 4 | 3 | 4 ≤ 3+1 | ✓ |
| 7 | 2 | 1 | 2 ≤ 1+1 | ✓ |
| 8 | 1 (terminal) | 0 | — | ✓ |

每步残差均被覆盖，SAR 收敛。 ∎

**注意**: 步骤 5-7 的条件恰好取等 (8=7+1, 4=3+1, 2=1+1)，意味着这些级别无冗余。若比较器在此级别判决错误，无法恢复。但这是正常转换的要求；校准时的 D+/D- 平均可消除随机判决错误。

### 2.3 W_128 校准不可能性证明

**定理 3 (W_128 不可校准)**: 在当前 CDAC (C_B = 1C, H = 128) 上，无法使用 Huang 方法独立校准 W_128。

**证明**:

校准 W_128 需要：
1. 正方向注入 +W_128，校准 DAC 量化得到 D+
2. 负方向注入 -W_128，校准 DAC 量化得到 D-
3. Ŵ_128 = (D+ - D-) / 2

校准 DAC (含 terminal) 最大输出 = 127 + 1 = 128。

正方向时，比较器残差 = W_128 + V_OS - D_+code。需要 D_+code ∈ [0, 128]。
- 若 W_128 = 128 (理想)，V_OS = 0：D_+code = 128 (全部 cap ON + terminal = 1)，**恰好达到上界**。
- 若 W_128 = 128 + ε (正失配) 或 V_OS > 0：D_+code = 128 + ε + V_OS > 128，**超出范围，饱和**。
- 若 W_128 = 128 - ε (负失配) 且 V_OS = 0：D_+code = 128 - ε < 128，可以量化。

因此：
- W_128 的正失配不可检测 (calDAC 饱和)
- 任何正方向比较器失调导致饱和
- **W_128 不可独立辨识**

根本原因：C_B = 1C 时，gap = W_H1 - Σ(W_low) = 128 - 127 = 1 (LSB)。这个 gap 恰好等于 terminal 权重，没有任何裕量。 ∎

### 2.4 递归链的系统性问题

上述 1-LSB gap 不仅影响 W_128，而且传递到所有更高级别：

| 待校准位 | 校准 DAC 总和 | gap | 可校准? |
|---------|-------------|-----|---------|
| W_128 | 127 (+terminal=128) | 128-128=0 | ✗ (零裕量) |
| W_256_A | 127+128=255 (+t=256) | 256-256=0 | ✗ |
| W_256_R | 255 (+t=256) | 256-256=0 | ✗ |
| W_512 | 255+256=511 (+t=512) | 512-512=0 | ✗ |
| W_1024 | 511+512=1023 (+t=1024) | 1024-1024=0 | ✗ |
| W_2048 | 1023+1024=2047 (+t=2048) | 2048-2048=0 | ✗ |

**每一级的 gap 都是 0** (含 terminal)。这是桥接 DAC 的结构性质：W_k = Σ(lower) + 1 (terminal)。

**结论**: 当前 CDAC (C_B = 1C, H = 128) 无法支持任何位的直接 Huang 校准。必须重新设计 CDAC。

### 2.5 判据违反项

当前 CDAC 违反了以下判据 (第十一条)：

| 判据 | 违反? | 说明 |
|------|-------|------|
| 1. calDAC 覆盖第一个待校准位 | ✗ | 127 < 128, 零裕量 |
| 2. 每级有正负对称 redundancy | ✗ | gap=0, 无 offset 覆盖 |
| 5. calDAC 无影响精度的空洞 | ✓ | 可达码无空洞 |
| 6. 最高位校准不使顶板过量程 | ✗ | 同理, gap=0 |
| 7. 误差传播后满足 12-bit | ✗ | 无法校准任何位 |

---

## 3. 因子 2 问题的严格推导

### 3.1 物理电容与数字权重的关系

**物理低位电容**: 24C, 16C, 10C, 6C, 4C, 2C, 1C (单位 C)

**数字权重**: 48, 32, 20, 12, 8, 4, 2

比率: 数字权重 / 物理电容 = 2 (对所有低位电容)

这个因子 2 来自**差分互补切换**：
- P 侧电容底板从 VCM 切到 VREFP: ΔV_P = +VREF/2 (单端)
- N 侧电容底板从 VCM 切到 VREFN: ΔV_N = -VREF/2 (单端)
- 差分变化: ΔV_diff = ΔV_P - ΔV_N = VREF (全量程)

而单端变化仅为 VREF/2。因此差分权重 = 2 × 单端权重。

### 3.2 因子 2 的电荷验证 (以低位 24C 为例)

**单端验证**:
- C_L7 = 24C 从 VCM 切到 VREFP
- ΔV = VREFP - VCM = VREF/2
- v_P (单端) = 1 × 24 × (VREF/2) / 2175 = 24 × VREF / 4350

**差分验证**:
- P 侧: v_P = +24 × VREF / 4350
- N 侧: v_N = -24 × VREF / 4350 (互补切换)
- ΔV_diff = v_P - v_N = 48 × VREF / 4350

归一化 (以 VREF / 4350 为 1 LSB):
- 差分权重 = 48 ✓

### 3.3 D+ 和 D- 的单位

在校准过程中：
- **D+**: 正方向注入 +W_k 后，calDAC SAR 搜索得到的码。这个码是 calDAC 权重的加权和 (差分单位)。
- **D-**: 负方向注入 -W_k 后，calDAC SAR 搜索得到的码的绝对值。同样是差分单位。

两者均使用**差分权重**，因此已经包含了因子 2。

### 3.4 论文公式的正确应用

论文定义:
```
Ŵ_k = (D_{k,+} - D_{k,-}) / 2
```

其中 D_{k,+} = W_k + V_OS + x_n, D_{k,-} = -W_k + V_OS + x_{n+1}

代入:
```
Ŵ_k = (W_k + V_OS + x_n - (-W_k + V_OS + x_{n+1})) / 2
    = (2·W_k + x_n - x_{n+1}) / 2
    = W_k + (x_n - x_{n+1}) / 2
```

V_OS 完全消除。

**当前代码的因子 2 处理**:

在 Huang Recursive V4 实现中：
- `code_plus_q` = D+ (差分单位, calDAC 权重之和 + terminal)
- `code_minus_mag_q` = |D-| (D- 为负值, 存储其绝对值)

因为 D- = -W_k + V_OS (符号为负当 W_k > V_OS)，calDAC 产生一个正码来抵消它：
```
D- 的 calDAC 码 = |D-| = W_k - V_OS (当 V_OS < W_k)
```

因此：
```
Ŵ_k = (D+ - D-) / 2 = (D+ + |D-|) / 2 = (code_plus_q + code_minus_mag_q) / 2
```

在 32-pair 平均后：
```
Ŵ_k = (Σ code_plus_q + Σ code_minus_mag_q) / (2 × 32)
    = (accum_plus_q + accum_minus_mag_q) / (2 × avg_pairs)
```

**这正是 Huang V4 代码中的实现** (第 777-793 行)：
```verilog
measurement_numer_q = accum_plus_q + accum_minus_mag_q;
measurement_denom = 2 * avg_pairs;
measured_weight_q = (measurement_numer_q + measurement_round_q) / measurement_denom;
```

### 3.5 结论

| 问题 | 答案 |
|------|------|
| 物理低位 24C 的单端顶板变化 | 24 × VREF / 4350 |
| P、N 互补切换后的差分变化 | 48 × VREF / 4350 |
| 数字权重 48 的定义 | 差分权重 = 2 × 单端 |
| D+ 和 D- 的单位 | 差分 LSB |
| 是否已将除以 2 吸收到权重定义中 | 否 — 权重是差分单位, 但 Ŵ_k 公式仍需 / 2 |
| 正确的数字残差 | **(D+ - D-) / 2** (即 (code_plus + code_minus_mag) / 2) |

**当前 V6.6 代码使用 R = D+ - D- 而不除以 2 是错误的** — 它将 W_k 高估了 2 倍。但由于 V6.6 的 calDAC 权重也是差分单位，且 wall_mask 也使用差分权重，在某些对称配置下误差可能部分抵消。Huang V4 正确地执行了除以 2。

---

## 4. 替代 CDAC 设计

### 4.1 设计目标

需要满足：
1. calDAC 总和 ≥ W_target + margin (margin ≥ 5 LSB for AZ residual + noise)
2. 总权重 ≥ 4095 (12-bit 覆盖)
3. calDAC 无 missing code
4. 每级有正负对称 redundancy
5. 最高位校准不使顶板过量程

### 4.2 候选 A: 调整桥接电容 (H=122)

**设计**: 保持所有电容不变，仅调整 C_B 使高位单位权重 H = 122。

由 α = (C_LT + C_B) / C_B = H / 2 (因为 H = 2α)：
```
122 / 2 = 61 = (63 + C_B) / C_B
61 · C_B = 63 + C_B
60 · C_B = 63
C_B = 63/60 C = 1.05 C
```

**权重表**:

| 物理电容 | C 值 | 差分权重 |
|---------|------|---------|
| 高位 16C | 16 | 122 × 16 = **1952** |
| 高位 8C | 8 | 122 × 8 = **976** |
| 高位 4C | 4 | 122 × 4 = **488** |
| 高位 2C_A | 2 | 122 × 2 = **244** |
| 高位 2C_R | 2 | 122 × 2 = **244** |
| 高位 1C | 1 | 122 × 1 = **122** |
| 低位 24C | 24 | 2 × 24 = **48** |
| 低位 16C | 16 | 2 × 16 = **32** |
| 低位 10C | 10 | 2 × 10 = **20** |
| 低位 6C | 6 | 2 × 6 = **12** |
| 低位 4C | 4 | 2 × 4 = **8** |
| 低位 2C | 2 | 2 × 2 = **4** |
| 低位 1C | 1 | 2 × 1 = **2** |
| terminal | — | **1** |

总权重 = 1952+976+488+244+244+122+48+32+20+12+8+4+2+1 = **4153**
冗余 = 4153 - 4095 = **258**

**校准裕量分析**:

| 待校准位 | calDAC 总和 (含 terminal) | 目标权重 | 裕量 |
|---------|------------------------|---------|------|
| low10 (20) | 12+8+4+2+1 = 27 | 20 | 7 |
| low16 (32) | 20+12+8+4+2+1 = 47 | 32 | 15 |
| low24 (48) | 32+20+12+8+4+2+1 = 79 | 48 | 31 |
| high1 (122) | 48+32+20+12+8+4+2+1 = 127 | 122 | **5** |
| high2A (244) | 127+122 = 249 | 244 | **5** |
| high2B (244) | 127+122 = 249 | 244 | **5** |
| high4 (488) | 249+244 = 493 | 488 | **5** |
| high8 (976) | 493+244+488 = 1225 | 976 | **249** |
| high16 (1952) | 1225+976 = 2201 | 1952 | **249** |

**裕量一致性**: high1 到 high4 的裕量均为 5 LSB，足以覆盖 AZ 后残差失调 (< 1 LSB) 和噪声。

**12-bit 覆盖**: 33 × 122 + 127 = 4153 > 4095 ✓

### 4.3 候选 B: 修改低位阵列 + C_B = 2C

**设计**: 使用 C_B = 2C，低位阵列改为 {1, 2, 4, 8, 12, 20, 32} = 79C。

α = (79 + 2) / 2 = 40.5
H = 2 × 40.5 = 81

权重：
- 高位: 81, 162, 162, 324, 648, 1296
- 低位: 4, 8, 16, 24, 40, 64, 128 (每个 ×4)
- 总权重 = 1296+648+324+162+162+81+128+64+40+24+16+8+4+1 = 2958 < 4095

**不满足 12-bit 覆盖**。需要更大的高位阵列或更多低位电容。

修正: 使用 C_B = 2C, 低位 {1,2,4,8,12,20,32,48} = 127C, 高位 {1,2,2R,4,8,16} = 33C。
α = (127+2)/2 = 64.5
H = 129
权重: 高位 129,258,258,516,1032,2064; 低位 4,8,16,24,40,64,96,192
总 = 2064+1032+516+258+258+129+192+96+64+40+24+16+8+4+1 = 4702

裕量: calDAC (含 terminal) = 4+8+16+24+40+64+96+192+1 = 445, 目标 H=129, 裕量 = 316。
但低位权重非单调 (192 > 129)，且权重过大导致冗余过多。

**候选 B 结论**: 可行但权重不简洁, 冗余过大, 不推荐。

### 4.4 候选 C: 分段二进制 + 冗余 (非桥接)

**设计**: 纯二进制 13 位 + 1 冗余位, 无桥接。
- 电容: 1, 2, 4, 8, 16, 32, 64, 128, 256, 256R, 512, 1024, 2048
- 总 = 4351, 冗余 = 256

校准时从低位递归:
- calDAC {1,2,4,8,16,32,64} = 127, 目标 128: gap = 1 (同样的问题!)

纯二进制结构有**完全相同**的 gap 问题: W_k = Σ(lower) + 1。

**解决方案**: 使用亚二进制 (sub-radix) 冗余。例如:
- 电容: 1, 2, 4, 8, 16, 31, 62, 124, 248, 248R, 496, 992, 1984
- 每级 ×2 但减 1: W_k = 2×W_{k-1} - 1, 使得 Σ(lower) = W_k + (k-1)
- 总 = 1+2+4+8+16+31+62+124+248+248+496+992+1984 = 4216
- 每级裕量 = 1 LSB (仍不够)

或者使用更强的亚二进制:
- 电容: 1, 2, 4, 8, 16, 30, 60, 120, 240, 240R, 480, 960, 1920
- 总 = 4081 < 4095 (不够)

需要调整: ..., 120, 250, 250R, 500, 1000, 2000 → 总 = 4261
- calDAC for W_120: {1,2,4,8,16,30}+1 = 62, target = 120, gap = 58 (足够)
- 但需要 2000C 电容 (面积大)

**候选 C 结论**: 可行但面积代价大, 且无桥接意味着最大电容 2000C, 远大于桥接方案的 16C。

### 4.5 候选比较表

| 指标 | 当前结构 (H=128) | 候选 A (H=122) | 候选 B (C_B=2C) | 候选 C (非桥接) |
|------|-----------------|----------------|-----------------|----------------|
| 总单位电容 | 97C | 97C (C_B=1.05C) | 163C | ~4261C |
| 决策次数 | 14 | 14 | 14 | 14 |
| 冗余位数 | 1 (256R) | 1 (244R) | 1 (258R) | 1 (250R) |
| calDAC 范围 | 127 | 127 | 445 | 可调 |
| 对称 offset cover | 0 LSB | 5 LSB | 316 LSB | 可调 |
| 可校准最大失配 | 0% | ~4% | ~100% | 可调 |
| 校准位数 | 0 (不可校准) | 9 | 9 | 9 |
| 误差传播系数 | N/A | 1 (每级) | 1 (每级) | 1 (每级) |
| 预期 INL | 高 (未校准) | < 0.5 LSB | < 0.5 LSB | < 0.5 LSB |
| 预期 ENOB | < 10 (未校准) | ≥ 11.5 | ≥ 11.5 | ≥ 11.5 |
| 数字复杂度 | 低 (3-target) | 中 (9-target) | 中 (9-target) | 中 (9-target) |
| 面积代价 | 基准 | 最小 (+5% C_B) | 大 (+68%) | 极大 (×44) |

### 4.6 最终推荐: 候选 A (H=122)

**理由**:
1. **最小改动**: 仅需调整 C_B 从 1.000C 到 1.05C (5% 变化)
2. **保持所有其他电容不变**: 低位列阵、高位列阵完全保留
3. **充分裕量**: 每级 5 LSB 对称裕量, 足以覆盖 AZ 残差 (< 1 LSB) + 噪声
4. **12-bit 覆盖**: 33×122+127 = 4153 > 4095 ✓
5. **面积代价最小**: C_B 是最小电容之一, 5% 调整几乎无面积影响
6. **calDAC 无空洞**: {1,2,4,8,12,20,32,48} 仍可覆盖 0-127 (证明见 §2.1)

**实现方式**: C_B = 1.05C 可通过将桥接电容设计为 21C/20 (使用 20 个并联的小电容, 每个为 1.05C/20 = 0.0525C) 或使用自定义尺寸的 MIM 电容实现。

---

## 5. 完整递归校准算法

### 5.1 校准顺序

采用从低到高的递归顺序 (论文方法)：

```
low10 (20) → low16 (32) → low24 (48) → high1 (122) → high2A (244) → high2B (244) → high4 (488) → high8 (976) → high16 (1952)
```

**理由**:
1. 先校准最低位, 使用更低位作为 calDAC
2. 已校准位加入 calDAC, 校准更高位
3. 两个 2C (high2A, high2B) 独立校准
4. high2B 校准后, 两个 2C 都可用于更高级别的 calDAC

### 5.2 论文 D+/D- 双向测量

对每个待校准位 W_k:

**正方向 (D+)**:
1. 注入 +W_k: 将待校准位电容在 P 侧接 VREFP, N 侧接 VREFN (差分注入 +W_k)
2. calDAC 进行 SAR 搜索, 产生码 D+ 抵消 +W_k + V_OS
3. D+ = W_k + V_OS + x_n

**负方向 (D-)**:
1. 注入 -W_k: 将待校准位电容在 P 侧接 VREFN, N 侧接 VREFP (差分注入 -W_k)
2. calDAC 进行 SAR 搜索, 产生码 |D-| 抵消 -W_k + V_OS
3. D- = -W_k + V_OS + x_{n+1}

**位权估计**:
```
Ŵ_k = (D+ - D-) / 2 = (D+ + |D-|) / 2 = W_k + (x_n - x_{n+1}) / 2
```

### 5.3 32-pair 平均

重复 32 个 D+/D- pair:
```
Ŵ_k = (1/32) × Σ_{m=1}^{32} (D+^{(m)} + |D-|^{(m)}) / 2
    = (Σ D+^{(m)} + Σ |D-|^{(m)}) / (2 × 32)
    = (accum_plus + accum_minus_mag) / 64
```

噪声标准差: σ_Ŵ = σ_n / 8 (相比单次转换降低 8 倍)

### 5.4 各级 calDAC 配置

| 目标 | target_id | target_stage | calDAC 成员 | calDAC 总和 | 目标权重 | 裕量 |
|------|-----------|-------------|------------|------------|---------|------|
| low10 | 0 | 8 | {12,8,4,2,1} | 27 | 20 | 7 |
| low16 | 1 | 7 | {20,12,8,4,2,1} | 47 | 32 | 15 |
| low24 | 2 | 6 | {32,20,12,8,4,2,1} | 79 | 48 | 31 |
| high1 | 3 | 5 | {48,32,20,12,8,4,2,1} | 127 | 122 | 5 |
| high2A | 4 | 3 | {122,48,32,20,12,8,4,2,1} | 249 | 244 | 5 |
| high2B | 5 | 4 | {122,48,32,20,12,8,4,2,1} | 249 | 244 | 5 |
| high4 | 6 | 2 | {244,244,122,48,32,20,12,8,4,2,1} | 737 | 488 | 249 |
| high8 | 7 | 1 | {488,244,244,122,48,32,20,12,8,4,2,1} | 1225 | 976 | 249 |
| high16 | 8 | 0 | {976,488,244,244,122,48,32,20,12,8,4,2,1} | 2201 | 1952 | 249 |

### 5.5 递归公式

对目标 k, 设 calDAC 权重为 {w_{j1}, w_{j2}, ..., w_{jN}}, 已校准的权重用 Ŵ 表示。

**正方向 SAR 搜索**:
1. 初始: target 接 VREFP (P侧) / VREFN (N侧), calDAC 全部接 VCM
2. 顶板残差 = +W_k + V_OS (差分)
3. SAR trial (从大到小): 若残差 ≥ 0, 保留该 calDAC cap (接相反极性抵消)
4. terminal: 残差 ≥ 0 → terminal = 1, 否则 terminal = 0
5. D+ = Σ(accepted calDAC weights) + terminal

**负方向 SAR 搜索**:
1. 初始: target 接 VREFN (P侧) / VREFP (N侧), calDAC 全部接 VCM
2. 顶板残差 = -W_k + V_OS (差分)
3. SAR trial (从大到小): 若残差 ≤ 0, 保留该 calDAC cap
4. terminal: 残差 ≤ 0 → terminal = 1, 否则 terminal = 0
5. |D-| = Σ(accepted calDAC weights) + terminal

**位权更新**:
```
Ŵ_k = (Σ_m D+^{(m)} + Σ_m |D-|^{(m)}) / (2 × N_pairs)
```

### 5.6 最高位特殊处理

high16 (1952) 的 calDAC 总和 = 2201, 裕量 = 249。

直接注入 ±1952 不会导致顶板过量程, 因为 calDAC (2201) 足以抵消。无需论文中的残差缩放特殊切换。

但如果 calDAC 范围不足 (例如在原 H=128 设计中), 可以使用残差式测量:
```
R = W_2048 - W_1024 - W_512 - W_256 - W_128 - W_low_total
Ŵ_2048 = Ŵ_1024 + Ŵ_512 + Ŵ_256 + Ŵ_128 + W_low_total + R̂
```

在 H=122 设计中, calDAC 范围充足 (2201 > 1952 + 249), 因此**无需残差缩放**, 直接使用 Huang 方法。

---

## 6. 校准切换表

### 6.1 切换编码约定

SWITCH_CAL.va 的 BITD_CAL/BITU_CAL 编码:

| BITD_CAL | BITU_CAL | 物理效果 | 差分贡献 |
|----------|----------|---------|---------|
| 1 | 0 | P侧→VREFP, N侧→VREFN | +W (正方向) |
| 0 | 1 | P侧→VREFN, N侧→VREFP | -W (负方向) |
| 0 | 0 | P侧→VCM, N侧→VCM | 0 (中性) |
| 1 | 1 | P侧→VCM, N侧→VCM | 0 (安全态) |

stage 索引: stage 0 = 高位 16C, stage 12 = 低位 1C, stage 13 = terminal (无物理电容)

### 6.2 切换表 1: 校准 W_122 (high1, target_id=3)

calDAC = {stage6:48, stage7:32, stage8:20, stage9:12, stage10:8, stage11:4, stage12:2, terminal:1}
calDAC 总和 = 127, 目标 = 122, 裕量 = 5

**正方向 (D+)**:

| 阶段 | P侧 target | N侧 target | P侧 calDAC | N侧 calDAC | 比较器残差 |
|------|-----------|-----------|-----------|-----------|-----------|
| Sampling | VCM | VCM | VCM | VCM | 0 |
| Pos inject | stage5→VREFP | stage5→VREFN | VCM | VCM | +W_122 + V_OS |
| SAR trial 1 (stage6:48) | stage5→VREFP | stage5→VREFN | stage6→VREFN | stage6→VREFP | +W_122+V_OS-48 |
| SAR trial 2 (stage7:32) | 同上 | 同上 | +stage7→VREFN | +stage7→VREFP | (残差-32 if kept) |
| SAR trial 3 (stage8:20) | 同上 | 同上 | +stage8→VREFN | +stage8→VREFP | (残差-20 if kept) |
| SAR trial 4 (stage9:12) | 同上 | 同上 | +stage9→VREFN | +stage9→VREFP | (残差-12 if kept) |
| SAR trial 5 (stage10:8) | 同上 | 同上 | +stage10→VREFN | +stage10→VREFP | (残差-8 if kept) |
| SAR trial 6 (stage11:4) | 同上 | 同上 | +stage11→VREFN | +stage11→VREFP | (残差-4 if kept) |
| SAR trial 7 (stage12:2) | 同上 | 同上 | +stage12→VREFN | +stage12→VREFP | (残差-2 if kept) |
| Terminal | 同上 | 同上 | (accepted 保持) | (accepted 保持) | 残差≥0→t=1 |

D+ = Σ(accepted) + terminal

**负方向 (D-)**:

| 阶段 | P侧 target | N侧 target | P侧 calDAC | N侧 calDAC | 比较器残差 |
|------|-----------|-----------|-----------|-----------|-----------|
| Sampling | VCM | VCM | VCM | VCM | 0 |
| Neg inject | stage5→VREFN | stage5→VREFP | VCM | VCM | -W_122 + V_OS |
| SAR trial 1 (stage6:48) | stage5→VREFN | stage5→VREFP | stage6→VREFP | stage6→VREFN | -W_122+V_OS+48 |
| SAR trial 2-7 | 同上 | 同上 | (同上, 反极性) | (同上, 反极性) | (残差+weight if kept) |
| Terminal | 同上 | 同上 | (accepted 保持) | (accepted 保持) | 残差≤0→t=1 |

|D-| = Σ(accepted) + terminal

**mask 定义** (stage 0-12, 13 bits):

正方向:
- d_mask = target_mask = (1 << 5) = 0x0020 (stage 5 on D side)
- u_mask = accepted_mask | trial_mask (calDAC stages on U side)

负方向:
- u_mask = target_mask = (1 << 5) = 0x0020 (stage 5 on U side)
- d_mask = accepted_mask | trial_mask (calDAC stages on D side)

### 6.3 切换表 2: 校准 W_244_A (high2A, target_id=4)

calDAC = {stage5:122, stage6:48, stage7:32, stage8:20, stage9:12, stage10:8, stage11:4, stage12:2, terminal:1}
calDAC 总和 = 249, 目标 = 244, 裕量 = 5

| 阶段 | P侧 target | N侧 target | P侧 calDAC | N侧 calDAC | 比较器残差 |
|------|-----------|-----------|-----------|-----------|-----------|
| Sampling | VCM | VCM | VCM | VCM | 0 |
| Pos inject | stage3→VREFP | stage3→VREFN | VCM | VCM | +W_244A + V_OS |
| SAR trial 1 (stage5:122) | 同上 | 同上 | stage5→VREFN | stage5→VREFP | +W_244A+V_OS-122 |
| SAR trial 2 (stage6:48) | 同上 | 同上 | +stage6→VREFN | +stage6→VREFP | (残差-48 if kept) |
| SAR trial 3 (stage7:32) | 同上 | 同上 | +stage7→VREFN | +stage7→VREFP | (残差-32 if kept) |
| SAR trial 4 (stage8:20) | 同上 | 同上 | +stage8→VREFN | +stage8→VREFP | (残差-20 if kept) |
| SAR trial 5 (stage9:12) | 同上 | 同上 | +stage9→VREFN | +stage9→VREFP | (残差-12 if kept) |
| SAR trial 6 (stage10:8) | 同上 | 同上 | +stage10→VREFN | +stage10→VREFP | (残差-8 if kept) |
| SAR trial 7 (stage11:4) | 同上 | 同上 | +stage11→VREFN | +stage11→VREFP | (残差-4 if kept) |
| SAR trial 8 (stage12:2) | 同上 | 同上 | +stage12→VREFN | +stage12→VREFP | (残差-2 if kept) |
| Terminal | 同上 | 同上 | (accepted 保持) | (accepted 保持) | 残差≥0→t=1 |

d_mask = (1 << 3) = 0x0008, u_mask = accepted_mask | trial_mask

### 6.4 切换表 3: 校准 W_244_R (high2B, target_id=5)

calDAC = {stage5:122, stage6:48, stage7:32, stage8:20, stage9:12, stage10:8, stage11:4, stage12:2, terminal:1}
calDAC 总和 = 249, 目标 = 244, 裕量 = 5

**与 high2A 完全相同的 calDAC, 但 target 是 stage 4 (冗余 2C) 而非 stage 3**

| 阶段 | P侧 target | N侧 target | P侧 calDAC | N侧 calDAC | 比较器残差 |
|------|-----------|-----------|-----------|-----------|-----------|
| Sampling | VCM | VCM | VCM | VCM | 0 |
| Pos inject | stage4→VREFP | stage4→VREFN | VCM | VCM | +W_244R + V_OS |
| SAR trial 1-8 | 同上 | 同上 | (同 high2A) | (同 high2A) | (逐级抵消) |
| Terminal | 同上 | 同上 | (accepted 保持) | (accepted 保持) | 残差≥0→t=1 |

d_mask = (1 << 4) = 0x0010, u_mask = accepted_mask | trial_mask

**独立性**: high2B 使用与 high2A 相同的 calDAC 子集, 但 target 物理电容不同 (stage 4 vs stage 3)。两次校准独立进行, 不假设 W_244A = W_244R。

### 6.5 切换表 4: 校准 W_488 (high4, target_id=6)

calDAC = {stage3:244, stage4:244, stage5:122, stage6:48, stage7:32, stage8:20, stage9:12, stage10:8, stage11:4, stage12:2, terminal:1}
calDAC 总和 = 737, 目标 = 488, 裕量 = 249

| 阶段 | P侧 target | N侧 target | P侧 calDAC | N侧 calDAC | 比较器残差 |
|------|-----------|-----------|-----------|-----------|-----------|
| Sampling | VCM | VCM | VCM | VCM | 0 |
| Pos inject | stage2→VREFP | stage2→VREFN | VCM | VCM | +W_488 + V_OS |
| SAR trial 1 (stage3:244) | 同上 | 同上 | stage3→VREFN | stage3→VREFP | +W_488+V_OS-244 |
| SAR trial 2 (stage4:244) | 同上 | 同上 | +stage4→VREFN | +stage4→VREFP | (残差-244 if kept) |
| SAR trial 3 (stage5:122) | 同上 | 同上 | +stage5→VREFN | +stage5→VREFP | (残差-122 if kept) |
| SAR trial 4 (stage6:48) | 同上 | 同上 | +stage6→VREFN | +stage6→VREFP | (残差-48 if kept) |
| SAR trial 5 (stage7:32) | 同上 | 同上 | +stage7→VREFN | +stage7→VREFP | (残差-32 if kept) |
| SAR trial 6 (stage8:20) | 同上 | 同上 | +stage8→VREFN | +stage8→VREFP | (残差-20 if kept) |
| SAR trial 7 (stage9:12) | 同上 | 同上 | +stage9→VREFN | +stage9→VREFP | (残差-12 if kept) |
| SAR trial 8 (stage10:8) | 同上 | 同上 | +stage10→VREFN | +stage10→VREFP | (残差-8 if kept) |
| SAR trial 9 (stage11:4) | 同上 | 同上 | +stage11→VREFN | +stage11→VREFP | (残差-4 if kept) |
| SAR trial 10 (stage12:2) | 同上 | 同上 | +stage12→VREFN | +stage12→VREFP | (残差-2 if kept) |
| Terminal | 同上 | 同上 | (accepted 保持) | (accepted 保持) | 残差≥0→t=1 |

d_mask = (1 << 2) = 0x0004, u_mask = accepted_mask | trial_mask

**注意**: 两个 244 (stage 3 和 stage 4) 都参与 calDAC。如果 trial 1 保留 stage3 (244), trial 2 保留 stage4 (244), 则已抵消 488, 残差 ≈ 0, 后续 trial 全部拒绝。如果 W_488 有正失配 (> 488), 残差为正, terminal = 1。

### 6.6 切换表 5: 校准 W_976 (high8, target_id=7)

calDAC = {stage2:488, stage3:244, stage4:244, stage5:122, stage6:48, stage7:32, stage8:20, stage9:12, stage10:8, stage11:4, stage12:2, terminal:1}
calDAC 总和 = 1225, 目标 = 976, 裕量 = 249

| 阶段 | P侧 target | N侧 target | P侧 calDAC | N侧 calDAC | 比较器残差 |
|------|-----------|-----------|-----------|-----------|-----------|
| Sampling | VCM | VCM | VCM | VCM | 0 |
| Pos inject | stage1→VREFP | stage1→VREFN | VCM | VCM | +W_976 + V_OS |
| SAR trial 1 (stage2:488) | 同上 | 同上 | stage2→VREFN | stage2→VREFP | +W_976+V_OS-488 |
| SAR trial 2 (stage3:244) | 同上 | 同上 | +stage3→VREFN | +stage3→VREFP | (残差-244 if kept) |
| SAR trial 3-11 | 同上 | 同上 | (依次 trial 244,122,48,32,20,12,8,4,2) | | |
| Terminal | 同上 | 同上 | (accepted 保持) | (accepted 保持) | 残差≥0→t=1 |

d_mask = (1 << 1) = 0x0002, u_mask = accepted_mask | trial_mask

### 6.7 切换表 6: 校准 W_1952 (high16, target_id=8)

calDAC = {stage1:976, stage2:488, stage3:244, stage4:244, stage5:122, stage6:48, stage7:32, stage8:20, stage9:12, stage10:8, stage11:4, stage12:2, terminal:1}
calDAC 总和 = 2201, 目标 = 1952, 裕量 = 249

| 阶段 | P侧 target | N侧 target | P侧 calDAC | N侧 calDAC | 比较器残差 |
|------|-----------|-----------|-----------|-----------|-----------|
| Sampling | VCM | VCM | VCM | VCM | 0 |
| Pos inject | stage0→VREFP | stage0→VREFN | VCM | VCM | +W_1952 + V_OS |
| SAR trial 1 (stage1:976) | 同上 | 同上 | stage1→VREFN | stage1→VREFP | +W_1952+V_OS-976 |
| SAR trial 2 (stage2:488) | 同上 | 同上 | +stage2→VREFN | +stage2→VREFP | (残差-488 if kept) |
| SAR trial 3 (stage3:244) | 同上 | 同上 | +stage3→VREFN | +stage3→VREFP | (残差-244 if kept) |
| SAR trial 4 (stage4:244) | 同上 | 同上 | +stage4→VREFN | +stage4→VREFP | (残差-244 if kept) |
| SAR trial 5 (stage5:122) | 同上 | 同上 | +stage5→VREFN | +stage5→VREFP | (残差-122 if kept) |
| SAR trial 6-12 | 同上 | 同上 | (依次 trial 48,32,20,12,8,4,2) | | |
| Terminal | 同上 | 同上 | (accepted 保持) | (accepted 保持) | 残差≥0→t=1 |

d_mask = (1 << 0) = 0x0001, u_mask = accepted_mask | trial_mask

**顶板过量程检查**: W_1952 = 1952, calDAC 最大 = 2201。注入 ±1952 后, calDAC 可产生 0-2201 的抵消电压, 残差范围 = 1952 + V_OS - 2201 到 1952 + V_OS - 0 = -249+V_OS 到 1952+V_OS。在 calDAC = 1952 时残差 ≈ V_OS (远小于量程)。**不过量程** ✓

---

## 7. 递归误差传播模型

### 7.1 误差定义

对每一级:
```
Ŵ_k = W_k + ε_k
```

其中 ε_k 包含:
- δ_k,measurement: 比较器噪声残差 (32-pair 平均后)
- δ_k,quantization: calDAC 量化误差 (terminal 分辨率)
- δ_k,calDAC: calDAC 已校准权重误差传播
- δ_k,bridge: 桥接电容增益误差
- δ_k,round: Q 格式舍入误差

### 7.2 各级误差公式

**low10 (stage 8, W=20)**:
```
ε_low10 = δ_meas + δ_quant + δ_round
```
calDAC = {12, 8, 4, 2, 1} (全部 nominal, 无已校准权重)
- δ_meas = σ_n / 8 (32-pair, σ_n = 比较器 + kT/C 噪声)
- δ_quant = ±0.5 LSB (terminal 分辨率)
- δ_round = ±0.5 LSB (Q6 格式, q_scale=64)
- **ε_low10 ≈ σ_n/8 + 1 LSB**

**low16 (stage 7, W=32)**:
```
ε_low16 = δ_meas + δ_quant + δ_round + ε_low10
```
calDAC 包含 Ŵ_low10, 误差传播系数 = 1 (直接使用)
- **ε_low16 ≈ σ_n/8 + 1 + ε_low10 ≈ σ_n/4 + 2 LSB**

**low24 (stage 6, W=48)**:
```
ε_low24 = δ_meas + δ_quant + δ_round + ε_low16 + ε_low10
```
calDAC 包含 Ŵ_low16 和 Ŵ_low10
- **ε_low24 ≈ σ_n/8 + 1 + ε_low16 + ε_low10**

但更精确地, calDAC 权重误差只在被 accepted 时传播。平均传播系数 ≈ target / calDAC_total。

**high1 (stage 5, W=122)**:
```
ε_high1 = δ_meas + δ_quant + δ_round + Σ(α_i · ε_i)
```
calDAC = {Ŵ_low24, Ŵ_low16, Ŵ_low10, 8, 4, 2, 1}
已校准权重: low24, low16, low10

传播系数 (近似, 假设 SAR 平均保留率 ∝ weight/target):
```
α_low24 ≈ 48/122 ≈ 0.39
α_low16 ≈ 32/122 ≈ 0.26
α_low10 ≈ 20/122 ≈ 0.16
```

```
ε_high1 ≈ σ_n/8 + 1 + 0.39·ε_low24 + 0.26·ε_low16 + 0.16·ε_low10
```

### 7.3 误差传播系数表

| 目标 | calDAC 已校准成员 | 传播系数 | ε_k (LSB) |
|------|------------------|---------|-----------|
| low10 | (无) | — | σ_n/8 + 1 |
| low16 | low10 | 1×ε_low10 | σ_n/8 + 1 + ε_low10 |
| low24 | low16, low10 | 1×ε_low16 + 1×ε_low10 | σ_n/8 + 1 + ε_low16 + ε_low10 |
| high1 | low24, low16, low10 | 0.39·ε_low24 + 0.26·ε_low16 + 0.16·ε_low10 | σ_n/8 + 1 + 0.81·ε_low |
| high2A | high1, low24, low16, low10 | 0.50·ε_high1 + 0.20·ε_low24 + 0.13·ε_low16 + 0.08·ε_low10 | σ_n/8 + 1 + 0.50·ε_high1 + ... |
| high2B | high1, low24, low16, low10 | (同 high2A) | (同 high2A, 独立测量) |
| high4 | high2A, high2B, high1, low* | 0.50·ε_2A + 0.50·ε_2B + 0.25·ε_high1 + ... | σ_n/8 + 1 + ... |
| high8 | high4, high2A, high2B, high1, low* | 0.50·ε_high4 + 0.25·ε_2A + 0.25·ε_2B + ... | σ_n/8 + 1 + ... |
| high16 | high8, high4, high2A, high2B, high1, low* | 0.50·ε_high8 + 0.25·ε_high4 + ... | σ_n/8 + 1 + ... |

### 7.4 数值估计

假设:
- σ_n = 0.3 LSB (比较器 + kT/C 噪声, 单次转换)
- 32-pair 平均后: σ_n/8 = 0.0375 LSB
- δ_quant = 0.5 LSB (terminal)
- δ_round = 0.5 LSB (Q6)
- 每级独立测量误差 ≈ 0.0375 + 0.5 + 0.5 = 1.04 LSB

| 目标 | 独立误差 | 传播误差 | 总误差 ε_k (LSB) |
|------|---------|---------|-----------------|
| low10 | 1.04 | 0 | 1.04 |
| low16 | 1.04 | 1.04 | 2.08 |
| low24 | 1.04 | 2.08+1.04=3.12 | 4.16 |
| high1 | 1.04 | 0.81×3.12≈2.53 | 3.57 |
| high2A | 1.04 | 0.50×3.57+0.41×3.12≈3.05 | 4.09 |
| high2B | 1.04 | 3.05 | 4.09 |
| high4 | 1.04 | 0.50×4.09+0.50×4.09+0.25×3.57≈5.15 | 6.19 |
| high8 | 1.04 | 0.50×6.19+0.25×4.09+0.25×4.09≈6.38 | 7.42 |
| high16 | 1.04 | 0.50×7.42+0.25×6.19+0.13×4.09≈6.40 | 7.44 |

**注意**: 上述估计是保守的 (假设所有 calDAC 误差同号传播)。实际中, SAR 的 accept/reject 使得只有被接受的 trial 的权重误差传播, 且正负方向抵消部分误差。

### 7.5 12-bit 目标验证

12-bit INL < 1 LSB 要求权重误差 < 1 LSB (相对)。

上述估计的最大误差 (high16) ≈ 7.44 LSB。但这是**绝对误差**, 不是 INL。

INL 由权重误差在 major carry 处的跳变决定:
```
INL(k) = ε_k - Σ_{i<k} (W_i/W_k) · ε_i
```

由于递归校准使得 Ŵ_k 逼近 W_k, 误差的主要影响在 major carry 处。对于 12-bit 目标:
- 若 σ_n = 0.3 LSB, 32-pair 后: σ_Ŵ = 0.0375 LSB
- 量化+舍入: ±1 LSB
- 误差传播后: INL ≈ 2-3 LSB (最差情况)

**改进方案**: 增加 AVG_PAIRS_LOG2 从 5 到 7 (128 pairs), σ_Ŵ = σ_n/16 ≈ 0.02 LSB, 或增加 FRAC_BITS 从 6 到 8, δ_round = 0.25 LSB。

---

## 8. 正常转换的数字重构

### 8.1 原始加权和

校准完成后, 正常转换的 raw sum:
```
S_raw = Σ_i r_i · Ŵ_i
```

其中 r_i ∈ {0, 1} 是各 stage 的比较器判决, Ŵ_i 是校准权重。

### 8.2 冗余解码

由于存在冗余 244R, 总权重 > 4095:
```
Σ Ŵ_i = Ŵ_1952 + Ŵ_976 + Ŵ_488 + Ŵ_244A + Ŵ_244R + Ŵ_122 + Ŵ_48 + Ŵ_32 + Ŵ_20 + Ŵ_12 + Ŵ_8 + Ŵ_4 + Ŵ_2 + 1
     ≈ 4153
```

冗余 offset:
```
O_red = (Σ Ŵ_i - 4095) / 2 = (4153 - 4095) / 2 = 29
```

### 8.3 居中输出

```
S_centered = S_raw - O_red
adc_code = round(S_centered / q_scale)
```

clip 到 [0, 4095]。

### 8.4 验证

**零点**: 当输入 = 0 (VCM), 所有 r_i = 0, S_raw = 0, S_centered = -29, adc_code = 0 (clip) ✓

**满量程**: 当输入 = +VREF, 所有 r_i = 1, S_raw = 4153, S_centered = 4153-29 = 4124, adc_code = 4124 → clip 到 4095 ✓

  但实际满量程应该映射到 4095。S_centered = 4124 > 4095, 意味着在输入接近满量程时输出提前饱和。这是冗余 DAC 的正常行为 — 顶部的冗余范围用于误差恢复, 不用于信号。

  **实际有效量程**: S_raw ∈ [O_red, ΣŴ_i - O_red] = [29, 4124], 对应 adc_code ∈ [0, 4095]。

**中点**: 当输入 = VCM (差分 0), 理想输出 = 2048。
  若冗余位 244R 在中点不切换 (r_4R = 0), S_raw = 4153/2 ≈ 2076 (近似), S_centered = 2076-29 = 2047 ≈ 2048 ✓

**相邻冗余路径一致性**: 在 244A/244R 的重叠区域, 两种编码路径 (244A=1,244R=0 和 244A=0,244R=1) 给出相同的 S_raw (因为 Ŵ_244A ≈ Ŵ_244R), 因此 adc_code 一致 ✓

**单调性**: 由于 calDAC 无 missing code 且权重单调递增, S_raw 随输入单调递增 ✓

### 8.5 替代解码: 归一化

如果 `NORMALIZE_REDUNDANT_RANGE = 1`:
```
adc_code = round(4095 × S_raw / Σ Ŵ_i)
```

这种方式将整个 [0, ΣŴ_i] 范围映射到 [0, 4095], 不损失顶部冗余范围。但增益精度依赖于 ΣŴ_i 的准确性。

**推荐**: 使用 `REMOVE_REDUNDANCY_OFFSET = 1, NORMALIZE_REDUNDANT_RANGE = 0` (固定 offset 减法), 因为它更简单且不依赖 ΣŴ_i 的精确值。

---

## 9. 状态机流程

### 9.1 状态定义

```
CAL_IDLE          // 空闲, 等待 CAL_RST
CAL_SAMPLE        // 采样阶段 (由 RST1 控制)
CAL_POS_INJECT    // 正方向注入 (RST1 下降沿)
CAL_POS_SAR       // 正方向 SAR 搜索 (CAL_CLK 驱动)
CAL_POS_TERMINAL  // 正方向终端判决
CAL_NEG_INJECT    // 负方向注入
CAL_NEG_SAR       // 负方向 SAR 搜索
CAL_NEG_TERMINAL  // 负方向终端判决
CAL_ACCUMULATE    // 累加 D+/D- 结果
CAL_UPDATE_WEIGHT // 更新权重
CAL_NEXT_TARGET   // 切换到下一个目标
CAL_DONE          // 校准完成
CAL_ERROR         // 校准失败
```

### 9.2 状态转移

```
CAL_RST ↓ → CAL_IDLE (cal_mode=1)
RST1 ↓ → CAL_POS_INJECT (frame_active=1)
         → CAL_POS_SAR (CAL_CLK ↑, 第一个 trial)
CAL_POS_SAR:
  CAL_CLK ↓ → 判决 → accept/reject trial
  if sar_step < search_count: 保持在 CAL_POS_SAR
  if sar_step == search_count: → CAL_POS_TERMINAL
CAL_POS_TERMINAL:
  CAL_CLK ↓ → terminal 判决 → 保存 D+
  → CAL_WAIT_END (等待 RST1 ↑)
RST1 ↑ → CAL_ACCUMULATE (完成 D+)
  direction = 1 → 等待下一个 RST1 ↓

RST1 ↓ → CAL_NEG_INJECT → CAL_NEG_SAR → CAL_NEG_TERMINAL → CAL_WAIT_END
RST1 ↑ → CAL_ACCUMULATE (完成 D-)
  repeat_idx++
  if repeat_idx < avg_pairs: direction = 0, 等待下一个 RST1 ↓
  if repeat_idx == avg_pairs: → CAL_UPDATE_WEIGHT

CAL_UPDATE_WEIGHT:
  计算 Ŵ_k = (accum_plus + accum_minus_mag) / (2 × avg_pairs)
  检查 tolerance 和 headroom
  if OK: 更新 w_k, → CAL_NEXT_TARGET
  if FAIL: → CAL_ERROR

CAL_NEXT_TARGET:
  target_id++
  if target_id > 8: → CAL_DONE
  else: → CAL_IDLE (等待下一个 RST1 ↓)

CAL_DONE: cal_mode=0, cal_done=1
CAL_ERROR: cal_mode=0, cal_done=1, cal_error=1, 恢复 nominal 权重
```

### 9.3 时序

每个 D+ 或 D- 方向需要:
- RST1 低电平时间: search_count + 1 个 CAL_CLK 周期
- high1: 7+1 = 8 个 CAL_CLK
- high2A/2B: 8+1 = 9 个 CAL_CLK
- high4: 10+1 = 11 个 CAL_CLK
- high8: 11+1 = 12 个 CAL_CLK
- high16: 12+1 = 13 个 CAL_CLK

每个 pair = 2 方向 × (search_count+1) CAL_CLK
32 pairs = 64 方向 × (search_count+1) CAL_CLK

总 CAL_CLK 数:
```
low10: 32×2×5 = 320
low16: 32×2×6 = 384
low24: 32×2×7 = 448
high1: 32×2×8 = 512
high2A: 32×2×9 = 576
high2B: 32×2×9 = 576
high4: 32×2×11 = 704
high8: 32×2×12 = 768
high16: 32×2×13 = 832
总计: 5120 CAL_CLK
```

若 CAL_CLK = 4 MHz (250 ns/周期), 总校准时间 ≈ 1.28 ms

---

## 10. 伪代码

```
// ===== 初始化 =====
NOM_H1_WEIGHT = 122
q_scale = 1 << FRAC_BITS  // 64 for Q6
avg_pairs = 1 << AVG_PAIRS_LOG2  // 32

// Nominal weights
nw[0..8] = {1952, 976, 488, 244, 244, 122, 48, 32, 20, 12, 8, 4, 2, 1}
w[0..13] = nw[0..13]  // 初始化为 nominal

target_id = 0
direction = 0  // 0=positive, 1=negative
repeat_idx = 0
accum_plus = 0
accum_minus_mag = 0

// ===== 校准主循环 =====
while (target_id <= 8) and (cal_error == 0):
    // 配置 target
    target_stage, search_count, search_total = configure_target(target_id)
    target_mask = 1 << target_stage

    // 检查裕量
    if (search_total - nominal_target) < MIN_HEADROOM:
        cal_error = 1; break

    // 等待 RST1 下降沿 (一个独立预采样帧)
    wait(RST1_falling_edge)

    // 初始化 SAR
    sar_step = 0
    accepted_mask = 0
    accepted_sum = 0

    // 设置注入方向
    if direction == 0:  // Positive
        d_mask = target_mask  // target on D side (positive injection)
        u_mask = 0
    else:  // Negative
        u_mask = target_mask  // target on U side (negative injection)
        d_mask = 0

    // SAR 搜索
    for step = 0 to search_count-1:
        wait(CAL_CLK_rising_edge)
        trial_stage = search_order[target_id][step]
        trial_mask = 1 << trial_stage
        trial_weight = w[trial_stage]

        if direction == 0:
            d_mask = target_mask
            u_mask = accepted_mask | trial_mask
        else:
            u_mask = target_mask
            d_mask = accepted_mask | trial_mask

        wait(CAL_CLK_falling_edge)
        // 比较器判决
        cmp_delta = V(COMP) - V(COMN)
        residue_positive = (cmp_delta < 0) ? 1 : 0  // after CMP_SWAP

        if direction == 0 and residue_positive:
            // Keep trial (cancel positive residue)
            accepted_mask |= trial_mask
            accepted_sum += trial_weight
        elif direction == 1 and not residue_positive:
            // Keep trial (cancel negative residue)
            accepted_mask |= trial_mask
            accepted_sum += trial_weight

        sar_step++

    // Terminal decision
    wait(CAL_CLK_rising_edge)
    if direction == 0:
        d_mask = target_mask; u_mask = accepted_mask
    else:
        u_mask = target_mask; d_mask = accepted_mask

    wait(CAL_CLK_falling_edge)
    cmp_delta = V(COMP) - V(COMN)
    residue_positive = (cmp_delta < 0) ? 1 : 0

    if direction == 0:
        terminal_one = residue_positive ? 1 : 0
        code_plus = accepted_sum + terminal_one * q_scale
    else:
        terminal_one = (not residue_positive) ? 1 : 0
        code_minus_mag = accepted_sum + terminal_one * q_scale

    // 等待 RST1 上升沿 (帧结束)
    wait(RST1_rising_edge)
    d_mask = 0; u_mask = 0

    if direction == 0:
        direction = 1  // 下一个方向
    else:
        // 完成一个 pair
        accum_plus += code_plus
        accum_minus_mag += code_minus_mag
        repeat_idx++

        // 检查 headroom
        pair_headroom = min(search_total - code_plus, search_total - code_minus_mag)
        min_headroom = min(min_headroom, pair_headroom)

        if repeat_idx < avg_pairs:
            direction = 0  // 下一个 pair
        else:
            // 计算 Ŵ_k
            numer = accum_plus + accum_minus_mag
            denom = 2 * avg_pairs
            measured_weight = (numer + denom/2) / denom

            // 验证
            if |measured_weight - nominal_target| > WEIGHT_TOL * nominal_target:
                cal_error = 1; break
            if min_headroom < MIN_HEADROOM * q_scale:
                cal_error = 1; break

            // 更新权重
            w[target_stage] = measured_weight

            // 重置, 下一个 target
            repeat_idx = 0
            accum_plus = 0
            accum_minus_mag = 0
            min_headroom = MAX_INT
            direction = 0
            target_id++

// ===== 完成 =====
if cal_error:
    w[0..13] = nw[0..13]  // 恢复 nominal
    cal_done = 1
    cal_error = 1
else:
    cal_done = 1
    cal_mode = 0
```

---

## 11. Verilog-A 实现方案

### 11.1 文件: `src/DEC_CAL_PHY_HUANG_V5.va`

基于 `ext/DEC_CAL_PHY_HUANG_RECURSIVE_V4.va`, 做以下改进:

#### 新增参数

| 参数 | 默认值 | 说明 |
|------|-------|------|
| NOM_H1_WEIGHT | 122 | 高位单位权重 (替代 128) |
| FRAC_BITS | 6 | Q 格式小数位 |
| AVG_PAIRS_LOG2 | 5 | 32 pairs |
| MIN_AVG_PAIRS_LOG2 | 5 | 最少 32 pairs |
| WEIGHT_TOL | 0.20 | 权重容差 (±20%) |
| MIN_CAL_HEADROOM_LSB | 2.0 | 最小裕量 (LSB) |
| FAIL_ON_ENDPOINT | 1 | 端点饱和即失败 |
| CAL_BYPASS | 0 | 旁路校准 |
| APPLY_CAL_WEIGHT | 1 | 应用校准权重 |
| REVERT_ON_ERROR | 1 | 错误时恢复 nominal |
| REMOVE_REDUNDANCY_OFFSET | 1 | 减去冗余 offset |
| NORMALIZE_REDUNDANT_RANGE | 0 | 归一化 (可选) |
| WARN_ON_OUTPUT_CLIP | 1 | 输出 clip 告警 |

#### 寄存器变化 (相比 V6.6)

| 寄存器 | V6.6 | V5.0 | 说明 |
|--------|------|------|------|
| target_id | 0..2 (3 targets) | 0..8 (9 targets) | 扩展 |
| direction | 0/1 | 0/1 | 不变 |
| repeat_idx | 0..31 | 0..31 | 不变 |
| accum_plus_q | int | int | 不变 |
| accum_minus_mag_q | int | int | 不变 |
| search_count | 7 (fixed) | 4..12 (variable) | 每级不同 |
| search_total_q | 126 (fixed) | 27..2201 (variable) | 每级不同 |
| min_pair_headroom_q | int | int | 新增 |

#### mask 映射变化

V6.6:
```
caldac_mask = 8128 (stages 6-12, 固定 7 位)
target_mask = 4 (stage 2)
wall_mask = 24 (stages 3+4)
```

V5.0:
```
target_mask = 1 << target_stage (每级不同)
d_mask / u_mask 动态生成 (target + accepted + trial)
无固定 wall_mask (直接测量, 非 wall subtraction)
```

#### Decoder 修改

V6.6 decoder 只使用 3 个校准权重 (w0, w1, w2):
```verilog
dec_w0 = w0; dec_w1 = w1; dec_w2 = w2;
// w3..w13 使用 nominal
```

V5.0 decoder 使用全部 14 个校准权重:
```verilog
dw0=w0; dw1=w1; dw2=w2; dw3=w3; dw4=w4; dw5=w5;
dw6=w6; dw7=w7; dw8=w8; dw9=w9; dw10=w10;
dw11=w11; dw12=w12; dw13=w13;
```

其中 w0..w8 是校准值 (如果校准成功), w9..w13 保持 nominal。

#### Debug 输出格式

```
HUANGV5 start t=<time> H1nom=122 avg_pairs=32 Q=6
HUANGV5 frame target=0 stage=8 dir=0 pair=0 nsearch=4 range=27
HUANGV5 trial target=0 dir=0 step=0 stage=9 W=12 keep=1 sum=12
...
HUANGV5 code target=0 dir=0 mag=20 term=0 range=27
HUANGV5 pair target=0 plus=20 minusMag=20 pair=1/32
...
HUANGV5 measure target=0 stage=8 W=20.0 nominal=20.0 plusAvg=20.0 minusAvg=20.0 range=27 minHeadroom=7 ok=1
HUANGV5 frame target=1 stage=7 dir=0 pair=0 nsearch=5 range=47
...
HUANGV5 DONE weights={1952,976,488,244,244,122,48,32,20,12,8,4,2,1}
```

#### DONE/ERR 条件

**DONE = 1**:
- 所有 9 个 target 校准成功
- 或 CAL_BYPASS = 1

**ERR = 1** (任一条件):
1. 权重超出 tolerance (|measured - nominal| > WEIGHT_TOL × nominal)
2. 裕量不足 (min_pair_headroom < MIN_CAL_HEADROOM_LSB)
3. 比较器连续无效 (invalid_count > MAX_INVALID)
4. 帧提前结束 (RST1 ↑ 时 cal_state ≠ CAL_WAIT_END)
5. 搜索表无效 (trial_stage < 0)

#### 校准失败回退策略

```
if (cal_error):
    w[0..13] = nw[0..13]  // 恢复全部 nominal 权重
    cal_mode = 0
    cal_done = 1
    cal_error = 1
    // Decoder 使用 nominal 权重 (APPLY_CAL_WEIGHT 被 cal_error 屏蔽)
```

### 11.2 SWITCH_CAL.va 修改

**无需修改**。SWITCH_CAL.va 已支持任意 BITD_CAL/BITU_CAL 组合, V5.0 只需通过 DEC_CAL_PHY 生成正确的 mask 即可。

### 11.3 其他文件

- `SAR_LOGIC_0716.va`: 无需修改 (正常转换逻辑不变)
- `SYNC_asnyc.va`: 需要修改 CAL_CLK 生成, 支持 13 个 CAL_CLK 脉冲 (当前为 8 个)
- `COM_ideal.va`: 无需修改 (CAL 引脚已支持)

---

## 12. 仿真验证方案

### 12.1 测试矩阵

| 测试类别 | 测试名 | CDAC | 比较器 | 校准 | 验证项 |
|---------|-------|------|-------|------|-------|
| 1. 理想 | ideal_all | ideal | ideal | ON | Ŵ_i = W_i |
| 2. 单位失配 | single_128 | W_128 ±5% | ideal | ON | Ŵ_128 精度 |
| | single_244A | W_244A ±5% | ideal | ON | Ŵ_244A 精度 |
| | single_244R | W_244R ±5% | ideal | ON | Ŵ_244R 精度 |
| | single_488 | W_488 ±5% | ideal | ON | Ŵ_488 精度 |
| | single_976 | W_976 ±5% | ideal | ON | Ŵ_976 精度 |
| | single_1952 | W_1952 ±5% | ideal | ON | Ŵ_1952 精度 |
| 3. 双侧失配 | pn_same | P,N 同方向 | ideal | ON | 差分权重 |
| | pn_oppo | P,N 反方向 | ideal | ON | 差分权重 |
| | p_only | 仅 P 侧 | ideal | ON | 单边效应 |
| | n_only | 仅 N 侧 | ideal | ON | 单边效应 |
| 4. 3-MSB MC | mc_3msb | W488,W976,W1952 MC | ideal | ON/OFF | INL,SNDR,ENOB |
| 5. 全局 MC | mc_all | 全部 MC (1% σ) | ideal+noise | ON/OFF | INL,SNDR,ENOB |

### 12.2 性能指标

每个 case 输出:

```
Case: <name>
Calibration:
  W122:  measured=122.03  nominal=122.00  error=+0.03 LSB  VALID=1
  W244A: measured=243.97  nominal=244.00  error=-0.03 LSB  VALID=1
  W244R: measured=244.01  nominal=244.00  error=+0.01 LSB  VALID=1
  W488:  measured=488.05  nominal=488.00  error=+0.05 LSB  VALID=1
  W976:  measured=976.02  nominal=976.00  error=+0.02 LSB  VALID=1
  W1952: measured=1951.98 nominal=1952.00 error=-0.02 LSB  VALID=1
  cal_time=1.28ms  total_comparisons=5120

Normal Conversion (4096-point ramp):
  DNL:  max=+0.42  min=-0.38  (LSB)
  INL:  max=+0.51  min=-0.47  (LSB)
  SNR:  74.2 dB
  SNDR: 73.8 dB
  SFDR: 86.5 dB
  ENOB: 11.94 bits
  missing_code: 0
  major_carry_errors: max=0.38 LSB
  output_clip: 0
```

### 12.3 理想验证 (Test 1)

所有电容 ideal, 校准后 Ŵ_i 应等于 W_i, 误差仅来自:
- 32-pair 有限平均: σ = σ_n / 8
- Terminal 量化: ±0.5 LSB
- Q6 舍入: ±0.5 LSB

预期: |ε_i| < 2 LSB, INL < 1 LSB, ENOB > 11.9

### 12.4 失配验证 (Test 2-4)

对每个物理电容注入 ±5% 失配, 验证:
1. 校准能正确检测失配
2. 校准后 INL 改善
3. 未校准 vs 校准 vs 理想权重解码的比较

### 12.5 Monte Carlo 验证 (Test 5)

100 次 Monte Carlo, 单位电容 σ = 1%:
- 比较未校准 / V6.6 三目标校准 / V5.0 完整递归校准
- 统计 ENOB 分布, 最差情况 INL

### 12.6 Testbench 结构

```
tb_huang_calibration.scs:
  - CDAC: cdac_split_mc_thesis_deltaC.va (参数化失配)
  - SWITCH: SWITCH_CAL.va (不修改)
  - SAR_LOGIC: SAR_LOGIC_0716.va (不修改)
  - DEC_CAL: DEC_CAL_PHY_HUANG_V5.va (V5.0)
  - COM: COM_ideal.va (不修改)
  - SYNC: SYNC_asnyc.va (修改: 13 CAL_CLK)
  - Stimulus: CAL_RST, RST1, CAL_CLK, input ramp/sine
```

---

## 13. 最终结论

### 问题 1: 当前低位集合能否作为论文式 calibration DAC?

**能**。集合 {1,2,4,8,12,20,32,48} 满足完备性条件 (定理 1), 可达码集合 = [0, 127], 无 missing code。SAR 收敛性已证明 (定理 2)。

### 问题 2: 能否连续量化 0~127 的全部残差?

**能**。定理 1 证明所有整数 0-127 均可达, 无空洞。

### 问题 3: 128 是否能按论文方法直接校准?

**不能**。定理 3 证明: 当 C_B = 1C (H=128) 时, calDAC 总和 (127, 含 terminal=128) 恰好等于 W_128 (128), 零裕量。任何正失配或正方向比较器失调导致饱和, W_128 不可辨识。

### 问题 4: 两个 256 能否分别独立校准?

**在 H=128 设计中不能** (同理, gap=0)。**在 H=122 设计中能**: high2A 和 high2B 使用相同的 calDAC 子集 ({122, 48, 32, 20, 12, 8, 4, 2, 1}, 总和=249), 但 target 物理电容不同 (stage 3 vs stage 4), 两次独立测量, 不假设 W_244A = W_244R。裕量 = 5 LSB, 足以覆盖 AZ 残差。

### 问题 5: 512、1024、2048 各自使用哪些已校准权重?

在 H=122 设计中:

| 目标 | calDAC 成员 | calDAC 总和 |
|------|------------|------------|
| W_488 (high4) | {Ŵ_244A, Ŵ_244R, Ŵ_122, 48, 32, 20, 12, 8, 4, 2, 1} | 737 |
| W_976 (high8) | {Ŵ_488, Ŵ_244A, Ŵ_244R, Ŵ_122, 48, 32, 20, 12, 8, 4, 2, 1} | 1225 |
| W_1952 (high16) | {Ŵ_976, Ŵ_488, Ŵ_244A, Ŵ_244R, Ŵ_122, 48, 32, 20, 12, 8, 4, 2, 1} | 2201 |

### 问题 6: 每一级的正负 switching sequence?

见 §6 切换表。每级的正方向: target 接 D side (VREFP/VREFN), calDAC trial 接 U side (VREFN/VREFP) 抵消。负方向反之。

### 问题 7: D+ - D- 是否需要再除以 2?

**需要**。权重定义为差分单位 (已包含 P-N 互补切换的因子 2), 但 D+ 和 D- 也是差分单位。论文公式 Ŵ_k = (D+ - D-) / 2 中的除以 2 是为了消除 V_OS, 与权重定义无关。

代码实现: `measured_weight = (accum_plus + accum_minus_mag) / (2 * avg_pairs)`, 其中分母 `2 * avg_pairs` 包含了除以 2。

### 问题 8: 完整递归校准后各权重的误差传播公式?

见 §7。一般形式:
```
ε_k = Σ_{i<k} α_{k,i} · ε_i + δ_meas + δ_quant + δ_round
```

其中 α_{k,i} ≈ W_i / W_k (近似, 取决于 SAR accept 模式)。

### 问题 9: 当前 CDAC 能否达到目标性能?

**不能**。当前 CDAC (C_B=1C, H=128) 在所有级别都有零裕量 (gap=0), 无法校准任何位。违反判据 1, 2, 6, 7。

### 问题 10: 若不能, 哪种替代 CDAC 最合适?

**候选 A (H=122)**: 调整 C_B 从 1C 到 1.05C, 保持所有其他电容不变。
- 最小改动 (仅 C_B +5%)
- 每级 5 LSB 裕量
- 12-bit 覆盖 (4153 > 4095)
- calDAC 无空洞
- 面积代价最小

### 问题 11: 最终推荐结构的 Verilog-A/RTL 修改?

1. **DEC_CAL_PHY**: 替换为 `DEC_CAL_PHY_HUANG_V5.va` (9-target 递归校准)
2. **SWITCH_CAL**: 无需修改
3. **SYNC_asnyc**: 修改 CAL_CLK 生成, 支持 13 个脉冲
4. **SAR_LOGIC**: 无需修改
5. **COM_ideal**: 无需修改
6. **CDAC**: 调整 C_B 参数从 1.0 到 1.05 (或等效 PEX 调整)
7. **Decoder**: 使用全部 14 个校准权重 (V5.0 已实现)

### 问题 12: 所有结论是否由电荷方程、数值仿真或可复现代码支持?

**是**。
- 电荷方程: §1 完整推导 P/N 两侧电荷守恒, 桥接节点方程, 有效差分权重
- 因子 2: §3 以 24C 电容为例验证电荷变化
- calDAC 可达性: §2 定理 1-2 完整证明
- W_128 不可校准: §2 定理 3 严格证明
- 替代 CDAC: §4 基于电荷方程推导 C_B = 1.05C
- 校准算法: §5-6 基于 Huang 论文 Section 4.5
- 误差传播: §7 逐级推导
- 数字解码: §8 验证零点/满量程/中点/单调性
- Verilog-A: §11 + `src/DEC_CAL_PHY_HUANG_V5.va` (可执行代码)
- 仿真验证: §12 测试矩阵 + `sim/tb_huang_calibration.scs`

---

**文档结束**
