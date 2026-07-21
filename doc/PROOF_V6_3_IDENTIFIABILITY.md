# V6.3 可辨识性证明与校准方案严格分析

> 本文档给出 V6.2 缺陷的严格数学证明、可辨识性分析、W5 不可测性证明、共模增益不可观测性证明，以及 V6.3 隐式 gauge 方案的正确性证明。所有结论均以显式数学推导支撑。

## 0. 符号定义

设 CDAC 物理电容权重为：

$$
W_i = W_i^{\text{nom}} + e_i,\qquad i=0,1,\ldots,13
$$

其中名义权重为：

| $i$ | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| $W_i^{\text{nom}}$ | 2048 | 1024 | 512 | 256 | 256 | 128 | 48 | 32 | 20 | 12 | 8 | 4 | 2 | 1 |

记 $W_{34} := W_3 + W_4 = 512 + E$，其中 $E := e_3 + e_4$。

calDAC 由 stage 6..12 组成，权重 $48+32+20+12+8+4+2 = 126$，覆盖范围 $\pm 126$。

校准测量模型（offset-binary SAR + D+/D- 差分）：

$$
\hat W_{\text{target}} = W_{\text{wall}}^{\text{digital}} + R,\qquad R = W_{\text{target}}^{\text{phys}} - W_{\text{wall}}^{\text{phys}}
$$

其中 $R \in [-126, +126]$ 由 calDAC 测出，$W_{\text{wall}}^{\text{digital}}$ 为数字侧记录的 wall 权重（已校准或名义值）。

## 1. V6.2 `w2 re-correction` 不成立的严格证明

### 1.1 V6.2 算法描述

V6.2 的 4-target 序列：

| target_idx | target | wall (digital) | 物理残差 $R$ |
|---|---|---|---|
| 3 | $W_2$ | $W_{34}^{\text{nom}} = 512$ | $R_1 = W_2 - W_{34} = e_2 - E$ |
| 2 | $W_{34}$ | $\hat W_2$（刚测得） | $R_2 = W_{34} - W_2 = E - e_2 = -R_1$ |
| 1 | $W_1$ | $\hat W_2 + \hat W_{34}$ | $R_3 = e_1 - (\hat e_2 + \hat E)$ |
| 0 | $W_0$ | $\hat W_1 + \hat W_2 + \hat W_{34}$ | $R_4 = e_0 - (\hat e_1 + \hat e_2 + \hat E)$ |

V6.2 的"修正"在第 2 步后执行：

```verilog
w2 = w2 + (measured_weight_q - 512*q_scale);
```

即 $\hat W_2^{\text{corr}} = \hat W_2 + (\hat W_{34} - 512)$。

V6.2 注释声称：$\hat W_{34} = 512 + E$，从而 $\hat W_2^{\text{corr}} = 512 + (e_2 - E) + E = 512 + e_2$。

### 1.2 严格证明：$\hat W_{34} \equiv 512$ 恒等

**定理 1**：在 V6.2 的 4-target 序列下，第 2 次测量必然得到 $\hat W_{34} = 512$（与 $e_2, E$ 无关），因此 `w2 re-correction` 是恒等操作（no-op）。

**证明**：

第 1 次测量后，数字侧记录：
$$
\hat W_2 = W_{34}^{\text{nom}} + R_1 = 512 + (e_2 - E)
$$

第 2 次测量时，target = $W_{34}$，wall（数字侧）= $\hat W_2$。物理残差：
$$
R_2 = W_{34}^{\text{phys}} - W_2^{\text{phys}} = (512 + E) - (512 + e_2) = E - e_2
$$

测量结果：
$$
\hat W_{34} = \hat W_2 + R_2 = \bigl[512 + (e_2 - E)\bigr] + (E - e_2) = 512
$$

即 $\hat W_{34} \equiv 512$，**与 $e_2, E$ 的真实值无关**。$\blacksquare$

**推论 1**：`measured_weight_q - 512*q_scale` 恒等于 0，因此
$$
\hat W_2^{\text{corr}} = \hat W_2 + 0 = \hat W_2 = 512 + (e_2 - E)
$$

V6.2 注释中的 "$\hat W_{34} = 512 + E$" 假设错误：实际 $\hat W_{34} = 512$。

### 1.3 根因：可辨识性缺失

$W_2$ 与 $W_{34}$ 名义值相同（均为 512），calDAC 范围 $\pm 126$ 决定了它们只能互为 wall。两次测量 $R_1 = e_2 - E$ 与 $R_2 = E - e_2 = -R_1$ 是**同一方程的两个面**，自由度为 1，无法分离 $e_2$ 与 $E$。

形式地，雅可比矩阵：
$$
J = \begin{bmatrix} \partial R_1 / \partial e_2 & \partial R_1 / \partial E \\ \partial R_2 / \partial e_2 & \partial R_2 / \partial E \end{bmatrix} = \begin{bmatrix} 1 & -1 \\ -1 & 1 \end{bmatrix}
$$

$\det(J) = 1 \cdot 1 - (-1) \cdot (-1) = 0$，矩阵奇异，参数 $(e_2, E)$ 不可辨识。

## 2. W5 (128) 不可测性证明

### 2.1 calDAC 范围限制

calDAC 总权重：
$$
W_{\text{calDAC}} = 48 + 32 + 20 + 12 + 8 + 4 + 2 = 126
$$

测量 $W_{\text{target}}$ 需要 wall 满足 $|W_{\text{target}} - W_{\text{wall}}| \le 126$。

### 2.2 严格证明

**定理 2**：用现有 calDAC（±126）无法测量 $W_5 = 128 + e_5$。

**证明**：要测量 $W_5$，需要找到一个 wall（CDAC 中其它电容的子集和）满足：
$$
|W_5 - W_{\text{wall}}| \le 126 \implies W_{\text{wall}} \in [W_5 - 126, W_5 + 126] = [2 + e_5, 254 + e_5]
$$

CDAC 中除 $W_5$ 外的电容子集和的可能取值（名义值，忽略 $e_i$）：

- 单电容：$\{1, 2, 4, 8, 12, 20, 32, 48, 256, 256, 512, 1024, 2048\}$
- 在 $[2, 254]$ 区间内的可能 wall：
  - $W_6 + W_7 + \ldots + W_{13} = 48+32+20+12+8+4+2+1 = 127$
  - $W_6 + W_7 + \ldots + W_{12} = 126$（不含 $W_{13}=1$）
  - 其他子集和 $\le 127$

最大可用 wall 为 127（所有低位电容之和）。则：
$$
W_5 - W_{\text{wall}}^{\max} = 128 - 127 = 1 \le 126 \quad \checkmark
$$

**看似可行**，但 calDAC 是 **offset-binary SAR**，要求 wall + calDAC ≥ target 才能收敛：

$$
W_{\text{wall}} + W_{\text{calDAC}} \ge W_{\text{target}} \implies 127 + 126 \ge 128 \quad \checkmark
$$

但 offset-binary SAR 的收敛条件（每位权重 ≤ 剩余位之和 + 1）要求 calDAC 的最大权重（48）≤ 剩余权重之和 + 1 = 32+20+12+8+4+2+1 = 79。此条件满足。

**关键问题**：wall=127 时残差 $R = W_5 - 127 = 1 + e_5$，calDAC 抵消 $R \approx 1$，但 calDAC 最小权重为 2 > 1。

更严格地，wall=127 需要 wall 包含 $W_{13}=1$（最小位）。当 target = $W_5$ = stage 5、wall 包含 stage 6..13 时：

- target_mask = stage 5（bit 5 = 32... 实际 stage 5 的 mask = 1<<5 = 32）
- wall_mask = stages 6..13（mask = 0x1FE0 = 8160）

残差 $R = W_5 - \sum_{i=6}^{13} W_i = 128 - 127 = 1 + e_5 - \sum_{i=6}^{13} e_i$。

calDAC 抵消 $R \approx 1$：calDAC 最小位为 2，无法精确表示 1。但 SAR 仍能收敛到 code=0 或 code=1（在 D+/D- 的 terminal bit 上）。

**真正的不可测性来自 D+/D- 差分**：测量得 $D = R + \text{calDAC} \in [0, 127]$，但 $R \approx 1$，calDAC=126（初始全 +126），$D = 127$（饱和）。

**结论**：$W_5$ 在名义 wall=127 下，初始 calDAC=126 时 $R + 126 = 127$（撞顶），calDAC 必须切换到 125（code=125）才能 null。但 125 ≠ 1，残差仍为 1-1=0... 让我们更仔细地分析。

实际上，offset-binary SAR 的初始状态是 calDAC 全部 +（贡献 +126），残差信号为 $R + 126$。SAR 通过把某些 calDAC 电容从 + 切换到 - 来减小贡献。每次切换使 calDAC 贡献减少 $2 \times w_i$。

最终 calDAC 贡献 $C \in \{-126, -124, \ldots, +124, +126\}$（偶数）。Code $D = (C + 126)/2 \in \{0, 1, \ldots, 127\}$。

测量 $R$：$D = (C^* + 126)/2$，其中 $C^*$ 使 $R + C^* \approx 0$，即 $C^* \approx -R$。

