---
title: 12位SAR ADC校准诊断报告 V2（更正版）
aliases: [calibration_diagnosis_v2, 校准诊断报告V2]
tags: [SAR_ADC, calibration, diagnosis, wall_propagation]
created: 2026-07-20
updated: 2026-07-20
---

# 12位SAR ADC前台校准系统诊断报告 V2

> [!warning] 更正声明
> 本报告为 V1 的更正版。V1 存在以下错误：
> 1. 将 dither 不足定性为"唯一根因" → 实际上墙传播误差是**更危险的结构性问题**
> 2. 扩展校准顺序（C8→C9→CR→C10→C11→C12）经物理可行性验证后确认为**不可行**
> 3. 精度计算错误：0.022 LSB → 正确值为 **±0.0625 LSB**
> 4. 码型比例错误：25% → 正确值为 **12.5%**
> 5. Monte Carlo 命名错误 → 应为 **Python 参数随机扫描**
> 6. DNL/INL 改善结论无依据 → 更正为 **尚未验证**

---

## 一、系统概述

### 1.1 CDAC 拓扑

12 位差分 SAR ADC，采用分段冗余 CDAC：

| 位 | 电容 | 权重 (LSB) | Stage | Mask | 校准状态 |
|----|------|-----------|-------|------|---------|
| C12 | 16C | 2048 | 0 | 1 | ✅ 可校准 |
| C11 | 8C | 1024 | 1 | 2 | ✅ 可校准 |
| C10 | 4C | 512 | 2 | 4 | ✅ 可校准 |
| C9 | 2C | 256 | 3 | 8 | ❌ 不可校准 |
| CR | 2C | 256 | 4 | 16 | ❌ 不可校准 |
| C8 | 1C | 128 | 5 | 32 | ❌ 不可校准 |
| C7-C1 | calDAC | 48,32,20,12,8,4,2 | 6-12 | 8128 | 搜索机制 |

calDAC 总权重 = 126 LSB，作为 offset-binary SAR 搜索机制。

### 1.2 校准算法

采用 Huang 2024 前台权重校准：
- 目标位：C10、C11、C12
- 参考墙：C9+CR（名义值 512 LSB）
- 残差：$R = W_{target} - W_{wall}$
- offset-binary SAR 搜索 + POS/NEG 双向测量消除失调
- Dither 扩展亚 LSB 分辨率

---

## 二、两个已确认的根因

### 2.1 根因 A：Dither 范围不足（已修复）

**问题**：原 `DITHER_RANGE_LSB=0.5`，dither 总范围 $[-0.5, +0.5)$ LSB，远小于 calDAC 最小步进 $\Delta F_{min} = 2 \times W_{C1} = 4$ LSB。

**修复**：`DITHER_RANGE_LSB=4.0`，dither 范围扩展为 $[-2, +2)$ LSB，覆盖一个完整 calDAC 步进。

**验证状态**：Python 数学模型通过，物理可行性已确认（calDAC 非墙时正常工作）。

### 2.2 根因 B：基础墙传播误差（结构性限制，无法修复）

> [!danger] 最严重问题
> C9 和 CR 作为未校准基础墙，其失配误差按 $1\times, 2\times, 4\times$ 递归传播至 C10、C11、C12。

**数学推导**：

定义基础墙误差：
$$E_B = (W_{3,nom} + W_{4,nom}) - (W_{3,real} + W_{4,real})$$

C10 校准：
- 物理墙：$W_{3,real} + W_{4,real}$
- 数字墙：$W_{3,nom} + W_{4,nom}$
- 测量残差：$R_2 = W_{2,real} - (W_{3,real} + W_{4,real})$
- 重构权重：$\widehat{W}_2 = (W_{3,nom} + W_{4,nom}) + R_2 = W_{2,real} + E_B$

递归传播：
$$\widehat{W}_2 = W_{2,real} + E_B$$
$$\widehat{W}_1 = W_{1,real} + 2E_B$$
$$\widehat{W}_0 = W_{0,real} + 4E_B$$

