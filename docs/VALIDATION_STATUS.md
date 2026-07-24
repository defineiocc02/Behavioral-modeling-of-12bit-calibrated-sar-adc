# v3.0 验证状态

## 发布门

| 检查 | 要求 |
|---|---:|
| unit tests | 全通过 |
| calibration valid yield | 100% |
| calibrated ENOB | 每个 seed > 11.5 bit |
| calibrated SNDR | 每个 seed > 70.99 dB |
| oracle gap P50 | <= 0.5 dB |
| oracle gap P95 | <= 2.0 dB |
| missing codes | 0 |
| maximum integer jump | <= 1 |
| code-density DNL peak | <= 1 LSB |
| code-density INL peak | <= 1 LSB |

正式发布数据由 100 seeds、0.5% unit-cap mismatch、512 calibration pairs、
1 mV RMS calibration noise 和 4096-point coherent rectangular-window FFT
生成。机器可读证据位于 `src/python_cal/validation_results/final_pipeline/`。

## 100-seed 结果

| 指标 | 实测 | 状态 |
|---|---:|:---:|
| valid calibration | 100/100 | PASS |
| calibrated SNDR P50 / min | 74.48 / 74.09 dB | PASS |
| calibrated ENOB P50 / min | 12.08 / 12.02 bit | PASS |
| physical-oracle gap P50 / P95 | 0.156 / 0.412 dB | PASS |
| negative gain | 0/100 | PASS |
| missing codes | 0/100 seeds | PASS |
| maximum integer jump | 1/100 seeds | PASS |
| DNL peak P95 / max | 0.8663 / 0.9501 LSB | PASS |
| INL peak P95 / max | 0.9234 / 0.9572 LSB | PASS |
| formal local backsteps | 27065 total | DIAGNOSTIC FAIL |

最后一项不进入 code-density 发布门；它明确限制了“严格数学单调”的外推，
但没有被删除、排序或用 LUT 修正。详见 [RELEASE_RESULTS_V3.md](RELEASE_RESULTS_V3.md)。

## 已验证

- 理想桥接权重与电荷求解一致；
- 全部 14 个 high/low physical capacitors 参与输入采样；
- 15 次异步 comparison；
- decoder 权重更新不改变物理 decisions；
- 校准路径不读取 physical oracle；
- 相干 FFT 参数、动态 VFS、幅度与 clipping 检查统一；
- 旧固定 `0.45 × VREF` 不再进入正式 pipeline；
- Blackman/Hann 不进入正式 coherent metric；
- 可达码本没有先验单调假设。

## 静态口径声明

发布门采用 silicon 常用的 code-density DNL/INL。形式化局部回退单独列为
diagnostic。只要该诊断非零，本项目不会声称“对任意无限小输入扰动严格
数学单调”，但也不会把窄重叠窗口错误等同为缺码。

## 证据边界

PASS 只代表 Python behavioral L2。晶体管级、PVT、版图后仿与硅片结果
仍需后续独立签核。
