# 本机 Git 与 Cadence VM 工作区地图

> 盘点日期：2026-07-26
> 性质：当前工作区交接与版本边界说明。它不是仿真签核报告，也不替代
> `docs/final_report.pdf`。

## 1. 当前权威工作目录

### 1.1 本机 Git 工程

- **Git 根目录**：
  `C:\Users\Administrator\Desktop\SAR_ADC_IDEAL_CAL_REPLACEMENT_V6_CLEAN`
- **当前分支**：`codex/python-cal-validation`
- **盘点时 HEAD**：`b4a71bd`（`Adopt STSong report typography`）
- **远端**：`origin/codex/python-cal-validation`
- **盘点时状态**：clean

会话最初落在下面这个同名嵌套目录：

`C:\Users\Administrator\Desktop\SAR_ADC_IDEAL_CAL_REPLACEMENT_V6_CLEAN\SAR_ADC_IDEAL_CAL_REPLACEMENT_V6_CLEAN`

该目录为空，也不是 Git 根。若从这里执行 `rg --files`，会得到“没有 VA、RTL、
Python”的假象。后续所有本机命令必须显式以真正 Git 根为工作目录。

### 1.2 Cadence VM 工程

- **SSH**：`meow@192.168.38.128:22`
- **Cadence 工作区**：`/home/meow/jxy`
- **OA 库**：`/home/meow/jxy/12bit_50M_SAR`
- **生成仿真数据**：`/home/meow/jxy/simulation/12bit_50M_SAR`
- **临时研究沙盒**：`/home/meow/jxy/trae_sandbox`
- **PDK**：`/home/meow/Desktop/TSMC18RF/tsmc18rf`
- **库定义**：`/home/meow/jxy/cds.lib`
- **审计输出**：`/tmp/vm_output`

盘点时 Virtuoso 和 Spectre 均未运行。`/home/meow/jxy` 下没有发现 Git 仓库，
所以 VM OA/AMS 文件不能用 Git commit 自动判断版本；必须使用 OA cell 名、文件
mtime、SHA-256 和 Maestro run ID 联合标识。

## 2. 两条实现线不能混为一谈

```text
Local Git line
  Python physical model -> calibration/decoder -> validation/evidence
                         -> synthesizable calibration RTL
                         -> compact AMS interface VA

Cadence VM line
  OA schematic / transistor blocks
      -> Cadence-native Verilog-A cells
      -> Maestro/Spectre run directories
      -> exploratory calibration sandboxes
```

本机 Git 是 2026-07-24 至 2026-07-26 收敛的行为级、RTL 和交付线；VM 是更早的
OA/AMS 集成线。两者物理目标相关，但模块接口、CDAC 结构、定点格式和校准状态并不
相同，不能把 VM 的旧通过结果直接算作当前 Git VA 的 Spectre 验证。

## 3. 本机工程组织

| 路径 | 责任 | 当前边界 |
|---|---|---|
| `src/python_cal/physical/` | P/N split-CDAC、浮动 bridge、两节点电荷守恒 | 行为级黄金物理链 |
| `src/python_cal/calibration/` | Shen-derived 前景权重校准 | Q8 逐目标写回 |
| `src/python_cal/conversion/`、`decode/` | 异步转换、trace 与 Q2 解码 | 不是完整芯片 RTL |
| `src/python_cal/validation/` | 失配、FFT、静态与验收矩阵 | Python L2 证据 |
| `rtl/` | 校准 FSM、lower-SAR、权重寄存器与 testbench | 可综合子系统，不是 full ADC RTL |
| `va/` | CDAC 与比较器 AMS 接口骨架 | 尚未与 VM 当前 OA 顶层闭环 |
| `evidence/` | 冻结结果、manifest 与报告输入 | 报告数据来源 |
| `docs/` | 架构、验收、报告与版本说明 | 不替代电路级签核 |

本机 VA 确实存在且由 Git 跟踪：

- `va/cdac_behavioral.va`：差分 split-CDAC 两节点电荷守恒；P/N 独立 group
  multiplier；模块内部不抽随机数。