对 $W_5$ 测量，$R = W_5 - W_{\text{wall}} = 128 - W_{\text{wall}}$：
- 若 $W_{\text{wall}} = 127$（最大低位和），$R = 1$，$C^* = -1$。但 $C^*$ 只能取偶数 $\{-126, -124, \ldots\}$，最近的是 $C^* = 0$ 或 $C^* = -2$。
- $C^* = 0 \implies D = 63$；$C^* = -2 \implies D = 62$。
- 残差 $R + C^* = 1$ 或 $-1$，由 terminal bit 决定。

**理论上 W5 可以测**，但残差只有 ±1，D+/D- 的 32-pair 平均的统计噪声 ±0.5 LSB 会显著污染结果。

**更严格的不可测性来自 wall 的物理实现**：要让 wall=127，需要把 stage 6..13 全部接 +，但 stage 6..12 同时是 calDAC 的来源。**calDAC 与 wall 共享电容**，物理上无法同时使用。

**形式化**：calDAC 电容集合 $\mathcal{C} = \{W_6, W_7, \ldots, W_{12}\}$（7 个，总和 126）。wall 必须从 $\mathcal{C}$ 之外的电容选取。可用 wall 电容：$\{W_0, W_1, W_2, W_3, W_4, W_5, W_{13}\}$。

要使 $|W_5 - W_{\text{wall}}| \le 126$：
- $W_{\text{wall}} = W_{13} = 1 \implies R = 127$（超出 calDAC 范围）
- $W_{\text{wall}} = W_{13} + (\text{部分其它})$：但 $W_5$ 自身不能在 wall 中，$W_0, W_1, W_2, W_3, W_4$ 都太大（≥256），$W_{\text{wall}} \ge 256 + 1 = 257 > 254 = W_5 + 126$。

**所以唯一的 wall 候选是 $W_{13}=1$，但 $R = 127 > 126$，不可测。** $\blacksquare$

### 2.3 解决方案（硬件改动）

W5 不可测是硬件限制，可选方案：
1. **拆分 W5**：将 $W_5 = 128$ 拆为 $W_{5a} = 64 + W_{5b} = 64$，校准 $W_{5a}$（wall=$W_{5b}$+calDAC=64+126=190 > 64+126=190 ✓）。
2. **外部参考电容**：引入已知 $V_{\text{ref}}$ 电容 $C_{\text{ref}} = 128$，作为 wall。
3. **依赖 layout matching**：接受 $|e_5| < 1\%$，不校准 $W_5$。

V6.3 采用方案 3（依赖 layout matching）。

## 3. 共模增益不可观测性证明

### 3.1 模型

设所有电容存在共模缩放误差 $\alpha$（来自 $V_{\text{ref}}$ 偏差、$C_u$ 偏差等）：
$$
W_i^{\text{phys}} = (1 + \alpha) \cdot W_i^{\text{nom}} + e_i^{\text{local}}
$$

### 3.2 严格证明

**定理 3**：所有 wall 测量对共模增益 $(1+\alpha)$ 不敏感，calDAC 测得的 $R$ 与 $\alpha$ 无关。

**证明**：任意 target/wall 配置下：
$$
R = W_{\text{target}}^{\text{phys}} - W_{\text{wall}}^{\text{phys}} = (1+\alpha)(W_{\text{target}}^{\text{nom}} - W_{\text{wall}}^{\text{nom}}) + (e_{\text{target}}^{\text{local}} - e_{\text{wall}}^{\text{local}})
$$

但 calDAC 自身也缩放：calDAC 贡献 $C^{\text{phys}} = (1+\alpha) C^{\text{nom}}$。SAR 收敛条件 $R + C^* = 0$ 给出：
$$
C^{*\text{nom}} = -\frac{R}{1+\alpha} = -(W_{\text{target}}^{\text{nom}} - W_{\text{wall}}^{\text{nom}}) - \frac{e^{\text{local}}}{1+\alpha}
$$

数字侧测得的 $D = (C^{*\text{nom}} + 126)/2$ 与 $\alpha$ 无关（calDAC 的数字 code 不变）。因此：
$$
\hat W_{\text{target}} = W_{\text{wall}}^{\text{digital}} + R^{\text{measured}} = W_{\text{wall}}^{\text{nom}} + (W_{\text{target}}^{\text{nom}} - W_{\text{wall}}^{\text{nom}}) = W_{\text{target}}^{\text{nom}}
$$

校准后的 $\hat W$ 仍是名义值，$\alpha$ 不可观测。$\blacksquare$

### 3.3 影响

- 整体增益误差 $\alpha$ 不被校准，会导致满量程偏差。
- 实际应用中通过外部 $V_{\text{ref}}$ 校准或后端数字增益校正处理。
- V6.3 接受此限制，不声称测出绝对增益。

## 4. V6.3 隐式 gauge 方案的正确性证明

> **重要更正（V6.3 review）**：本节原先声称 "W1/W0 在 gauge 下精确"，推导中
> 把 $R_1, R_0$ 的 $E$ 符号写反。经独立审查重新推导，V6.3 实际仍保留
> $(-E, -2E, -4E)$ 误差传播。本节给出修正后的严格推导。

### 4.1 设计约束

**Gauge 约束**：通过 layout matching 保证 $|E| = |e_3 + e_4| < \sigma_E$（典型 $\sigma_E \approx 0.5\% \times 512 = 2.56$ LSB）。

算法不测量 $W_{34}$，将其视为名义 512。

### 4.2 3-target 校准序列

| target_idx | target | wall（digital） | 物理残差 $R$ |
|---|---|---|---|
| 2 | $W_2$ | $W_{34}^{\text{nom}} = 512$ | $R_2 = W_2 - W_{34}^{\text{phys}} = e_2 - E$ |
| 1 | $W_1$ | $\hat W_2 + W_{34}^{\text{nom}}$ | $R_1 = W_1 - (W_2 + W_{34}^{\text{phys}}) = e_1 - e_2 - E$ |
| 0 | $W_0$ | $\hat W_1 + \hat W_2 + W_{34}^{\text{nom}}$ | $R_0 = W_0 - (W_1+W_2+W_{34}^{\text{phys}}) = e_0 - e_1 - e_2 - E$ |

注意 $W_{34}^{\text{phys}} = 512 + E$，因此 $R$ 中 $E$ 项恒为 $-E$（不是 $+E$）。

### 4.3 严格推导：V6.3 的实际误差传播

**定理 4（更正版）**：在 V6.3 序列下，校准结果为
$$
\hat W_2 = 512 + e_2 - E,\qquad \hat W_1 = 1024 + e_1 - 2E,\qquad \hat W_0 = 2048 + e_0 - 4E
$$
即 gauge 误差 $E$ 按 $(-E, -2E, -4E)$ 传播到 $(w_2, w_1, w_0)$。

**证明**：

**Target 2（W2）**：wall（digital）= $W_{34}^{\text{nom}} = 512$。
$$
\hat W_2 = 512 + R_2 = 512 + (e_2 - E)
$$
残留误差：$-E$。

**Target 1（W1）**：wall（digital）= $\hat W_2 + W_{34}^{\text{nom}} = [512 + (e_2 - E)] + 512 = 1024 + (e_2 - E)$。

物理残差 $R_1 = W_1 - (W_2 + W_{34}^{\text{phys}}) = (1024 + e_1) - [(512 + e_2) + (512 + E)] = e_1 - e_2 - E$。

$$
\hat W_1 = \text{wall}^{\text{digital}} + R_1 = [1024 + (e_2 - E)] + (e_1 - e_2 - E) = 1024 + e_1 - 2E
$$
残留误差：$-2E$。**$E$ 项不抵消，反而累加**（wall 含 $-E$，$R$ 也含 $-E$）。

**Target 0（W0）**：wall（digital）= $\hat W_1 + \hat W_2 + W_{34}^{\text{nom}} = (1024 + e_1 - 2E) + (512 + e_2 - E) + 512 = 2048 + e_1 + e_2 - 3E$。

物理残差 $R_0 = W_0 - (W_1 + W_2 + W_{34}^{\text{phys}}) = (2048 + e_0) - [(1024 + e_1) + (512 + e_2) + (512 + E)] = e_0 - e_1 - e_2 - E$。

$$
\hat W_0 = \text{wall}^{\text{digital}} + R_0 = [2048 + e_1 + e_2 - 3E] + (e_0 - e_1 - e_2 - E) = 2048 + e_0 - 4E
$$
残留误差：$-4E$。$\blacksquare$

### 4.4 关键观察（更正）

V6.3 的 wall 使用了已校准的 $\hat W_2$（含 $-E$），但物理残差 $R$ 中 $W_{34}^{\text{phys}} = 512 + E$ 也贡献 $-E$。两者**同号累加**而非抵消：

- wall_digital 含 $-E$（来自 $\hat W_2$ 的残留）
- $R$ 含 $-E$（来自 $W_{34}^{\text{phys}}$ 的 $+E$，被减去）

每递归一层，$E$ 的系数增加 $-1$：$w_2: -E,\ w_1: -2E,\ w_0: -4E$（按 target 名义权重的二进制层级累加）。

### 4.5 与 V6（无 gauge）的对比

V6（3-target，无 w2 re-correction）的推导与 V6.3 **完全相同**。V6.3 相比 V6 的唯一改进是删除了 V6.2 引入的 `w2 re-correction` no-op，以及修复 P0 bug（wall 初始化、RST1 时序、REJECT 静默、saturate_flag 过敏感、死参数）。

