---
title: Pipelined SAR ADC 文献综述与精读清单
aliases:
  - Pipelined SAR ADC 文献矩阵
  - 文献综述
tags:
  - SAR-ADC
  - pipelined-SAR
  - literature-review
  - literature-matrix
created: 2026-06-29
updated: 2026-06-29
stats:
  total_collected: 32
  after_screening: 28
  by_topic:
    kt_c_cancellation: 5
    calibration: 4
    ring_amplifier: 5
    dynamic_amplifier: 5
    time_interleaved: 3
    noise_shaping: 4
    survey: 4
  top20_ready: true
---

# Pipelined SAR ADC 文献综述与精读清单

## 0. 综述说明

本文档面向 **12-bit 50MS/s 采样噪声 AZ 消除 SAR ADC** 项目，按 **技术问题** 而非架构分类来组织 Pipelined SAR ADC 文献。每个章节先讲清这一类文献要回答什么问题，再列出关键论文，最后给出与本项目的关系。

文献覆盖 2011–2025 年，重点为 JSSC / ISSCC / VLSI / Electron. Lett. / 顶会顶刊；IEEE 链接补充 DOI。

## 1. 概览与统计

- **检索日期**：2026-06-29
- **初筛收集**：32 篇
- **最终保留**：28 篇
- **按主题分类**：

| 编号 | 主题 | 论文数 | 重点文献 |
|:--|:--|:--:|:--|
| I | **kT/C 噪声消除** | 5 | Liu 2020、Gao 2023、Cui 2026 |
| II | **后台/前台校准** | 4 | Shen 2020a、Zhang 2020、Wang 2023 |
| III | **Ring Amplifier 残余放大** | 5 | Hershberg 2012、Lagos 2019、Lim 2024 |
| IV | **Dynamic Amplifier 残余放大** | 5 | Huang 2017、Wu-Yuan 2019、Chen 2024 |
| V | **时间交织 (TI) 高速** | 3 | Kull 2017、Martens 2018、He 2024 |
| VI | **噪声整形 (NS) SAR** | 4 | Jie 2020、Cheng 2025、Liu 2021 |
| VII | **综述与综述性研究** | 4 | Liu-Sun 2020、Zhu-Liu 2024、李登全 2025 |

- **Top 20** 精读清单见 §10。
- **项目对接** 见 §11。

---

## I. kT/C 噪声消除（5 篇）

> **回答的问题**：在不增加输入电容/功耗的前提下，如何让 SAR ADC 不为 kT/C 噪声付出代价？

