# SAR ADC 理想数字链路 + 前景校准替代包 V6.6

> [!summary] V6.6 定位
> V6.6 合并了两个**互补**的修复，解决 V6.3 在不同失配方向上校准效果不一致的根本原因：
> - **W5 粗调自动量程**（继承自 V6.5）：calDAC 量程从 ±122 LSB 扩展到 ±250 LSB，覆盖 ±5% 任意方向 MSB 失配。
> - **外部 Anchor 通道**（§7 方案 A 工程实现）：`ANCHOR_W3_LSB/ANCHOR_W4_LSB` 参数允许用户提供物理表征的 $W_3/W_4$，消除 $E = e_3 + e_4$ 传播。

## 目录结构

```
src/    核心 Verilog-A 模块
sim/    仿真辅助模型与顶层网表
rtl/    可综合 Verilog RTL 版本
ext/    扩展校准版本
doc/    文档（含严格数学证明）
ref/    参考论文
archive/ 版本归档
```

本包核心模块（src/）：

- `src/SWITCH_CAL.va` — CDAC 开关阵列
- `src/SAR_LOGIC_0716.va` — 14-beat 非二进制 SAR 逻辑
- `src/SYNC_asnyc.va` — 时序生成器
- `src/COM_ideal.va` — 理想比较器（含 CAL-gated dither）
- `src/DEC_CAL_PHY.va` (V6.6：3-target + W5 autoranging + external anchor + 全部 P0/P1 修复)

RTL 镜像：

- `rtl/DEC_CAL_PHY_rtl.v` — V6.6 可综合 RTL，与 VA 引脚兼容、功能同步

归档（archive/）：

- `DEC_CAL_PHY_v6.va` — V6（7-bit calDAC，3-target，无饱和检测）
- `DEC_CAL_PHY_v6_2.va`, `DEC_CAL_PHY_rtl_v6_2.v` — V6.2（DEFECT：`w2 re-correction` 数学无效）
- `DEC_CAL_PHY_v6_3.va`, `DEC_CAL_PHY_rtl_v6_3.v` — V6.3（3-target + 隐式 gauge + P0/P1 修复，无 autoranging）
- `DEC_CAL_PHY_v6_5.va` — V6.5（ChatGPT 草案：W5 autoranging，无 V6.6 文档与外部 anchor 联合覆盖分析）
- `DEC_CAL_PHY_v7.va` — V7（DEFECTIVE：128>126 违反 offset-binary SAR 收敛，请勿使用）

## V6.6 相对 V6.3 的核心改动

### 1. 识别出两个互补根因

V6.3 在不同失配方向上效果不一致有两个**独立**根因，必须分别处理：

| 根因 | 描述 | 触发条件 | V6.6 解决方案 |
|---|---|---|---|
| **(I) $E$ 传播** | $E = e_3 + e_4$ 作为 $(-E, -2E, -4E)$ 进入 $w_{2,1,0}$ | 任何 $E \neq 0$ | §7 方案 A：外部 anchor $A_{34} = W_3 + W_4$（物理表征） |
| **(II) $R$ 量程饱和** | $R_0 = e_0 - e_1 - e_2$ 超过 ±126 LSB | 反向失配且 $|p| > 3.5\%$ | V6.5：W5 粗调自动量程，扩展到 ±250 LSB |

> [!important] 关键洞察
> 消除 $E$（根因 I）不改变 $R$ 量程（根因 II 仍存在）；扩展 $R$ 量程（根因 II）不消除 $E$ 传播（根因 I 仍存在）。**V6.6 必须同时处理两者**。

### 2. W5 粗调自动量程（继承自 V6.5）

calDAC 仍为 7-bit（stages 6..12 = 48+32+20+12+8+4+2 = 126），SAR 仍为 7 步。**ideal $W_5 = 128$ 作为固定粗调电容**（不是额外 SAR 位）。

测量协议：

1. 第一次试探 $k = 0$（$W_5$ 不参与），测 $R_{\text{fine}} = R$。
2. 若正向越界（$D^+ \geq 126$ 或 $D^- \leq 1$）：选 $k = +1$，重新测量 $R_{\text{fine}} = R - 128$。
3. 若负向越界（$D^+ \leq 1$ 或 $D^- \geq 126$）：选 $k = -1$，重新测量 $R_{\text{fine}} = R + 128$。
4. 恢复：$R = (D^+ - D^-) + k \cdot 128$。

