# Python 校准模型交接入口

本文件只提供代码入口，不再复制会随正式矩阵变化的性能数字。权威顺序为：

1. 根目录 `spec.yml`：当前验收口径；
2. `docs/MODELING_GUIDE.md`：CDAC、采样、校准与解码定义；
3. `evidence/mismatch_matrix/mismatch_matrix_summary.json`：冻结结果；
4. `docs/final_report.pdf`：结论、证据边界与流片前缺口；
5. `scripts/reproduce.ps1`：测试和复现入口。

## 当前主问题

主验证研究单位电容失配对 12-bit SAR ADC 的影响。正常转换路径不注入噪声。
校准测量的 `0.3 mV RMS` 扰动只用于判断 lower-SAR 量化锁定是否影响失配
校准；它不是本项目的主要性能自变量。

正式失配方式是 PER-UNIT：每个 Cu 独立高斯抽样后再按物理 group 求和，
P/N 两侧独立。递归校准权重每完成一个 target 都截断到 Q8，与 RTL
寄存器和 lower-SAR accumulator 一致。

## 快速命令

```powershell
# 单元/回归测试
python -m pytest

# 快速单场景验证
.\scripts\reproduce.ps1 -RunPipeline -Seeds 8 `
  -MismatchSigma 0.005 -CalibrationNoiseSigmaV 0

# 完整理想/失配/校准扰动矩阵
.\scripts\run_mismatch_matrix.ps1 -Seeds 100 -AveragePairs 128
```

## 关键实现边界

- Python 是行为级 L2 证据，不是晶体管级或版图后签核。
- `rtl/` 当前实现 calibration FSM 与 lower-SAR，不是完整 ADC RTL。
- `va/` 已完成结构复核，但本机没有 Spectre，因此没有编译/波形签核。
- 严格局部单调只作诊断；总验收以动态性能、缺码和 code-density DNL/INL
  为准。