**物理模型验证结果**（C9 失配 +1 LSB）：

| 位 | 理论误差 | 物理模型误差 | 确认 |
|----|---------|------------|------|
| C10 | -1.0 LSB | -1.0000 LSB | ✅ |
| C11 | -2.0 LSB | -2.0000 LSB | ✅ |
| C12 | -4.0 LSB | -4.0000 LSB | ✅ |

---

## 三、扩展校准顺序的物理可行性分析

### 3.1 提议方案

为消除墙传播误差，提议将校准顺序扩展为：
$$C8 \to C9 \to CR \to C10 \to C11 \to C12$$

各目标位的 wall 配置：

| 目标 | Wall 构成 | Wall 名义值 | R (理想) | calDAC 范围 |
|------|----------|-----------|---------|------------|
| C8 (128) | calDAC | 126 | 2 | ±126 |
| C9 (256) | C8+calDAC | 254 | 2 | ±126 |
| CR (256) | C8+calDAC | 254 | 2 | ±126 |
| C10 (512) | C9+CR | 512 | 0 | ±126 |

### 3.2 物理可行性验证

> [!bug] 关键发现：calDAC 不能同时作为 wall 和搜索机制
> 当 calDAC 被设为 wall（`wall_mask = caldac_mask`）时，SWITCH_CAL 编码导致未切换的 calDAC cap 处于状态 11（VCM），而非状态 10（+w）。

**SWITCH_CAL 编码**：
- `d_mask` 中 BITD=1，`u_mask` 中 BITU=1
- 状态 10：`d_mask` only → +w
- 状态 01：`u_mask` only → -w
- 状态 11：两者都有 → **VCM（0 贡献）**
- 状态 00：都没有 → VCM

当 `wall_mask = caldac_mask = 8128` 时：
- **d_mask** = `target_mask | (caldac_mask & ~(switched|trial))` → 包含未切换 calDAC
- **u_mask** = `wall_mask | switched | trial` = `8128 | ...` = **包含所有 calDAC**

因此未切换 calDAC cap 同时在 d_mask 和 u_mask 中 → **状态 11 (VCM)**。

### 3.3 SAR 公式变化

**正常情况**（wall 非 calDAC，如 C10）：
$$F = W_{target} - W_{wall} + 126 - 2S$$

**calDAC 作 wall 时**（如 C8）：
$$F = W_{target} - W_{wall\_fixed} - S$$

其中 $W_{wall\_fixed}$ 是 wall 中非 calDAC 部分的权重。calDAC 贡献从 $+126 - 2S$ 变为 $-S$。

### 3.4 验证结果

| 测试项 | 理想 Python 模型 | 物理模型 | 结论 |
|--------|----------------|---------|------|
| C8 校准 (R=2) | D+-D- = 2.0 ✅ | D+-D- = 127.0 ❌ | **不可行** |
| C9 校准 (R=2) | D+-D- = 2.0 ✅ | D+-D- = 127.0 ❌ | **不可行** |
| C10 基线 (R=0) | D+-D- = 0.0 ✅ | D+-D- = 0.0 ✅ | 可行 |

**结论**：

$$\boxed{\text{扩展校准顺序（C8→C9→CR→C10→C11→C12）物理上不可行}}$$

原因：
1. calDAC 同时出现在 d_mask（搜索）和 u_mask（wall）中，导致状态 11（VCM）
2. SAR 测量值变为 $W_{target} - W_{wall\_fixed} \approx 127$，而非残差 $R = 2$
3. C8（128）与 calDAC（126）仅差 2 LSB，但 calDAC 无法同时充当 wall 和搜索机制

---

## 四、精度计算更正

### 4.1 原报告（错误）

$$\frac{0.125}{\sqrt{32}} \approx 0.022 \text{ LSB}$$

### 4.2 更正

32 级确定性均匀 dither 扫描，非 32 次独立随机高斯测量。精度由网格分辨率决定：

