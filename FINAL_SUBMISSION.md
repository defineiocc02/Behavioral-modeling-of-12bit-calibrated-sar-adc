# v3.1.1 最终交付说明

## 交付结论

本次交付围绕一个问题收口：PER-UNIT 电容失配会怎样影响 12-bit SAR ADC，
以及前景权重校准能否把失配后的整体性能稳住。

当前证据支持：

- 理想 CDAC、全阵列采样、15 次比较和 Q2 重构正确；
- 失配会显著降低 nominal decoder 的 SNDR；
- 七目标 P/N 权重校准能把 nominal 0.5% mismatch case 恢复到接近
  physical-weight oracle；
- 0.3 mV RMS 是校准比较器输入等效扰动，不是正常转换噪声；
- 局部 backstep 是诊断，不单独否决当前应用；
- Python 与 calibration/lower-SAR RTL 已统一到逐目标 Q8；
- Verilog-A 的 split-CDAC 与 comparator 已通过隔离 VM Spectre standalone smoke；
- 仍缺完整 ADC RTL、full-ADC AMS、目标 PDK、PVT、PEX 和硅片验证，
  因此不能声称“已经可以直接流片”。

## 权威交付物

| 交付物 | 路径 | 用途 |
|---|---|---|
| 最终报告 | `docs/final_report.pdf` | 完整结论、方程、图表、风险和流片缺口 |
| 报告源文件 | `docs/final_report.tex` | XeLaTeX 可重建源 |
| 冻结矩阵 | `evidence/mismatch_matrix/` | CSV、JSON、run manifest、SHA-256 |
| VM standalone 证据 | `evidence/vm_sandbox/current_git_74e7366/` | Spectre/Xcelium 状态、TB、runner、日志摘要和 SHA-256 |
| 当前规格 | `spec.yml` | 验收口径与场景定义 |
| 建模指南 | `docs/MODELING_GUIDE.md` | CDAC、采样、校准、解码和验证协议 |
| 硬件/VA说明 | `docs/HARDWARE_AND_VERILOGA_PORT.md` | RTL资源、接口与移植边界 |
| 验证状态 | `docs/VALIDATION_STATUS.md` | 正式数值与测试状态 |
| 版本管理 | `docs/VERSION_MANAGEMENT.md` | 活动、冻结、历史与临时产物边界 |
| 复现入口 | `scripts/reproduce.ps1` | 测试、矩阵、图表和 PDF |

性能数字只以冻结 evidence 和由其生成的报告为准。历史 v3.0 结果保留在
`docs/archive/v3.0/RELEASE_RESULTS_V3.md`，不进入当前发布路径。

## 正式场景

| 场景 | 失配 | 校准比较器扰动 | 正常转换噪声 | 定位 |
|---|---:|---:|---:|---|
| Ideal | 0 | 0 | 0 | 理想自检 |
| M0.5-Z | 0.5% PER-UNIT | 0 | 0 | 纯失配/量化锁定隔离 |
| M0.5-N | 0.5% PER-UNIT | 0.3 mV RMS | 0 | nominal acceptance |
| M1.0-Z | 1.0% PER-UNIT | 0 | 0 | 压力对照 |
| M1.0-N | 1.0% PER-UNIT | 0.3 mV RMS | 0 | margin stress |

除 ideal 为 1 seed 外，每个 mismatch case 使用 seeds 10000–10099、
128 calibration pairs、4096-point coherent FFT 和精确可达静态审计。

## 实现一致性

### Python

- 每个单位电容独立高斯抽样，再组成 group；
- P/N 侧分别抽样与校准；
- lower-SAR 使用此前提交的高段权重递归构造量尺；
- 每个 target 立即按 RTL 语义截断到 Q8；
- pre/cal/oracle 共享物理 decisions，统一使用 Q2；
- integer-12 只作二次量化诊断；
- 无 oracle leakage、LUT、DP remap、CAM 或 monotonic clamp。

### RTL

- 七目标 P0/P1/N0/N1 calibration FSM；
- 24-bit signed Q8 lower-SAR sum；
- 20-bit Q8 P/N high-weight registers；
- 最后一对样本正确计入平均；
- 校准失败显式输出；
- lower-SAR 读取已校准 P/N 权重，而非固定 nominal ruler。

