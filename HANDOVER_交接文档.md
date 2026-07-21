# SAR ADC 递归校准项目 — AI 任务交接文档

> **交接时间**：2026-07-21
> **项目**：12-bit SAR ADC · 二进制桥接 CDAC · Huang 双向递归前台权重校准
> **关键词**：SAR ADC, CDAC, 前台校准, 递归权重, Spectre, Verilog-A

---

## 1. 项目概述

本项目实现基于 Qifeng Huang 博士论文 (HKUST, 2024) Section 4.5 的双向递归位权校准算法。核心思想是通过 D+/D- 双向 SAR 搜索 + 32-pair 平均，逐一测量 7 个高位电容的实际物理权重，在数字域补偿 CDAC 失配。

### 1.1 CDAC 结构（已定版）

```
低位阵列:  {1, 2, 4, 8, 16, 32} = 63 Cu   (纯二进制, calDAC)
桥接电容:  C_B = 2 Cu                       (整数桥接)
高位阵列:  {1A, 1R, 2, 4, 8, 16, 32} = 64 Cu  (二进制 + 冗余 1C)
```

**有效权重**（G_B = (63+2)/2 = 32.5, H = 2×32.5 = 65）：
- 低位 calDAC: {64, 32, 16, 8, 4, 2} + Terminal 1
- 高位: {2080, 1040, 520, 260, 130, 65_R, 65_A}
- 总权重 = 4287 > 4095（12-bit 覆盖，192 LSB 冗余区间）

### 1.2 校准目标（7 个）

| 目标 ID | 名称 | Stage | Nominal | 搜索范围 | SAR 步数 |
|---------|------|-------|---------|----------|---------|
| 0 | H1C-A | 6 | 65 | calDAC {7..12} | 6 |
| 1 | H1C-R | 5 | 65 | {stg6, calDAC} | 7 |
| 2 | H2C | 4 | 130 | {stg5, stg6, calDAC} | 8 |
| 3 | H4C | 3 | 260 | {stg4..stg6, calDAC} | 9 |
| 4 | H8C | 2 | 520 | {stg3..stg6, calDAC} | 10 |
| 5 | H16C | 1 | 1040 | {stg2..stg6, calDAC} | 11 |
| 6 | H32C | 0 | 2080 | {stg1..stg6, calDAC} | 12 |

---

## 2. 目录结构

### 2.1 工作文件（不在 archive/ 中的文件都要使用）

