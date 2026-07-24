# 12-bit 异步 SAR ADC / Shen 校准根因报告

日期：2026-07-24
范围：`src/python_cal` 当前生产候选；Shen 2018 JSSC 论文只作为算法与架构契约。

## 结论先行

“理想 12 位只能得到约 11 位”不是 CDAC 的物理上限，也不是当前
`-0.5 dBFS` 输入太小。主因是旧解码链在物理 SAR 已量化一次以后，
又把分数校准重构码舍入成 12-bit 整数，加入了第二份近似独立的量化
噪声。对同一组物理 decisions：

- 12-bit 整数物理 oracle 约为 70.6～70.9 dB；
- Q2（保留 2 个小数位）物理 oracle 约为 73.25～73.45 dB；
- 差值约 2.5～2.9 dB，接近两个等量量化噪声相加的理论 3.01 dB。

模型修正后，理想物理 CDAC 为 73.666 dB / 11.944 bit；因此模拟器、
桥接 CDAC 和输入幅度都能达到完整 12-bit 量化极限附近。

校准本身的动态结果也已越过门槛：在高段、低段和 bridge 都包含
0.5% unit-cap mismatch 的 100-seed 回归中，100/100 校准有效，校准后
SNDR P50=73.112 dB、ENOB P50=11.852 bit，物理 Q2 oracle
P50=73.322 dB / 11.887 bit，oracle gap P50=0.222 dB、P95=0.524 dB。
94/100 个样本 gap 不超过 0.5 dB，99/100 不超过 1.0 dB，负校准增益为
0/100。动态规格通过，但顶层验收仍因完整静态单调性未通过而判为 FAIL。

但不能把这写成“完整 Shen 论文复现”或“全规格签核”。完整 4095
transition 静态检查发现单 H1R 架构的 carry codebook 仍缺少确定性
单调裕量。512 对平均时无缺码但 DNL 峰值为 +1.00047 LSB；2048 对
平均时权重更准，却出现 2 个缺码/2 个相邻回退，DNL=-1 LSB。真实
P/N 物理权重 oracle 也在四个 H4 carry 边界出现 -0.25 LSB Q2 回退，
证明剩余问题属于架构/数字 codebook，而不是增加平均次数可以解决。

## 为什么不是输入幅度

统一 FFT 协议为：

- `N=4096`；
- coherent bin `k=127`，`gcd(127,4096)=1`；
- phase `0.123 rad`；
- 幅度 `-0.5 dBFS`；
- VFS 由当前物理转换动态二分测得；
- 同一组 `vin` 和 decisions 用于 nominal/calibrated/oracle 对比。

理想模型实测 VFS=0.89934075 V，输入峰值=0.84903242 V，无削顶。
数学理想为 73.592 dB / 11.932 bit，物理理想为 73.666 dB /
11.944 bit。

旧脚本使用固定 `0.45*VREF` 再乘 `-0.5 dBFS`，峰值只有
0.76468931 V，理想物理结果为 72.657 dB / 11.777 bit。旧幅度会
损失约 1.01 dB，但仍明显高于 11.5 bit，不能解释先前约 70 dB 的
“11 位上限”。`run_srm_off_isolation.py` 当前已经使用动态 VFS，
不存在与主 pipeline 混用 `VREF*0.45` 的问题；固定幅度只保留在
`run_baseline_diagnosis.py` 的显式 legacy 对照项中。

证据：

- `validation_results/baseline_diagnosis/baseline_diagnosis.json`
- `validation/fft_protocol.py`
- `run_srm_off_isolation.py`

## 为什么旧电容模型也压低了上限

旧 Python 拓扑同时存在三项互相冲突的假设：

1. VA/配置把 stage 13 定义为 comparator-only terminal，Python 却
   额外放入一个 0.5Cu `low_term` 物理电容；
2. 低段总电容因此从设计值 63Cu 变成 63.5Cu，但 bridge 仍为 2Cu，
   低段衰减不再精确为二进制；
3. Python 让所有电容采输入，配置与 VA 却要求低段 calDAC 和 H1R
   正常采样时接 VCM。

