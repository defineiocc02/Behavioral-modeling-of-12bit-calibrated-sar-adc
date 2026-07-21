---
title: VCM CDAC 校准解码 VA 模型审阅报告
aliases:
  - VA模型审阅
  - 校准解码审阅
  - vcm_cdac_cal_decode 审阅
tags:
  - type/review
  - topic/sar-adc
  - topic/verilog-a
  - topic/calibration
  - status/pending-review
created: 2026-07-14
updated: 2026-07-14
author: 赵诣（审阅）
reviewer: 赵诣
target_author: VA 模型代码作者
related:
  - "[[20260601_CMP2SAR_valid_gated_DEC_N接口方案分析]]"
  - "[[SAR_LOGIC_SYNC_分析]]"
---

# VCM CDAC 校准解码 VA 模型审阅报告

> 本报告审阅对象为 `vcm_cdac_cal_decode_va` 模块（纯数字输出版）。
> 审阅基于项目 `2026_12bit10Msar` 的实际电路网表 `netlist.txt`，交叉验证 CDAC 架构、SAR_LOGIC 接口和校准算法。

---

## 一、模型概述

该 VA 模块实现了 VCM-based SAR ADC 的完整数字后处理流程：

1. **前台权重校准**：`start` 脉冲触发，11 个 `clk` 周期完成 11 个权重的逐位标定
2. **Raw code 解码**：`raw_valid` 上升沿锁存，使用校准后权重进行加权求和
3. **Offset-binary 编码**：根据 `first_cmp` 判断上/下半区，输出 12-bit offset-binary 码（0~4095）

与上一版（`vcm_cdac_cal_decode_ideal_dac_va`）的差异：移除了内嵌理想 DAC（`vout`/`vcode`/`vmag`），仅输出纯数字 `D[11:0]` + `CODE_VALID`。这使其更适合作为独立数字后处理单元与外部模拟电路联合仿真。

---

## 二、CDAC 架构验证

### 2.1 网表提取的电容阵列结构

从实际电路网表 `subckt CDAC` 中提取的电容配置：

| 节点 | 位 | 电容值 | 有效权重 | VA 模型对应 |
|:---|:---|:---|:---|:---|
| net1/net2（子阵列） | BIT\<1\> | 1C | 1 | RAW0 → W0=1 |
| | BIT\<2\> | 2C | 2 | RAW1 → W1=2 |
| | BIT\<3\> | 4C | 4 | RAW2 → W2=4 |
| | BIT\<4\> | 6C | 6（冗余） | RAW3 → W3=6 |
| | BIT\<5\> | 10C | 10（冗余） | RAW4 → W4=10 |
| | BIT\<6\> | 16C | 16（冗余） | RAW5 → W5=16 |
| | BIT\<7\> | 24C | 24（冗余） | RAW6 → W6=24 |
| N/P（主阵列） | BIT\<8\> | 1C | 64 | RAW7 → W7=64 |
| | BIT\<9\> | 2C | 128 | RAW8 → W8=128 |
| | BIT\<10\> | 4C | 256 | RAW9 → W9=256 |
| | BIT\<11\> | 8C | 512 | RAW10 → W10=512 |
| | BIT\<12\> | 16C | 1024 | RAW11 → W11=1024 |
| 桥接 | C16/C17 | 1C | — | $\alpha = 1/(1+63) = 1/64$ |

### 2.2 权重计算验证

桥接衰减系数：

$$\alpha = \frac{C_b}{C_b + C_{sub}} = \frac{1C}{1C + (1+2+4+6+10+16+24)C} = \frac{1}{64}$$

主阵列权重 = $C_{main} \times 64$，子阵列权重 = $C_{sub} \times 1$。乘以 64 后所有 12 个权重与 VA 模型标称值完全一致。总权重 $= 2047$，配合 `FIRST_CMP` 实现 12-bit offset-binary 输出（0~4095）。

