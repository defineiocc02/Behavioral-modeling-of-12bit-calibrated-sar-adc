# SAR ADC 工程组织与权威边界

本文定义 v3.1.0 工程的目录职责、跨语言接口、证据流和当前缺口。它回答的不是
“仓库里有哪些文件”，而是每一层为什么存在、上游输入是什么、向下游交付什么，
以及哪一份实现对哪类结论具有权威性。

## 1. 总体分层

工程按六条相互关联、但不得混为一谈的链组织：

1. `spec.yml` 与 `src/python_cal/config.py`：版本化规格和共同参数；
2. `src/python_cal/`：行为级黄金模型、校准算法、解码器与验收逻辑；
3. `rtl/`：可综合的前景校准与递归 lower-SAR 子系统；
4. `va/`：CDAC 和比较器的 Verilog-A 混合信号移植骨架；
5. `scripts/` 与 `evidence/`：正式运行、汇总、冻结、图表、综合和复现；
6. `docs/` 与 CI：面向审查者的报告、状态、版本边界和自动回归。

```text
spec.yml / config.py
        |
        v
Python physical model -> calibration -> decoder -> validation
        |                    |             |
        | Q8 contract        |             +-> CSV/JSON summaries
        v                    v
Verilog-A equations      SystemVerilog calibration subset
        |                    |
        +------ pending AMS integration ------+
                             |
                             v
              evidence/ frozen artifacts
                             |
                  figures + LaTeX macros
                             |
                             v
                    XeLaTeX final PDF
```

Python 是本轮架构和失配统计的行为级黄金链路；RTL 只覆盖校准控制、权重寄存器和
校准用 lower-SAR；Verilog-A 是待接入 Spectre/AMS 的模拟行为骨架。三者是不同
证据层，不能互相替代。

## 2. Python 行为模型

### 2.1 配置与拓扑层

- `src/python_cal/config.py`
  - 定义 15 个决策 stage、14 个物理电容、标称单位数、参考电压、Q8 校准权重和
    Q2 输出格式；
  - 明确失配模式为 `PER-UNIT`，而不是给所有 capacitor group 施加相同相对误差；
  - 是 Python 运行参数的唯一代码级入口。
- `src/python_cal/topology/capacitor.py`
  - 表示单个物理电容组及其单位数；
  - 区分物理电容 stage 与 comparator-only terminal stage。
- `src/python_cal/topology/cdac_topology.py`
  - 构建高段、bridge 和低段；
  - 支持 P/N 两侧独立的已实现电容值；
  - 不求解电压，只定义连线和元件。
- `src/python_cal/topology/switch_state.py`
  - 表示每个 bottom plate 所接的 `VINP/VINN/VCM/VREFP/VREFN`；
  - P/N switch state 相互独立。
- `src/python_cal/topology/switching_policy.py`
  - 生成 sampling、reset、trial 和 commit 状态；
  - 正常转换时高低两段均参与输入采样；
  - stage 14 只产生比较决策，不驱动物理电容。

这一层的输出是“拓扑 + 开关状态”，而不是 ADC code。它刻意不包含校准算法，
以防算法层通过修改物理决策掩盖失配。

### 2.2 物理求解层

- `src/python_cal/physical/charge_state.py`
  - 保存 sampling 时 P/N 两侧 top/bridge 节点电荷；
  - 使后续切换只通过电荷守恒求解。
- `src/python_cal/physical/charge_solver.py`
  - 每侧求解一个 top/bridge 两节点矩阵；
  - sampling 时只把 top node 钳位到 VCM，bridge node 保持浮动；
  - differential solver 将 P/N 两侧组合成比较器输入。
- `src/python_cal/physical/differential_cdac.py`
  - 组合 topology、switching policy、sampled charge 和 solver；
  - 提供 sample、apply switch state、solve current 和 physical weight extraction；
  - 物理权重 oracle 由同一电荷方程计算，不由校准结果反推。