第一次饱和的 pair 只用于判断量程，不进入平均；切换量程时之前零档样本全部清除，避免不同 coarse range 的数据混合。

**定理 5（量程扩展）**：可测对称残差范围从 $\pm 122$ LSB 扩展到 $\pm 250$ LSB（证明见 `doc/PROOF_V6_3_IDENTIFIABILITY.md` §8.2）。

| MSB 失配 $|p|$ | $\|R_0\|_{\max}$ | V6.3 (±122) | V6.6 (±250) |
|---|---|---|---|
| 1% | 35.84 | ✅ | ✅ |
| 3% | 107.5 | ✅ | ✅ |
| 5% | 179.2 | ❌ FAIL | ✅ |
| 7% | 250.9 | ❌ FAIL | ⚠️ 边界 |
| 10% | 358.4 | ❌ FAIL | ❌ FAIL |

### 3. 外部 Anchor 通道（§7 方案 A 工程实现）

V6.6 暴露 `ANCHOR_W3_LSB` 和 `ANCHOR_W4_LSB` 两个参数。记 $A_{34} := \text{ANCHOR\_W3\_LSB} + \text{ANCHOR\_W4\_LSB}$，$e_{\text{REF}} := A_{34} - 512$。

**定理 6（anchor 误差传播）**：anchor 误差 $e_{\text{REF}}$ 按 $(+e_{\text{REF}}, +2 e_{\text{REF}}, +4 e_{\text{REF}})$ 传播，**符号与 $E$ 相反**：

$$
\hat W_2 = 512 + e_2 - E + e_{\text{REF}}, \quad \hat W_1 = 1024 + e_1 - 2E + 2 e_{\text{REF}}, \quad \hat W_0 = 2048 + e_0 - 4E + 4 e_{\text{REF}}
$$

- **名义 anchor**（默认 $A_{34} = 512$，$e_{\text{REF}} = 0$）：退化为 V6.3 行为，$E$ 按 $(-E, -2E, -4E)$ 传播。
- **外部 anchor**（用户提供 $A_{34} = W_3 + W_4$ 物理表征值，$e_{\text{REF}} = E$）：$E$ 传播完全消除。

获取 $A_{34} = W_3 + W_4$ 物理值的硬件途径：
1. Post-fab 表征 $W_3, W_4$（trim、laser、fuse 等）
2. 外部参考电容 $C_{\text{REF}}$ 配合已知 $V_{\text{REF}}$，一次性测量阶段切换替代 $W_3 + W_4$
3. Split-ADC（McNeill 2005）：拆分 $W_3$（或 $W_4$）为两半，互为独立参考

### 4. P0/P1 bug 全修复（继承自 V6.3）

| Bug | V6.2 | V6.6 |
|---|---|---|
| `wall_weight_q` 在 `initial_step` 未初始化 | t=0 时 CAL_RST=0 → wall=0 → 第一个 target 失败 | 三处均设置 `wall = anchor_a34_q` |
| 两个 `RST1 rising` handler / handoff 时序 | 最后 target 后需额外 frame 才 DONE | 单一 handler，direction finish 在前 + handoff 独立 if（P0-2 同边沿 DONE） |
| REJECT 静默继续 | 不设 ERR，可能 DONE=1 ERR=0 但权重未更新 | **Fail-fast**：`cal_error_i=1` 立即 + `finish_pending_i=1`；handoff 时 w0/w1/w2 回退名义值 |
| `saturate_flag` 单 bit / per-direction 计数 | 32 对中任一饱和即拒绝；后改为 per-direction（最大 2×avg_pairs），与 avg_pairs 阈值不匹配 | per-pair OR（D- 完成时判定），范围 [0..avg_pairs]（P1-1） |
| saturated sample 进入平均 | 即使饱和比例低于阈值，clipped code 也污染 `residual_q` | saturated pair 跳过 accum，用 `valid_pair_count` 作除数（P1-2） |
| decoder 在 ERR=1 时仍用部分校准权重 | 注释说 "caller can decide"，但 decoder 自动应用部分权重 | decoder 在 `(APPLY_CAL_WEIGHT != 0) && (cal_error_i == 0)` 时才应用校准权重，否则回退名义权重（P1-4） |
| `REMOVE_REDUNDANCY_OFFSET` 死参数 | 声明但未 gate 任何逻辑 | **V6.6 恢复并 GATE**（默认 1 = 移除冗余偏移） |
| V6.3 数学推导符号错误 | 原声称 `w1/w0 exact`，实际 `R` 中 `E` 符号写反 | PROOF §4 重写为 `(-E, -2E, -4E)` 传播（P0-1） |