**结论：权重架构与实际电路网表完全吻合。**

---

## 三、校准算法分析

### 3.1 算法核心：Measure-then-Set 差分双相测量

每个权重的校准执行以下流程：

1. 根据当前 `cal_idx` 选择目标位 `target` 和 wall 组合
2. 计算真实残差：`true_residual = ACT_W_target - ACT_W_wall`
3. 双相测量模拟：
   - `meas_pos = +true_residual + CMP_OFFSET_LSB + POS_ERR_LSB`
   - `meas_neg = -true_residual + CMP_OFFSET_LSB + NEG_ERR_LSB`
4. 差分相减消除失调：`residual_est = 0.5 × (meas_pos - meas_neg) = true_residual`
5. 更新权重：`cw_target = calibrated_wall + residual_est`
6. 合理性检查：`candidate` 必须在 `nominal_target × (1 ± WEIGHT_TOL)` 范围内

### 3.2 Wall 选择策略验证

每步的 wall 选择使得标称 wall 值等于标称 target 值，从而在理想情况下残差为零：

| 步骤 | target | wall 组成 | 标称 wall | 标称 target | 残差 |
|:---|:---|:---|:---|:---|:---|
| 1 | W1=2 | W0=1 | 1 | 2 | 1 |
| 2 | W2=4 | W1+W0=3 | 3 | 4 | 1 |
| 3 | W3=6 | W2+W1=6 | 6 | 6 | 0 |
| 4 | W4=10 | W3+W2=10 | 10 | 10 | 0 |
| 5 | W5=16 | W4+W3=16 | 16 | 16 | 0 |
| 6 | W6=24 | W5+W3+W1=24 | 24 | 24 | 0 |
| 7 | W7=64 | $\Sigma$(W0..W6)=63 | 63 | 64 | 1 |
| 8 | W8=128 | $\Sigma$(W0..W7)=127 | 127 | 128 | 1 |
| 9~11 | W9~W11 | $\Sigma$(所有低位) | target-1 | target | 1 |

步骤 1-2 的残差为 1（二进制起始位固有特性），步骤 3-6 残差为零，步骤 7-11 残差为 1（桥接边界）。

**步骤 6 的 wall 选择 `W5+W3+W1=24` 是最优解**——跳过 W4(10)、W2(4)、W0(1)，使标称残差恰好为零。

### 3.3 冗余覆盖分析

| 冗余位 | 权重 | 低位总和 | 覆盖率 |
|:---|:---|:---|:---|
| W3=6 | 6 | 7（W0..W2） | 117% |
| W4=10 | 10 | 13（W0..W3） | 130% |
| W5=16 | 16 | 23（W0..W4） | 144% |
| W6=24 | 24 | 39（W0..W5） | 163% |
| W7=64 | 64 | 63（W0..W6） | 98.4% |

子阵列 4 位冗余位（W3~W6）提供充分的误差纠正余量。主-子阵列边界处 W7 的覆盖率为 98.4%，约 1 LSB 间隙，属于桥接 CDAC 的固有特性。

---

## 四、VCM 半量程映射验证

解码逻辑：

```
amplitude_bit[i] = RAW[i] XOR FIRST_CMP XOR RAW_POLARITY

FIRST_CMP = 1:  CODE = 2048 + MAGNITUDE
FIRST_CMP = 0:  CODE = 2047 - MAGNITUDE
```

边界连续性验证：

- 上半区底端：`FIRST_CMP=1`, all `amp=0` → `CODE=2048`
- 下半区顶端：`FIRST_CMP=0`, all `amp=1` → `CODE=0`
- 相邻码 2047→2048 跳变正确，无间隙无重叠

**结论：VCM 映射逻辑正确。**

---

## 五、联合仿真方案

### 5.1 信号接口映射

VA 模块需要从现有电路网表连接以下信号：

#### 控制信号