这一层是 Python 与 `va/cdac_behavioral.va` 的方程等价边界。若两者不同，优先检查
采样电荷、bridge 浮动条件和 P/N 独立性，而不是调整 FFT 或验收门槛。

### 2.3 比较器与异步控制

- `src/python_cal/comparator/dynamic_comparator.py`
  - 将差分 top-node 电压映射为 polarity、decision delay 和结果；
  - 支持 offset/noise 参数，但正式 normal-conversion matrix 设为零噪声。
- `src/python_cal/async_control/handshake.py`
  - 执行 15-stage trial/commit；
  - 保存每一步的开关状态、比较器结果和时序事件；
  - 决策由物理 CDAC 产生，不由 decoder 产生。
- `src/python_cal/async_control/sar_fsm.py` 与 `events.py`
  - 定义控制状态和事件语义；
  - 用于 trace 与时序审查，不承担数值校准。
- `src/python_cal/conversion/async_sar_adc.py`
  - 组合 CDAC、comparator、controller、calibrator 和 decoder；
  - 暴露 normal conversion、batch conversion、calibration 与多种 decode 输出；
  - 是 Python 模型的应用层 façade。

### 2.4 前景校准

- `src/python_cal/calibration/shen_switching.py`
  - 构造 P0、P1、N0、N1 force 状态；
  - 不执行 averaging 或 decoder 更新。
- `src/python_cal/calibration/shen_calibrator.py`
  - 对 H1、H2、H4、H8-R、H8-A、H16、H32 依次校准；
  - 每个 target 执行 `4 × 128` 个 lower-SAR subconversions；
  - 已校准高段递归加入后续 target 的 lower ruler；
  - 每个 target 写回时立即按 RTL 算术右移语义截断到 Q8；
  - 0.3 mV RMS 只可注入这些校准比较，不进入 normal conversion。
- `src/python_cal/calibration/calibration_fsm.py`
  - 定义算法状态名和 operating mode；
  - 用于使 Python trace 与 RTL state intent 可对照。

校准的输出是 P/N 分侧七个 Q8 权重。它不改物理电容、不重跑已经发生的 normal
conversion decisions，也不引入 LUT、排序或单调钳位。

### 2.5 数字重构

- `src/python_cal/decode/sar_decoder.py`
  - 使用 15 个 P/N 权重直接重构；
  - 提供 integer、float、Q-format 与 detailed decode；
  - formal dynamic acceptance 使用 Q2-to-Q2 公平比较；
  - physical-weight oracle、nominal 和 calibrated 三路读取同一组 decisions。

decoder 是失配校准的作用点。若“校准后性能改善”，必须来自数字权重更接近物理
权重，而不是来自重新决策、重新采样或改变输出量化口径。

### 2.6 验证与正式 pipeline

- `src/python_cal/validation/fft_protocol.py`
  - 规定 coherent FFT 点数、bin、幅度、相位、VFS 测量和 clipping 检查。
- `src/python_cal/validation/reachable_codebook.py`
  - 遍历精确可达 decision tree；
  - 计算 missing code、code-density DNL/INL、float/integer backstep、
    rollback 与受影响输入宽度；
  - 不排序或修改输出。
- `src/python_cal/validation/acceptance.py`
  - 将 dynamic、code-density static 与 monotonic diagnostic 分开；
  - strict monotonicity 默认不是当前 release hard gate。
- `src/python_cal/validation/summarize_mismatch_matrix.py`
  - 只读取完整正式 CSV/JSON；
  - 生成跨 case 的 yield、尾部统计、transfer-integrity 和 provenance hash。
- `src/python_cal/run_final_calibration_pipeline.py`
  - 生成 PER-UNIT mismatch；
  - 运行校准、同决策三路解码、FFT 与精确静态审计；
  - 输出每种子 CSV、case summary 和 run manifest。

## 3. SystemVerilog RTL

### 3.1 当前 top 与模块职责

