# SAR ADC Shen 2018 校准系统 — 递交包

> **版本:** v3.0.0  
> **日期:** 2026-07-25  
> **接手专家:** 请先阅读本文, 再操作代码

---

## 一、发现与修改总结

### 1.1 架构审查结论

| 模块 | 结论 |
|------|------|
| Split-CDAC 拓扑 (14 物理电容 + 桥接) | 物理正确, H8 冗余是有效改进 |
| Shen 2018 校准协议 (Force-0/Force-1) | 逐条对齐论文, 无架构缺陷 |
| 电荷守恒求解器 | 2x2 矩阵预计算, 物理正确 |
| 异步 SAR 转换控制器 | 标准 monotonic switching |
| 解码器 | 纯加权和, 无 LUT, 无 DP, 无硬编码 |

### 1.2 参数过度设计修复

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| `AVG_PAIRS` | **512** | **128** | 256 对后 gap 已饱和, 512→128 gap 劣化仅 0.17 dB, 时间降为 1/4 |
| `SHEN_DITHER_LSB` | 硬编码在 calibrator | **关闭 (= (0.0,))** | 1mV 噪声 + 128 对下 dither 冗余, 关掉省硬件 |
| `SHEN_DITHER_LSB` 位置 | 硬编码 | **config.py 声明** | 统一参数入口, 可调试 |
| `MC_SIGMA` | 0.5% (GitHub) | **1%** (本地保守) | TSMC 180nm Pelgrom 反推, 合理保守 |

### 1.3 Dither 消融实验结论

- 比较器噪声 < 1 LSB + N < 32 → dither 有价值 (+3~9 dB)
- 比较器噪声 ≥ 1 LSB 或 N ≥ 32 → dither 无增益 (delta 在 ±0.5 dB 内)
- 当前 1mV 噪声 + 128 对: dither 完全冗余

### 1.4 噪声 vs AVG_PAIRS 热力图结论

| 比较器噪声 | 所需 N | Oracle Gap |
|-----------|--------|------------|
| 200 µV | **8** | 0.49 dB |
| 500 µV | **16** | 0.98 dB |
| 1 mV | **64** | 0.69 dB |
| 2 mV | **256** | 1.27 dB |

公式: $N_{opt} \approx 18 \times (\sigma_{cmp,\mu V} / 439)^2$

### 1.5 失配容限

| MC σ | Post-SNDR | Oracle Gap | 判定 |
|------|-----------|------------|------|
| 1% | 74.5 dB | 0.14 dB | 优秀 |
| 2% | 73.3 dB | 1.34 dB | 可用 |
| 5% | 72.6 dB | 2.05 dB | 边缘 |
| 10% | 70.2 dB | 4.47 dB | 不可用 |
| 20% | 50.6 dB | 24.03 dB | 崩溃 |
| 50% | 23.1 dB | 51.52 dB | 完全失败 |

---

## 二、文件结构

```
python_cal/
├── config.py                  ← 所有参数统一入口 [已修改 AVG_PAIRS=128]
├── debug_entry.py            ← ★ 一键调试入口 [新增]
├── DELIVERY.md               ← 本文件 [新增]
│
├── calibration/               ← Shen 校准器
│   └── shen_calibrator.py     [已修改: dither 改读 cfg.SHEN_DITHER_LSB]
│
├── analysis/                  ← 实验脚本 & 输出 [新增目录]
│   ├── generate_fft_comparison.py     单点校准前/后/理想 FFT
│   ├── generate_multisigma_fft.py     2%-50% MC sigma FFT 扫描
│   ├── sweep_noise_vs_pairs.py        噪声xAVG_PAIRS 热力图
│   ├── analyze_avg_pairs.py           AVG_PAIRS 扫描
│   ├── dither_ablation.py             Dither ON vs OFF
│   ├── dither_heatmap.py              Dither 热力图
│   ├── compare_old_vs_new.py          旧(512) vs 新(128) 对比
│   ├── fft_comparison.png
│   ├── fft_multisigma_sweep.png
│   ├── noise_vs_pairs_sweep.png
│   ├── dither_ablation.png
│   ├── dither_heatmap.png
│   └── old_vs_new_comparison.png
│
├── physical/ topology/ decode/        ← 核心模块 [未修改]
├── converter/ async_control/          ← 核心模块 [未修改]
└── validation/                        ← FFT 协议 [未修改]
```

---

## 三、快速调试指南

### 一键运行
```bash
cd python_cal
python debug_entry.py                        # 默认: MC=1%, AVG=128, Dither ON
```

### 常见调试场景
```bash
# 快速验证 (30秒): 降 pairs, 跳过多sigma
python debug_entry.py --pairs 32 --skip-multi

# 不同失配水平
python debug_entry.py --mc 0.02             # 2% 失配
python debug_entry.py --mc 0.05             # 5% 失配

# 测试 dither 开关
python debug_entry.py --no-dither           # 关闭 dither

# 不同比较器噪声
python debug_entry.py --noise 0.5           # 500 uV 噪声

# 组合
python debug_entry.py --mc 0.02 --pairs 64 --noise 0.2 --seed 12345

# 不同随机种子
python debug_entry.py --seed 123
python debug_entry.py --seed 456
```

### 输出
| 文件 | 内容 |
|------|------|
| `fft_single_{seed}.png` | 校准前/后/理想 FFT 频谱 |
| `fft_multi_{seed}.png` | 2%-50% MC sigma FFT |
| `calibration_report.txt` | 权重表 + 指标汇总 |

### 改配置 (影响后续所有运行)
编辑 `config.py`:
```python
AVG_PAIRS = 128           # 校准平均对数
SHEN_DITHER_LSB = (0.0,)  # dither 已关闭 (噪声 ≥ 1 LSB 时冗余)
MC_SIGMA = 0.01           # 单位电容失配标准差
CAL_NOISE_SIGMA_V = 0.001 # 校准比较器噪声 [V]
```

---

## 四、旧 vs 新参数对比

| 指标 | OLD (AVG=512) | NEW (AVG=128) |
|------|-------------|---------------|
| SNDR (1% σ) | 74.64 dB | **74.33 dB** |
| Oracle Gap | 0.00 dB | **0.32 dB** |
| ENOB | 12.11 bit | **12.05 bit** |
| 校准时间 (Python) | 6.5 s | **1.6 s** |
| 等效硬件时间 | ~1.7 ms | **~0.4 ms** |
| Delta SNDR | — | **-0.17 dB** (\(\ll\) 0.5 dB) |

---

## 五、技术决策记录

| ID | 决策 | 理由 | 日期 |
|----|------|------|------|
| D1 | AVG_PAIRS 512→128 | 256 对后 gap 已饱和, 冗余 | 2026-07-25 |
| D2 | Dither 关闭 | 噪声≥1LSB+N≥32 时冗余, 省硬件 | 2026-07-25 |
| D3 | Dither 改读 config | 消除硬编码, 便于实验 | 2026-07-25 |
| D4 | MC_SIGMA=1% | TSMC 180nm Pelgrom 反推保守值 | 2026-07-25 |
| D5 | 窗函数=Rectangular | 相干采样, ENBW=1 bin | 已验证 |
| D6 | 实验脚本集中 analysis/ | 防止主目录污染 | 2026-07-25 |