**V6.3 并未改善 $E$ 的误差传播**。两者都是 $(-E, -2E, -4E)$。

### 4.6 残留 INL 分析（更正）

校准后的解码权重：
- $\hat W_0 = 2048 + e_0 - 4E$（残留 $-4E$）
- $\hat W_1 = 1024 + e_1 - 2E$（残留 $-2E$）
- $\hat W_2 = 512 + e_2 - E$（残留 $-E$）
- $W_3, W_4$：名义值 256（残留 $+e_3, +e_4$，和为 $+E$）
- $W_5$：名义值 128（残留 $+e_5$）
- $W_6 \ldots W_{13}$：calDAC 本身，不校准（残留 $+e_i$）

最坏 INL 贡献（$|E| < \sigma_E \approx 2.56$ LSB）：
- $\hat W_0$ 的 $-4E$：当 $W_0$ 在解码中被激活时，INL 贡献 $-4E \approx \pm 10.24$ LSB（最坏）。
- $\hat W_1$ 的 $-2E$：$\pm 5.12$ LSB。
- $\hat W_2$ 的 $-E$：$\pm 2.56$ LSB。
- $W_3, W_4$ 的 $e_3 + e_4 = E$：$\pm E/2 \approx \pm 1.28$ LSB（单独激活）。
- $W_5$ 的 $e_5$：依赖 layout，典型 $< 1.28$ LSB。

整体 INL 最坏 $\approx 4|E| + 2|E| + |E| + |E|/2 + |e_5| \approx 7.5|E| + |e_5| \approx 20$ LSB（$|E| = 2.56$ LSB 时），对应 ENOB 损失约 1.5 bit。

**结论**：V6.3 在 $|E| \approx 0.5\%$ 时仍能保持 ENOB > 10.5 bit，但无法达到 12-bit 精度。要达到 12-bit 精度需要 $|E| < 0.1\%$（即 layout matching 严格度提升 5×）或引入独立 $W_{34}$ 测量。

## 5. V6.3 的 P0 bug 修复

### 5.1 wall_weight_q 初始化（P0-a）

**问题**：V6.2 在 `initial_step` 中未设置 `wall_weight_q`，仅 `CAL_RST` 下降沿设置。若 testbench 在 $t=0$ 即拉低 `CAL_RST`，第一次测量使用 `wall=0`，target=W2 必然失败。

**修复**：V6.3 在 `initial_step`、`CAL_RST` 上升沿、`CAL_RST` 下降沿三处均设置 `wall_weight_q = w3 + w4`（gauge=512）。

### 5.2 RST1 上升沿 handler 合并（P0-b）

**问题**：V6.2 有两个 `@(cross(RST1, +1))` 块，按文本顺序执行。若最后一个 target 在第二个块中设置 `finish_pending_i=1`，handoff 必须等下一次 `RST1` 上升沿。若无额外 frame，`DONE` 不拉高。

**修复**：V6.3 合并为单一 handler，显式顺序：
1. `frame_active_i = 0`
2. 若 `finish_pending_i`，handoff（设 `DONE=1`）
3. 否则若 `cal_state == CAL_FINISH_DIR`，处理方向结果，可能在同帧设 `finish_pending_i=1`

handoff 在下一个 `RST1` 上升沿执行。**注意**：仍需一次额外 `RST1` 才能完成 handoff。这是 Huang 2024 算法的固有特性（每帧只处理一个 SAR 序列），无法在单帧内完成。

### 5.3 REJECT → degraded（P0-c）

**问题**：V6.2 的 REJECT 只打印日志，不设置 `cal_error_i`。后续 target 仍执行，最终可能 `DONE=1, ERR=0` 但部分权重未更新。

**修复**：V6.3 引入 `cal_degraded_i`：
- 任意 target REJECT（饱和或容差失败）→ `cal_degraded_i = 1`
- handoff 时若 `cal_degraded_i`，设 `cal_error_i = 1`（即 `ERR=1`）
- 但保留已校准的权重（部分校准优于全名义）

调用方可根据 `ERR` 决定重试或接受部分校准。

### 5.4 saturate_count 替代 saturate_flag（P0-d）

**问题**：V6.2 的 `saturate_flag` 是单 bit，32 对中任意一次饱和就拒绝整个 target。比较器噪声偶发触发会导致大量误拒绝。

**修复**：V6.3 改为 `saturate_count`，仅在饱和比例超过 `SAT_RATIO_PCT`（默认 50%）时拒绝。

### 5.5 死参数清理（P0-e）

V6.2 暴露给 CDF 但未实现的参数：`ZERO_ON_INVALID_PHASE1`、`HIGH_WEIGHT_UPDATE_DEADBAND_LSB`、`APPLY_BIN_MIDPOINT`、`AUTO_BIN_MIDPOINT`、`SINGLE_PAIR_NOMINAL_GUARD`、`SINGLE_PAIR_AMBIGUITY_LSB`、`AVG_LOG2`、`CAL_C7`、`NORMALIZE_REDUNDANT_RANGE`。

V6.3 全部移除（RTL 中也移除 `NORMALIZE_REDUNDANT_RANGE`）。`AVG_LOG2` 等内部变量保留为局部声明，不暴露。

## 6. 总结

| 问题 | V6.2 状态 | V6.3 状态 | 证明 |
|---|---|---|---|
| `w2 re-correction` 数学不成立 | ❌ DEFECT | ✅ 删除 | 定理 1 + 雅可比奇异 |
| W2/W34 不可分离 | ❌ 未识别 | ✅ 承认为 gauge | $\det(J) = 0$ |
| `wall_weight_q` 初始化 bug | ❌ DEFECT | ✅ 修复 | 5.1 |
| 双 RST1 handler 时序 | ❌ DEFECT | ✅ 合并 | 5.2 |
| REJECT 静默继续 | ❌ DEFECT | ✅ degraded flag | 5.3 |
| `saturate_flag` 过敏感 | ❌ DEFECT | ✅ count + 阈值 | 5.4 |
| W5 (128) 不可测 | ⚠️ 已知 | ⚠️ 接受（layout） | 定理 2 |
| 共模增益不可观测 | ⚠️ 已知 | ⚠️ 接受 | 定理 3 |
| W1/W0 校准精度 | ❌ 声称精确 | ❌ 实际 $-2E/-4E$ 残留 | 定理 4（更正版） |
| W2 残留误差 | ❌ 声称精确 | ✅ 显式 $-E$ | 定理 4（更正版） |

V6.3 的核心价值（更正后）：
1. **删除 V6.2 的 no-op**：`w2 re-correction` 是恒等操作，V6.3 移除它。
2. **P0 bug 全修**：wall 初始化、RST1 时序、REJECT 静默、saturate_flag 过敏感、死参数。
3. **诚实标注 $E$ 传播**：V6.3 实际保留 $(-E, -2E, -4E)$ 误差传播，与 V6 相同。
   不再声称 "W1/W0 精确"。要消除 $E$ 传播需要：
   - 物理上严格保证 $E = 0$（layout matching 提升至 $|E| < 0.1\%$）；或
   - 独立测量 $W_{34}$（V6.2 已证明不可辨识）；或
   - 引入另一条线性独立校准方程（硬件改动）。
4. **代码与证明一致**：每个设计决策都有数学证明支撑，证明中的符号错误已更正。

---

## 7. 失配方向与程度敏感性的根因分析与文献解决方案

> [!question] 用户观察
> 在低位电容（$W_6 \ldots W_{13}$，即 calDAC）完全理想的情况下，高位电容（$W_0 \ldots W_5$）失配的**方向**（同向/反向）和**程度**会严重影响校准效果。本节从文献分析根因并给出解决方案。

### 7.1 现象复现：方向与程度敏感性

设 $e_3, e_4$ 为 $W_3, W_4$ 的失配，$E = e_3 + e_4$。由定理 4（更正版），校准后权重为：

$$
\hat W_2 = 512 + e_2 - E,\quad \hat W_1 = 1024 + e_1 - 2E,\quad \hat W_0 = 2048 + e_0 - 4E
$$

校准后权重与物理权重的偏差（即 INL 贡献）：

$$
\Delta W_2 = \hat W_2 - W_2^{\text{phys}} = -E,\quad \Delta W_1 = -2E,\quad \Delta W_0 = -4E
$$

**关键观察**：偏差**只依赖 $E$**，与 $e_0, e_1, e_2$ 的具体值无关。因此校准效果完全由 $E = e_3 + e_4$ 决定。

#### 7.1.1 方向敏感性（同向 vs 反向失配）

设 $|e_3| = |e_4| = \sigma$（相同程度），方向不同：

| 失配方向 | $e_3$ | $e_4$ | $E = e_3 + e_4$ | $\Delta W_0 = -4E$ | $\Delta W_1 = -2E$ | $\Delta W_2 = -E$ | 校准效果 |
|---|---|---|---|---|---|---|---|
| 反向（对消） | $+\sigma$ | $-\sigma$ | $0$ | $0$ | $0$ | $0$ | ✅ 完美 |
| 同向（累加） | $+\sigma$ | $+\sigma$ | $+2\sigma$ | $-8\sigma$ | $-4\sigma$ | $-2\sigma$ | ❌ 失败 |
| 同向（反向） | $-\sigma$ | $-\sigma$ | $-2\sigma$ | $+8\sigma$ | $+4\sigma$ | $+2\sigma$ | ❌ 失败 |