```
ROOT/
├── src/                          # 源码 (Verilog-A)
│   ├── DEC_CAL_PHY_HUANG_V6.va   # [核心] 校准引擎 + decoder (606行)
│   ├── COM_ideal.va              # 理想比较器 (带亚LSB dither)
│   ├── SAR_LOGIC_0716.va         # 正常模式 SAR 逻辑
│   ├── SWITCH_CAL.va             # 校准感知开关阵列
│   └── SYNC_asnyc.va             # 异步时序生成器
│
├── sim/                          # 仿真目录
│   ├── DEC_CAL_PHY_HUANG_V6.va   # 链接/复制到 sim 的校准引擎
│   ├── SWITCH_CAL.va             # 开关阵列 (sim 副本)
│   ├── COM_ideal.va              # 理想比较器 (sim 副本)
│   ├── CAL_CMP_TB.va             # 测试台专用比较器
│   ├── SAR_LOGIC_0716.va         # SAR 逻辑 (sim 副本)
│   ├── SYNC_asnyc.va             # 时序生成器 (sim 副本)
│   ├── cdac_binary_mc.va         # [核心] 二进制 CDAC MC 模型 (270行)
│   │
│   ├── tb_huang_cal_ramp.scs     # [主测试台] 校准 + 斜坡转换 (80us+410us)
│   ├── tb_huang_calibration.scs  # [备选测试台] 更短, 仅校准
│   │
│   ├── params.scs                # 外部参数文件 (vdd, cunit, 失配参数)
│   ├── params_ideal_calon.scs    # 理想参数
│   ├── params_debug.scs          # 调试参数
│   │
│   ├── run_campaign_vm.py        # VM 批量仿真脚本 (Python 2 兼容)
│   ├── run_full_campaign.py      # 完整仿真任务脚本
│   ├── run_mismatch_campaign.py  # 失配扫描脚本
│   ├── run_mismatch_sweep.sh     # Shell 失配扫描
│   │
│   ├── analyze_and_plot.py       # [核心] 数据分析 + 学术级绘图生成
│   │
│   ├── sim_results/              # 仿真结果存档
│   │   ├── log_ideal_calon.log   # 理想校准 ON (H8C VALID=0)
│   │   ├── log_ideal_caloff.log  # 理想校准 OFF
│   │   ├── log_mild_2pct_calon.log
│   │   ├── log_sev_5pct_calon.log / caloff.log
│   │   ├── log_sys_pos/neg_2pct_calon.log / caloff.log
│   │   ├── log_debug_cal.log     # 调试日志 (DEBUG=2, 含SAR逐步骤跟踪)
│   │   ├── parsed_results.json   # 解析后的性能数据
│   │   └── performance_summary.csv
│   │
│   └── plots/                    # 已生成的图表
│       ├── fig1_cdac_structure.pdf/png
│       ├── fig2_calibration_scheme.pdf/png
│       ├── fig3_performance_comparison.pdf/png
│       ├── fig4_weight_error.pdf/png
│       ├── fig5_inl_dnl.pdf/png
│       └── fig6_calibration_targets.pdf/png
│
├── rtl/                          # RTL 实现
│   └── DEC_CAL_PHY_rtl.v         # 校准引擎 RTL (Verilog)
│
├── doc/                          # 文档
│   ├── report/
│   │   ├── huang_calibration_report.tex/pdf   # 校准报告 (V6)
│   │   └── comprehensive_report.tex/pdf       # 综合报告 (旧)
│   ├── HUANG_RECURSIVE_CALIBRATION_DESIGN.md   # 设计文档
│   ├── PROOF_V6_3_IDENTIFIABILITY.md           # 可辨识性证明
│   ├── README_使用说明.md                       # 使用说明
│   ├── STATIC_CHECK_REPORT.txt                 # 静态检查报告
│   ├── sar_adc_mismatch_calibration_report_cn.tex/pdf
│   └── *.pdf                                    # 参考论文
│
├── figures/                      # 已生成的学术级图表
│   ├── fig1_cal_on_off.pdf/png/svg
│   ├── fig2_sourcecenter_8sample.pdf/png/svg
│   ├── fig3_sigma_sweep.pdf/png/svg
│   ├── fig4_cdac_architecture.pdf/png/svg
│   ├── fig5_calibration_flow.pdf/png/svg
│   └── fig6_weight_convergence.pdf/png/svg
│
├── spectre_sim/                  # 可直接上传 VM 的最小仿真包
│   ├── tb_huang_calibration.scs
│   ├── DEC_CAL_PHY_HUANG_V6.va
│   ├── SWITCH_CAL.va
│   ├── COM_ideal.va
│   ├── CAL_CMP_TB.va
│   ├── SYNC_asnyc.va
│   ├── SAR_LOGIC_0716.va
│   └── cdac_binary_mc.va
│
├── ref/                          # 参考论文
│   └── 0764 - Huang - 2024 - Advanced clock multiplier....
│
├── 提示词                        # 项目提示词 (原始需求)
└── HANDOVER_交接文档.md           # 本文件
```

### 2.2 archive/ — 已归档旧版本

> 所有旧版本已移入此处，后续接手 AI 无需关注。如需回溯历史，查阅此目录：
> - DEC_CAL_PHY_v6.va ~ v7.va — 基于"墙+残差"架构的旧版本
> - DEC_CAL_PHY_HUANG_V5.va — Huang 递归 V5 版本（9 目标、权重系统不同）
> - cdac_split_mc_*.va — 旧分裂式 CDAC 模型
> - SIMULATION_GUIDE_V5.md — V5 版本的仿真指南
> - 其他旧文件

---

## 3. 当前状态（关键！）

### 3.1 ✅ 已完成
- CDAC 拓扑设计定版（二进制整数倍，桥接 2C）
- 7 目标递归校准算法实现（DEC_CAL_PHY_HUANG_V6.va）
- 理想 Spectre 仿真运行成功（零错误）
- H1C-A/H1C-R/H2C/H4C 校准通过（VALID=1, SAT=0）
- 校准后权重正确：65, 65.53, 130.53, 261.06, ...
- 仿真环境完整：测试台、参数文件、MC 模型、分析脚本
- 已有初步图表（复数套，含 CDAC 结构图、校准流程图等）