| VA 端口 | 来源 | 网表对应 | 说明 |
|:---|:---|:---|:---|
| `clk` | SYNC 输出的 `CLK` | 网表中 `CLK` 节点 | SAR 内部时钟 |
| `rst` | 网表中 `RST` | `V7 (RST AGND)` | 异步复位，高有效 |
| `start` | 需新增脉冲源 | 仿照 `V8 (SOUT)` | 校准启动脉冲 |

#### SAR 转换结果

| VA 端口 | 来源 | 网表对应 | 说明 |
|:---|:---|:---|:---|
| `raw0~raw6` | SAR_LOGIC 子阵列输出 | `BITP<0>~BITP<6>` 或 `BITN<0>~BITN<6>` | 子阵列 7 位 |
| `raw7~raw11` | SAR_LOGIC 主阵列输出 | `BITP<7>~BITP<11>` 或 `BITN<7>~BITN<11>` | 主阵列 5 位 |
| `first_cmp` | SAR_LOGIC 首位判决 | `BITP<12>` 或 `BITN<12>` | 判断输入在 $V_{CM}$ 上方/下方 |
| `raw_valid` | SAR 转换完成信号 | 需从 `SET<12>` 或 `CCLK` 提取 | 标识 raw code 有效 |

> [!question] 待确认 1：BITP 还是 BITN 作为 raw code？
> SAR_LOGIC 网表中 BITP 和 BITN 为互补差分对。需确认 BITP=1 对应"该位电容被切换到 $V_{REFP}$"还是"$V_{REFN}$"。这直接决定 `RAW_POLARITY` 参数取值。

> [!question] 待确认 2：first_cmp 的极性
> `BITP<12>` 是 SAR_LOGIC 的首个判决结果。需确认 `BITP<12>=1` 对应"输入高于 $V_{CM}$"还是低于。建议通过一次慢速 DC ramp 仿真确定。

> [!question] 待确认 3：raw_valid 信号来源
> 当前网表中没有明确的"转换完成"信号。`SET<12>` 是最后一位的 SET 控制脉冲，可作为候选。需确认 `SET<12>` 的时序是否在所有 12 位判决完成后才拉高。

### 5.2 仿真时序设计

联合仿真分 3 个时序阶段：

**阶段 1：上电复位（0 ~ 100ns）**

`RST` 脉冲初始化所有模拟电路。VA 模块在 `initial_step` 中自动初始化权重为标称值。

**阶段 2：前台校准（~100ns ~ 500ns）**

`start` 脉冲触发后，VA 模块在后续 11 个 `clk` 上升沿依次完成 W1~W11 的权重校准。此阶段不需要模拟前端工作——校准算法通过 `ACT_W*` 参数模拟真实电容值。

**阶段 3：正常转换 + 解码（~500ns 以后）**

差分正弦输入经 CDAC 采样、SAR_LOGIC 逐次逼近产生 12 位 raw code + first_cmp，`raw_valid` 上升沿触发 VA 模块解码，输出 `D[11:0]` 和 `CODE_VALID`。

### 5.3 RAW_POLARITY 确定方法

通过一次慢速 DC ramp 仿真确定：

1. 设 `VIN - VCM = +100mV`（正差分输入）
2. 运行一次完整 SAR 转换
3. 检查 `BITP<12>`（first_cmp）和 `BITP<11>`（raw11，MSB）
4. 若 `first_cmp=1` 且 `raw11=1`（高位被激活），则 `RAW_POLARITY=0`
5. 若 `first_cmp=1` 但 `raw11=0`，则 `RAW_POLARITY=1`

### 5.4 现有网表需要的改动

| 改动项 | 说明 |
|:---|:---|
| 新增 `start` 脉冲源 | 仿照 `V8 (SOUT)` 的脉冲定义 |
| 新增 `raw_valid` 信号 | 从 `SET<12>` 或 `CCLK` 最后一个脉冲提取 |
| VA 模块实例化 | 替换或并联原有的 `I34 (SNDR_DAC)` |
| BITP/BITN 信号引出 | 当前 BITP/BITN 在 SAR_LOGIC 到 DEC 的内部连线上，需引出到 VA 模块 |

