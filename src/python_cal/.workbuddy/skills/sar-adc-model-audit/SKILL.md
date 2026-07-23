---
name: sar-adc-model-audit
description: 审查/核查 SAR ADC 行为级模型（python_cal）的标准流程与反陷阱清单。适用于：继续编号审查链（38/39/40...）、核查构建方提交、复现/审计模型性能声明、撰写复现方案。
agent_created: true
---

# SAR ADC 行为模型审查与核查流程

项目：`SAR_ADC_IDEAL_CAL_REPLACEMENT_V6_CLEAN/src/python_cal`（12-bit 冗余异步非二进制 SAR ADC + 前台校准行为模型）。

## 编号审查链惯例

- 无扩展名编号文档置于包根目录：32 执行指令 → 33 修正 → 34 交付 → 35/36 一、二审 → 37 根因调查令 → 38 独立审查 → 39 监控结论 → 40 复现方案。
- 文档风格：判定先行（粗体 verdict）、P0/P1 分级、每条给证据（文件:行 / 报告章节 / 数字）、量化验收判据、交接条款。
- 审查方实验脚本放 `reports/review*.py`，只 import 不改模型源码；结果 JSON 附进文档。

## 模型架构速查（修改后版本，2026-07-23 起）

- 关键口径：**1 code-LSB = 2 Q0**（signal_weight 4095 Q0 ↔ ±0.8597 V 满量程 ↔ codes 0..4095）。L1C=2 Q0=1 LSB；terminal=1 Q0=0.5 LSB（无物理电容）。
- 新 SARDecoder：`code=(signed_sum+signal_weight)/2`；signed_sum 恒为奇数（奇数权重 65/65/1）→ 整数权重下精确映射。`fixedpoint.decode_va_exact` 与其**互补极性**（code_va=4095−code_sar）。
- 校准：7 target 升序 + wall + D± + calDAC 6 步搜索 + **terminal ±1 Q0 判定**（治截尾）；terminal_adj 目前用求解器无噪声符号判定。
- 不变量：decoder 隔离（校准不得改变 decisions）；physical weights oracle 仅供测试；CMP=1 ⇔ VTOP_P>VTOP_N；电荷守恒 <1e-24 C。

## 反陷阱清单（血泪教训）

1. **判缺码/SNDR 上限前，先核对输入满量程与 decoder 归一化。** 38 号曾用旧假满量程 ±0.4301 V 扫描（真实为 ±0.8597 V），把"半量程输入"误判为"半数缺码 + 6 dB 损失"。先跑 code(0)、code(±真 FS) 锚定映射。
2. **区分三类缺码来源**：decoder 归一化错误 / 贪心搜索未达 / DAC level 集合本身稀疏。判别实验：全组合 decoder 枚举（2^14）→ 若全码覆盖则非 decoder；exhaustive codebook → 若更差则查其 target 归一化；DC 扫描奇偶模式 → 整数权重+零噪声才有完美奇偶锁定。
3. **证据包自查**：交付的成对 CSV 先做 `diff -q`（构建方曾把 ideal quantizer 与 bridge SAR 的频谱 CSV 交成字节级相同）；表格内部数字互相核对（头条 0 缺码 vs 扫描表 3071）；稀疏扫描的 unobserved ≠ missing（CB sweep 3071=4096−1025）。
4. **校准零噪声截尾检查**：ideal CDAC 零噪声校准，7 target 测得值应精确等于物理值；出现 ×64/65 式比例链 = calDAC 搜索缺 rounding/terminal 位（Chen §8.3：确定性测量无法平均掉量化偏差，需 ~0.5 LSB rms 抖动）。
5. **terminal/rounding 判定必须有幅度门限**：只判残差符号会在微小非零残差（如 P/N 失配自归一化后的 ±0.08 Q0）上每方向净 +1 Q0，沿 wall 链放大（实测 ×66/65）。门限参考：同号且 |残差| ≥ 1 Q0 才调整，或 terminal 用含噪比较器输出 + 对平均（Bagheri §7.2/Huang §4.5）。警惕"用求解器无噪声符号代替比较器判决"的隐形作弊。
6. **calDAC 是尺子，尺子的失配会 1:1 传入测量值**：低段物理权重偏移（桥接比变化→整段偏移；P/N 失配→分侧偏移 ±2%）而码值按标称编码 → 测量偏差并沿 wall 放大（实测 ×63/65 与 ×129/130 两种链）。Chen §8.2 三类后端 DAC 误差源。判别实验：权重注入（只扰低段/桥接/单侧）分离"被校位误差"与"尺子误差"。**关键：高段电容步进在共模失配下自归一化（分子分母同比例），低段（calDAC）步进只随该侧顶板总电容变化——共模失配下尺子照样歪 ±2%。** 残余偏差排除法：零噪声 vs 抖动（排量化噪声）vs 猴子补丁门限（排 terminal）。
7. **共模失配自归一化**：整侧电容同比例变化时 δW≈0（报告式 3.32）——"P/N 共模 ±x%"类场景物理上≈良性，若 calibrated SNDR 大跌而 nominal/physical 正常，必是校准测量链问题而非架构限制。
8. **排障用 target 级校准 trace**：`rep.targets[k].traces` 给出每个 D+/D- 方向逐 calDAC 步的 vdiff/cmp——先核对初始残差量级，再看 terminal 步行为，可一步定位符号/门限类 bug。
9. **交叉验证 FFT 管线**：理想 12-bit 量化器（−0.5 dBFS 相干）必须 ≈73.5 dB，否则先修分析器再谈模型；THD 数字必须声明谐波计入范围。
10. **文献锚点**：Chen 2024（递归传播 (I−A)⁻¹η、§8.2 尺子误差、§8.3 抖动阈值、§8.4 增益归一化）；Bagheri 2020（确定性+随机量化、p 窗口）；Huang 2024 §4.5（无 wall 独立测量、(D+−D−)/2、SRM 降噪）；Wang 2022（位 vs 低位和、两步校正、LSB 段免校前提是不作尺子）。

## 快速核查命令

```bash
cd src && python -m pytest python_cal/tests/ -q
python python_cal/reports/review_monitor_check.py   # 审查方独立核查（20 s）
```

## 当前监控状态（2026-07-23 末，41 号后）

审查文档已迁入 `review/`（38/39/40/41）。R1 部分通过；P0-A 关闭、P0-C 关闭。两项违规已根因裁定：P/N asym −5.4 = terminal_adj 只判符号无门限（×66/65 链）；bridge +2% −1.2 = calDAC 标称码尺子误差（×63/65 链）。41 号强制专项 C1–C5（C1 terminal 修复最高优先，判据：P/N asym target ±0.5 Q0、7 场景 ≥ −0.5 dB；两次不交触发交接条款）。待办：C1 > R5(VA 对账) > C2/C3 > C4 > R3/R2/R7/R6/C5。42 号《完整复现方案》待写。详见当日 memory 与 review/41。