$$\Delta R_{grid} = \frac{\text{dither\_range}}{N_{levels}} = \frac{4.0}{32} = 0.125 \text{ LSB}$$

理想最大量化误差：

$$\boxed{\pm \frac{\Delta R_{grid}}{2} = \pm 0.0625 \text{ LSB}}$$

Python 验证：10 种子最大误差 = 0.0620 LSB，与 $\pm 0.0625$ 一致。

> [!note] 说明
> $\frac{1}{\sqrt{N}}$ 仅适用于独立随机噪声叠加场景。确定性 dither 扫描的精度由网格分辨率决定，不随 $N$ 减小。

---

## 五、码型比例更正

### 5.1 原报告（错误）

> 25% 的 dither 产生 D=65

### 5.2 更正

若输出只有 63 和 65，令产生 65 的比例为 $p$：

$$63(1-p) + 65p = 63.25$$
$$2p = 0.25$$

$$\boxed{p = 12.5\%}$$

验证：$\frac{R}{\Delta} = \frac{0.5}{4.0} = 12.5\%$ ✓

---

## 六、Monte Carlo 命名更正

### 6.1 原报告（错误）

> CDAC Monte Carlo 验证通过

### 6.2 更正

$$\boxed{\text{Python 参数随机扫描（非电路 Monte Carlo）}}$$

原测试仅改变目标位权重（如 513.1, 1027.8, 2053.8），保持参考墙 $(w_3, w_4)$ 为理想值。因此无法暴露墙传播误差。

真正的电路 Monte Carlo 需包含：
- Spectre 电容 mismatch Monte Carlo
- P/N 两侧独立失配
- $w_3, w_4$ 参考墙失配
- 开关寄生
- 有限建立
- comparator regeneration
- 参考电压动态压降

---

## 七、DNL/INL 结论更正

### 7.1 原报告（错误）

> 修改后能够在失配和 offset 条件下改善 DNL/INL

### 7.2 更正

$$\boxed{\text{Python 数学模型显示目标高位权重可被精确估计；实际 DNL/INL 改善尚未验证}}$$

缺少的验证项：
- DC ramp 测试
- code histogram
- DNL/INL 曲线
- 校准前后对比
- Spectre FFT 波形

且在基础墙未校准的情况下，即使权重估计精确，DNL/INL 仍受墙传播误差影响。

---

## 八、可交付文件清单

### 8.1 已修改文件

| 文件 | 修改内容 | 状态 |
|------|---------|------|
| `COM_ideal.va` | 新增 `DITHER_RANGE_LSB=4.0`，dither 范围 $[-2, +2)$ LSB | ✅ 已完成 |
| `DEC_CAL_PHY_V6.va` | `WEIGHT_TOL` 0.35→0.15，新增 `MAX_CAL_CYCLES=512` watchdog | ✅ 已完成 |

### 8.2 未修改文件

| 文件 | 原因 |
|------|------|
| `DEC_CAL_PHY_V6.va`（扩展校准顺序） | 物理可行性验证表明 calDAC 不能同时作 wall 和搜索机制，扩展顺序不可行 |

### 8.3 验证脚本

| 脚本 | 位置 | 用途 |
|------|------|------|
| `verify_physical_feasibility.py` | 工作目录 | 物理模型验证扩展顺序不可行 |
| `base_wall_attack_test.py` | 工作目录 | 墙传播误差 1×/2×/4× 验证（Python 理想模型） |

---

## 九、当前结论

### 9.1 可接受结论

$$\boxed{\text{Dither 范围不足是真实、可信的算法缺陷，已修复}}$$

$$\boxed{[-2, +2) \text{ LSB dither 范围是有效的候选修复}}$$

$$\boxed{\text{基础墙 } w_3+w_4 \text{ 误差按 } 1, 2, 4 \text{ 递归传播已确认}}$$

$$\boxed{\text{扩展校准顺序物理不可行，calDAC 不能同时作 wall 和搜索}}$$