### 5.5 推荐验证流程

| 步骤 | 仿真类型 | 目的 | ACT_W 设置 |
|:---|:---|:---|:---|
| 1 | 纯 VA 行为级 | 验证校准算法收敛 | 标称值（无失配） |
| 2 | 纯 VA 行为级 | 验证失配下的校准精度 | ~0.1% 随机失配 |
| 3 | DC ramp 联合 | 确定 `RAW_POLARITY` | 任意 |
| 4 | 瞬态联合 | 验证端到端 SNDR/SFDR | PEX 提取值 |
| 5 | Monte Carlo | 验证良率 | 随机采样 |

---

## 六、审阅意见

### 6.1 正确性判定

| 审查项 | 结论 | 依据 |
|:---|:---|:---|
| CDAC 权重与网表一致性 | 通过 | 12 个权重逐一对应，桥接衰减 $\alpha=1/64$ 正确 |
| 校准算法数学正确性 | 通过 | 差分双相测量消除失调，wall 选择使标称残差最小化 |
| 冗余位覆盖 | 通过 | 4 位冗余提供 117%~163% 覆盖率 |
| VCM 半量程映射 | 通过 | 边界连续性验证无间隙无重叠 |
| Offset-binary 编码 | 通过 | 输出范围 0~4095，码 2047/2048 跳变正确 |
| Spectre 语法兼容 | 通过 | Style B 端口声明、`cross()` 事件、`transition()` 输出均合规 |

### 6.2 改进建议

> [!bug] 问题 1（功能性）：校准测量无噪声模型
> 当前测量模型仅包含 `CMP_OFFSET_LSB`（DC 失调，差分抵消）和 `POS_ERR/NEG_ERR`（非对称误差）。**缺少随机噪声项**，导致校准精度被高估。
>
> 真实场景中比较器噪声 $\sigma_{n,comp}$ 与残差幅度可比拟时，校准结果会出现散布。建议增加 `MEAS_NOISE_LSB` 参数，使用 `$random` 添加高斯噪声。
>
> **请作者确认**：是否计划在后续版本中加入噪声模型？还是认为噪声验证应在晶体管级联合仿真中体现？

> [!bug] 问题 2（鲁棒性）：无校准超时保护
> 如果 `CLK` 停止翻转，`cal_state` 永远停在 1，校准挂死，`cal_busy` 持续为高。
>
> **请作者确认**：是否需要增加超时保护？还是在 testbench 层面保证 CLK 可靠性？

> [!bug] 问题 3（可调试性）：缺少 final_step 诊断输出
> 校准完成后无法通过仿真日志查看恢复的权重值。`w_mon` 端口提供了模拟电压监控，但在 Spectre log 中搜索数值更方便。
>
> 建议添加 `@(final_step)` 块，使用 `$strobe` 输出最终权重。

> [!question] 待确认 4：`start` 与 `clk` 同沿竞争
> 如果 `start` 和 `clk` 在同一时刻上升，`start` 事件块设置 `cal_state=1`，但 `clk` 事件块可能在本 timestep 尚未看到 `cal_state` 的新值（取决于 Spectre 的事件求值顺序）。
>
> **请作者确认**：实际使用中 `start` 和 `clk` 是否可能同沿？如果是，是否需要在 `start` 事件中直接执行第一步校准？

> [!question] 待确认 5：`ACT_W*` 参数的实际值来源
> 当前默认值带有 ~0.1% 失配，看起来像是手工设置的示例值。
>
> **请作者确认**：这些值是来自 Monte Carlo 仿真采样、PEX 提取、还是手工假设？后续联合仿真时应使用什么来源的权重值？

