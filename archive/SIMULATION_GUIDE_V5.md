# Huang Recursive V5 校准仿真指南

## 1. 文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| 设计文档 | `doc/HUANG_RECURSIVE_CALIBRATION_DESIGN.md` | 完整数学推导和设计 |
| Verilog-A | `src/DEC_CAL_PHY_HUANG_V5.va` | 9目标递归校准 + 解码器 |
| 开关 | `src/SWITCH_CAL.va` | CDAC 开关阵列 (无需修改) |
| 比较器 | `src/COM_ideal.va` 或 `CAL_CMP_TB.va` | 比较器模型 |
| 测试台 | `sim/tb_huang_calibration.scs` | 参数化仿真测试台 |
| 扫描脚本 | `sim/run_mismatch_sweep.sh` | 失配扫描自动化脚本 |

## 2. 环境准备

### 2.1 文件链接

在仿真目录中建立文件链接 (或复制):

```bash
cd sim
# 链接 Verilog-A 模型
ln -sf ../src/DEC_CAL_PHY_HUANG_V5.va .
ln -sf ../src/SWITCH_CAL.va .
ln -sf ../src/COM_ideal.va .
# 或使用测试台比较器
ln -sf ../2026_12bit10Msar/04_辅助工具/veriloga_models/CAL_CMP_TB.va .
```

### 2.2 Spectre 版本

需要 Spectre 19.1+ 或 IC6.1.8 ISR22+ (支持 Verilog-A `$strobe` 和 `cross`)。

## 3. 测试 1: 理想电容验证

**目的**: 所有电容 ideal, 验证校准后 Ŵ_i = W_i。

```bash
cd sim
spectre tb_huang_calibration.scs
```

**参数**: 所有 md/mu = 1.0, cb_mult = 1.05

**预期日志**:

```
HUANGV5 start t=50n H1nom=122 avg_pairs=32 Q=6
CAL TARGET name=low10 stage=8 Wnom=20 range=27
...
HUANGV5 measure target=0 stage=8 W=20.0 nominal=20.0 plusAvg=20.0 minusAvg=20.0 range=27 minHeadroom=7 ok=1
CAL TARGET name=low16 stage=7 Wnom=32 range=47
...
HUANGV5 measure target=1 stage=7 W=32.0 nominal=32.0 ...
...
CAL TARGET name=high16 stage=0 Wnom=1952 range=2201
...
HUANGV5 measure target=8 stage=0 W=1952.0 nominal=1952.0 ...
CAL WEIGHTS={1952,976,488,244,244,122,48,32,20,12,8,4,2,1}
HUANGV5 DONE
```

**验证标准**:
- DONE = 1, ERR = 0
- 每个目标的 |measured - nominal| < 2 LSB
- 最小 headroom ≥ 5 LSB (high1 到 high4)

## 4. 测试 2: 单电容失配扫描

**目的**: 对每个物理电容注入 ±5% 失配, 验证校准能正确检测。

### 4.1 P 侧 high-1C (stage 5) +5% 失配

```bash
spectre tb_huang_calibration.scs +md8=1.05
```

**预期**: Ŵ_122 ≈ 122 × 1.05 = 128.1, 实际测量值应接近 128.1。

### 4.2 P 侧 high-2C-A (stage 3) -5% 失配

```bash
spectre tb_huang_calibration.scs +md9=0.95
```

**预期**: Ŵ_244A ≈ 244 × 0.95 = 231.8, 实际测量值应接近 231.8。

### 4.3 P 侧 high-2C-B redundant (stage 4) +5% 失配

```bash
spectre tb_huang_calibration.scs +md10=1.05
```

**预期**: Ŵ_244R ≈ 244 × 1.05 = 256.2, 与 Ŵ_244A 不同 (独立校准)。

### 4.4 完整扫描脚本

```bash
cd sim
./run_mismatch_sweep.sh
```

该脚本对 6 个物理电容 (stage 5, 3, 4, 2, 1, 0) 分别在 P 侧和 N 侧扫描 ±5%, ±2.6%, 0%。

## 5. 测试 3: 双侧失配