当前综合只覆盖 calibration/lower-SAR：

```text
Vivado 2018.3, xc7z020clg400-1, 100 MHz
449 LUT, 595 FF, 0 DSP, 0 BRAM
setup WNS +0.298 ns, 0/2101 failing endpoints
hold WHS -0.147 ns, THS -0.436 ns, 4/2101 failing endpoints
bonded IOB 342/125 (273.60%)
```

因此当前 unplaced synthesis estimate 的 setup 通过，但完整 timing constraints
并未通过；失败点是三条 `start` 输入路径和一条 `cmp_out` 输入路径。
raw parallel `cal_top` 也无法在该 FPGA package 上布局布线。结论仅是内部
校准逻辑可综合，不是 FPGA implementation 或 ASIC STA signoff。

### Verilog-A

- `cdac_behavioral.va`：P/N 独立 bottom plates、PER-GROUP realized mismatch
  参数、SAMPLE 下降沿电荷捕获、两节点精确矩阵；
- 只有 VTOP 在采样时钳到 VCM，VBRIDGE 保持内部浮动；
- `strongarm_cmp.va`：统一极性、1.8 V 输出、offset/noise、输入相关 delay
  和 ready；
- `strongarm_cmp.va` 已通过 Spectre standalone smoke：0 errors、0 warnings；
- `cdac_behavioral.va` 已通过 Spectre standalone smoke：0 errors、4条
  `VACOMP-1116`；警告来自连续信号 `transition()`，full-ADC AMS 前仍需处理或论证；
- standalone PASS 不替代 Python/RTL/VA 同 seed trace、PVT、transistor 或 post-layout。

## 消除的过度设计

- 512 pairs 降为 128 pairs；
- 不增加 calibration sub-DAC；
- 不增加 auxiliary comparator；
- 不增加 dither DAC；
- 不增加 decision LUT/CAM、异常表或单调钳位；
- 删除重复 comparator Verilog-A；
- 删除未使用的 RTL accumulator/CDAC model；
- 删除 bridge-node sampling clamp；
- 删除旧的矛盾综合报告和未使用配置常量；
- 删除无 PDK 证据的 foundry、面积、功耗和良率结论。

保留 Q2、Q8、P/N 分侧权重和 comparator-only terminal 是因为它们分别
对应已测性能、RTL一致性、独立失配可观测性和残差舍入，不属于无收益堆料。

## 流片前必须补齐

1. 使用目标 PDK MOMCAP 和 mismatch Monte Carlo 替换 4 fF/0.5%/1.0%
   行为假设；
2. 完成 sampling switch 的 Ron、settling、charge injection、
   clock feedthrough 和可靠性；
3. 完成 comparator offset/noise/metastability/kickback 的 transistor PVT；
4. 完成 reference buffer、droop、switching energy 和 package impedance；
5. 补齐 normal SAR、Q2 decoder、CDC/reset/DFT 和 ASIC synthesis/STA；
6. 运行 Spectre/AMS trace cross-check、PVT/MC 和 post-layout extraction；
7. 用硅片 coherent FFT、code-density 与前景校准时间/良率重新验收。

## 复现

```powershell
python -m pip install `
  -c requirements\report-render-py313.txt `
  -e ".[dev,docs]"

$env:PYTHONPATH = (Resolve-Path src).Path
python -m pytest

.\scripts\run_mismatch_matrix.ps1 -Seeds 100 -AveragePairs 128
python -m python_cal.validation.summarize_mismatch_matrix
python scripts\freeze_mismatch_evidence.py
python -m python_cal.validation.summarize_mismatch_matrix `
  --root evidence\mismatch_matrix

python scripts\generate_report_figures.py `
  --matrix-root evidence\mismatch_matrix
python scripts\generate_report_metrics.py
python scripts\generate_vm_evidence_manifest.py
.\scripts\reproduce.ps1 -BuildPdf
```

完整矩阵耗时较长；提交中已经冻结正式证据，日常代码回归可只运行
`python -m pytest`。