> [!question] 待确认 6：`WEIGHT_TOL = 0.125`（12.5%）的选择依据
> 12.5% 的容差窗口较宽。对于 12-bit ADC，电容失配通常在 0.1%~0.5% 量级。
>
> **请作者确认**：这个容差是故意设宽以容纳极端 PVT 条件，还是有其他考量？

> [!question] 待确认 7：`CMP_OFFSET_LSB = 0.20` 的选择依据
> 0.20 LSB 的比较器失调在差分测量中会被理想抵消。但如果实际失调更大（如 0.5 LSB），是否会超出差分抵消的有效范围？
>
> **请作者确认**：这个值是来自晶体管级仿真提取，还是保守估计？

---

## 七、Spectre 兼容性检查

| 检查项 | 状态 | 说明 |
|:---|:---|:---|
| `include` 头文件 | 通过 | `constants.vams` + `disciplines.vams` |
| 端口声明风格 | 通过 | Style B（方向与 discipline 分离），`electrical` 声明合规 |
| 声明位置 | 通过 | 所有 `parameter`/`real`/`integer` 在 module level |
| `integer` vs `genvar` | 通过 | `integer` 用于 procedural 循环，无 `genvar` 误用 |
| `cross()` 事件 | 通过 | 带方向标记 `+1`，含 `TTOL`/`VTOL`（硬编码为默认值） |
| `transition()` 输出 | 通过 | 所有输出经 `transition()` 驱动，使用 target 变量 |
| 位运算 | 通过 | `>>`、`&`、`^` 在 `integer` 上合法 |
| `initial_step` 初始化 | 通过 | 所有状态变量在 `initial_step` 中显式初始化 |
| `rst` 复位 | 通过 | 异步高有效复位，复位后状态与 `initial_step` 一致 |

---

## 八、总结

该 VA 模型在算法层面完全正确：权重与实际 CDAC 网表逐一对应，校准算法数学推导无误，VCM 映射逻辑正确，冗余覆盖充分，Spectre 语法合规。

主要改进方向集中在三个方面：

1. **真实性增强**：加入校准测量噪声模型（问题 1）
2. **鲁棒性**：增加校准超时保护（问题 2）
3. **可调试性**：增加 `final_step` 诊断输出（问题 3）

上述改进对于后续替换为真实 CDAC/比较器后的验证尤为关键。

---

## 附录 A：校准状态机状态转移

```
cal_state=0 (IDLE)
    │
    ├── start↑ ──→ cal_state=1 (CALIBRATING), cal_idx=1
    │
    └── rst↑ ────→ cal_state=0 (复位权重为标称值)

cal_state=1 (CALIBRATING)
    │
    ├── clk↑ && cal_idx < 11 && candidate 合理
    │   ──→ 更新 cw[cal_idx], cal_idx++
    │
    ├── clk↑ && cal_idx == 11 && candidate 合理
    │   ──→ 更新 cw[11], cal_done=1, cal_busy=0, cal_state=0
    │
    └── clk↑ && candidate 超出容差
        ──→ cal_error=1, cal_busy=0, cal_state=2 (ERROR)

cal_state=2 (ERROR)
    │
    └── rst↑ ────→ cal_state=0
```

## 附录 B：端口信号方向汇总

| 端口 | 方向 | 功能 |
|:---|:---|:---|
| `clk` | input | 校准时钟 |
| `rst` | input | 异步复位（高有效） |
| `start` | input | 校准启动脉冲 |
| `first_cmp` | input | 首位比较结果（判断上/下半区） |
| `raw_valid` | input | 转换完成标志 |
| `raw0~raw11` | input | 12 位 raw code |
| `cal_done` | output | 校准完成标志 |
| `cal_busy` | output | 校准进行中标志 |
| `cal_error` | output | 校准错误标志 |
| `code_valid` | output | 输出码有效标志 |
| `d0~d11` | output | 12-bit offset-binary 输出 |
| `w0_mon~w11_mon` | output | 校准权重模拟监控（×WMON_SCALE） |