### 3.2 ❌ 已知问题

#### P0: H8C 校准失败（VALID=0）

**现象**：在理想仿真中，H4C 校准结束后，H8C 目标（stage=2, target_id=4）的测量值为 387.422（应为 520），VALID=0。

**日志中的关键观测**：
```
CAL TARGET name=H8C stage=2 Wnom=520 scnt=10
... (32次重复)
POS avg_code=387.422
NEG avg_code=387.422
DIFF=774.844
WEIGHT=387.422
VALID=0
SAT=0
```

387.422 ≈ 257.422(H4C) + 130(H2C) = 387.422，显然 H1C-A(65) 和 H1C-R(65.53) 未被纳入搜索 DAC！

**根因分析**：
DEC_CAL_PHY_HUANG_V6.va 第 286-290 行的 SAR trial stage 生成逻辑存在设计缺陷：

```verilog
if (sar_step < (6 - target_stage)) begin
    trial_stage = 6 - sar_step;  // 高位侧: stg6, stg5, ..., stg(target_stage+1)
end else begin
    trial_stage = 7 + (sar_step - (6 - target_stage));  // calDAC: 7..12
end
```

对于 H8C（target_stage=2），6-2=4，所以前 4 步遍历 stg6→stg5→stg4→stg3，然后切换到 calDAC stg7..12。**stg2 本身作为待测目标**，搜索范围包含 {stg3,stg4,stg5,stg6 + calDAC}——这逻辑上看似乎是正确的。

问题可能出在：`search_total_q` 在 RST1 下降沿计算时，可能未包含正确的已校准低位权重。或者 `d_mask/u_mask` 组合在 SAR 搜索过程中未正确包含所有已校准权重的可选状态。

**调试日志中需要进一步分析的内容**：
`log_debug_cal.log` 中包含了 `DBG T4` 前缀的详细 SAR 逐步骤决策日志。需要完整分析该日志中 H8C 阶段的每一步 SAR 搜索决策。

#### P1: LaTeX 报告编译报错
`doc/report/huang_calibration_report.tex` 存在 LaTeX 编译错误，需要修复。

### 3.3 性能指标（初步）
- 校准 SNDR（H4C 之前）：D+/D- 完美对称，误差 0~1.062 LSB
- H8C 失败后校准中断：需要先修复 H8C 问题才能获得完整 7 目标性能

---

## 4. 待完成工作（按优先级排序）

### P0: 修复 H8C 校准 Bug

**详细任务**：
1. 分析 `sim/sim_results/log_debug_cal.log` 中 H8C 阶段的 `DBG T4` 逐步骤 SAR 决策
2. 在 `DEC_CAL_PHY_HUANG_V6.va` 的 RST1 下降沿处理中，打印 `search_total_q` 和 `target_mask` 确认搜索范围计算是否正确
3. 检查 SAR 搜索循环（CAL_CLK 上升沿）的 trial_stage 生成是否正确包含 stg3..stg6
4. 修复后重新运行 `tb_huang_cal_ramp.scs` 验证

**诊断命令**（在 VM 上执行）：
```bash
cd /home/meow/jxy/trae_sandbox/sim_campaign
spectre -64 tb_huang_cal_ramp.scs +escchars -format psfxl -raw psf_debug_cal +log log_debug_cal.log
```

### P0: 修复 LaTeX 报告编译

**文件**：`doc/report/huang_calibration_report.tex`

运行命令获取具体错误：
```bash
cd doc/report
xelatex huang_calibration_report.tex
```

### P0: 在 VM 上运行完整失配仿真

修复 H8C 后，在远程 CentOS7 VM 上执行多组失配场景仿真：

**VM 信息**：
- Host: meowu (CentOS 7)
- Spectre: 23.1.0.242.isr1
- 仿真目录: `/home/meow/jxy/trae_sandbox/sim_campaign/`
- 文件传输: 将 `spectre_sim/` 目录通过 WinSCP/scp 上传至 VM