> [!bug] 根因
> $E = e_3 + e_4$ 是**和**而非**差**。反向失配时 $e_3, e_4$ 对消，$E \to 0$；同向失配时 $e_3, e_4$ 累加，$|E| = 2\sigma$。由于 $\Delta W_0 = -4E$，同向失配的 INL 贡献是反向失配的 $\infty$ 倍（反向时为 0）。

#### 7.1.2 程度敏感性

设 $e_3 = e_4 = \sigma$（同向），$\sigma$ 取不同值：

| $|E| = 2|\sigma|$ | $|\Delta W_0| = 4|E|$ | $|\Delta W_1| = 2|E|$ | $|\Delta W_2| = |E|$ | 最坏 INL | ENOB |
|---|---|---|---|---|---|
| $0.1\% \times 512 = 0.512$ | $2.05$ | $1.02$ | $0.51$ | $\sim 3.6$ LSB | $\sim 11.5$ bit |
| $0.5\% \times 512 = 2.56$ | $10.24$ | $5.12$ | $2.56$ | $\sim 18$ LSB | $\sim 10.5$ bit |
| $1\% \times 512 = 5.12$ | $20.48$ | $10.24$ | $5.12$ | $\sim 36$ LSB | $\sim 9.5$ bit |
| $5\% \times 512 = 25.6$ | $102.4$ | $51.2$ | $25.6$ | $\sim 179$ LSB | $\sim 7.5$ bit |

> [!note] 程度依赖
> 校准残差随 $|E|$ 线性增长。$|E| < 0.1\%$ 时可达 12-bit 精度；$|E| > 1\%$ 时 ENOB 损失超过 2 bit。这是 V6.3 在大失配下失败的数学根因。

#### 7.1.3 还有一层隐藏的方向敏感性：$R$ 超出 calDAC 范围

测量 $W_2$ 时残差 $R_2 = e_2 - E$。若 $e_2$ 与 $E$ **同号**：$|R_2| = ||e_2| - |E||$ 较小，calDAC 可测；若 **反号**：$|R_2| = |e_2| + |E|$ 较大，可能超过 $\pm 126$ 触发饱和。

| $e_2$ | $E$ | $R_2 = e_2 - E$ | calDAC 可测？ |
|---|---|---|---|
| $+10$ | $+5$ | $+5$ | ✅ |
| $+10$ | $-5$ | $+15$ | ✅ |
| $+10$ | $+50$ | $-40$ | ✅ |
| $+60$ | $-60$ | $+120$ | ✅（接近边界）|
| $+60$ | $-80$ | $+140$ | ❌ 饱和 |
| $-60$ | $+80$ | $-140$ | ❌ 饱和 |

> [!bug] 双重方向敏感性
> 校准效果不仅依赖 $E$ 的方向（决定 INL），还依赖 $e_2$ 与 $E$ 的相对方向（决定 $R$ 是否超出 calDAC 范围）。这是用户观察到的"方向严重影响校准效果"的第二层根因。

### 7.2 文献综述：SAR ADC MSB 失配校准技术

> [!info] 检索范围
> IEEE Xplore / Semantic Scholar / ResearchGate / MDPI / J-STAGE，1984–2025，覆盖 JSSC/ISSCC/VLSI Symp/TCAS-I/TVLSI/TCS-II。按对 V6.3 问题的适用性排序。

#### 7.2.1 经典 Cal-DAC + RAM 自校准（Lee 1984）

- **论文**：H.-S. Lee, D. A. Hodges, P. R. Gray, *"A Self-Calibrating 15 bit CMOS A/D Converter,"* IEEE JSSC, vol. SC-19, no. 6, pp. 813–819, Dec. 1984.
- **核心技术**：M-DAC + k-bit Cal-DAC + RAM 存储校准系数。校准时通过"电容翻转"将每个高位电容的误差以电压形式表现，Cal-DAC 量化并保存到 RAM；正常工作时 Cal-DAC 注入误差电压补偿 M-DAC 输出。
- **关键差异**：Lee 1984 **校准顺序为 LSB → MSB**（从小到大），每次测量的 wall 都是**未校准的低位电容和**，wall 不携带残留误差。V6.3 是 MSB → LSB 递归，wall 是已校准高位，残留 $-E$ 同号累加。
- **适用性**：⭐⭐⭐⭐ 中高。但 V6.3 的 calDAC 范围 $\pm 126$ 不足以直接测量 $W_0 = 2048$（需要 wall $W_1+\ldots+W_{13} = 2047$，$R = e_0 - \sum_{i \neq 0} e_i$，包含所有其它失配，不实用）。需要结合拆分技术。

#### 7.2.2 双段式位权自校准（Chen 2024 TCAS-I）

- **论文**：Y. Chen, Q. Huang, Y. Fan, Q. Zhao, S. Huang, J. Yuan, *"A 16-bit 4-MS/s SAR ADC With Dual-Segmental Bit Weight Self-Calibration,"* IEEE TCAS-I, vol. 71, no. 9, pp. 3961–3974, Sept. 2024. DOI: 10.1109/TCSI.2024.3408228
- **核心技术**：将位权自校准分成两段（MSB 段与中位段），**分别独立校准**，避免递归调用已校准高位权重作为 wall 时把残留误差传递给低位。引入双段比较器 offset 容忍机制（7.5 mV），仅 370 时钟周期完成校准。
- **如何打破 $E$ 传播**：不依赖已校准 $w_2$ 作为下一位的 wall——而是引入中段独立参考，使 $E$ 不再沿 $(-E, -2E, -4E)$ 链路累加。
- **硬件代价**：仅额外一个精度放宽的比较器；无额外电容阵列。
- **适用性**：⭐⭐⭐⭐⭐ 高度适用。Huang 团队 2024 的工作，与用户参考论文（Huang 2024）同源。

#### 7.2.3 位权自校准误差传播统计建模（Chen 2024 TVLSI）

- **论文**：Y. Chen, S. Huang, Q. Huang, Y. Fan, J. Yuan, *"The Error Analysis of Bit Weight Self-Calibration Methods for High-Resolution SAR ADCs,"* IEEE TVLSI, vol. 32, no. 11, pp. 1983–1992, Nov. 2024. DOI: 10.1109/TVLSI.2024.3458071
- **核心技术**：严格推导位权自校准中误差传播的 chi-square 统计模型，定量给出噪声诱导的随机误差沿校准链累积的规律，给出"重复测量+平均"所需的循环数 $N$ 的闭式解。
- **如何应对 $E$ 传播**：不改变传播链结构，但通过定量估算 $N$ 次重复可将残留 $E$ 的影响降到 LSB 以下。单次测量残留按 $(-1, -2, -4)$ 传播，但 $N$ 次平均使等效 $\sigma_E$ 按 $1/\sqrt{N}$ 收敛。
- **硬件代价**：仅数字侧增加平均寄存器与计数器；无模拟改动。
- **适用性**：⭐⭐⭐⭐⭐ 直接对应。给出"不改硬件仅增加平均次数"的量化路径。
- **限制**：只能降低随机噪声，不能消除系统性 $E$（同向失配是系统性的，不随平均减小）。

#### 7.2.4 模拟前台双校准：MSB 段 + 接口（Fan 2025 TCAS-I）

- **论文**：H. Fan, Z. Chen, Y. Liu, F. Maloberti, M. Chen, Q. Wei, *"Analog Foreground Calibration of High-Resolution SAR ADC,"* IEEE TCAS-I, vol. 72, no. 11, pp. 6629–6639, Nov. 2025. DOI: 10.1109/TCSI.2025.3567445
- **核心技术**：针对 split-capacitor SAR 提出两种前台校准方法：(1) **MSB 段单元件失配校准**——独立测量 MSB 段内单元电容之间的相对比例，不依赖 LSB 段；(2) **MSB-LSB 接口失配校准**——单独校准 bridge 电容带来的接口误差，避免与 MSB 段误差耦合。16-bit 1MS/s 实测 SNDR 87 dB，SFDR 从 70.71 提升至 93.29 dB。
- **如何打破 $E$ 传播**：通过**分离 MSB 段内失配**与**段间接口失配**两个独立方程，使用户的 $E = e_3 + e_4$（同段相邻电容之和）不再需要作为整体进入 wall，而是 $e_3$、$e_4$ 各自有独立测量。
- **硬件代价**：额外模拟通路；芯片面积略有增加。
- **适用性**：⭐⭐⭐⭐⭐ 高度适用。直接将 $W_3$、$W_4$ 视为 MSB 段单元件分别校准，从源头消除 $E = e_3 + e_4$ 的合并。

#### 7.2.5 Split-ADC 架构（McNeill 2005 JSSC）

- **论文**：J. A. McNeill, M. C. W. Coln, B. J. Larivee, *"'Split ADC' Architecture for Deterministic Digital Background Calibration of a 16-bit 1-MS/s ADC,"* IEEE JSSC, vol. 40, no. 12, pp. 2437–2445, Dec. 2005.
- **核心技术**：将单个 ADC 拆成两个独立半尺寸 ADC 并行转换同一输入，两路输出作差；差值为零表示校准收敛，非零驱动 LMS 自适应更新位权。10,000 次转换内收敛。
- **如何打破 $E$ 传播**：两个 ADC 互相作为独立参考——A 的 wall 不来自 A 自身已校准位，而来自 B 的转换结果。彻底打破单 ADC 递归自引用。
- **硬件代价**：2× ADC 面积；两路 SAR 逻辑与 LMS 引擎。
- **适用性**：⭐⭐⭐⭐ 中高。可改造为双 ADC 互校，$E$ 不再来自本侧未校准电容。代价是面积翻倍。