### 5.1 P、N 同方向失配

```bash
spectre tb_huang_calibration.scs +md8=1.05 +mu8=1.05
```

差分权重变化 = (1.05 + 1.05) / 2 = 1.05×, 校准应检测到 +5% 差分失配。

### 5.2 P、N 反方向失配

```bash
spectre tb_huang_calibration.scs +md8=1.05 +mu8=0.95
```

差分权重变化 = (1.05 + 0.95) / 2 = 1.0×, 差分权重不变, 但共模变化。校准结果应接近 ideal。

### 5.3 仅 P 侧失配

```bash
spectre tb_huang_calibration.scs +md8=1.05 +mu8=1.0
```

差分权重变化 = (1.05 + 1.0) / 2 = 1.025×, 校准应检测到 +2.5% 差分失配。

## 6. 测试 4: 三 MSB 同时失配

```bash
spectre tb_huang_calibration.scs +md11=1.03 +md12=0.97 +md13=1.05 \
    +mu11=1.03 +mu12=0.97 +mu13=1.05
```

比较:
1. 未校准 (CAL_BYPASS=1): 使用 nominal 权重解码
2. V6.6 三目标校准: 仅校准 W488, W976, W1952
3. V5.0 完整递归校准: 校准全部 9 目标
4. 理想权重: 使用真实物理权重解码

## 7. 正常转换验证

校准完成后 (CAL_RST 恢复高电平), 将输入改为斜坡或正弦波, 验证 DNL/INL。

### 7.1 斜坡输入

修改测试台中的 VIP/VIN 为斜坡源:

```
VVIP (VIP AGND) vsource type=pulse val0=0 val1=vdd period=2m \
    delay=900u rise=1m fall=1m width=0
VVIN (VIN AGND) vsource dc=vdd/2
```

### 7.2 正弦输入

```
VVIP (VIP AGND) vsource type=sine ampl=vdd/2 freq=100k \
    offset=vdd/2 delay=900u
VVIN (VIN AGND) vsource dc=vdd/2
```

## 8. 性能指标提取

使用 ADCToolbox (Python/MATLAB) 从仿真数据提取:

```python
from adctoolbox import toolset_dout

# 加载仿真数据
data = toolset_dout.load_spectre_data("tb_huang_calibration.raw")

# 提取 ADC 输出码
codes = data["B11":"B0"]  # 12-bit 输出

# 计算 DNL/INL
dnl, inl = toolset_dout.compute_dnl_inl(codes, nl=4096)

# 计算 SNDR/SFDR/ENOB (正弦输入)
sndr, sfdr, enob = toolset_dout.compute_dynamic_performance(codes, fs=10e6, fin=100e3)
```

## 9. 校准控制器集成说明

在实际芯片中, CAL_CLK 需要由数字校准控制器生成。控制器需要:

1. 检测 RST1 下降沿, 开始一个 D+ 或 D- 方向
2. 生成 search_count + 1 个 CAL_CLK 脉冲
3. 检测 RST1 上升沿, 结束该方向
4. 交替 D+ / D- 方向, 每 32 对更新一次权重
5. 9 个目标顺序执行

最大 CAL_CLK 数: 13 (high16), 最小: 5 (low10)

控制器可用简单的移位寄存器 + 计数器实现, 无需复杂状态机。

## 10. 预期性能

| 指标 | 未校准 | V6.6 (3-target) | V5.0 (9-target) | 理想 |
|------|--------|-----------------|-----------------|------|
| INL (LSB) | 10-50 | 2-5 | < 1 | < 0.5 |
| DNL (LSB) | 5-20 | 1-2 | < 0.5 | < 0.5 |
| SNDR (dB) | 55-65 | 68-72 | > 73 | > 74 |
| ENOB (bit) | 9-10 | 11-11.5 | > 11.8 | > 12 |
| SFDR (dB) | 60-70 | 75-80 | > 85 | > 90 |
| 校准时间 | 0 | ~0.5 ms | ~1.3 ms | - |
| 比较次数 | 0 | ~1500 | ~5120 | - |