- `rtl/cal_top.sv`
  - 当前可综合 top；
  - 实例化 `cal_fsm`、`cal_weight_reg` 和 `sar_subconverter`；
  - 暴露时钟/复位/start/comparator、四组 P/N high/low switch buses、
    P/N 权重和 done/fail；
  - 参数默认值：7 targets、128 pairs、20-bit Q8 weight、24-bit lower sum、
    32-bit accumulator。
- `rtl/cal_fsm.sv`
  - 16 个状态；
  - 每 pair 严格运行 P0、P1、N0、N1；
  - `raw_delta_P=P0-P1`，`raw_delta_N=N1-N0`；
  - 最后一对先纳入累加，再右移 `log2(128)+1` 得到 Q8；
  - ±20% 只是失控 sanity check，不是 ADC 精度验收。
- `rtl/cal_weight_reg.sv`
  - P/N 各 7 项、每项 20-bit Q8；
  - reset 时装载 nominal values；
  - synchronous write、combinational read。
- `rtl/sar_subconverter.sv`
  - 5-state calibration-only lower-SAR；
  - 目标从 H1 到 H32 时 lower-stage 数由 8 增到 14；
  - 已校准 high-stage 从 register file 读取分侧 Q8；
  - low segment 和 terminal 继续使用 nominal base ruler；
  - 输出 24-bit signed Q8 sum。

### 3.2 时序和数据量

默认配置执行：

- `7 × 4 × 128 = 3584` 个 lower-SAR subconversions；
- `4 × 128 × (8+9+10+11+12+13+14) = 39,424` 次 lower comparator
  decisions；
- 按当前同步 FSM、每个 lower stage 使用 TRIAL/COMMIT 两周期，并计入
  SAMPLE/DONE/handshake 和 target 边界，纯数字 schedule 约 94,115 clocks；
- 100 MHz 下约 0.941 ms。

0.941 ms 只是 RTL schedule，不包含真实 CDAC settling、comparator ready、
metastability recovery 或 reference recovery。当前 RTL 没有 comparator-ready 输入；
集成时必须证明一次 trial/commit 周期满足模拟最差 PVT，或增加明确握手。

### 3.3 已验证与未覆盖

`rtl/tb_cal_rtl.sv` 自检：

- 7/7 target commit；
- P0/P1/N0/N1 全部出现；
- 最后一对正确进入平均；
- Q8 位宽和 P/N 写回正确。

`rtl/tb_sar_subconverter.sv` 自检：

- H32 lower ruler 使用前六项已校准 P/N 权重；
- P/N signed sum 极性正确；
- 未退回全 nominal ruler。

当前 RTL 不包含：

- normal-conversion 15-stage SAR sequencer；
- Q2 normalization/decoder；
- 完整 ADC top；
- comparator-ready 异步握手；
- CDC、reset release、DFT/scan；
- ASIC synthesis、CTS、place-and-route 或 signoff STA。

因此 `cal_top` 不能被描述成“完整 ADC RTL 已签核”。

## 4. Verilog-A

### 4.1 `va/cdac_behavioral.va`

- P/N 两侧各自有 top node、bridge node、7 high 和 7 low bottom ports；
- 采样端口为 `VINP`、`VINN` 和 `SAMPLE`；
- 每侧使用独立两节点 charge-conservation matrix；
- sample 时只钳位 top node，bridge node 由 bridge/low capacitive divider 决定；
- `P_MC_*`/`N_MC_*` 是外部传入的 realized group multipliers；
- 模块内不做随机抽样，避免 simulator RNG 与 Python seed 失去一一对应。

### 4.2 `va/strongarm_cmp.va`

- 行为级 clocked comparator；
- 参数包括 offset、可选输入等效噪声、基础延迟、再生时间常数、最小差分电压和
  最大等待时间；
- 输出 result 和 ready；
- 延迟使用输入差分相关的对数模型并设置上限。

它不是 transistor StrongArm，也不能给出真实 kickback、输入电容、PVT offset/noise、
metastability tail 或功耗。