- `va/strongarm_cmp.va`：带 offset、可选噪声、输入相关决策延迟与 `ready`
  握手的行为比较器；明确不是晶体管 StrongArm signoff model。

两份文件最初进入 Git 的 commit 是 `65a02dd`，当前 PER-UNIT 语义更新在
`5e4b6a8`。因此“当前文件夹没有 VA”的原因是工作目录多套了一层，不是文件丢失。

## 4. VM 工程组织

### 4.1 OA 库：`/home/meow/jxy/12bit_50M_SAR`

盘点大小约 88 MB。它包含晶体管级单元、schematic/symbol、Cadence Verilog-A
cellview 和 Maestro state。与当前失配/校准相关的主要 VA cell 为：

| OA cell | 文件 | 作用 | 盘点版本 |
|---|---|---|---|
| `CDAC_VA` | `CDAC_VA/veriloga/veriloga.va` | 内部 PER-UNIT MC 的 binary split-CDAC | 2026-07-21，SHA-256 `9b5332d9...525e` |
| `COM_ideal_VA` | `COM_ideal_VA/veriloga/veriloga.va` | 带校准 dither 的理想锁存比较器 | 2026-07-21，`70538cb7...9376` |
| `SWITCH_CAL` | `SWITCH_CAL/veriloga/veriloga.va` | 正常转换/校准复用开关 | 2026-07-21，`d04bb530...a2b` |
| `SYNC_asnyc_ideal` | `SYNC_asnyc_ideal/veriloga/veriloga.va` | 行为同步/异步控制接口 | 2026-07-21，`2afac238...82db` |
| `DEC_CAL_PHY` | `DEC_CAL_PHY/veriloga/veriloga.va` | V6.5 三目标 Huang 权重校准与解码 | 2026-07-22，`35088cfd...fb0` |

VM 的 `CDAC_VA` 在模块内部按 unit capacitor 生成失配；本机
`cdac_behavioral.va` 接受外部已经实现的 group multiplier。两者的随机数责任和
端口契约不同，不能按文件名相似就当成同一个版本。

### 4.2 Maestro/Spectre 生成区

`/home/meow/jxy/simulation` 当前约 25 GB，主要由以下三组结果组成：

| 目录 | 大小 | 处理原则 |
|---|---:|---|
| `.../test_12bit50MSAR_AMS_final` | 约 13 GB | 含最新 2026-07-23 normal/noise run；先保留 |
| `.../test_12bit50MSAR_AMS_final_0713` | 约 11 GB | 历史大结果；只列为清理候选 |
| `.../test_12bit50MSAR_AMS_final_0716` | 约 887 MB | 含校准 VA run 381--388；先保留 |

这些是生成数据，不是 OA 源码。未确认可复现与结果归档前不得移动或删除。

### 4.3 `trae_sandbox`

2026-07-26 已完成受控整理：139个历史 `.va/.scs/.sv/脚本/日志` 按原路径归档到
`trae_sandbox/_archive/legacy_sources_netlists_20260726.tar.gz`，归档 SHA-256 为
`6de472cec03ace5456d332738a6d7652f1037c27beabf8cd6384143addf068e4`。
随后只删除清单中的20个旧沙箱顶层项，共706,362,969 bytes；未触碰 OA 库或主
`simulation`。当前结构为：

- `_archive/`：历史源码/网表归档、manifest 和清理日志；
- `current_git_74e7366/`：当前 Git VA/RTL standalone 验证沙箱；
- 当前源、testbench、run 和报告互相隔离，不再使用 `codex_agent_*` 临时目录。

该 current 沙箱的复核结果为：StrongARM VA PASS；split-CDAC VA PASS（保留4条
`VACOMP-1116` 连续信号 `transition()` 语义警告）；calibration RTL self-check PASS；
lower-SAR RTL self-check PASS；`cal_top` compile/elaborate PASS。最终占用15 MB。
这些结果只证明 standalone VA/RTL 契约，不代表 OA/AMS、PVT、噪声或流片通过。

## 5. 之前工作实际停在哪里

### 5.1 独立的 2026-07-18 source-centered campaign

