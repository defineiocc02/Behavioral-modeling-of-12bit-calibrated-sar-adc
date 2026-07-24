# 12 位异步 SAR ADC Python 建模方案

## 1. 建模目标与证据等级

本模型的目标是把以下三条路径明确分开，并允许独立验证：

1. **物理路径**：输入采样、P/N split-CDAC、电荷守恒、比较器与异步逐次逼近；
2. **校准路径**：只能使用 comparator decisions 和数字重构，禁止读取真实物理权重；
3. **验收路径**：物理 P/N oracle 仅用于离线误差归因，不参与校准或转换。

当前证据等级是 Python behavioral L2：理想基线、失配 Monte Carlo、相干
FFT、分侧 oracle 和静态 codebook 检查均可复现。它不是晶体管级 L3 PVT
签核，也不是硅片结果。

## 2. 顶层架构

![Architecture](assets/figures/fig01_model_architecture.png)

顶层类为
[`AsyncBehavioralSARADC`](../src/python_cal/conversion/async_sar_adc.py)，
其主要组成如下：

| 模块 | 代码 | 责任 |
|---|---|---|
| 拓扑 | `topology/cdac_topology.py` | split-CDAC 电容与 bridge |
| 开关策略 | `topology/switching_policy.py` | sampling、trial、commit、terminal |
| 电荷求解 | `physical/charge_solver.py` | 依据电荷守恒求顶板电压 |
| 差分 CDAC | `physical/differential_cdac.py` | P/N 独立电容与物理 oracle |
| 比较器 | `comparator/dynamic_comparator.py` | 极性、offset、noise、decision time |
| 异步控制 | `async_control/handshake.py` | 逐 stage trial/compare/commit |
| 校准 | `calibration/shen_calibrator.py` | 七目标分侧权重估计 |
| Shen 开关 | `calibration/shen_switching.py` | active force state；与 legacy calDAC 隔离 |
| Shen 状态 | `calibration/calibration_fsm.py` | P0/P1/N0/N1 active 状态词汇 |
| 解码 | `decode/sar_decoder.py` | int12、float、Q2 分侧重构 |
| FFT 协议 | `validation/fft_protocol.py` | VFS、相干输入、削顶检查 |

## 3. Split-CDAC 和 decision weights

模型使用 13 个物理 trial stages 和一个数字 terminal decision：

![Decision weights](assets/figures/fig02_cdac_decision_weights.png)

标称 decision weights 为：

```text
[2080, 1040, 520, 260, 130, 65, 65,
   64,   32,  16,   8,   4,  2,  1]
```

其中：

- stages 0–6：高段 H32、H16、H8、H4、H2、H1R、H1A；
- stages 7–12：低段 L32、L16、L8、L4、L2、L1；
- stage 13：数字 terminal，固定解码权重 1 Q0，没有物理电容。

之前为了补出 1 Q0 而加入 `0.5Cu low_term` 的做法会改变低段总电容和
bridge 缩放，属于模型过度物理化。当前拓扑低段是六个真实电容，terminal
只比较当前残差。

## 4. 输入采样与异步转换

![Async sequence](assets/figures/fig03_async_conversion_sequence.png)

一次转换包含：

1. P/N 顶板分别采样 `vinp`/`vinn`；
2. stage 0 开始执行差分 trial；
3. 比较器输出决定 P 或 N 侧保留 VREFP；
4. commit 后进入下一 stage；
5. stage 13 只比较当前残差，不改变任何开关；
6. 14 个 decisions 交给独立 decoder。

这种结构保证数字权重变化不会反向改变物理 decision 序列。测试
`test_decoder_weights_do_not_change_decisions` 明确约束了这一隔离。

## 5. P/N 独立物理权重

P/N 电容失配是独立的，因此真实上限不能用两侧平均权重代替。离线
oracle 通过 `get_physical_weights_per_side_q0()` 分别测量：

```text
P side: P capacitor VCM -> VREFP, N side held
N side: N capacitor VCM -> VREFP, P side held
```

两侧使用同一个 Q0 scale，得到 `weights_p` 和 `weights_n`。该 API 仅供
验证脚本使用；生产 Shen 校准测试会 monkeypatch 该方法并在任何调用时失败，
以防 oracle leakage。

## 6. Shen-derived 七目标校准

![Calibration flow](assets/figures/fig04_shen_calibration_flow.png)

目标顺序：

```text
H1R -> H1A -> H2 -> H4 -> H8 -> H16 -> H32
```

对每个目标和每个 calibration pair，运行四个 lower-SAR 子转换：

```text
P0: P target forced to VREFN
P1: P target forced to VREFP
N0: N target forced to VREFN
N1: N target forced to VREFP
```

分侧估计公式：