这会让理想低段权重变成约 63.511、31.756、…、0.992 Q0，而不是
64、32、…、1。修正为 13 个物理电容 + 1 个数字 terminal，并执行
VCM sampling mask 后，物理 oracle 精确回到
`[2080,1040,520,260,130,65,65,64,32,16,8,4,2,1]`。

当前契约：

- stage 0..12 是物理电容；
- stage 13 只进行一次残差比较，不切换电容；
- 只有 H32C..H2C 与 H1C-A 采输入；
- H1R、低段 calDAC 和 terminal 正常采样时保持 VCM；
- bridge=2Cu、低段物理总量=63Cu。

## Shen 校准到底哪里错了

### 旧实现不是论文中的半差公式

旧 `shen_calibrator.py` 的注释写“force0/force1 并除以 2”，实际执行
的是：

- baseline：target 接 VCM；
- active：target 从 VCM 切到 VREFP；
- `W=baseline-active`，没有 `/2`。

这不是纯粹的数值 bug：VCM 恰好位于 VREFN/VREFP 中点时，单边半程
测量在理想线性模型中也可以得到 W。但它额外依赖 VCM 中点、单边
线性和锁码对称，不能声称严格复现 Shen。

当前实现改为：

- P0：P target→VREFN，N target→VCM；
- P1：P target→VREFP，N target→VCM；
- `W_P=mean(P0-P1)/2`；
- N0/N1 对称执行，`W_N=mean(N1-N0)/2`；
- 四电平对称固定 dither `(-1.5,-0.5,+0.5,+1.5) LSB` 以输入等效
  行为模型在配对测量中重复，平均比较器失调和量化锁码。它还不是
  论文逐电容 dither 开关网络的电荷级复现。

理想模型在 comparator offset=0、0.5 LSB、1 mV、3 mV、10 mV 时，
均恢复精确的七个高段权重。

### 旧失调配置存在 2276 倍量纲错误

旧 `CAL_OFFSET_SIGMA_V=0.5` 表示 0.5 V，而注释实际想表达 0.5 LSB。
12-bit、1.8 V 参考下，0.5 LSB 只有：

`0.5*1.8/4096 = 0.0002197266 V = 0.2197 mV`。

当前配置按该公式派生，避免把“0.5 LSB”误当成“0.5 V”。

### P/N 物理上限曾被错误平均

MC 电容由独立 P/N 电容数组生成，但旧 pipeline 只读取一个平均物理
权重，并把它同时传给 `weights_p` 和 `weights_n`。这不是严格 oracle，
会掩盖 P/N 总增益和局部失配。当前
`get_physical_weights_per_side_q0()` 分别测量 P/VCM→VREFP 与
N/VCM→VREFP 的真实半参考步进，并只用共同比例因子归一化，两侧
不对称被保留。stage 13 由数字定义固定为 1 Q0。

## 校准前后指标区别

### 理想模型

| 路径 | SNDR | ENOB | 说明 |
|---|---:|---:|---|
| 数学理想量化器 | 73.592 dB | 11.932 bit | `-0.5 dBFS` |
| 修正后的物理 CDAC | 73.666 dB | 11.944 bit | 标称/物理权重一致 |
| 旧固定 0.45VREF 激励 | 72.657 dB | 11.777 bit | 仅 legacy 对照 |

### 0.5% 全 CDAC mismatch，100 seeds，512 pairs，1 mV 校准噪声

| 指标 | 校准前/标称 | 校准后 Q2 | P/N 物理 Q2 oracle |
|---|---:|---:|---:|
| SNDR P50 | 66.939 dB | 73.112 dB | 73.322 dB |
| SFDR P50 | 73.309 dB | 92.820 dB | 94.412 dB |
| ENOB P50 | 10.828 bit | 11.852 bit | 11.887 bit |
| oracle gap P50/P95 | — | 0.222/0.524 dB | 0 dB 定义 |
| 校准有效 | — | 100/100 | — |
| 负增益 | — | 0/100 | — |
| FFT clipping | — | 0/100 | 0/100 |

同一组 calibrated decisions 若在末端强制舍入成整数 12-bit，SNDR P50
从 73.112 dB 降为 70.574 dB，ENOB P50 从 11.852 降为 11.431 bit；
物理 oracle 也从 73.322 dB 降为 70.684 dB。两条路径都损失约
2.54～2.64 dB，故损失来自共同的整数重构，而不是校准器估错权重。

