---
title: CAAZ SAR ADC Cadence 仿真指南
aliases: [Cadence仿真, Virtuoso ADE, PSS PNOISE]
tags: [type/guide, topic/sar-adc]
created: 2026-03-24
updated: 2026-03-24
---

# CAAZ SAR ADC Cadence 仿真指南

本文档提供 12-bit 50-MS/s SAR ADC with CAAZ 前置放大器的 Cadence Virtuoso 仿真完整指南。

---

## 1. 瞬态噪声仿真设置 (Transient Noise Simulation)

### 1.1 ADE Explorer 配置步骤

1. **打开 ADE Explorer**
   ```
   Virtuoso IC617 → Menu → Tools → ADE Explorer
   ```

2. **创建新仿真**

   - 点击 `Setup` → `Simulator Directory`
   - 选择 `spectre` 作为 simulator

3. **设置仿真类型**

   - 点击 `Analysis` → `Choose` → `tran` (Transient)
   - 配置参数：
     ```
     Stop Time: 20us
     Accuracy Default: moderate
     Noise Enable: enabled
     ```

4. **配置瞬态噪声参数**

   ```
   Noise Options:
   ├── Noise Type: port
   ├── Max Frequency (Fmax): 10GHz
   ├── Noise Seed: 1
   ├── Number of Runs: 5
   └── Sampling Noise: yes
   ```

### 1.2 关键参数设置原理

| 参数 | 推荐值 | 原理 |
|:-----|:-------|:-----|
| Fmax | 10 GHz | 应覆盖 10× 采样频率以捕获噪声折叠 |
| Noise Seed | 1 | 保证噪声源可重复性 |
| Number of Runs | 5-10 | 平均多次运行以获得稳定结果 |
| Time Step | auto | 由 Cadence 自动优化 |

### 1.3 kT/C 噪声折叠捕获

由于 kT/C 噪声在采样瞬间被斩波，噪声折叠效应必须准确建模：

```matlab
% 折叠因子计算
fs = 50e6;        % 采样频率
BW = 100e6;       % 放大器带宽
N_folding = 1 + BW/fs
```

---

## 2. PSS + PNOISE 仿真 (Periodic Steady-State Noise)

### 2.1 PSS 仿真设置

```
Analysis: PSS
├── Beat Frequency: 50MHz
├── Output Harmonics: 50
├── Accuracy: medium
├── Method: shooting
└── Output: all
```

### 2.2 PNOISE 仿真设置

```
Analysis: PNOISE
├── PSS Engine: spectre
├── Frequency Range: 1kHz to 1GHz
├── Frequency Steps: 100
├── Noise Type: sources
├── Sweep Type: logarithmic
└── Ref-node: DVDD
```

### 2.3 等效输入参考噪声提取

在后处理中，输入参考噪声功率谱密度为：

```matlab
% 从 PNOISE 输出提取
noise_psd = Vout_noise / (gain_preamp * gain_adder);
```

---

## 3. SNDR 自动计算 Ocean 脚本

```ocean
;=============================================================
; OCEAN Script for SNDR Calculation
; Usage: Load this script in ADE → Run → Results → OCEAN
;=============================================================

;--- Configuration ---
simulator('spectre)
design(	"/path/to/your/library/ADC_test/schematic"
        "adc_top" "spectre")
resultsDir("/path/to/simulation/results")

;--- Load TRAN simulation results ---
run()

;--- Extract output data ---
selectResult('tran)
Vout = getData("/VOUT")
time = getData("time")

;--- Import to MATLAB for FFT ---
MATLAB(...)
evalstr(["data = vs(t, ''/VOUT'');" ...
         "csvwrite(''output_data.csv'', data);"])

;--- MATLAB FFT Analysis ---
; (Run externally, save results to CSV)
;=============================================================
; MATLAB FFT_Sinalysis.m
;=============================================================
data = csvread('output_data.csv');
N = length(data);
fs = 50e6;
dt = 1/fs;

% Apply windowing (Hanning)
window = hanning(N);
windowed_data = data .* window;

% FFT
Y = fft(windowed_data);
P2 = abs(Y/N);
P1 = P2(1:N/2+1);
P1(2:end-1) = 2*P1(2:end-1);

% Frequency axis
f = fs*(0:(N/2))/N;

% Find signal and noise bins
[~, idx_signal] = max(P1);
freq_signal = f(idx_signal);
signal_power = P1(idx_signal)^2;

% Noise floor (exclude DC and signal bins)
noise_bins = [1:idx_signal-10, idx_signal+10:N/2];
noise_power = sum(P1(noise_bins).^2);

% Calculate SNDR
sndr = 10*log10(signal_power / noise_power);

% Calculate ENOB
enob = (sndr - 1.76) / 6.02;

fprintf('SNDR = %.2f dB\n', sndr);
fprintf('ENOB = %.2f bits\n', enob);
```

---

## 4. 仿真验证清单

### 4.1 前置放大器特性验证

| 验证项 | 仿真类型 | 预期结果 |
|:-------|:---------|:---------|
| 低增益采样模式 | AC | $A_{samp} \approx 0\,$dB |
| 高增益转换模式 | AC | $A_{amp} > 30\,$dB |
| 大信号瞬态响应 | TRAN | 输出无饱和 |
| kT/C 噪声消除 | PNOISE | 残余噪声 $< -74\,$dB |

### 4.2 完整 ADC 动态性能

| 验证项 | 仿真类型 | 预期结果 |
|:-------|:---------|:---------|
| SNDR | FFT | $> 71\,$dB |
| SFDR | FFT | $> 85\,$dB |
| ENOB | 计算 | $> 11.5\,$bits |
| DNL/INL | Static | $< 1\,$LSB |

---

## 5. 常见问题与解决方案

| 问题 | 原因 | 解决方案 |
|:-----|:-----|:--------|
| 噪声不收敛 | Fmax 过高 | 降低 Fmax 至 5GHz |
| 结果不稳定 | seed 不一致 | 设置固定 seed=1 |
| 仿真时间过长 | 步长过小 | 使用 adaptive stepping |
| 谐波失真大 | 输入非相干 | 使用相干采样 |

---

**上级文档**：[paper_IEEEtran.tex]