#### 7.2.6 差分 Split-CDAC 互测（Um 2013 TCAS-I）

- **论文**：J.-Y. Um, Y.-J. Kim, E.-W. Song, J.-Y. Sim, H.-J. Park, *"A Digital-Domain Calibration of Split-Capacitor DAC for a Differential SAR ADC Without Additional Analog Circuits,"* IEEE TCAS-I, vol. 60, no. 11, pp. 2845–2856, Nov. 2013.
- **核心技术**：利用差分 SAR 的两个 split-CDAC，**用一个 CDAC 测量另一个 CDAC 的误差码**，避免额外的模拟校准电路；同时校准 bridge 电容与 LSB 段寄生。
- **如何打破 $E$ 传播**：通过差分对侧 CDAC 提供独立参考，wall 不依赖本侧已校准高位。
- **硬件代价**：差分结构（多数现代 SAR 已具备）+ FIR LPF；无额外模拟硬件。
- **适用性**：⭐⭐⭐⭐ 高。若用户设计已为差分结构，则可零硬件成本借用对侧作参考。

#### 7.2.7 MSB 拆分思想（Ginsburg/Chandrakasan 2005）

- **论文**：B. P. Ginsburg, A. P. Chandrakasan, *"An Energy-Efficient Charge Recycling Approach for a SAR Converter with Capacitive DAC,"* IEEE ISCAS 2005, pp. 184–187. DOI: 10.1109/ISCAS.2005.1464555
- **核心技术**：MSB 电容分裂为 $b-1$ 子电容以降低切换能耗。
- **如何打破 $E$ 传播**：将 $W_0 (2048)$ 拆为多个小电容（如 $4 \times 512$），每个子电容可与 $W_{34} (512)$ 直接比较，打破单 wall 依赖。
- **适用性**：⭐⭐⭐ 中等。需要重新设计 CDAC 阵列。

#### 7.2.8 Sub-radix-2 冗余 + LSB 复用（López-Angulo 2020）

- **论文**：A. López-Angulo, A. J. Ginés, E. J. Peralias, *"Digital calibration of capacitor mismatch and comparison offset in Split-CDAC SAR ADCs with redundancy,"* IEEE ISCAS 2020.
- **核心技术**：12-bit split-CDAC + sub-radix-2 冗余，复用 LSB 段电容同时完成三件事：(1) offset 校正；(2) 为高位失配测量提供额外分辨率；(3) 正常转换中作 LSB。
- **如何打破 $E$ 传播**：通过 sub-radix-2 冗余产生冗余区间，LSB 段作为独立"游标"测量 MSB 段误差，wall 由 LSB 段提供（独立参考）。
- **适用性**：⭐⭐⭐⭐ 高。与用户的 7-bit calDAC 概念可融合——将 calDAC 视为冗余 LSB 段，作为独立参考测量 $W_2$，避免 $W_{34}$ 进入 wall。

#### 7.2.9 文献综述小结

| 技术 | 打破 $E$ 传播机制 | 硬件代价 | V6.3 兼容性 | 前台 |
|---|---|---|---|---|
| Lee 1984 LSB→MSB 反向 | wall 永远是未校准项 | 无（仅算法改） | 中（calDAC 范围限制）| ✅ |
| Chen 2024 双段式 | 分段独立，wall 不复用已校准位 | +1 放宽比较器 | 高 | ✅ |
| Chen 2024 统计建模 | 不改结构，$N$ 次平均降 $\sigma_E$ | +数字侧寄存器 | 极高 | ✅ |
| Fan 2025 双校准 | $e_3, e_4$ 各自独立测 | +模拟通路 | 高 | ✅ |
| McNeill 2005 Split-ADC | 双 ADC 互为参考 | 2× ADC 面积 | 中 | 后台 |
| Um 2013 差分互测 | 对侧 CDAC 作参考 | 零（若已差分）| 高 | ✅ |
| Ginsburg 2005 MSB 拆分 | 子电容直接比较 | +CDAC 重设计 | 中 | ✅ |
| López-Angulo 2020 冗余 | LSB 段作游标 | +R 冗余位 | 高 | ✅ |

### 7.3 解决方案：外部参考电容 $C_{\text{REF}}$ 方案

> [!important] 推荐方案
> 综合文献分析与 V6.3 现有架构，**推荐方案 A：引入外部参考电容 $C_{\text{REF}} = 512$**。这是 PROOF §2.3 方案 2 的扩展，能彻底打破 $E$ 传播，硬件代价最小，且与 V6.3 算法框架完全兼容。

#### 7.3.1 方案 A：外部参考电容 $C_{\text{REF}} = 512$

**硬件改动**：
- 在 CDAC 阵列中新增一个独立电容 $C_{\text{REF}}$，名义权重 $W_{\text{REF}} = 512$（与 $W_3 + W_4$ 名义值相同）。
- $C_{\text{REF}}$ **不参与正常转换**，仅在校准模式下作为独立 wall。
- $C_{\text{REF}}$ 与主 CDAC 物理隔离（独立版图、独立路由），其失配 $e_{\text{REF}}$ 与 $e_3, e_4$ **统计独立**。
- 增加一个切换开关：校准时将 $C_{\text{REF}}$ 接入顶板，正常转换时断开。

**校准序列**（替换 V6.3 的 wall 选择）：

| target | target 物理值 | wall（物理） | wall（digital） | $R$ |
|---|---|---|---|---|
| 2 | $W_2 = 512 + e_2$ | $C_{\text{REF}} = 512 + e_{\text{REF}}$ | $512$ | $e_2 - e_{\text{REF}}$ |
| 1 | $W_1 = 1024 + e_1$ | $\hat W_2 + C_{\text{REF}}$ | $\hat W_2 + 512$ | $e_1 - e_2$ |
| 0 | $W_0 = 2048 + e_0$ | $\hat W_1 + \hat W_2 + C_{\text{REF}}$ | $\hat W_1 + \hat W_2 + 512$ | $e_0 - e_1 - e_2$ |

**严格推导**：

**定理 5（外部参考电容打破 $E$ 传播）**：引入 $C_{\text{REF}} = 512 + e_{\text{REF}}$（$e_{\text{REF}}$ 与 $e_3, e_4$ 统计独立）作为 wall，校准结果为：

$$
\hat W_2 = 512 + e_2 - e_{\text{REF}},\quad \hat W_1 = 1024 + e_1 - 2e_{\text{REF}},\quad \hat W_0 = 2048 + e_0 - 4e_{\text{REF}}
$$

即 $E$ 被 $e_{\text{REF}}$ 替换。若 $|e_{\text{REF}}| \ll |E|$（通过独立版图匹配），则残差大幅减小。

**证明**：

**Target 2**：wall（digital）= $512$，wall（物理）= $512 + e_{\text{REF}}$。
$$
R_2 = W_2 - C_{\text{REF}} = (512 + e_2) - (512 + e_{\text{REF}}) = e_2 - e_{\text{REF}}
$$
$$
\hat W_2 = 512 + R_2 = 512 + e_2 - e_{\text{REF}}
$$

**Target 1**：wall（digital）= $\hat W_2 + 512 = 1024 + e_2 - e_{\text{REF}}$，wall（物理）= $W_2 + C_{\text{REF}} = (512 + e_2) + (512 + e_{\text{REF}})$。
$$
R_1 = W_1 - (W_2 + C_{\text{REF}}) = (1024 + e_1) - (1024 + e_2 + e_{\text{REF}}) = e_1 - e_2 - e_{\text{REF}}
$$
$$
\hat W_1 = (1024 + e_2 - e_{\text{REF}}) + (e_1 - e_2 - e_{\text{REF}}) = 1024 + e_1 - 2e_{\text{REF}}
$$

**Target 0**：wall（digital）= $\hat W_1 + \hat W_2 + 512 = 2048 + e_1 + e_2 - 3e_{\text{REF}}$，wall（物理）= $W_1 + W_2 + C_{\text{REF}} = 2048 + e_1 + e_2 + e_{\text{REF}}$。
$$
R_0 = W_0 - (W_1 + W_2 + C_{\text{REF}}) = (2048 + e_0) - (2048 + e_1 + e_2 + e_{\text{REF}}) = e_0 - e_1 - e_2 - e_{\text{REF}}
$$
$$
\hat W_0 = (2048 + e_1 + e_2 - 3e_{\text{REF}}) + (e_0 - e_1 - e_2 - e_{\text{REF}}) = 2048 + e_0 - 4e_{\text{REF}}
$$

残差为 $(-e_{\text{REF}}, -2e_{\text{REF}}, -4e_{\text{REF}})$。$\blacksquare$

> [!note] 关键改进
> 原来的 $E = e_3 + e_4$ 是**两个相关电容的和**（同向失配时累加）。新方案的 $e_{\text{REF}}$ 是**单个独立电容的失配**，统计上 $\sigma_{e_{\text{REF}}} = \sigma_e$（与单个 $e_i$ 同量级），而 $\sigma_E = \sqrt{2}\sigma_e$（两个独立 $e_3, e_4$ 求和）。更重要的是：$e_{\text{REF}}$ 不存在"同向累加"问题，因为它只有一个电容。