七个目标最大分侧权重误差的 P50/P95（Q0）：

| 目标 | P50 | P95 |
|---|---:|---:|
| H1R | 0.1797 | 0.3765 |
| H1A | 0.1783 | 0.4271 |
| H2 | 0.2663 | 0.7726 |
| H4 | 0.4960 | 1.4442 |
| H8 | 0.8672 | 2.8114 |
| H16 | 1.7687 | 5.5258 |
| H32 | 3.2743 | 10.8503 |

绝对误差随递归权重放大，但归一化比例误差反而在 MSB 端较小；
H32 的比例误差 P95 只有 0.0177%。因此动态性能接近 oracle。

证据：

- `validation_results/final_pipeline/final_summary_a3330136.json`
- `validation_results/final_pipeline/final_pipeline_a3330136.csv`
- `validation_results/final_pipeline/final_report_a3330136.md`

### 高段隔离，低段/bridge 理想，8 seeds

校准后 ENOB P50=11.856、P95=11.889，8/8 大于 11.5 bit；标称
ENOB P50=10.386。生产校准与“物理低段尺子”诊断 oracle 的 ENOB
P50 都为 11.856，说明在该隔离场景中低段尺子不是瓶颈。

证据：

- `validation_results/srm_off_isolation/high_only_summary.json`
- `validation_results/srm_off_isolation/high_only_rows.csv`

### 全 4095 transition 静态结果

seed 70000、高段 mismatch、低段/bridge 理想：

| 模式 | 缺码 | 非单调/相邻回退 | DNL peak | INL peak |
|---|---:|---:|---:|---:|
| 标称 decoder | 0 | 0 | 2.596 LSB | 2.703 LSB |
| 512-pair calibrated | 0 | 0 | 1.00047 LSB | 1.580 LSB |
| 2048-pair calibrated | 2 | 2 | -1.000 LSB | 1.580 LSB |

2048 对时 H32 最大误差从 4.04 Q0 降到 0.89 Q0，却出现两个缺码，
证明“更多平均”不是静态根治方案。

按当前异步 timing model，七目标完整校准时间随 pair 数近似线性：
128/512/2048 对分别为 207.15 us、828.61 us、3.314 ms。2048 对把
校准时间增至 4 倍且没有修复 codebook，因此属于无收益的堆平均，
不应设为生产默认。

用真实 P/N 物理权重在 32769 点密集 ramp 上，Q2 仍出现 4 个
-0.25 LSB 回退；四处都是同一种 H4 carry：

- stage 3 从 1→0；
- stage 4、H1R、H1A、L32 从 0→1；
- L16..terminal 从 1→0；
- 该 seed 的真实加权和变化为 -0.682728 Q0。

在 100 个 0.5% 全 CDAC mismatch 权重样本中，此 carry margin：

- P50 = -1.916 Q0；
- P5 = -3.802 Q0；
- minimum = -4.841 Q0；
- 91/100 为负。

因此单一 H1R 的当前 12-bit codebook 在该 carry 处没有统计裕量。
随意减小 H1R 数字权重只能把回退移动到别的边界：单 seed 减
0.25 Q0 可让整数码单调且 4096 码齐全，但 Q2 仍有 3 个 -0.25 LSB
回退；减 0.5 Q0 可让 Q2 单调，却只剩 4094 个整数码。不能把固定
guard 当成已验证修复。

证据：

- `validation_results/static_signoff/full_static_signoff.json`
- `validation_results/static_signoff_2048/full_static_signoff.json`
- `validation_results/codebook_margin/h4_carry_margin.json`
- `run_codebook_margin_audit.py`

## 哪些是“过度设计/过度假设”

1. **过度要求整数 12-bit 输出保持理想 12-bit SNDR。**
   Shen 校准产生分数权重；强制回到整数会重新量化。Q2 是最小数字
   代价，只增加累加器/输出 2 bit，不增加 CDAC、电容、比较次数或
   转换周期。

2. **过度声称当前代码“严格复现 Shen”。**
   旧代码用 VCM→VREFP 单边测量且没有 `/2`；当前才实现对称
   VREFN/VREFP 半差。即使公式修正，项目架构仍只是 Shen-derived。