**仿真场景**（5组失配 × cal_on/caloff = 10次）：

| 场景 | md8..md14 | mu8..mu14 | 说明 |
|------|-----------|-----------|------|
| ideal | 1.0 | 1.0 | 理想电容 |
| mild_2pct | 1.02(h) / 0.98(l) | 1.02(h) / 0.98(l) | 2% 系统失配 |
| sev_5pct | 1.05(h) / 0.95(l) | 1.05(h) / 0.95(l) | 5% 系统失配 |
| sys_pos_2pct | 1.02 | 1.02 | P/N 同向 +2% |
| sys_neg_2pct | 0.98 | 0.98 | P/N 同向 -2% |

**运行命令**：
```bash
cd /home/meow/jxy/trae_sandbox/sim_campaign
python2 run_campaign_vm.py
```

或单次运行：
```bash
spectre -64 tb_huang_cal_ramp.scs +escchars -format psfxl -raw psf_xxx +log log_xxx.log
```

### P1: 学术级绘图生成

修复 H8C + 仿真完成后，运行分析脚本：

```bash
cd /path/to/sim
python analyze_and_plot.py --log_dir sim_results --output_dir plots
```

生成以下必须图表：
1. **CDAC 结构图** — 展示二进制 CDAC 拓扑
2. **校准方案图** — 展示 7 目标递归校准流程
3. **性能对比图** — 校准 ON/OFF 的 ENOB/SFDR/SNR 条形图
4. **权重误差图** — 各目标校准误差及递归传播
5. **INL/DNL 图** — 校准前后的线性度对比
6. **校准目标收敛图** — 32-pair 平均过程中权重收敛

### P2: 重写综合研究报告

基于修复后的仿真数据和生成图表，重写 `doc/report/comprehensive_report.tex`，需包含：
1. CDAC 具体结构（含桥接比例推导）
2. 校准算法数学原理
3. 仿真验证数据（理想 + 失配场景）
4. **校准 ON/OFF 性能对比表**：ENOB、SFDR、SNR
5. 误差分析 & 递归传播模型
6. 所有学术级图表
7. 结论与展望

### P3: Dither 验证

- 替换 COM_ideal.va 为带 DITHER 版本
- 验证 32-pair 平均能否达到 Q6 亚 LSB 精度
- 确认 DITHER_PAIR_EDGES=18 参数

---

## 5. 关键文件逐文件说明

### 5.1 DEC_CAL_PHY_HUANG_V6.va

这是校准系统的核心，功能包括：
- 7 目标直接递归校准状态机
- D+/D- 双向测量 + 32-pair 平均
- SAR 搜索逻辑（高位优先 → calDAC）
- 校准后数字解码器（14 决策位 → 12-bit 输出）
- 错误检测与回退（REVERT_ON_ERROR）

**参数说明**：
- `NOM_H1_WEIGHT=65` — 高位单位电容名义权重
- `FRAC_BITS=6` — 小数位精度（Q6）
- `AVG_PAIRS_LOG2=5` — 32-pair 平均
- `CAL_BYPASS=calbp` — 校准旁路开关
- `REVERT_ON_ERROR=1` — 出错时回退到名义权重
- `DEBUG=2` — 输出 H8C+ 目标的逐步骤 SAR 跟踪

### 5.2 tb_huang_cal_ramp.scs

主测试台，包含：
- Phase 1 (0-75us): 7 目标递归校准
- Phase 2 (82-492us): 斜坡输入 + 正常 SAR 转换
- 完整时钟生成（RST, RST1, CLK_SAR, CAL_CLK）
- 使用 SAR_LOGIC_0716 做正常模式 SAR 控制

### 5.3 cdac_binary_mc.va

二进制 CDAC MC 模型，特点：
- 每个物理电容由 N 个单位电容并行构成
- 单位电容使用 $rdist_normal 独立随机失配
- P/N 侧独立 seed 生成
- 支持 MC_ENABLE, SIGMA_C_REL, CLIP_SIGMA 参数

### 5.4 analyze_and_plot.py

数据分析和绘图脚本，功能：
- 解析仿真日志中的校准结果
- 计算 ENOB/SFDR/SNR
- 生成 matplotlib 学术级图表（LaTeX 标签）
- 输出 PDF/PNG/SVG 格式