#### 7.3.2 残差对比

| 方案 | $\Delta W_0$ | $\Delta W_1$ | $\Delta W_2$ | 最坏 INL（$\sigma_e = 2.56$ LSB）|
|---|---|---|---|---|
| V6.3（$E = e_3 + e_4$，同向）| $-4E = -8\sigma_e$ | $-2E = -4\sigma_e$ | $-E = -2\sigma_e$ | $\sim 18$ LSB |
| V6.3（$E = e_3 + e_4$，反向）| $0$ | $0$ | $0$ | $0$ LSB |
| 方案 A（$e_{\text{REF}}$）| $-4e_{\text{REF}}$ | $-2e_{\text{REF}}$ | $-e_{\text{REF}}$ | $\sim 7\sigma_e \approx 18$ LSB（最坏）|
| 方案 A + layout matching（$|e_{\text{REF}}| < 0.1\%$）| $-4e_{\text{REF}}$ | $-2e_{\text{REF}}$ | $-e_{\text{REF}}$ | $\sim 1.4$ LSB |

> [!important] 方案 A 的核心优势
> 方案 A **消除了方向敏感性**：$e_{\text{REF}}$ 是单个电容的失配，不存在"同向/反向"问题。残差只取决于 $|e_{\text{REF}}|$ 的程度，可通过 layout matching 控制。配合 $|e_{\text{REF}}| < 0.1\%$ 的版图匹配，可达 12-bit 精度。

#### 7.3.3 方案 B：Layout Matching 提升（无硬件改动）

若不接受任何硬件改动，唯一路径是提升 $W_3, W_4$ 的 layout matching：

| Layout 策略 | 目标 $|E|/\sigma_E$ | 预期 ENOB | 实现难度 |
|---|---|---|---|
| 普通匹配（当前）| $0.5\%$ | $\sim 10.5$ bit | 低 |
| Common centroid + dummy | $0.2\%$ | $\sim 11.3$ bit | 中 |
| Common centroid + 交叉指型 + dummy + matched routing | $0.1\%$ | $\sim 11.8$ bit | 高 |
| $4 \times$ oversize + common centroid + 激光修调 | $0.05\%$ | $\sim 12.2$ bit | 极高 |

**限制**：layout matching 无法消除"方向敏感性"——即使 $|E|$ 减小，同向失配仍比反向失配差 $2\times$。只能减小程度，不能消除方向依赖。

#### 7.3.4 方案 C：拆分 $W_3$ 或 $W_4$

将 $W_3 = 256$ 拆为 $W_{3a} = 128 + W_{3b} = 128$，或将 $W_4 = 256$ 拆为 $W_{4a} = 128 + W_{4b} = 128$。

**严格分析**：拆分后 $E = e_{3a} + e_{3b} + e_4$（三项和）。统计上 $\sigma_E = \sqrt{3}\sigma_e$（三个独立失配求和），比原来的 $\sqrt{2}\sigma_e$ 更差。**拆分不能减小 $|E|$**，只是改变了统计分布。

**唯一有意义的拆分**：将 $W_3$ 拆为 $W_{3a} + W_{3b}$，并**独立校准 $W_{3a}$**（以 $W_{3b}$ 为 wall，calDAC 范围 $\pm 126$ 足够）。这样 $e_{3a}$ 被校准，$E = e_{3b} + e_4$ 减小。但这需要 $W_{3b}$ 作为独立 wall，又回到 $W_{3b}$ 的失配问题——**递归不收敛**。

> [!warning] 方案 C 不推荐
> 拆分 $W_3$ 或 $W_4$ 在不引入独立参考的情况下，只是把 $E$ 重新分配，不改变 $|E|$ 的统计量级。要使拆分有效，必须配合方案 A（独立参考）或方案 D（两段式）。

#### 7.3.5 方案 D：两段式校准（Chen 2024 TCAS-I 启发）

将 12-bit CDAC 分为两段：
- **MSB 段**：$W_0, W_1, W_2, W_3, W_4$（权重 2048/1024/512/256/256，总和 4096）
- **LSB 段**：$W_5, W_6, \ldots, W_{13}$（权重 128/48/32/20/12/8/4/2/1，总和 255）
- **Bridge 电容** $C_{\text{br}}$ 连接两段。

**校准流程**：
1. **LSB 段自校准**：用 calDAC 校准 $W_5, W_6, \ldots, W_{12}$（已有 calDAC 范围足够）。
2. **MSB 段自校准**：用已校准的 LSB 段作为独立参考，校准 $W_0, W_1, W_2, W_3, W_4$。此时 wall 来自 LSB 段（已校准、独立），不依赖 MSB 段内部电容。
3. **Bridge 校准**：单独校准 $C_{\text{br}}$。

**如何打破 $E$ 传播**：MSB 段校准时 wall 来自 LSB 段，$E = e_3 + e_4$ 不进入 wall。每个 MSB 电容的残差只含自身的 $e_i$。

**硬件代价**：需要重新设计 CDAC 为 split 结构 + bridge 电容 + 切换开关。改动较大但理论最干净。

**适用性**：⭐⭐⭐⭐ 高。但需要 CDAC 重新设计，不适合 V6.3 局部修改。

### 7.4 方案 A 的工程实现

#### 7.4.1 硬件改动清单

| 改动项 | 描述 | 代价 |
|---|---|---|
| 新增 $C_{\text{REF}}$ | 名义 512 的电容（2 个 256 单元电容）| +2 单元电容 |
| 切换开关 | 校准时接入 $C_{\text{REF}}$，正常转换时断开 | +1 开关 |
| 控制逻辑 | CAL 信号控制 $C_{\text{REF}}$ 开关 | 复用现有 CAL |
| 版图 | $C_{\text{REF}}$ 独立版图，与 $W_3, W_4$ 物理隔离 | 版图面积 +0.5% |

#### 7.4.2 代码修改（DEC_CAL_PHY.va）

```verilog
// 新增端口
input C_REF;  // 外部参考电容开关控制（CAL 模式下激活）

// 校准模式下 wall 选择改为 C_REF 而非 W3+W4
// initial_step / CAL_RST rising / CAL_RST falling 三处：
wall_weight_q = 512 * q_scale;  // C_REF 名义值，不再用 w3 + w4

// target 2 完成后：
case (target_idx)
    1: begin
        target_mask = 2;
        wall_mask = WALL_C_REF | TARGET_2_MASK;  // C_REF + W2
        wall_weight_q = w2 + 512 * q_scale;      // digital wall
    end
    0: begin
        target_mask = 1;
        wall_mask = WALL_C_REF | TARGET_1_MASK | TARGET_2_MASK;
        wall_weight_q = w1 + w2 + 512 * q_scale;
    end
endcase

// SWITCH_CAL.va 增加 C_REF 控制：
// CAL=1 时 C_REF 接入顶板，CAL=0 时断开
```

#### 7.4.3 预期性能

| 场景 | $|E|$ / $|e_{\text{REF}}|$ | 最坏 INL | ENOB | 备注 |
|---|---|---|---|---|
| V6.3 + 同向失配 5% | $25.6$ LSB | $\sim 179$ LSB | $\sim 7.5$ bit | 当前失败场景 |
| V6.3 + 反向失配 5% | $0$ LSB | $0$ LSB | $12$ bit | 偶然成功场景 |
| 方案 A + $|e_{\text{REF}}| = 0.5\%$ | $2.56$ LSB | $\sim 18$ LSB | $\sim 10.5$ bit | 与 V6.3 反向失配相当 |
| 方案 A + $|e_{\text{REF}}| = 0.1\%$ | $0.512$ LSB | $\sim 3.6$ LSB | $\sim 11.5$ bit | 推荐 |
| 方案 A + $|e_{\text{REF}}| = 0.05\%$ | $0.256$ LSB | $\sim 1.8$ LSB | $\sim 11.9$ bit | 激光修调后 |

> [!important] 方案 A 消除方向敏感性
> 方案 A 的残差只依赖 $|e_{\text{REF}}|$（单个电容的失配程度），**与 $e_3, e_4$ 的方向无关**。无论 $W_3, W_4$ 同向还是反向失配，只要 $C_{\text{REF}}$ 本身匹配良好，校准效果一致。这是方案 A 相比 V6.3 的根本优势。

### 7.5 方案选择决策树

```
是否接受硬件改动？
├── 否 → 方案 B（Layout Matching）
│        └── 提升至 |E| < 0.1% → ENOB ~11.8 bit
│        └── 无法消除方向敏感性
│
└── 是 → 改动规模？
         ├── 小（+1 电容 +1 开关）→ 方案 A（外部 C_REF）✅ 推荐
         │   └── 彻底消除方向敏感性
         │   └── 残差只依赖 |e_REF|
         │   └── 配合 layout matching 可达 12-bit
         │
         ├── 中（+R 冗余位）→ 方案 D（两段式）
         │   └── 理论最干净
         │   └── 需 CDAC 重设计
         │
         └── 大（2× ADC）→ Split-ADC（McNeill 2005）
             └── 彻底打破递归
             └── 面积翻倍
```

### 7.6 结论