### 5. 不变的部分

- calDAC 仍为 7-bit（stages 6..12 = 126）
- SAR 仍为 7 步 + 1 terminal
- DITHER_PAIR_EDGES 仍为 16（COM_ideal）
- CAL_CLK 边沿数不变
- 外部时序和接口完全不变（VA/RTL 引脚兼容 V6.3）

## 必须修改的两处原理图连接

### 1. 消除最终 CLK 双驱动

```text
SYNC_asnyc.CLK -> CLK_SAR -> DEC_CAL_PHY.CLK_SAR
DEC_CAL_PHY.CLK -> CLK -> COM_ideal.CLK
```

### 2. COM_ideal 增加 CAL 引脚

```text
COM_ideal CLK COMN COMP N P CAL
```

CAL 直接连接 DEC_CAL_PHY 的 CAL 输出。阈值 dither 只在校准模式开启。

## 模块参数（V6.6 默认）

```text
CAL_BYPASS            = 0      // 0=运行校准，1=旁路
APPLY_CAL_WEIGHT      = 1      // decoder 是否应用校准权重（ERR=1 时强制回退）
AVG_PAIRS_LOG2        = 5      // 2^5 = 32 对 D+/D-
MIN_AVG_PAIRS_LOG2    = 5
ENFORCE_MIN_AVG       = 1
FRAC_BITS             = 6      // Q6 固定小数位
WEIGHT_TOL_PCT        = 35     // 名义位权 35% 容差窗
DEBUG                 = 1      // 0=quiet, 1=basic, 2=verbose

# V6.6 新增 / 重定义
ANCHOR_W3_LSB         = 256    // 外部 anchor：物理 W3 表征值（默认名义）
ANCHOR_W4_LSB         = 256    // 外部 anchor：物理 W4 表征值（默认名义）
COARSE_W5_LSB         = 128    // 粗调电容名义权重（W5 不可测，假设理想）
MAX_SAT_PAIR_PCT      = 25     // 饱和对百分比阈值（V6.3 的 50% → 25%）
REMOVE_REDUNDANCY_OFFSET = 1   // 0=保留冗余偏移，1=移除（V6.6 GATE，默认 1）
```

每个目标至少 32 对 D+/D-，日志打印：

- calibration start（含 anchor 模式）
- 每个目标 coarse probe 选档（k=0/+1/-1）
- 每个目标最终 measure（ACCEPT 或 REJECT）
- calibration finish（含 error 状态）
- 最终 weights_q
- SATURATE 警告（每次端点撞击）

`DEBUG=2` 输出逐位 CMPDIAG。

## V6.6 三种操作模式

### 模式 1：名义 anchor（向后兼容 V6.3 + autoranging）

```
ANCHOR_W3_LSB = 256  (default)
ANCHOR_W4_LSB = 256  (default)
```

行为等同 V6.3 + W5 autoranging。$E$ 仍按 $(-E, -2E, -4E)$ 传播。适用于：
- 低位电容失配可忽略
- layout matching 保证 $|E| < 1\%$
- 仅需扩展量程覆盖 ±5% MSB 失配

### 模式 2：外部 anchor（消除 $E$ 传播）

```
ANCHOR_W3_LSB = <post-fab characterized W3>
ANCHOR_W4_LSB = <post-fab characterized W4>
```

或等价地：

```
ANCHOR_W3_LSB = 256 + <measured e3>
ANCHOR_W4_LSB = 256 + <measured e4>
```

$E$ 传播完全消除，可达 12-bit 精度（受限于 $e_{\text{REF}}$ 表征精度和 $W_5$ layout matching）。适用于：
- 12-bit 精度要求
- $|E|$ 可能 $> 1\%$
- 已有 post-fab 表征或外部 $C_{\text{REF}}$ 硬件

### 模式 3：CAL_BYPASS（旁路校准）

```
CAL_BYPASS = 1
```