---

## 6. VM 远程操作指南

### 6.1 连接方式
通过 SSH 连接 CentOS 7 VM：
```bash
ssh meow@meowu
```

### 6.2 仿真部署
```bash
# 将 spectre_sim/ 上传到 VM
scp -r spectre_sim/* meow@meowu:/home/meow/jxy/trae_sandbox/sim_campaign/

# 或直接在 VM 上操作
cd /home/meow/jxy/trae_sandbox/sim_campaign
```

### 6.3 文件更新流程
1. 本地修改 VA/SCS 文件
2. 通过 WinSCP 或 scp 上传到 VM
3. VM 上运行 Spectre
4. 将日志/scs 文件下载回本地的 sim/sim_results/

### 6.4 常用命令
```bash
# 单次仿真
spectre -64 tb_huang_cal_ramp.scs +escchars -format psfxl -raw psf_xxx +log log_xxx.log

# 检查日志
grep -E "VALID|WEIGHT|ERROR|FAIL" log_xxx.log

# 校准结果提取
grep -E "WEIGHT=|VALID=|SAT=" log_xxx.log
```

---

## 7. 已知技术细节

### 7.1 SAR 搜索算法
- 高位优先（greedy 逼近）：先尝试高位已校准电容，再试 calDAC LSB
- 每个 CAL_CLK 周期：上升沿设 trial 值 → 下降沿锁存比较器结果
- KEEP/DISCARD 决策：残差为正（D+ 方向）或零命中 → KEEP
- Terminal 阶段：最后一个 CAL_CLK 周期处理比较器 LSB 判决

### 7.2 校准数学
- D+ 方向：待测电容接 VREFP，搜索 DAC 接 VREFN
- D- 方向：待测电容接 VREFN，搜索 DAC 接 VREFP
- $\hat{W} = (D^+ + |D^-|) / (2 \times N_{pairs})$，失调自然消除
- 直接递归：$\hat{W}_k$ 直接作为该 stage 的权重值

### 7.3 桥接比例推导
```
C_L,Σ = 1+2+4+8+16+32 = 63
C_B = 2
G_B = (C_L,Σ + C_B) / C_B = (63+2)/2 = 32.5
H = 2 × G_B = 65  (差分 LSB)
```

### 7.4 权重映射
```
Stage 0: H32C → 2080 (W0)
Stage 1: H16C → 1040 (W1)
Stage 2: H8C  → 520  (W2)
Stage 3: H4C  → 260  (W3)
Stage 4: H2C  → 130  (W4)
Stage 5: H1C-R → 65  (W5)
Stage 6: H1C-A → 65  (W6)
Stage 7: L32C → 64   (W7)
...      ...    ...
Stage 12: L1C → 2    (W12)
Terminal:    → 1    (W13)
```

---

## 8. 延续工作指引

接手本任务的 AI 应当按以下顺序执行：

1. **读取本文档** → 理解项目全貌
2. **修复 H8C Bug** → 分析调试日志，修复 DEC_CAL_PHY_HUANG_V6.va
3. **VM 上传** → 将修复后的 spectre_sim/ 上传至 VM
4. **运行仿真** → 执行 5 组 × cal_on/off 共 10 次仿真
5. **分析数据** → 运行 analyze_and_plot.py 生成学术级图表
6. **修复 LaTeX** → 修复 huang_calibration_report.tex 编译错误
7. **重写报告** → 基于新数据重写 comprehensive_report.tex
8. **编译 PDF** → 生成最终学术报告 PDF

---

## 9. 注意事项

- **不要使用 DEM**：用户明确拒绝动态元件匹配
- **不要过度工程化**：只做用户要求的功能
- **桥接电容必须为整数**：C_B=2C 已定版
- **所有电容必须为二进制倍数**：1,2,4,8,16,32 序列
- **保持与 Huang 论文一致**：双向递归、D+/D- 架构
- **Spectre 版本**：VM 上为 23.1.0.242.isr1
- **VM Python**：仅 Python 2.7，脚本需兼容
- **仿真日志分析**：VOLT=0 表示校准失败，需检查搜索范围/headroom
- **Communication**: 用户使用中文沟通