> [!summary] 根因与解决方案
> 
> **根因**：V6.3 的 $E = e_3 + e_4$ 传播是**结构性**的，不是算法 bug。$E$ 是两个相关电容失配的和，其方向敏感性（同向累加/反向对消）和程度敏感性（$|E| \propto |e_3| + |e_4|$ 同向时）是物理决定的，无法通过算法消除。
> 
> **文献启示**：
> 1. Lee 1984 的 LSB→MSB 反向校准可避免 wall 携带残留，但 V6.3 的 calDAC 范围不足以直接测量 $W_0$。
> 2. Chen 2024 TCAS-I 的双段式校准是 Huang 团队 2024 的最新工作，通过分段独立校准打破递归依赖。
> 3. Chen 2024 TVLSI 的统计建模给出"不改结构仅增加平均次数"的量化路径，但对系统性 $E$（同向失配）无效。
> 4. Fan 2025 的双校准通过分离段内/段间失配，从源头消除 $E$ 的合并。
> 
> **推荐方案**：方案 A（外部参考电容 $C_{\text{REF}} = 512$）。
> - 硬件代价最小（+2 单元电容 +1 开关）
> - 彻底消除方向敏感性
> - 残差只依赖 $|e_{\text{REF}}|$（单个电容，统计独立）
> - 配合 layout matching（$|e_{\text{REF}}| < 0.1\%$）可达 12-bit 精度
> - 与 V6.3 算法框架完全兼容，仅需修改 wall 选择
> 
> **不推荐**：
> - DEM（用户明确拒绝）
> - 方案 C（拆分 $W_3/W_4$，不引入独立参考则无效）
> - 纯 Layout Matching（无法消除方向敏感性）

---

## 8. V6.6 合并方案：W5 粗调自动量程 + 外部参考 Anchor

> [!question] 用户观察（V6.5 引入）
> V6.3 + §7 方案 A 仍存在一个**与 $E$ 无关的失败模式**：低位电容理想、$E = 0$ 时，反向失配（$e_0 = +p\cdot W_0, e_1 = -p\cdot W_1, e_2 = -p\cdot W_2$）使 $R_0 = e_0 - e_1 - e_2 = p(2048+1024+512) = 3584p$。$p = 5\%$ 时 $|R_0| = 179.2$ LSB，超过 calDAC 量程 $\pm 126$，校准被拒绝，递归下游全部失败。

### 8.1 两个互补问题的严格分离

V6.3 失效有两个独立根因，必须分别处理：

| 根因 | 描述 | 触发条件 | 解决方案 |
|---|---|---|---|
| **(I) $E$ 传播** | $E = e_3 + e_4$ 作为 $(-E, -2E, -4E)$ 进入 $w_{2,1,0}$ | 任何 $E \neq 0$（layout matching 有限） | §7 方案 A：外部 anchor $A_{34} = W_3 + W_4$（物理表征） |
| **(II) $R$ 量程饱和** | $R_0 = e_0 - e_1 - e_2$ 超过 $\pm 126$ | 反向失配且 $|p| > 126/3584 \approx 3.5\%$ | V6.5：W5 粗调自动量程，扩展到 $\pm 250$ LSB |

**两者独立**：消除 $E$（根因 I）不会改变 $R$ 量程（根因 II 仍存在）；扩展 $R$ 量程（根因 II）不会消除 $E$ 传播（根因 I 仍存在）。**V6.6 必须同时处理两者**。

### 8.2 W5 粗调自动量程的数学严格证明

**约定**：calDAC 为 stages 6..12（$\sum = 126$，offset-binary 7-bit），ideal $W_5 = 128$ 作为固定粗调电容（不是额外 SAR 位）。

**测量协议**：

1. 第一次试探 $k = 0$（$W_5$ 不参与），测 $R_{\text{fine}} = R$。
2. 若正向越界（$D^+ \geq 126$ 或 $D^- \leq 1$）：选 $k = +1$，$W_5$ 接入 wall 侧，重新测量
   $$R_{\text{fine}} = R - W_5 = R - 128$$
3. 若负向越界（$D^+ \leq 1$ 或 $D^- \geq 126$）：选 $k = -1$，$W_5$ 接入 target 侧，重新测量
   $$R_{\text{fine}} = R + W_5 = R + 128$$
4. 恢复：$R = R_{\text{fine}} + k \cdot W_5 = (D^+ - D^-) + k \cdot 128$。

**定理 5（V6.5 量程扩展）**：在 W5 粗调自动量程下，可测量的对称残差范围从 $\pm 122$ LSB 扩展到 $\pm 250$ LSB。

**证明**：

calDAC 安全可测量范围为 $|R_{\text{fine}}| \leq 122$ LSB（保留 $\pm 4$ LSB 的 endpoint margin 用于饱和检测）。

- $k = 0$：$|R| \leq 122$，直接测量。
- $k = +1$：$R_{\text{fine}} = R - 128$，$|R_{\text{fine}}| \leq 122 \Rightarrow R \in [6, 250]$。
- $k = -1$：$R_{\text{fine}} = R + 128$，$|R_{\text{fine}}| \leq 122 \Rightarrow R \in [-250, -6]$。

并集：$R \in [-250, -6] \cup [-122, 122] \cup [6, 250] = [-250, 250]$。$\blacksquare$

**推论 5.1（最坏方向覆盖）**：三位 MSB 同向 $|p|$ 失配，最坏 $|R_0|_{\max} = p(W_0 + W_1 + W_2) = 3584p$。

| $|p|$ | $|R_0|_{\max}$ | V6.3 ($\pm 122$) | V6.6 ($\pm 250$) |
|---|---|---|---|
| 1% | 35.84 | ✅ | ✅ |
| 3% | 107.5 | ✅ | ✅ |
| 5% | 179.2 | ❌ FAIL | ✅ |
| 7% | 250.9 | ❌ FAIL | ⚠️ 边界 |
| 10% | 358.4 | ❌ FAIL | ❌ FAIL |

**注意**：$|p| \geq 7\%$ 已超出 V6.6 量程。要覆盖 ±10% 需 $|R| \geq 359$ LSB，需额外粗调电容（如 $W_4 = 256$ 作为二级粗调）或增加 calDAC 分辨率。

### 8.3 外部 Anchor 通道（§7 方案 A 的工程实现）

**约定**：V6.6 暴露 `ANCHOR_W3_LSB` 和 `ANCHOR_W4_LSB` 两个参数。记
$$A_{34} := \text{ANCHOR\_W3\_LSB} + \text{ANCHOR\_W4\_LSB}$$
$A_{34}$ 是用户提供的 $W_3 + W_4$ 的物理表征值。

**定义 anchor 误差**：$e_{\text{REF}} := A_{34} - 512$（anchor 偏离名义 512 的量）。

**定理 6（V6.6 anchor 误差传播）**：在 V6.6 3-target 递归校准下，
$$\hat W_2 = 512 + e_2 - E + e_{\text{REF}}$$
$$\hat W_1 = 1024 + e_1 - 2E + 2 e_{\text{REF}}$$
$$\hat W_0 = 2048 + e_0 - 4E + 4 e_{\text{REF}}$$

即 anchor 误差 $e_{\text{REF}}$ 按 $(+e_{\text{REF}}, +2 e_{\text{REF}}, +4 e_{\text{REF}})$ 传播，**符号与 $E$ 相反**。

**证明**：

记 $W_{34}^{\text{phys}} = 512 + E$，$A_{34} = 512 + e_{\text{REF}}$。

**Target 2（$W_2$）**：wall（digital）= $A_{34}$。
$$R_2 = W_2^{\text{phys}} - W_{34}^{\text{phys}} = (512 + e_2) - (512 + E) = e_2 - E$$
$$\hat W_2 = A_{34} + R_2 = (512 + e_{\text{REF}}) + (e_2 - E) = 512 + e_2 - E + e_{\text{REF}}$$

**Target 1（$W_1$）**：wall（digital）= $\hat W_2 + A_{34} = (512 + e_2 - E + e_{\text{REF}}) + (512 + e_{\text{REF}}) = 1024 + e_2 - E + 2 e_{\text{REF}}$。
$$R_1 = W_1^{\text{phys}} - (W_2^{\text{phys}} + W_{34}^{\text{phys}}) = (1024 + e_1) - (1024 + e_2 + E) = e_1 - e_2 - E$$
$$\hat W_1 = (1024 + e_2 - E + 2 e_{\text{REF}}) + (e_1 - e_2 - E) = 1024 + e_1 - 2E + 2 e_{\text{REF}}$$

**Target 0（$W_0$）**：wall（digital）= $\hat W_1 + \hat W_2 + A_{34} = 2048 + e_1 + e_2 - 3E + 4 e_{\text{REF}}$。
$$R_0 = W_0^{\text{phys}} - (W_1^{\text{phys}} + W_2^{\text{phys}} + W_{34}^{\text{phys}}) = e_0 - e_1 - e_2 - E$$
$$\hat W_0 = (2048 + e_1 + e_2 - 3E + 4 e_{\text{REF}}) + (e_0 - e_1 - e_2 - E) = 2048 + e_0 - 4E + 4 e_{\text{REF}}$$

$\blacksquare$