直接使用名义权重，不执行校准。适用于 debug 或已知 ideal capacitor 场景。

## 校准与 A/B 验证

最干净的权重应用对比：

```text
A：CAL_BYPASS=0，APPLY_CAL_WEIGHT=0
B：CAL_BYPASS=0，APPLY_CAL_WEIGHT=1
```

纯旁路参考：

```text
CAL_BYPASS=1，APPLY_CAL_WEIGHT=0
```

外部 anchor 启用：

```text
CAL_BYPASS=0, APPLY_CAL_WEIGHT=1
ANCHOR_W3_LSB=<W3_phys>, ANCHOR_W4_LSB=<W4_phys>
```

## 仿真时间

V6.6 仍为 3 个目标，每个目标 32 对 D+/D-。最坏情况下每个目标需要一次 $k=0$ 探测 + 一次正式测量 = 2 倍帧数，但典型情况（无越界）只 1 倍。

```text
tran stop >= 45 us（典型，无越界）
tran stop >= 90 us（最坏，每目标都需 k=±1 重测）
```

FFT 必须从 `DONE=1` 之后开始取样。

## 预期最终日志

典型（无越界）：

```text
OFFSAR V6.6 init ... targets=3 anchor_mode=NOMINAL A34=512
OFFSAR measure target=2 ... ACCEPT valid=32/32 sat=0/32 [coarse k=0]   (w2)
OFFSAR measure target=1 ... ACCEPT valid=32/32 sat=0/32 [coarse k=0]   (w1)
OFFSAR measure target=0 ... ACCEPT valid=32/32 sat=0/32 [coarse k=0]   (w0)
OFFSAR finish done=1 err=0
OFFSAR weights_q={...}
```

越界后重测：

```text
OFFSAR measure target=0 ... SAT_POS pair=0 [k=0 probe, discard]
OFFSAR measure target=0 ... ACCEPT valid=32/32 sat=0/32 [coarse k=+1]   (w0)
```

若任意 target REJECT（fail-fast）：

```text
OFFSAR REJECT target=N measured_q=... [sat_pairs=X/32 | out-of-tolerance | all_pairs_saturated | coarse_ambiguous]
OFFSAR finish done=1 err=1
OFFSAR weights_q={...} (top weights reverted to nominal)
```

`ERR=1` 但 `DONE=1`：**decoder 自动回退到名义权重**（P1-4 fail policy），不应用部分校准权重。

若出现 `OFFSAR SATURATE` 警告：该次 D+/D- 撞击 calDAC 端点（code≤1 或 ≥126）。第一次饱和的 pair 用于 coarse range 判断（不进入平均）；recentering 后的 saturated pair 不进入累加，仅当 saturated pair 比例超过 `MAX_SAT_PAIR_PCT`（默认 25%）或 `valid_pair_count==0` 时才 fail-fast 拒绝 target。

## 已知限制

详见 `doc/PROOF_V6_3_IDENTIFIABILITY.md`（含定理 1–6 + §7 + §8 完整推导）：

- **$W_5$ (128) 不校准**：定理 2 证明不可测（唯一 wall 候选 $W_{13}=1$，$|W_5-1|=127>126$）。V6.6 把 $W_5$ 用作粗调电容，假设 $|e_5| < 1\%$（layout matching）。硬件修复：拆分 $W_5$ 为 64+64，或外部 $V_{\text{ref}}$ 电容。
- **$e_3$ 与 $e_4$ 不可分离**：只假设 $W_3+W_4=512$（gauge）。$e_3 - e_4$ 差分失配作为 DNL 噪声保留。V6.6 外部 anchor 模式可消除 $e_3+e_4 = E$，但 $e_3-e_4$ 仍存在。
- **共模增益不可见**：定理 3 证明所有 wall 都是差分测量，$(1+\alpha)$ 缩放在 $R$ 中对消。
- **$E$ 传播双模式**：
  - 默认（名义 anchor）：$(-E, -2E, -4E)$，与 V6.3 相同，最坏 INL ≈ 20 LSB（$|E|=2.56$ LSB 时），ENOB 损失约 1.5 bit。
  - 外部 anchor（$e_{\text{REF}} = E$）：$E$ 完全消除，最坏 INL ≈ 10.8 LSB（$|e_{\text{REF}}-E|<0.5$ LSB 时），ENOB ≈ 11.2 bit。