Windows Obsidian 归档中仍存在完整报告和脚本：

`D:\ReedZhao\Document\Obsidian\日常\10_项目区\2026_12bit10Msar\04_辅助工具\veriloga_models\codex_calibration_20260717`

该报告记录：实际源网表中心、Omran PER-UNIT 失配、8/8 校准 `DONE=1/ERR=0`，
以及完整晶体管级 ADC FFT 的 7/8 样本超过 73 dB；`sample03` 为 72.6214 dB
尾部限制。这是一条已经冻结的 source-centered campaign，但其命名交付物当前不在
VM OA 根或 `trae_sandbox` 中，不能据此声称 VM 最新 cellview 仍等价。

### 5.2 VM Cadence-native VA 集成线

VM 里的后续工作继续改了 `CDAC_VA`、`SWITCH_CAL`、`COM_ideal_VA`、
`SYNC_asnyc_ideal` 和 `DEC_CAL_PHY`：

1. `Interactive.383` 与 `.384`（2026-07-21）曾得到 ENOB 11.87 和 11.50；
2. 之后 `DEC_CAL_PHY` 在 2026-07-22 更新为 V6.5；
3. 更新后的 `Interactive.387` 结果退化到 ENOB -0.675；
4. 最后一次 `.388` 被用户停止；停止前日志已经给出
   `SATURATE target=2`、`AUTORANGE FAIL`、`DONE=1`、`ERR=1`，因此最终 V6.5
   不能判为闭环通过。

这意味着 VM VA 集成线停在“源码可编译、部分旧版本跑通过、当前最终版本校准接口
失败待定位”，而不是“当前 VA 已签核”。

### 5.3 2026-07-23 normal/noise 线

`Interactive.339` 是正常晶体管级 ADC sweep，五点完成且无仿真错误，汇总为
ENOB 11.55、SNR 71.22 dB、SFDR 86.31 dB。`Interactive.340` 与 `.339` 的关键
netlist 差异是：

```spectre
noisescale=10 noiseon=[ I14 I1]
```

其中 `I14` 是 `SWITCH`，`I1` 是 `CDAC`。该 10 倍瞬态器件噪声压力导致点 3--5
的 ENOB 约 10.08--10.61。它是噪声注入敏感性测试，不是失配校准失败，也不应
覆盖本项目“失配对 SAR ADC 的影响”这一主线。

## 6. 当前版本结论

- 本机 Git 才是当前 Python/RTL/紧凑 VA/报告的版本化工程；
- VM OA 库才是晶体管级和 Cadence-native AMS 的真实工程；
- 两条线尚未完成一一映射，尤其是 CDAC 拓扑、失配注入责任、Q-format、目标数量和
  comparator/ready 接口；
- 当前不能用 VM 的旧 VA run 替代本机当前 VA 的 Spectre/AMS 验证；
- 当前也不能把 `Interactive.340` 的 10 倍 CDAC/开关噪声退化解释成失配校准结论。

## 7. 安全整理规则与下一步

1. 本机所有工作固定从真正 Git 根执行；同名空嵌套目录不作为项目入口。
2. 不直接修改 `/home/meow/jxy/cds.lib`、PDK、OA 根或正在运行的 Maestro run。
3. 先建立“本机 current VA -> VM staging cell/testbench”的明确端口映射和 hash
   manifest，再导入 OA；禁止覆盖现有 `CDAC_VA`/`DEC_CAL_PHY`。
4. 第一闭环只做 ideal trace：四个输入、逐 stage `VTOP_P-VTOP_N`、decision 和
   code 对齐；通过后再加入同一 PER-UNIT seed。
5. 失配是主验证轴；噪声仅作为校准稳健性附加轴，默认不使用 `.340` 的 10 倍压力
   条件代表产品规格。
6. 主 `/home/meow/jxy/simulation` 被明确列为保护路径；即使其中存在约24 GB历史
   数据，也必须获得针对该目录的单独授权后才能制定清理计划。
7. 所有后续操作遵循 [VM远程操作规范](VM_REMOTE_OPERATIONS_STANDARD.md)。