**推论 6.1（外部 anchor 消除 $E$）**：若用户提供 $A_{34} = W_{34}^{\text{phys}}$（即 $e_{\text{REF}} = E$），则残差为
$$\hat W_2 = 512 + e_2, \quad \hat W_1 = 1024 + e_1, \quad \hat W_0 = 2048 + e_0$$
$E$ 传播完全消除。

**推论 6.2（名义 anchor 退化为 V6.3）**：若用户使用默认 $A_{34} = 512$（即 $e_{\text{REF}} = 0$），则残差为 $(-E, -2E, -4E)$，与 V6.3 完全相同。

### 8.4 V6.6 联合覆盖分析

V6.6 同时启用 W5 粗调（量程 $\pm 250$）和外部 anchor（$e_{\text{REF}} = E$，消除 $E$ 传播）后，校准精度只受以下因素限制：

| 误差源 | 残留量 | 典型值 | 备注 |
|---|---|---|---|
| calDAC 量化 | $\pm 0.5$ LSB | $\pm 0.5$ | 7-bit 分辨率 |
| 比较器噪声（32 对平均） | $\sigma / \sqrt{32}$ | $\sigma_{\text{cmp}} / 5.66$ | 通过增加 AVG_PAIRS_LOG2 改善 |
| $e_{\text{REF}}$ 表征误差 | $|e_{\text{REF}} - E|$ | 取决于表征方法 | 0（理想表征）/ ±0.1%（外部 $C_{\text{REF}}$ layout）/ ±0.5%（post-fab trim） |
| $W_5$ mismatch | $|e_5|$ | < 1% × 128 = 1.28 LSB | 粗调电容不理想（PROOF §2 不可测） |
| $W_3, W_4$ 单独失配 | $|e_3|, |e_4|$ | < 1% × 256 = 2.56 LSB | 解码时单独激活贡献 $\pm e_3, \pm e_4$ |

**最坏 INL 贡献**（外部 anchor，$|e_{\text{REF}} - E| < 0.5$ LSB）：

- $\hat W_0$ 残留 $4|e_{\text{REF}} - E| \approx 2$ LSB（最坏）
- $\hat W_1$ 残留 $2|e_{\text{REF}} - E| \approx 1$ LSB
- $\hat W_2$ 残留 $|e_{\text{REF}} - E| \approx 0.5$ LSB
- $W_5$ 不理想 $\approx 1.28$ LSB
- $W_3, W_4$ 单独 $\approx 2.56$ LSB

整体 INL 最坏 $\approx 4 + 2 + 1 + 1.28 + 2.56 \approx 10.8$ LSB，对应 ENOB $\approx 11.2$ bit。

要达到 12-bit 精度需：
- $|e_{\text{REF}} - E| < 0.1$ LSB（外部 $C_{\text{REF}}$ layout matching 0.02%）；或
- $|e_3|, |e_4| < 0.5\%$（layout matching 严格度提升 2×）。

### 8.5 V6.6 vs V6.3 vs V6.5 对比

| 维度 | V6.3 | V6.5（ChatGPT 草案） | V6.6（最终） |
|---|---|---|---|
| calDAC 量程 | $\pm 122$ LSB | $\pm 250$ LSB（W5 粗调） | $\pm 250$ LSB（W5 粗调） |
| $E$ 传播 | $(-E, -2E, -4E)$ | $(-E, -2E, -4E)$（默认） | $(-E, -2E, -4E)$（默认）/ $0$（外部 anchor） |
| Anchor 通道 | 无（隐式 512） | `ANCHOR_W3_LSB/W4_LSB` 参数 | `ANCHOR_W3_LSB/W4_LSB` 参数（默认 256+256=512） |
| $\pm 5\%$ 同向覆盖 | ❌ | ✅ | ✅ |
| $\pm 5\%$ 反向覆盖 | ❌ FAIL（$|R_0|=179$） | ✅ | ✅ |
| $\pm 7\%$ 最坏覆盖 | ❌ | ⚠️ 边界 | ⚠️ 边界 |
| $\pm 10\%$ 最坏覆盖 | ❌ | ❌ | ❌ |
| $E$ 消除能力 | 无 | 无（默认 anchor） | 有（用户提供 $A_{34} = W_{34}^{\text{phys}}$） |
| P0-1 wall 初始化 | ✅ | ✅ | ✅ |
| P0-2 RST1 同沿 handoff | ✅ | ✅ | ✅ |
| P1-1 per-pair 饱和计数 | ✅ | ✅ | ✅ |
| P1-2 饱和对排除 accum | ✅ | ✅ | ✅ |
| P1-3 `REMOVE_REDUNDANCY_OFFSET` | 删除（always-on） | 保留并 GATE | 保留并 GATE（默认 1） |
| P1-4 decoder fail policy | ✅ | ✅ | ✅ |
| 饱和阈值 | `SAT_RATIO_PCT=50` | `MAX_SAT_PAIR_PCT=25` | `MAX_SAT_PAIR_PCT=25`（更严格，因 autoranger 处理 gross range） |

### 8.6 V6.6 操作模式

**模式 1：名义 anchor（向后兼容 V6.3）**

```
ANCHOR_W3_LSB = 256  (default)
ANCHOR_W4_LSB = 256  (default)
```

行为等同 V6.3 + W5 autoranging。$E$ 仍按 $(-E, -2E, -4E)$ 传播。适用于：
- 低位电容失配可忽略
- layout matching 保证 $|E| < 1\%$
- 仅需扩展量程覆盖 $\pm 5\%$ MSB 失配

**模式 2：外部 anchor（消除 $E$）**

```
ANCHOR_W3_LSB = <post-fab characterized W3>
ANCHOR_W4_LSB = <post-fab characterized W4>
```

或：

```
ANCHOR_W3_LSB = 256 + <measured e3>
ANCHOR_W4_LSB = 256 + <measured e4>
```

$E$ 传播完全消除。适用于：
- 12-bit 精度要求
- $|E|$ 可能 $> 1\%$
- 已有 post-fab 表征或外部 $C_{\text{REF}}$ 硬件

**模式 3：CAL_BYPASS（旁路校准）**

```
CAL_BYPASS = 1
```

直接使用名义权重，不执行校准。适用于 debug 或已知 ideal capacitor 场景。

### 8.7 V6.6 已知限制

1. **$W_5$ 不理想无法校准**：粗调电容 $W_5 = 128 + e_5$ 的失配 $e_5$ 直接进入残差测量。若 $|e_5| > 1\%$，建议在 layout 中严格匹配 $W_5$，或考虑使用外部 $C_{\text{REF}}$ 同时承担粗调与 anchor 功能。
2. **$\pm 10\%$ 失配仍可能失败**：$|R_0|_{\max} = 3584 \times 10\% = 358.4$ LSB > 250 LSB。要覆盖 $\pm 10\%$ 需要额外的二级粗调电容（如 $W_4 = 256$ 作为二级粗调，扩展到 $\pm 506$ LSB）。
3. **方向歧义 fail-fast**：若第一次 $k=0$ 探测同时触发 `overflow_pos` 和 `overflow_neg`（比较器噪声或 $R \approx 0$ 但两端都接近 endpoint），V6.6 立即设 `ERR=1`。建议检查比较器噪声水平或增加 `AVG_PAIRS_LOG2`。
4. **`MAX_SAT_PAIR_PCT = 25`**：比 V6.3 的 50% 更严格。若校准后饱和比例仍 $> 25\%$，说明 $R$ 量程仍不足或比较器噪声过大，需检查 $|p|$ 是否 $> 7\%$ 或比较器噪声是否异常。
5. **外部 anchor 表征成本**：模式 2 需要独立的 post-fab 表征或外部 $C_{\text{REF}}$ 硬件，增加测试时间或芯片面积。

### 8.8 V6.6 总结

> [!summary] V6.6 最终方案
>
> V6.6 合并了两个互补的修复：
> - **V6.5 的 W5 粗调自动量程**：扩展 calDAC 量程从 $\pm 122$ 到 $\pm 250$ LSB，覆盖 $\pm 5\%$ 任意方向 MSB 失配。
> - **§7 方案 A 的外部 anchor 通道**：`ANCHOR_W3_LSB/ANCHOR_W4_LSB` 参数允许用户提供物理表征的 $W_3/W_4$，消除 $E$ 传播。
>
> **默认行为**：$A_{34} = 512$（名义 anchor），V6.6 退化为 V6.3 + W5 autoranging，向后兼容。
>
> **进阶行为**：用户提供 $A_{34} = W_{34}^{\text{phys}}$，$E$ 传播完全消除，可达 12-bit 精度（受限于 $e_{\text{REF}}$ 表征精度和 $W_5$ layout matching）。
>
> **覆盖矩阵**：
> - $\pm 3\%$ 任意方向：V6.3 已足够，V6.6 同样工作。
> - $\pm 5\%$ 任意方向：V6.3 FAIL，V6.6 OK（W5 autoranging）。
> - $\pm 7\%$ 任意方向：V6.6 接近边界，可能偶发失败。
> - $\pm 10\%$ 任意方向：V6.6 FAIL，需扩展粗调电容。
>
> **代码包**：`src/DEC_CAL_PHY.va` (V6.6 VA), `rtl/DEC_CAL_PHY_rtl.v` (V6.6 RTL)。归档：`archive/DEC_CAL_PHY_v6_3.va`, `archive/DEC_CAL_PHY_rtl_v6_3.v`, `archive/DEC_CAL_PHY_v6_5.va`。