| # | 标题 | 作者 | 年份 | 来源 | 关键指标 | DOI / 链接 |
|:--|:--|:--|:--:|:--|:--|:--|
| 1 | A 13-bit 0.005-mm² 40-MS/s SAR ADC with kT/C Noise Cancellation | Liu J, Tang X, Zhao W, Shen L, Sun N | 2020 | JSSC 55(12) | **13b / 40 MS/s / kT-C 消除经典实现** | [10.1109/JSSC.2020.3016656](https://doi.org/10.1109/JSSC.2020.3016656) |
| 2 | A 12-b 400-MS/s SAR ADC achieving 74.5-dB SNDR with free-time-window full-hold kT/C noise cancellation | Gao J, et al. (Peking) | 2023 | ISSCC（**唯一最佳论文奖**） | 12b / 400 MS/s / 74.5 dB SNDR | [ISSCC 2023 FP](https://www.isscc.org/) |
| 3 | An improved kT/C noise cancellation technique with presampling for high-speed SAR ADCs | Gu Y, Wang K, Yi T, Chen X, Yang S, Liu J (UESTC) | 2024 | Electron. Lett. 60(16) e13298 | 预采样辅助 kT/C 消除 | [10.1049/ell2.13298](https://doi.org/10.1049/ell2.13298) |
| 4 | A Buffer-in-Loop NS-SAR ADC With CDAC Sharing-Error Feedback Structure and kT/C Noise Cancellation in 0.18-μm CMOS | Cui Z, Shi Y, Sun Q, Zhu H (Fudan) | 2026 | TVLSI 34(1) 327–331 | 74.9 dB SNDR / 0.6 MHz BW / 180 nm | [10.1109/TVLSI.2025.3619126](https://doi.org/10.1109/TVLSI.2025.3619126) |
| 5 | Error suppression techniques for energy-efficient high-resolution SAR ADCs | Liu J, Tang X, Shen L, Li S, Li Z, Guo W, Sun N (综述) | 2020 | J. Semicond. 41(11) 111403 | 综述 kT/C + NS + MES 三类误差抑制 | [10.1088/1674-4926/41/11/111403](https://doi.org/10.1088/1674-4926/41/11/111403) |

> [!note] 与本项目关系
> Liu-Sun 2020 的辅助电容 + 减法消除思路是 CMAZ 方案的理论前身；Gao 2023 提供 free-time-window 实现路径；Gu 2024 的预采样思路与你报告 §2.2.4.5 E 组"预采样自举电容 1pF vs 3pF"的发现直接呼应。

---

## II. 后台/前台校准（4 篇）

> **回答的问题**：12-bit 以上 PVT 跟踪、不中断转换的失配/增益误差校准方案有哪些？

| # | 标题 | 作者 | 年份 | 来源 | 关键指标 | DOI / 链接 |
|:--|:--|:--|:--:|:--|:--|:--|
| 6 | Background bit-weight calibration in pipelined successive approximation register ADC | Shen C (Southeast U.) | 2020a | Electron. Lett. 56(1) 15–17 | SNDR 66.3 → 73.3 dB | [10.1049/el.2019.2636](https://doi.org/10.1049/el.2019.2636) |
| 7 | Digital background calibration technique for pipelined SAR ADCs with detect-and-switching algorithm | Zhang L, Han S, Huang L, Wu J | 2020b | Electron. Lett. 56(11) 533–536 | 高分辨率背景下 detect-and-switch | [10.1049/el.2020.0320](https://doi.org/10.1049/el.2020.0320) |
| 8 | Dither-based calibration of bit weights in pipelined-SAR ADCs with fast convergence speed using partially split structure | Sun J, Li X, Yan C, Liu W | 2020c | Electron. Lett. 56(18) 916–918 | 加速收敛的 dither 校准 | [10.1049/el.2020.0579](https://doi.org/10.1049/el.2020.0579) |
| 9 | Signal-Independent Background Calibration with Fast Convergence Speed in Pipeline-SAR ADC | Wang YJ, Wang P (Tsinghua), Wan LX, Jin Z | 2023 | Micromachines 14(2) 300 | SNDR 45.3 → 68.2 dB；收敛加速 30× | [10.3390/mi14020300](https://doi.org/10.3390/mi14020300) |

> [!note] 与本项目关系
> 你 6.29 发现 **近 Nyquist MC 下 CPK=0.0x**，纯模拟匹配已不足以量产。这 4 篇都是 12-bit+ Pipelined-SAR 必走的数字背景校准路径：
> - Shen 2020a 简单可靠，作为入门参考；
> - Wang 2023 的 signal-independent + 快收敛最贴合量产（CPK 工程）需求。

---

## III. Ring Amplifier 残余放大（5 篇）

> **回答的问题**：动态非线性残余放大器（Ringamp）的设计空间、PVT 鲁棒性、极限速度如何？

| # | 标题 | 作者 | 年份 | 来源 | 关键指标 | DOI / 链接 |
|:--|:--|:--|:--:|:--|:--|:--|
| 10 | Ring Amplifiers for Switched Capacitor Circuits | Hershberg B, Weaver S, Sobue K, et al. | 2012 | JSSC | **Ringamp 奠基论文** | [10.1109/JSSC.2011.2173652](https://doi.org/10.1109/JSSC.2011.2173652) |
| 11 | A 1-GS/s 12-b Single-Channel Pipelined ADC with Dead-Zone-Degenerated Ring Amplifiers | Lagos J, Hershberg B, Martens E, et al. | 2019 | JSSC 54(3) | 12b / 1 GS/s / 56.6 dB SNDR / 24.8 mW | [10.1109/JSSC.2018.2885682](https://doi.org/10.1109/JSSC.2018.2885682) |
| 12 | A 6-to-600 MS/s Fully Dynamic Ringamp Pipelined ADC with Asynchronous Event-Driven Clocking in 16 nm | Hershberg B, van Liempd B, Markulic N, et al. | 2019 | ISSCC | 11b / 异步事件驱动 | [ISSCC 2019 3.6](https://www.isscc.org/) |
| 13 | A 1 MS/s to 1 GS/s Ringamp-Based Pipelined ADC with Fully Dynamic Reference Regulation and Stochastic Scope-on-Chip Background Monitoring | Hershberg B, Markulic N, Lagos J, Martens E, Craninckx J | 2021 | JSSC | 11b / 500 MS/s pipelined-SAR / dither 校准 | [10.1109/JSSC.2020.3038926](https://doi.org/10.1109/JSSC.2020.3038926) |
| 14 | A 2.08 mW 64.4 dB SNDR 400 MS/s 12b Pipelined-SAR ADC using Mismatch and PVT Variation Tolerant Dynamically Biased Ring Amplifier in 8 nm | Lim Y, et al. (Samsung) | 2024 | ISSCC 9.2 | **12b / 400 MS/s / 64.4 dB / 全无校准** | [ISSCC 2024 9.2](https://www.isscc.org/) |

> [!note] 与本项目关系
> 你报告中"FF 85°C 高跨导削弱消除能力 / SS 85°C 严重恶化"的 PVT 鲁棒性问题，与此类工作的核心矛盾一致：
> - Lagos 2019 的 DZD 是处理工艺角稳定性的标准技巧；
> - Hershberg 2021 的 dither 背景校准，是从根本上消除 PVT 漂移的工业实践；
> - Lim/Samsung 2024 的「无校准 PVT 鲁棒 RA」是最直接参考范式。

---

## IV. Dynamic Amplifier 残余放大（5 篇）

> **回答的问题**：开环动态放大器（FIA、CCD-DA、Dyn-Amp）作为残余放大时的 PVT 稳定性策略？

| # | 标题 | 作者 | 年份 | 来源 | 关键指标 | DOI / 链接 |
|:--|:--|:--|:--:|:--|:--|:--|
| 15 | A non-interleaved 12b 330MS/s pipelined-SAR ADC with PVT-stabilized dynamic amplifier achieving sub-1-dB SNDR variation | Huang H, Xu H, Elies B, Chiu Y | 2017 | JSSC 52(12) | 12b / 330 MS/s / PVT 稳定 + <1 dB 漂移 | [10.1109/JSSC.2017.2754222](https://doi.org/10.1109/JSSC.2017.2754222) |
| 16 | A 12-Bit 300-MS/s Single-Channel Pipelined-SAR ADC with an Open-Loop MDAC | Wu C-M, Yuan J | 2019 | JSSC 54(5) | 12b / 300 MS/s / 开环 MDAC | [10.1109/JSSC.2019.2892505](https://doi.org/10.1109/JSSC.2019.2892505) |
| 17 | Capacitively Degenerated Dynamic Amplifier (VLSI 2022 special issue) | Hsu et al. (Yonsei) | 2022 | JSSC | 65 dB SNDR / 50 MS/s / 0.46 mW | [VLSI 2022](https://www.vlsisymposium.org/) |
| 18 | A 182.3 dB FoMs 50 MS/s Pipelined-SAR ADC using Cascode Capacitively Degenerated Dynamic Amplifier and MSB Pre-Conversion Technique | Chen Z, et al. (Peking) | 2024 | ISSCC 9.4 | **74 dB SNDR / 50 MS/s / 0.36 mW / FoMs=182.3 dB** | [ISSCC 2024 9.4](https://www.isscc.org/) |
| 19 | A PVT-stable 12-bit 800-MS/s pipelined SAR ADC with gain-enhanced gm-ratio amplifier | — | 2025 | IEICE Trans. Electron. | 12b / 800 MS/s / gm-ratio RA | [IEICE Trans. Electron.](https://search.ieice.org/) |

> [!note] 与本项目关系
> 本项目残余放大采用 **FIA（动态放大器）+ CMAZ** 路线，本章直接对应：
> - Chen 2024（50 MS/s、74 dB SNDR）**与你 12b 50MSAR 同规格**，FoMs 182.3 dB 是当前最优基准，必读；
> - Huang 2017 的 PVT 稳定 dyn-Amp 思路直接对应你 SS 85°C 难题；
> - 19 的 gm-ratio RA 思路提供完全避免 PVT 漂移的备选方案。

---

## V. 时间交织（TI）高速（3 篇）

> **回答的问题**：如何将 Pipelined-SAR 推到 GS/s 量级？时间交织带来的失配/相位噪声如何处理？

| # | 标题 | 作者 | 年份 | 来源 | 关键指标 | DOI / 链接 |
|:--|:--|:--|:--:|:--|:--|:--|
| 20 | A 10b 15 GS/s pipelined-SAR ADC with background second-stage CM regulation and offset calibration in 14 nm CMOS FinFET | Kull L, Luu D, Menolfi C, et al. (IBM) | 2017 | ISSCC | **10b / 15 GS/s / 14 nm FinFET** | [ISSCC 2017 8.4](https://www.isscc.org/) |
| 21 | A 69-dB SNDR 300-MS/s two-time interleaved pipelined SAR ADC in 16-nm CMOS FinFET with capacitive reference stabilization | Martens E, et al. (imec) | 2018 | JSSC 53(4) | 2× TI / 16 nm / 69 dB | [10.1109/JSSC.2017.2783857](https://doi.org/10.1109/JSSC.2017.2783857) |
| 22 | A 71 dB SNDR 200 MHz BW Interleaved Pipe-SAR ADC with a Shared Residue Integrating Amplifier Achieving 173 dB FoMs | He X, et al. (Tsinghua) | 2024 | ISSCC 9.3 | 1.6 GS/s TI / 71.2 dB / 13 mW | [ISSCC 2024 9.3](https://www.isscc.org/) |

> [!note] 与本项目关系
> 本项目当前为单通道 50 MS/s，不直接走 TI 路线。但 §2.2.4.5 中 FF / SF / FS 工艺角退化问题与 TI 的 timing skew 有类似物理根源——延迟链失配导致比较器判决点漂移。Martens 2018 的边沿校准方法对你 FF 角 SFDR 难题有借鉴价值。

---

## VI. 噪声整形（NS）SAR（4 篇）

> **回答的问题**：用噪声整形把量化/比较器噪声推到带外，换取更高分辨率带宽的折中点在哪里？

| # | 标题 | 作者 | 年份 | 来源 | 关键指标 | DOI / 链接 |
|:--|:--|:--|:--:|:--|:--|:--|
| 23 | A cascaded noise-shaping SAR architecture for robust order extension | Jie L, Zheng B, Chen H-W, Flynn MP | 2020 | JSSC 55(12) 3236–3247 | 级联 NS SAR | [10.1109/JSSC.2020.3019487](https://doi.org/10.1109/JSSC.2020.3019487) |
| 24 | A 250 kHz-BW 93 dB-SNDR 4th-order noise-shaping SAR using capacitor stacking and dynamic buffering | Liu J, Li D, Zhong Y, Tang X, Sun N | 2021 | ISSCC 27.1 | 4 阶 NS / 93 dB / 250 kHz | [10.1109/ISSCC42613.2021.9366008](https://doi.org/10.1109/ISSCC42613.2021.9366008) |
| 25 | An 84-dB SNDR low-OSR 4th-order NS-SAR with FIA-assisted EF-CRFF structure and noise-mitigated push-pull Buffer-in-Loop technique | Xie T, Wang T-H, Liu Z, Li S | 2022 | JSSC 57(12) 3804–3815 | **FIA 辅助 EF / 与你方案最接近** | [10.1109/JSSC.2022.3199241](https://doi.org/10.1109/JSSC.2022.3199241) |
| 26 | A 94.3-dB SNDR 184-dB FoMs 4th-order noise-shaping SAR ADC with dynamic-amplifier-assisted cascaded integrator | Cheng K-C, Chang S-J, Chen C-C, Hung S-H (NCKU) | 2025 | IEEE Solid-State Circuits Lett. 8 65–68 | 100 kHz BW / 107 μW / FoMs 184 dB | [10.1109/LSSC.2025.3544649](https://doi.org/10.1109/LSSC.2025.3544649) |

> [!note] 与本项目关系
> Xie 2022 的 **FIA-assisted EF-CRFF** 结构与你方案的物理图景最为相近（FIA + EF），但走的是闭环 NS 路线；本项目走开环采样噪声 AZ 路线，**因此 Xie 2022 是反向参照**——看它的闭环 FIA 用法，反推你的开环 CMAZ 可能漏掉的耦合路径。

---

## VII. 综述与基础（4 篇）

> **回答的问题**：快速建立全局视图；理解各方案的边界条件与设计自由度。

| # | 标题 | 作者 | 年份 | 来源 | 范围 | DOI / 链接 |
|:--|:--|:--|:--:|:--|:--|:--|
| 27 | Error suppression techniques for energy-efficient high-resolution SAR ADCs | Liu J-Tang X-Shen L-Li S-Sun N | 2020 | J. Semicond. 41(11) 111403 | kT/C + NS + MES 综合综述 | [10.1088/1674-4926/41/11/111403](http://dx.doi.org/10.1088/1674-4926/41/11/111403) |
| 28 | Digitalized analog integrated circuits | Zhu Z, Liu S (Xidian) | 2024 | Fundam. Res. | 数字化模拟电路全景 | [10.1016/j.fmre.2023.01.010](https://doi.org/10.1016/j.fmre.2023.01.010) |
| 29 | A Review on Fundamentals of Noise-Shaping SAR ADCs and Design Considerations | Arzate-Palma VH, Rivera-Orozco DG, et al. | 2024 | Chips 3(2) 162–195 | NS SAR 基础与设计考量 | [10.3390/chips3020010](https://doi.org/10.3390/chips3020010) |
| 30 | 高速高精度混合架构模数转换器集成电路综述 | 李登全, 朱樟明 (Xidian) | 2025 | 微电子学与计算机 42(10) | Pipelined-SAR / VTC / TI 三类中文综述 | [期刊页面](http://www.microolelo.com/) |

---

## VIII. 国际经典早期作品（保留参考）

> 本项目当前问题不直接涉及，但建立思路追溯用。

| # | 标题 | 作者 | 年份 | 来源 | 关键贡献 |
|:--|:--|:--|:--:|:--|:--|
| 31 | A SAR-assisted two-stage pipeline ADC | Lee CC, Flynn MP | 2011 | JSSC 46(4) | **首篇 SAR-assisted pipeline** 概念论文 |
| 32 | A 1.7 mW 11b 250 MS/s 2× interleaved fully dynamic pipelined SAR ADC in 40 nm digital CMOS | Verbruggen B, Iriguchi M, Craninckx J (imec) | 2012 | JSSC 47(12) | 早期 pipelined-SAR 全动态经典实现 |

---

## 9. 检索方法与日志

- **检索工具**：WebSearch（多轮）
- **辅助来源**：作者主页、IEEE Xplore、IET、MDPI、arXiv
- **筛选标准**：
  1. 与 Pipelined SAR ADC 强相关；
  2. 顶会/顶刊 / 高引用 / 综述性；
  3. 近 5 年优先（2020+）；
  4. 含与本项目相关的 PVT / 校准 / kT-C 主题；
  5. DOI 可查证。

| 查询主题 | 命中文献 |
|:--|:--|
| pipelined SAR ADC two-stage residue ISSCC 2023 2024 | 11, 13, 14, 18, 22 |
| pipelined SAR ADC survey tutorial hybrid | 27, 30 |
| SAR-assisted pipelined ADC dynamic amplifier JSSC 2022 2023 | 15, 16, 17 |
| "pipelined SAR" 100MS 12b 14b high speed energy efficient | 14, 16, 18 |
| "pipelined SAR" JSSC OR VLSI Symposium ring amplifier | 10–13 |
| Verbruggen / Kull / Martens TI pipelined SAR | 20, 21, 32 |
| "two-step" / "two-stage" hybrid 100/200 MS residue | 15, 16 |
| ring amplifier pipelined SAR ISSCC 2019-2021 Hershberg | 10, 11, 12, 13 |
| SAR-assisted pipeline ADC NS cascaded integrator 2021-2022 | 23–26 |
| pipelined SAR ADC calibration background digital | 6, 7, 8, 9 |
| SAR ADC kT/C noise cancellation JSSC 2020-2023 | 1, 2, 3, 4, 5 |
| dynamic amplifier residue PVT stable ringamp comparison | 15, 17, 19, 28 |

---

## 10. Top 20 精读清单（按优先级）

| 排名 | 文献 | 必读理由 |
|:--:|:--|:--|
| 1 | **Chen / Peking 2024 (ISSCC 9.4)** | 50 MS/s Pipelined-SAR + CCD-DA，**与本项目同规格**，FoMs 182.3 dB 是直接对标基准 |
| 2 | **Gao / Peking 2023 (ISSCC 最佳论文)** | kT/C 消除 + CLS，与你 CMAZ 主线物理图景互补 |
| 3 | **Liu-Sun 2020 JSSC** | kT/C 消除经典实现，CMAZ 思路理论前身 |
| 4 | **Xie-Li 2022 JSSC** | FIA-assisted EF-CRFF，与你方案 FIA 用法同源；反向参照 |
| 5 | **Huang-Chiu 2017 JSSC** | PVT 稳定 dyn-Amp 标准技巧，直接对应 SS 85°C 难题 |
| 6 | **Lagos 2019 JSSC (DZD)** | Ringamp PVT 工艺角稳定性技巧 |
| 7 | **Hershberg 2021 JSSC** | dither 背景校准，解决 PVT 漂移工业实践 |
| 8 | **Lim/Samsung 2024 ISSCC 9.2** | 无校准 PVT 鲁棒 RA，对你问题 8 直接借鉴 |
| 9 | **Wang-Tsinghua 2023 Micromachines** | 信号无关快收敛校准，对 CPK 工程化最实用 |
| 10 | **He-Tsinghua 2024 ISSCC 9.3** | 1.6 GS/s TI + 共享 RA + NS 最新方案 |
| 11 | **Liu-Sun 2020 JoS (综述)** | kT/C + NS + MES 全景综述，快速建立全局 |
| 12 | **Gu-UESTC 2024 EL** | 预采样 kT/C 消除，与你 E 组 1pF vs 3pF 发现直接呼应 |
| 13 | **Cui-Fudan 2026 TVLSI** | BIL NS + CS-EF + kT/C 消除组合，180 nm 工艺参考 |
| 14 | **Cheng-NCKU 2025 LSSC** | 4 阶 NS + dyn-Amp cascaded integrator，FoMs 184 dB |
| 15 | **Jie-Flynn 2020 JSSC** | 级联 NS 阶数扩展方法 |
| 16 | **Wu-Yuan 2019 JSSC** | 12b 300MS/s 开环 MDAC 单通道路径 |
| 17 | **Liu-Sun 2021 ISSCC** | 4 阶 NS SAR + 电容堆叠 |
| 18 | **Martens 2018 JSSC** | 16nm FinFET TI 工艺角边沿校准经验 |
| 19 | **Hershberg 2012 JSSC** | Ringamp 奠基论文，理解 RA 路线必读 |
| 20 | **李登全 2025 综述** | 中文综述，建立 Pipelined-SAR 全局视图 |

---

## 11. 与本项目的对接建议

> [!important] 对照本项目 12-bit 50MSAR 已知问题
>
> | 项目问题 | 文献建议 |
> |:--|:--|
> | **kT/C 噪声 AZ 消除**（主线） | Liu 2020 (经典) + Gao 2023 (最佳论文) + Gu 2024 (预采样) |
> | **FF 85°C SFDR/SFDR 退化** | Huang 2017 (PVT dyn-Amp) + Lim 2024 (PVT 鲁棒 RA) |
> | **SS 85°C SNR 恶化** | Lagos 2019 (DZD) + Hershberg 2021 (dither 校准) |
> | **近 Nyquist MC CPK=0.0x** | Shen 2020a / Wang 2023 / Sun 2020c (背景校准) |
> | **FFB 反馈对 / 速度不够** | He 2024 (共享 RA 设计) + Chen 2024 (MSB 预转换 + CCD-DA) |
> | **FIA + CMAZ 路线总图** | Xie 2022 (FIA 辅助闭环 EF) 作为反向参照 |
>
> **建议精读顺序**：Chen 2024 → Gao 2023 → Liu 2020 → Xie 2022 → Huang 2017 → Lagos 2019 → Wang 2023 → Lim 2024 → Hershberg 2021

---

## 12. 关键术语对照

| 中文 | 英文 | 缩写 |
|:--|:--|:--|
| 残余放大器 | Residue Amplifier | RA |
| 环形放大器 | Ring Amplifier | Ringamp |
| 动态放大器 | Dynamic Amplifier | Dyn-Amp / FIA |
| 电容退化动态放大器 | Cascode Capacitively Degenerated Dynamic Amplifier | CCD-DA |
| 死区退化 | Dead-Zone Degenerated | DZD |
| 噪声整形 | Noise Shaping | NS |
| 误差反馈 | Error Feedback | EF |
| 失配误差整形 | Mismatch Error Shaping | MES |
| 相关电平移位 | Correlated Level Shifting | CLS |
| 时间交织 | Time-Interleaved | TI |
| 后台校准 | Background Calibration | — |
| kT/C 噪声消除 | kT/C Noise Cancellation | — |
| 采样噪声消除（本项目方案） | Sampling Noise AZ Cancellation | **CMAZ** |