- **±250 LSB 量程上限**：覆盖 ±5% 任意方向、±7% 边界。±10% 仍 FAIL（$|R_0|_{\max}=358.4$ LSB）。需扩展粗调电容（如 $W_4=256$ 作为二级粗调，扩展到 ±506 LSB）。
- **方向歧义 fail-fast**：若第一次 $k=0$ 探测同时触发 `overflow_pos` 和 `overflow_neg`（比较器噪声或 $R \approx 0$ 但两端都接近 endpoint），V6.6 立即设 `ERR=1`。建议检查比较器噪声水平或增加 `AVG_PAIRS_LOG2`。
- **`MAX_SAT_PAIR_PCT = 25`**：比 V6.3 的 50% 更严格。若 recentering 后饱和比例仍 $> 25\%$，说明 $R$ 量程仍不足或比较器噪声过大。

## V6.6 覆盖矩阵（与 V6.3 / V6.5 对比）

| 维度 | V6.3 | V6.5（草案） | V6.6（最终） |
|---|---|---|---|
| calDAC 量程 | ±122 LSB | ±250 LSB（W5 粗调） | ±250 LSB（W5 粗调） |
| $E$ 传播 | $(-E, -2E, -4E)$ | $(-E, -2E, -4E)$ | 默认 $(-E, -2E, -4E)$ / 外部 anchor $0$ |
| Anchor 通道 | 无（隐式 512） | `ANCHOR_W3/W4_LSB` 参数 | `ANCHOR_W3/W4_LSB`（默认 256+256=512） |
| ±5% 同向覆盖 | ✅ | ✅ | ✅ |
| ±5% 反向覆盖 | ❌ FAIL（$\|R_0\|=179$） | ✅ | ✅ |
| ±7% 最坏覆盖 | ❌ | ⚠️ 边界 | ⚠️ 边界 |
| ±10% 最坏覆盖 | ❌ | ❌ | ❌ |
| $E$ 消除能力 | 无 | 无（默认 anchor） | 有（用户提供 $A_{34} = W_{34}^{\text{phys}}$） |
| P0-1 wall 初始化 | ✅ | ✅ | ✅ |
| P0-2 RST1 同沿 handoff | ✅ | ✅ | ✅ |
| P1-1 per-pair 饱和计数 | ✅ | ✅ | ✅ |
| P1-2 饱和对排除 accum | ✅ | ✅ | ✅ |
| P1-3 `REMOVE_REDUNDANCY_OFFSET` | 删除（always-on） | 保留并 GATE | 保留并 GATE（默认 1） |
| P1-4 decoder fail policy | ✅ | ✅ | ✅ |
| REJECT 语义 | degraded flag → ERR=1 at finish | fail-fast ERR=1 immediately | fail-fast ERR=1 immediately |
| 饱和阈值 | `SAT_RATIO_PCT=50` | `MAX_SAT_PAIR_PCT=25` | `MAX_SAT_PAIR_PCT=25` |

## 文档

- `doc/PROOF_V6_3_IDENTIFIABILITY.md`：严格数学证明
  - 定理 1：V6.2 `w2 re-correction` 是 no-op
  - 定理 2：$W_5$ (128) 不可测
  - 定理 3：共模增益不可观测
  - 定理 4（更正版）：V6.3 $E$ 传播为 $(-E, -2E, -4E)$，**不是**精确
  - §7：方向/程度敏感性根因 + 8 篇文献综述
  - 定理 5（§8.2）：V6.6 W5 autoranging 量程扩展 ±122 → ±250 LSB
  - 定理 6（§8.3）：V6.6 anchor $e_{\text{REF}}$ 按 $(+e_{\text{REF}}, +2 e_{\text{REF}}, +4 e_{\text{REF}})$ 传播，符号与 $E$ 相反；$e_{\text{REF}}=E$ 时 $E$ 完全消除
- `doc/STATIC_CHECK_REPORT.txt`：V6.6 静态检查报告
- `doc/sar_adc_mismatch_calibration_report_cn.pdf`：V6.2 时期报告（历史参考）

## 说明

此包用于 Spectre 行为级替代和校准算法验证。比较器的校准 dither 是仿真辅助机制；实际芯片需要比较器噪声统计、offset/dither DAC 或更细校准 DAC 来获得亚 LSB 可观测性。