### 4.3 计划中的 AMS 接口

预期 AMS testbench 应完成：

1. 将 RTL 的 2-bit switch encoding 映射到模拟 rail connections；
2. 用 Python 同一 realized PER-UNIT seed 生成各 Verilog-A group multipliers；
3. 将 `strongarm_cmp.va` 的 result/ready 接回数字控制；
4. 对同一 stimulus 保存 decisions、top/bridge waveforms 和 decoded output；
5. 与 Python trace 做逐 stage 交叉检查。

本轮没有可用 Spectre/OpenVAF 编译器，因此以上仍是待闭环接口，不是已完成结果。

## 5. 脚本、证据与文档

- `scripts/run_mismatch_matrix.ps1`
  - 启动理想、0.5%、1.0% 及 zero/0.3 mV calibration-only 条件；
  - 保持 seed、FFT 和 pairs 一致。
- `scripts/freeze_mismatch_evidence.py`
  - 只把完整 case 的 CSV、summary 和 manifest 复制到跟踪的 `evidence/`；
  - 不修改数据。
- `scripts/generate_report_metrics.py`
  - 从冻结总 summary 生成 LaTeX macros；
  - 避免在报告正文手抄数据。
- `scripts/generate_report_figures.py`
  - 只读取冻结 CSV/JSON；
  - 输出 PDF/SVG/PNG；
  - 图内使用英文，报告正文使用中文。
- `scripts/synth_cal.tcl` 与 `scripts/timing.xdc`
  - 对 `cal_top` 做 Vivado 2018.3 synthesis proxy；
  - 输出 utilization、setup/hold summary 和 timing completeness check；
  - 不是 ASIC flow。
- `scripts/reproduce.ps1`
  - 汇总测试、矩阵、图表和报告的最短复现路径。

`evidence/mismatch_matrix/` 是正式报告数据的唯一来源。工作目录下的
`src/python_cal/validation_results/` 可以重跑和比较，但不能绕过 freeze/provenance
直接进入最终图表。

## 6. 综合与时序证据如何解释

目标 part 是 `xc7z020clg400-1`，只作为综合代理：

- 449 LUT、595 FF、0 DSP、0 BRAM；
- 100 MHz setup WNS `+0.298 ns`，0 个 setup failing endpoints；
- hold WHS `-0.147 ns`，4 个 failing endpoints，THS `-0.436 ns`；
- hold failures 来自 raw FPGA top 的 `start`/`cmp_out` 输入路径；
- timing completeness check 无 missing clock、missing I/O delay、unconstrained internal
  endpoints 或 combinational loop；
- 342/125 bonded IOB，273.6%，raw parallel top 无法在该 FPGA package 布局布线。

因此正确结论是：

- 校准逻辑可综合，setup 在当前 unplaced synthesis estimate 下满足 100 MHz；
- 当前约束全集并未全部满足，因为 hold 仍有 4 个端点；
- IOB overuse 说明 `cal_top` 是 ASIC-internal interface，不是直接可用 FPGA package top；
- FPGA 原型必须增加 serialized/packed wrapper，之后重新 implementation、hold repair
  和 post-route timing；
- ASIC 仍需目标库、真实 I/O/clock 模型、CTS 和 signoff STA。

## 7. 版本与维护规则

1. 改算法前先修改/增加 Python unit test，再同步 RTL contract；
2. 改 Q-format、stage map 或 switch encoding 时，必须同时检查 Python、RTL、VA 和报告；
3. 正式矩阵重跑后先生成 working summary，再 freeze，最后要求两份总 summary 字节一致；
4. 当前报告只引用 `docs/figures/mismatch_report/`；
5. 旧版本图和结果只进入 `docs/archive/<version>/`；
6. 图表必须单独视觉检查，PDF 嵌入后还需逐页检查；
7. 任何 PDK、transistor、layout 或 silicon 结论必须引用对应层的新证据，不能从行为级
   100-seed result 外推。