### 9.2 不能接受结论

以下结论**未被证明**，不应宣称：
- CDAC 正常架构完全正确
- CAL 物理路径完全正确
- 参考墙没有问题
- DNL/INL 已经改善
- 校准系统已完整修复

### 9.3 当前最危险的问题

$$\boxed{w_3 + w_4 \text{ 作为未校准基础墙，其误差按 } 1, 2, 4 \text{ 递归传播}}$$

这是**结构性限制**，无法通过调整 dither 或校准顺序解决。

---

## 十、建议的后续测试

### 10.1 Test 1: Dither 修复闭环验证（Spectre）

- 理想电容，理想开关，$V_{OS}=0$，关闭随机噪声
- 分别测试 `DITHER_RANGE_LSB=1.0` 和 `4.0`
- 构造残差 $R = 0.5, 1.1, 1.5, 3.8, 5.8$ LSB
- 验证每个 dither level 的 $D_+, D_-, D_+ - D_-$ 码型

### 10.2 Test 2: CDAC 静态物理验证（Spectre）

直接记录 $V_P, V_N, V_P - V_N$，验证：
- 单电容步进
- P/N 对称
- target 与 wall 真正相减
- dither 只改变比较器阈值，不改变 CDAC
- RST1 释放后配置稳定保持
- CAL_CLK 期间没有重新预充电
- 比较器读取时残差已建立

### 10.3 Test 3: 墙传播误差 Spectre 验证

在 Spectre 中修改 $W_3$（C9）+1 LSB，运行完整校准，验证：
- C10 误差 ≈ -1 LSB
- C11 误差 ≈ -2 LSB
- C12 误差 ≈ -4 LSB

### 10.4 Test 4: ADC 系统验证

按顺序执行：
$$\text{权重恢复} \to \text{DC ramp} \to \text{DNL/INL} \to \text{FFT}$$

对比四种配置：
1. 理想电容、关闭校准
2. 理想电容、开启校准
3. 失配电容、关闭校准
4. 失配电容、开启校准

理想电容开启校准后不能比关闭校准更差。

---

## 十一、替代方案建议

由于扩展校准顺序不可行，墙传播误差无法通过当前电路消除。可能的替代方案：

### 11.1 方案 A：接受墙误差（短期）

- 保持当前校准顺序（C10→C11→C12）
- 墙误差取决于 C9/CR 物理失配（典型 1-2 LSB）
- C12 误差 = 4-8 LSB（0.1-0.2% FS）
- 适用于 INL 要求不极端的应用

### 11.2 方案 B：修改 CDAC 增加校准电容（中期）

- 增加 ~128 LSB 专用校准电容
- 使 C8 可独立校准
- 打破递归依赖链

### 11.3 方案 C：背景校准（长期）

- 使用正常转换数据提取电容失配
- 无需前台校准周期
- 不受 wall 限制
- 需要重新设计数字校准逻辑

### 11.4 方案 D：精密电压源 + 数字校正

- 外部施加精密 DC 电压
- 从输出码偏差提取墙误差 E
- 数字校正：$W_{corrected} = W_{measured} - k \cdot E$

---

## 十二、总结

本次诊断确认了两个根因：

1. **Dither 范围不足**（已修复，Python 验证通过）
2. **基础墙传播误差**（结构性限制，无法通过当前电路修复）

扩展校准顺序经物理可行性验证确认为**不可行**。Python 理想模型的"通过"结果源于错误假设——calDAC 作 wall 时仍保持 +126 贡献，但物理上 calDAC 同时在 d_mask 和 u_mask 中导致状态 11（VCM）。

**建议**：不将当前代码接入主仿真。先完成 Spectre 验证（Test 1-4），确认 dither 修复在闭环中的有效性。墙传播误差作为已知结构性限制记录，根据应用需求决定是否需要替代方案。

---

*报告生成时间：2026-07-20*
*验证脚本：`verify_physical_feasibility.py`, `base_wall_attack_test.py`*
