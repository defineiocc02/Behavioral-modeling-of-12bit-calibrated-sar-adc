# v3.1 建模与实现指南

## 1. 设计边界

模型把三条路径严格分离：

- 物理路径：采样、split-CDAC、电荷守恒、比较器和异步 SAR；
- 校准路径：只观察 comparator decisions，不读取物理 oracle；
- 验证路径：允许读取真实 P/N 权重，用于误差归因和上限比较。

校准权重不会反馈改变物理 decision。测试会把 oracle API 替换成异常函数，
确保生产校准没有偷读真实电容。

## 2. 电容与桥接权重

每侧：

```text
CH = 32+16+8+8+4+2+1 = 71 Cu
CB = 2 Cu
CL = 32+16+8+4+2+2+1 = 65 Cu
```

对两节点 split array，低段单位权重取 `CB = 2 Q0`，高段单位权重为
`CL + CB = 67 Q0`，因此：

```text
High: 32×67, 16×67, 8×67, 8×67, 4×67, 2×67, 1×67
Low:  32×2,  16×2,  8×2,  4×2,  2×2,  2×2,  1×2
Term:  1 Q0 comparator-only rounding decision
```

物理 signal-weight 总量是 `4887 Q0`。输出仍为 12-bit，decoder 统一缩放到
`0..4095`。

## 3. 全阵列采样

采样阶段：

```text
P-side all high/low bottom plates -> VINP
N-side all high/low bottom plates -> VINN
bridge capacitor -> internal floating series element
VTOP_P/VTOP_N -> VCM; VBRIDGE_P/VBRIDGE_N remain floating
```

复位后所有 14 个 bottom plates 回到 VCM，保存的电荷产生满幅差分输入。
低段不再被当成只供校准的隐藏 DAC，因此理想初始差分增益为 1。

## 4. 普通异步 SAR

每个物理 stage：

1. 当前 P/N 电容同时 trial 到 VREFP；
2. 求解 P/N top 与 bridge 节点；
3. comparator 决定保留 P 侧或 N 侧；
4. commit 后进入下一 stage。

最后 stage 14 只比较当前残差，不切换物理电容。一次转换有 15 次比较，
比退役版本多 1 次。

## 5. 校准量尺与冗余

Chen 等 2024 给出的通用判据是：被测位以下的可用权重之和减去被测权重，
必须覆盖 comparator offset 与最大噪声。它说明冗余不能只看“总共多了多少
电容”，而应逐目标检查 backend coverage。

本设计的关键 nominal margin：

```text
H32/H16/H8-A: 600 Q0
H8-R/H4/H2/H1: 64 Q0
L32..L4: 3 Q0
```

主比较器足以从 H1 开始校准，但不适合从 L4 开始校准；因此完整低段作为
匹配基准尺。这个取舍不复制 Chen 的 auxiliary comparator，只采用其
“按局部 backend range 检查冗余”的思想。

校准公式：

```text
W_P = mean(S_P0 - S_P1) / 2
W_N = mean(S_N1 - S_N0) / 2
```

当前主验证关闭额外 dither（`SHEN_DITHER_LSB=(0.0,)`）。高段 7 targets、
默认 128 pairs，总子转换次数 3584。正式矩阵分别运行 0 mV 校准扰动和
0.3 mV RMS 比较器输入等效扰动；后者只用于解除重复 lower-SAR 整数结果的
量化锁定，不进入正常转换。RTL 的 lower-SAR 使用已提交的 P/N Q8 高段
权重递归构造下一目标的量尺；每个目标写回时截断到 Q8，低段与 terminal
仍是标称基准尺。Python 采用完全相同的逐目标 Q8 格点。

## 6. 解码

对 decision `d_i`：

```text
signed_sum += W_P[i]   if d_i == 0
signed_sum -= W_N[i]   if d_i == 1
```

所有 14 个物理 stage 都是 signal stage。P/N 中心为：

```text
center = (sum(W_P_signal) + sum(W_N_signal)) / 2
code_f = (signed_sum + center) * 4095 / total_signal_range
```

活动 decoder 只有上述加权和。Q2 仅保留两个小数位，避免把校准后的分数
权重再次粗暴量化成整数；它不增加 CDAC 或比较周期。

## 7. 静态验证

`validation/reachable_codebook.py` 不假设传递函数单调，而是递归求解每个
可达 decision prefix 的输入区间。报告：

- reachable leaves；
- unique/missing integer codes；
- float/integer local backsteps；
- maximum integer jump；
- exact code-density DNL/INL。

code-density DNL 把同一 code 的所有不相交输入区间宽度相加，等价于无限
慢、无限样本 ramp histogram。形式化 backstep 是更强的诊断，两者分别报告。

## 8. 动态验证

正式 FFT 先用 nominal decoder 二分测量每个 seed 的正向 VFS，再生成：

```text
N = 4096
k = 1019, gcd(k,N)=1
phase = 0.123 rad
amplitude = VFS × 10^(-0.5/20)
window = rectangular
```

输入先检查 clipping。SNDR、SFDR、ENOB 的 calibrated、integer-12 和
physical-oracle 版本均由同一组物理 decisions 解码，避免不同 stimulus
或旧 VFS 混用。

## 9. 硬件资源

相对退役的 128 Cu / 14-comparison 模型：

| 资源 | v3.1 |
|---|---:|
| CDAC | 138 Cu/side，+7.8% |
| normal comparisons | 15，+1 |
| calibration sub-conversions | 3584（128 pairs） |
| calibrated registers | 14 P/N weights + terminal constant |
| decoder | signed MAC + common normalization + Q2 round |
| LUT / CAM / SRAM exception table | 0 |
| auxiliary calibration comparator | 0 |

删除或不实现的过度设计包括：512-pair 默认平均、calibration sub-DAC、
auxiliary comparator、decision-word LUT/CAM、单调 clamp、额外 dither
DAC、双份 comparator Verilog-A 和未使用的 RTL accumulator/CDAC 模型。
这些删减不改变物理 decision，只移除当前证据不需要的硬件或重复路径。

## 10. 不能外推的结论

当前结果不包含 comparator transistor noise model、settling PVT、reference
droop、switch charge injection、layout parasitics 或 silicon histogram。
这些必须在 Verilog-A/transistor/post-layout 阶段重新验证。