\[
\hat W_P = \frac{1}{N}\sum_{j=1}^{N}\frac{S_{P0,j}-S_{P1,j}}{2}
\]

\[
\hat W_N = \frac{1}{N}\sum_{j=1}^{N}\frac{S_{N1,j}-S_{N0,j}}{2}
\]

`/2` 来自全差分 force 的两倍变化；缺少它会把权重放大两倍。固定 dither
序列 `[-1.5, -0.5, +0.5, +1.5] LSB` 在输入等效域对称注入，避免零噪声
比较器锁在单一码，并使恒定 offset 在 VREFN/VREFP 半差中抵消。

H1R 首先使用标称低段 ruler 校准；后续高段使用已经校准的较低高段与低段
共同递归。生产路径不使用 SRM，也不读取 physical weights。

## 7. 分侧数字解码与 Q2

对于 decision \(d_i\)：

\[
s = \sum_i
\begin{cases}
W_{P,i}, & d_i=0 \\
-W_{N,i}, & d_i=1
\end{cases}
\]

信号范围只由 signal stages `[0,1,2,3,4,6]` 决定：

\[
code_f =
\frac{(s + W_{N,\mathrm{signal}})\,(2^{12}-1)}
     {W_{P,\mathrm{signal}} + W_{N,\mathrm{signal}}}
\]

三个接口具有不同用途：

| 接口 | 输出 | 用途 |
|---|---|---|
| `decode()` | integer 0…4095 | 兼容旧 12-bit 接口 |
| `decode_float()` | 浮点码 | 算法参考 |
| `decode_fixed(..., 2)` | 0.25 LSB 步长 | 当前生产动态输出 |

物理 SAR 已经产生一次量化。将分数加权和再次舍入为整数会增加第二份近似
独立的量化噪声，因此 Q2 不是“虚构 ADC 位数”，而是避免数字后处理丢掉
校准信息所需的最小内部精度。

![Output precision](assets/figures/fig07_q2_output_precision.png)

## 8. FFT 验证协议

所有生产验证统一使用：

| 参数 | 值 |
|---|---:|
| FFT points | 4096 |
| Coherent signal bin | 127 |
| Phase | 0.173 rad |
| Amplitude | -0.5 dBFS |
| Window | rectangular |
| VFS | 每个模型动态测量 |
| Clipping | 每次运行显式检查 |

输入为：

\[
v_d[n] = A\sin(2\pi k n/N+\phi)
\]

其中 \(A=V_{FS}\,10^{-0.5/20}\)。旧 `VREF × 0.45` 只保留为诊断对照，
不再与生产 pipeline 混用。SFDR spur 搜索包含 H2–H7；noise mask 不会
错误地屏蔽谐波。

## 9. 验证分层

| 层级 | 方法 | 结论 |
|---|---|---|
| 理想基线 | 数学量化器 vs 物理 CDAC | 物理模型达到 11.944 bit |
| 高段隔离 | 低段/bridge 理想 | 校准链本身可达约 11.86 bit |
| 全 CDAC MC | 100 seeds，0.5% | 动态门通过 |
| P/N oracle | 独立真实权重 | 校准接近物理上限 |
| sampled static | 每 64 codes | 只能筛查，不能签核 |
| full static | 4094 transitions | 发现缺码与回退 |
| carry audit | 100 P/N weight sets | 91/100 H4 margin 为负 |

## 10. 为什么不是完整 Shen 论文复现

当前项目只采用了 Shen 的 comparator-observable force 与递归权重思想。
论文级架构还包含当前模型没有实现的：

- 三组 trial-group redundancy，而不是单一 H1R；
- 每 bit reservoir charge-sharing；
- 非采样 bit dither；
- 最多 10 次 LSB repeat；
- SRM 残差估计路径；
- flash 前端和论文对应的三段 DAC 划分。

因此准确表述是 **Shen-derived 12-bit split-CDAC calibration**。完整论文复现
应另建 paper-exact profile，并分别验证 calibration-only、
LSB-repeat-on/SRM-off 和 SRM-on。

## 11. 已确认的静态根因

![Static risk](assets/figures/fig10_static_codebook_risk.png)

权重估计误差降低并不保证 codebook 单调。单 H1R 的 H4 carry margin 在
100-seed 中 P50 为 -1.916 Q0，91/100 为负。2048 pairs 时权重更接近
oracle，但仍出现 2 缺码和 2 回退，证明这不是平均噪声问题。

可能的工程方向：

1. 增加与 carry group 对应的可观测冗余；
2. 增加 monotonic codebook/LUT 校准；
3. 重构为 paper-exact 三冗余 profile。

在其中一种方案实现并重新跑 full-static MC 之前，不能宣称全规格通过。