3. **把 terminal 过度物理化。**
   为了凑 1 Q0 在低段添加 0.5Cu，反而破坏了 63Cu/2Cu split 比例。
   terminal 应是一次数字残差判决。

4. **把 P/N 平均权重当作真实上限。**
   这会掩盖独立两侧的失配，得到错误 oracle。

5. **假设一个 H1R 足以代表 Shen 的完整 redundancy。**
   原论文有 b12r、b8r、b4r 三个冗余电容，并按 trial group 使用；
   当前项目只有一个 H1R。100-seed carry margin 已证明该简化没有
   静态裕量。

6. **假设论文只是一套权重校准公式。**
   原论文同时依赖三段 DAC、三冗余、非采样 dither、最多 10 次 LSB
   repeat、每 bit 独立 reservoir capacitor，以及可选 SRM。当前项目
   没有 flash 3-MSB、三段完整拓扑、三冗余、reservoir 网络和完整
   LSB-repeat/SRM，不能宣称 paper-exact。

7. **把论文的 SNR 成果误当成理想 16-bit SNDR。**
   论文校准主要修复 reservoir charge-sharing 引起的 INL/SFDR；
   文中等效 ADC noise 约 3 LSB，实测 SNR >78 dB，并非理想 16-bit
   量化噪声极限。要求本项目“校准后整数码必须等于理想 N-bit SNDR”
   比论文目标更严格。

## 当前实现状态

已经完成：

- 13 physical + 1 digital terminal；
- 正确 VCM sampling mask；
- 理想 split-CDAC 权重精确闭合；
- Shen VREFN/VREFP half-difference；
- P/N 分侧校准与真实 P/N oracle；
- 固定对称 dither；
- offset 单位修正；
- Q2/float/int 三种明确解码接口；
- 主 pipeline 动态验收使用 Q2，整数结果保留诊断；
- SFDR 搜索重新包含 H2-H7，不再因复用 noise mask 而虚高；
- 统一动态 VFS、相干 N/k/phase、幅度和削顶检查；
- `src/python_cal/tests` 58/58 通过；10 条 warning 均来自明确 deprecated
  的旧 `AsyncCalibrationController` 兼容测试。

生产证据入口限定为：

- `run_baseline_diagnosis.py`；
- `run_final_calibration_pipeline.py`；
- `run_srm_off_isolation.py`；
- `run_static_signoff.py`；
- `run_codebook_margin_audit.py`。

`close_ideal_baseline.py`、`run_bridge_model_audit.py` 和
`debug_shen_low.py` 已明确标记为历史诊断；`test_observable_alpha.py`
与 `run_deterministic_tests.py` 已标记为 experimental/frozen。它们的
旧幅度、旧单边 force 或 common-alpha 结果不能替代生产验收。

尚未完成、不能伪装为通过：

- 当前单 H1R 架构未通过严格静态 DNL/单调性签核；
- paper-exact 三冗余、reservoir、LSB repeats、SRM 和 flash 前端未实现；
- 旧 `AsyncCalibrationController` 仍保留兼容测试，但带 oracle leakage，
  已明确 deprecated，不能作为生产证据。

## 建议的架构决策

如果目标是“完成当前 12-bit 单 H1R 硬件模型”，应接受：

- 动态生产输出为 Q2；
- 12-bit integer 仅是兼容接口；
- 静态规格必须单列，当前状态为未签核；
- 若必须 `<1 LSB DNL` 且零回退，需要增加可观测的 monotonic codebook
  校准/LUT，或重新分配物理冗余，不能只加平均次数。

如果目标是“完整实现 Shen 论文”，应另建 paper-exact profile：

- 按 12-bit 目标重新分配至少三个 trial-group redundancy；
- 为每个 bit 建 reservoir charge-sharing 模型；
- 非采样 bit 采随机 dither；
- 实现最多 10 次 LSB repeat 的加权和；
- SRM 作为独立可开关残差估计器；
- 分别验证 calibration-only、LSB-repeat-on/SRM-off 和 SRM-on；
- 不能继续把当前 single-H1R split-CDAC 改名为“完整 Shen”。
