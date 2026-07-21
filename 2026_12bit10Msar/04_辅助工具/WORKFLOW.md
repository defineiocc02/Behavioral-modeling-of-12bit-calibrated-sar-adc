# SAR ADC 仿真自动化工作流

## 设计哲学：AI-Native 的模拟 IC 自动化基础设施

> 本工作流基于张托肯（Token Zhang / Zhishuai Zhang, Tsinghua）开源的 Agentic EDA 基础设施。
> 核心理念：**不给 AI 换工具，给 AI 装"手"**——让 LLM 直接操作工业标准 EDA 工具，而非另起炉灶。

---

### 为什么不是"自动化工具"？

传统自动化跑仿真就是包装一层脚本（`run_simulation.sh`、`parse_results.py`），但张托肯这套的切入点完全不同：

| 对比维度 | 传统脚本自动化 | 张托肯的 AI-Native 方案 |
|---------|-------------|---------------------|
| 驱动方式 | 人类写好脚本 → 机器执行 | AI 理解意图 → AI 自己写代码调用 Cadence |
| 交互通道 | Shell 命令 | **TCP RPC + SKILL IPC** — AI 直接与 Virtuoso 内存对话 |
| 反馈回路 | 等结果 → 人类看波形 | AI 自己打开 PSF → 读数据 → 调整参数 → 再跑 |
| 知识传递 | 靠人写文档 | **`skills/` 目录** — 写给 AI 看的"说明书" |
| 适用范围 | 单一环节（如跑仿真） | 原理图 / 版图 / Maestro / Spectre **四域覆盖** |

**核心一句话**：virtuoso-bridge-lite 不是封装 Virtuoso 的 Python SDK，它是**给 LLM 装了一双能直接操作 Cadence 的手**。

---

## 第一章：virtuoso-bridge-lite 三层架构

张托肯这套体系的工程实现非常优雅——极度轻量（99.7% Python），三层高度解耦：

### 1.1 三层核心理念

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AI Agent (Claude / Cursor)                   │
│   reads skills/*.md → 理解 API → 按需求写 Python → 调用 bridge      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           │ TCP JSON-RPC
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 1: VirtuosoClient (纯 TCP 客户端)                             │
│                                                                     │
│  "AI —Ethernet— Virtuoso 内存"                                       │
│                                                                     │
│  execute_skill("geGetSelSet()") → JSON → TCP socket → daemon → SKILL│
│  load_il("script.il")         → 远端加载 SKILL 脚本                   │
│  fetch("geGetSelSet()")       → SKILL s-expression → Python dict     │
│  screenshot() / list_windows() → 图形界面的 AI 控制                  │
│                                                                     │
│  核心原理：Virtuoso daemon 监听 TCP 端口，执行 SKILL 表达式返回结果    │
│  这使得 LLM 可以直接"读取" Virtuoso 数据库中的电路信息                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           │ SSH
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 2: SpectreSimulator (仿真控制器)                               │
│                                                                     │
│  "AI —SSH— Spectre 引擎"                                            │
│                                                                     │
│  run_simulation(netlist)  → 上传网表 → spectre +aps → 下载结果      │
│  submit(netlist)          → 异步提交（返回 Future）                  │
│  run_parallel([...])      → PVT 角并行仿真                          │
│  check_license()          → 验证 license 状态                        │
│  parse_psf_ascii_dir()    → 解析仿真结果（PSF → Python dict）        │
│                                                                     │
│  关键设计：不依赖 Virtuoso GUI！纯 CLI 模式 + SSH 隧道                │
│  格式必须用 -format psfascii（二进制 PSF 不可解析）                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           │ ControlMaster SSH
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 3: SSHClient / SSHRunner (多路复用通道)                       │
│                                                                     │
│  "一条 SSH 通道干三件事"                                             │
│                                                                     │
│  ① 端口转发 → VirtuosoClient 的 TCP 通道（执行 SKILL）              │
│  ② Shell 命令 → SpectreSimulator 的远程调用                         │
│  ③ 文件传输 → scp / tar 管道同步网表和结果                          │
│                                                                     │
│  ControlMaster 保持持久连接，避免反复握手                              │
│  跳板机模式下自动重试端口冲突（+1 递增，最多 10 次）                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 四域覆盖

virtuoso-bridge-lite 打通了模拟 IC 设计的四大场景：

| 域 | 入口 | AI 能做 |
|----|------|--------|
| **Schematic** | `client.execute_skill("sch...")` | 创建/修改原理图、例化器件、连线 |
| **Layout** | `client.execute_skill("le...")` | 绘制版图、摆放器件、布线 |
| **Maestro** | `writer.py` (create_test, set_corner, run_simulation) | 配置仿真、设 Corner、加表达式、启动作业 |
| **Spectre** | `SpectreSimulator.run_simulation()` | 独立跑仿真、解析 PSF 结果 |

### 1.3 `skills/` 目录：写给 AI 的说明书

这是整个仓库最容易被忽略但最关键的设计。`skills/` 不是给人看的文档，是**给 AI 智能体的预加载知识**：

```
virtuoso-bridge-lite/skills/
├── virtuoso-skill/SKILL.md    ← AI 读这个学会调 Virtuoso
├── spectre-skill/SKILL.md     ← AI 读这个学会跑 Spectre
├── maestro-skill/SKILL.md     ← AI 读这个学会操作 Maestro
└── layout-skill/SKILL.md      ← AI 读这个学会画版图
```

当 Cursor 或 Claude Code 加载项目时，AI 自动读取这些 `.md` 文件，**瞬间学会 Cadence API 的调用方法**。不需要人类写"用哪个函数"，AI 自己就知道：

```
用户："帮我跑个 TT 27C 的瞬态仿真"
  ↓
AI 读取 maestro-skill/SKILL.md → 知道用 set_corner() + run_simulation()
  ↓
AI 调用 virtuoso-bridge 的 Python API → SSH → Cadence
  ↓
结果返回给用户
```

---

## 第二章：全栈工具链总览

### 2.1 8 个仓库的定位

| # | 仓库 | 在本工作流中的角色 | 核心功能 |
|---|------|-------------------|----------|
| 1 | **virtuoso-bridge-lite** | AI 控制 Cadence 的"手" | TCP SKILL IPC + SSH Spectre 调度 + Maestro 读写 |
| 2 | **ADCToolbox** | 数据分析引擎 | 频谱分析(SNR/SNDR/ENOB)、INL/DNL、误差分解、校准 |
| 3 | **analog-agents** | 流程编排框架 | 4-Agent设计流程、spec驱动、L1/L2/L3验证等级 |
| 4 | **sar-adc-skills** | SAR ADC 知识库 | SAR架构/CDAC/比较器/逻辑/仿真验证方法 |
| 5 | **veriloga-skills** | Verilog-A 编码规范 | 8条强制规则、12类电路参考、domain-routing |
| 6 | **EVAS** | 行为级仿真 | 事件驱动Verilog-A仿真器，纯Python |
| 7 | **gmoverid-skill** | 晶体管尺寸设计 | gm/ID查表法、GmIdTable API、多节点支持 |
| 8 | **ADC_Visualization** | 可视化面板 | ADC特性仪表盘(index.html) |

### 2.2 针对本项目的工作流总图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        AI Layer (Claude Code)                             │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  tasks: 理解需求 → 调用 bridge → 分析结果 → 迭代优化               │  │
│  │  knowledge: analog-agents 框架 + sar-adc-skills 知识库             │  │
│  └────────────────────────┬───────────────────────────────────────────┘  │
└───────────────────────────┼──────────────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                  │
          ▼                 ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌──────────────────────┐
│ VirtuosoClient  │ │ SpectreSimulator│ │    ADCToolbox        │
│                 │ │                 │ │                      │
│ Maestro 读写    │ │ PVT 并行提交    │ │ analyze_spectrum()   │
│ SKILL 表达式    │ │ PSF 解析        │ │ analyze_inl()        │
│ Snapshot        │ │ License 检查    │ │ fit_sine_4param()    │
└────────┬────────┘ └────────┬────────┘ └──────────┬───────────┘
         │                   │                      │
         │     SSH Tunnel    │                      │
         ▼                   ▼                      │
   ┌──────────────────────────────────────┐         │
   │          VM (CentOS 7)               │         │
   │  ┌──────────────────────────────┐    │         │
   │  │  Cadence IC618 / Spectre 231 │    │         │
   │  │  .cshrc → 环境变量设置正确   │    │         │
   │  │  License: OK, /tmp/: 已清理  │    │         │
   │  └──────────────────────────────┘    │         │
   └──────────────────────────────────────┘         │
                                                    │
                                                    ▼
                                          ┌─────────────────────┐
                                          │  仿真报告 LaTeX      │
                                          │  simulation_report  │
                                          └─────────────────────┘
```

### 2.3 各仓库引用速查

| 模块 | 引用仓库 | 具体文件/函数 |
|------|---------|-------------|
| SSH连接管理 | virtuoso-bridge-lite | `transport/ssh.py` → SSHRunner, `transport/tunnel.py` → SSHClient |
| 远程Spectre | virtuoso-bridge-lite | `spectre/runner.py` → SpectreSimulator.from_env(), run_simulation() |
| PSF数据解析 | virtuoso-bridge-lite | `spectre/parsers.py` → parse_psf_ascii_directory() |
| Maestro读取 | virtuoso-bridge-lite | `virtuoso/maestro/reader/runs.py` → read_results(), export_waveform() |
| Maestro写入 | virtuoso-bridge-lite | `virtuoso/maestro/writer.py` → set_corner(), run_simulation() |
| 频谱分析 | ADCToolbox | `analyze_spectrum()` → enob/sndr/snr/sfdr/thd + 频谱图 |
| INL/DNL | ADCToolbox | `analyze_inl_from_sine()` → inl/dnl in LSB |
| 误差分析 | ADCToolbox | `analyze_error_pdf()`, `analyze_error_spectrum()` |
| 正弦拟合 | ADCToolbox | `fit_sine_4param()` → DC/amplitude/frequency/phase |
| 相干频率 | ADCToolbox | `find_coherent_frequency(Fs, fin_target, N)` |
| 数字校准 | ADCToolbox | `calibrate_weight_sine()` → bit weight提取 |
| 流程编排 | analog-agents | `skills/analog-pipeline/SKILL.md` → pipeline定义 |
| 架构分解 | analog-agents | `skills/analog-decompose/SKILL.md` → budget分配 |
| 行为验证 | analog-agents | `skills/analog-behavioral/SKILL.md` → Va模型验证 |
| 验证审查 | analog-agents | `skills/analog-verify/SKILL.md` → pre-sim审查+margin报告 |
| 集成验证 | analog-agents | `skills/analog-integrate/SKILL.md` → 顶层集成 |
| 仿真参数 | sar-adc-skills | `references/simulation-and-verification.md` → 完整仿真配置 |
| CDAC设计 | sar-adc-skills | `references/cdac.md` → 单位电容/建立时间/线性度验证 |
| 比较器 | sar-adc-skills | `references/comparator.md` → StrongArm拓扑/PSS+Pnoise |
| SAR逻辑 | sar-adc-skills | `references/sar-logic.md` → 异步锁存链/时序约束 |
| Bootstrap | sar-adc-skills | `references/bootstrap_switch.md` → THD测试/Ron扫描 |
| 顶层集成 | sar-adc-skills | `references/integration.md` → 交叉连接检查清单 |
| 参考设计 | sar-adc-skills | `references/sar-adc-11b-zzs.md` → 28nm已流片设计 |
| Va编码规则 | veriloga-skills | `veriloga/SKILL.md` → 8条强制规则 |
| 电路类别 | veriloga-skills | `veriloga/references/categories/` → 12类电路模板 |
| Domain路由 | veriloga-skills | `veriloga/references/domain-routing.md` → 电压域/电流域判定 |
| 行为仿真 | EVAS | `evas/cli.py` → evas simulate | evas run |
| SCS网表 | EVAS | `evas/netlist/spectre_parser.py` → .scs解析格式 |
| 跨导效率 | gmoverid-skill | `gmoverid/assets/design_gmoverid.py` → GmIdTable |
| 工艺表征 | gmoverid-skill | `gmoverid/assets/run_gmoverid.py` → 180nm表征 |

---

## 第三章：环境搭建

### 2.1 virtuoso-bridge-lite 安装与配置

```bash
# 进入项目目录
cd "D:\ReedZhao\Document\Obsidian\日常\10_项目区\2026_12bit10Msar\04_辅助工具\virtuoso-bridge-lite"

# 创建虚拟环境
python -m venv .venv
source .venv/Scripts/activate

# 本地安装（editable模式）
pip install -e .

# 验证安装
python -c "import virtuoso_bridge; print(virtuoso_bridge.__version__)"
```

#### 初始化连接配置

参照 [virtuoso-bridge-lite AGENTS.md](10_项目区/2026_12bit10Msar/04_辅助工具/virtuoso-bridge-lite/AGENTS.md) 中的远程模式设置：

```bash
# 初始化 .env（VM场景）
virtuoso-bridge init meow@192.168.38.128

# 或手动创建 ~/.virtuoso-bridge/.env:
cat > ~/.virtuoso-bridge/.env << 'ENVEOF'
VB_REMOTE_HOST=192.168.38.128
VB_REMOTE_USER=meow
VB_REMOTE_PORT=65081
VB_LOCAL_PORT=65082
VB_CADENCE_CSHRC=/home/meow/.cshrc
ENVEOF
```

> **⚠ VM环境注意**（来自 `env.py` 的 `resolve_env_path()`）：
> - `.env` 查找优先级：`--env` 参数 → 当前目录向上遍历 → `~/.virtuoso-bridge/.env`
> - VM的 `.cshrc` 中 CADHOME 指向 `/opt/eda/cadence`（不存在），正确路径是 `/opt/cadence`
> - 每次运行前需通过 `VB_CADENCE_CSHRC` 覆盖，或直接设置环境变量

#### Profile多配置（可选）

```bash
# 如果需要同时管理多组配置
virtuoso-bridge init meow@192.168.38.128 -p vm1
# 会读取 VB_REMOTE_HOST_vm1, VB_REMOTE_USER_vm1 等
```

### 2.2 ADCToolbox 安装

```bash
# 从PyPI安装
pip install adctoolbox

# 或从本地安装
cd "D:\ReedZhao\Document\Obsidian\日常\10_项目区\2026_12bit10Msar\04_辅助工具\ADCToolbox"
pip install -e .

# 验证
python -c "from adctoolbox import analyze_spectrum; print('OK')"
```

### 2.3 SSH 连接验证

参照 [virtuoso-bridge-lite `transport/ssh.py`](virtuoso-bridge-lite/virtuoso_bridge/transport/ssh.py) 的 SSHRunner 类：

```python
from virtuoso_bridge.transport.ssh import SSHRunner

runner = SSHRunner(
    host="192.168.38.128",
    user="meow",
    timeout=30,
)

# 测试连接
result = runner.run_command("whoami")
print(f"Connected as: {result.stdout}")

# 检查 Cadence 环境
result = runner.run_command("which spectre")
print(f"Spectre: {result.stdout}")

result = runner.run_command("which ocean")
print(f"Ocean: {result.stdout}")
```

### 2.4 VM 环境修复（必须）

参照 [sar-adc-skills `simulation-and-verification.md`](sar-adc-skills/references/simulation-and-verification.md) 的仿真设置，以及历史故障记录：

```bash
# 1. 修复环境变量路径
cat > /home/meow/fix_env.sh << 'EOF'
export CADHOME=/opt/cadence
export CDSHOME=/opt/cadence/IC618
export CDS_LIC_FILE=/opt/cadence/IC618/share/license/license.dat
export PATH=$PATH:/opt/cadence/IC618/tools/bin:/opt/cadence/IC618/tools/dfII/bin:/opt/cadence/SPECTRE231/tools/bin
export CDS_LOG_PATH=/tmp  # 防止锁文件在HOME下创建
EOF

# 2. 清理历史锁文件（预防 Virtuoso 闪退）
rm -f /home/meow/CDS.log* /tmp/psflck* /tmp/cdslck*
```

---

## 第四章：analog-agents 流程框架适配

参照 [analog-agents 4-Agent框架](analog-agents/prompts/) 和 [pipeline定义](10_项目区/2026_12bit10Msar/04_辅助工具/analog-agents/skills/analog-pipeline/SKILL.md)：

### 3.1 本项目 Spec

```yaml
# spec.yml - 12-bit 50MS/s SAR ADC with CAAZ
block: 12bit-50M-SAR-ADC-CAAZ
version: 1.0
process: tsmc18rf
supply: 1.8V

specs:
  enob:          { min: 11.5, unit: bit  }
  sndr:          { min: 69.5, unit: dB   }
  snr:           { min: 70,   unit: dB   }
  sfdr:          { min: 80,   unit: dB   }
  thd:           { max: -75,  unit: dB   }
  power:         { max: 5,    unit: mW   }
  sampling_rate: { min: 50,   unit: MHz  }
  resolution:    { min: 12,   unit: bit  }

corners:
  - { name: tt_27c,  process: tt,  temperature: 27  }
  - { name: ff_m40c, process: ff,  temperature: -40 }
  - { name: ss_150c, process: ss,  temperature: 150 }
  - { name: sf_27c,  process: sf,  temperature: 27  }
  - { name: fs_27c,  process: fs,  temperature: 27  }

checklists:
  - common
  - adc
  - comparator
```

### 3.2 验证等级定义

参照 [analog-agents `shared-references/effort-contract.md`](effort-contract.md)：

| 等级 | 时机 | 内容 | 通过标准 |
|------|------|------|---------|
| **L1 Functional** | 每次迭代 | 1 corner (TT/27C), .tran 验证功能正确 | 产生正确数字码，无非单调性 |
| **L2 Performance** | L1通过 | 5 corners, 提取 SNR/SNDR/ENOB/POWER | 所有 spec 在 TT 达标 |
| **L3 Robustness** | Sign-off | 5 corners + 噪声 + 电压变化 | PVT 全达标 |

> 注意：本项目当前处于 **L3 噪声仿真阶段**——行为级和晶体管级功能已验证，正在跑带噪声 PVT。

### 3.3 Effort Level

参照 analog-agents 的 effort 系统：

```yaml
# config/effort.yml
effort: intensive   # standard | intensive | exhaustive
# standard:  3 corners, 3 轮迭代
# intensive: 5 corners, 5 轮迭代 (当前选择)
# exhaustive: 全 PVT + MC
```

---

## 第五章：仿真执行（virtuoso-bridge + sar-adc-skills）

### 4.1 相干采样参数计算

参照 [sar-adc-skills `simulation-and-verification.md`](sar-adc-skills/references/simulation-and-verification.md) §1.1：

```
fin = M / N * Fs    (M和N互质)

本项目参数：
Fs = 50 MHz
N = 128 (FFT点数)
M = 61 (素数)
fin = 61/128 * 10 MHz = 4.765625 MHz
```

用 ADCToolbox 自动选择：

```python
from adctoolbox import find_coherent_frequency

Fs = 50e6
fin_target = 4.765625e6
N = 128

fin, fin_bin = find_coherent_frequency(Fs, fin_target, N)
print(f"Coherent fin = {fin:.6f} Hz, bin = {fin_bin}")
```

### 4.2 Spectre 仿真配置模板

参照 [sar-adc-skills `simulation-and-verification.md`](sar-adc-skills/references/simulation-and-verification.md) §1.3：

| 参数 | 保守模式 | 快速迭代 | 本项目当前 |
|------|---------|---------|-----------|
| maxstep | 5-10 ps | 50-200 ps | 0.1 ns |
| Spectre模式 | spectre/aps | **mx** | aps |
| N (FFT) | 128-1024 | 16-64 | 128 |
| 额外周期 | 5-20 | 2-5 | 13 |
| strobeperiod | 1/Fs | 1/Fs | 20 ns |

> **推荐使用 `mx` 模式**（来自 sar-adc-skills）：精度几乎不变但速度提升3-5倍。
> 参照 virtuoso-bridge-lite `spectre/runner.py` 中 `SPECTRE_MODE_ARGS`：
> `"mx": ["+preset=mx", "+mt"]`

### 4.3 通过 Maestro Explorer 运行（推荐）

参照 [virtuoso-bridge-lite `virtuoso/maestro/writer.py`](virtuoso-bridge-lite/virtuoso_bridge/virtuoso/maestro/writer.py) 的完整 Maestro 控制 API：

```python
# 1. 打开 Maestro GUI session
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro.lifecycle import open_gui_session

client = VirtuosoClient.from_env(timeout=60)

# 2. 创建5个PVT角点 (参照 virtuoso-bridge-lite writer.py)
from virtuoso_bridge.virtuoso.maestro.writer import (
    setup_corner, set_analysis, add_output, set_spec,
    set_var, set_parameter, run_and_wait, save_setup
)

session = open_gui_session(client, "LIB", "CELL")

# 3. 配置角点
corners = [
    ("tt_27c",  "models.scs", "tt",  { "temp": 27  }),
    ("ff_m40c", "models.scs", "ff",  { "temp": -40 }),
    ("ss_150c", "models.scs", "ss",  { "temp": 150 }),
    ("sf_27c",  "models.scs", "sf",  { "temp": 27  }),
    ("fs_27c",  "models.scs", "fs",  { "temp": 27  }),
]
for name, model_file, section, vars_dict in corners:
    setup_corner(name, model_file, section, vars_dict, session)

# 4. 设置瞬态分析 (参照 sar-adc-skills §1.2)
set_analysis("tran", enable=True, options={
    "start": "0", "stop": "12.5u",
    "maxstep": "0.1n",
    "strobeperiod": "20n",   # 精确每个采样点
    "strobeoutput": "all",
}, session=session)

# 5. 添加输出表达式
add_output("SNR", "tran",
    expr='spectrum(getData("SNDR_DAC") 20n 12.5u 8192 "Rectangular" nil nil "all")',
    session=session)

# 6. 运行
history, status = run_and_wait(session, timeout=3600)
print(f"Simulation: {history}, Status: {status}")

# 7. 保存
save_setup("LIB", "CELL", session)
```

### 4.4 通过 Spectre CLI 独立运行（备选）

参照 [virtuoso-bridge-lite `spectre/runner.py`](virtuoso-bridge-lite/virtuoso_bridge/spectre/runner.py) 的 SpectreSimulator：

#### Python方式（推荐）

```python
from pathlib import Path
from virtuoso_bridge.spectre import SpectreSimulator

# 远程模式自动创建（参照 runner.py from_env()）
sim = SpectreSimulator.from_env(
    spectre_args=["+aps"],
    timeout=3600,
    output_format="psfascii",
)

# 单个仿真
result = sim.run_simulation(
    Path("/path/to/tb_tran.scs"),
    params={
        "include_files": ["models.scs"],
        "spectre_args": ["+aps", "+lqtimeout 900"],
    }
)
print(f"Status: {result.status}")
print(f"Signals: {list(result.data.keys())[:10]}")
```

#### Spectre 命令构建（参照 runner.py `_build_spectre_argv()`）

virtuoso-bridge-lite 自动构建的命令等价于：

```bash
spectre -64 +aps +lqtimeout 900 -maxw 5 -maxn 5 +escchars \
  +log output/spectre.out \
  -format psfascii \
  -raw output/psf \
  tb_tran.scs
```

关键参数说明（参照 runner.py `SPECTRE_MODE_ARGS`）：
- `+aps`：APS加速模式
- `+x`：APS极限模式（更快）
- `+preset=mx` + `+mt`：多线程mx模式（速度最快，精度尚可）
- `-format psfascii`：**必须**，产生可解析ASCII PSF
- `+lqtimeout 900`：license等待超时

#### SSH直连方式

```bash
# 若 virtuoso-bridge 未就绪，直接通过SSH运行
ssh meow@192.168.38.128 '
export CADHOME=/opt/cadence
export CDSHOME=/opt/cadence/IC618
export CDS_LIC_FILE=/opt/cadence/IC618/share/license/license.dat
export PATH=$PATH:/opt/cadence/IC618/tools/bin:/opt/cadence/IC618/tools/dfII/bin:/opt/cadence/SPECTRE231/tools/bin

cd /path/to/simulation

spectre tb_tran.scs \
  +escchars +aps \
  +log output/psf/spectre.out \
  -format psfascii \
  -raw output/psf
'
```

### 4.5 网表模板与参数切换

参照 [sar-adc-skills `simulation-and-verification.md`](sar-adc-skills/references/simulation-and-verification.md) §1.2 输入信号设置：

```spectre
// tb_tran.scs
simulator lang=spectre
global 0

// === 参数定义 ===
parameters td=26.5n temperature=27 va=0.89
parameters noisefmax=10G noiseseed=64261112 noisescale=10

// === 模型文件 ===
section tt
  include "models.scs" section=tt
  include "res_models.scs" section=tt_res
  include "mim_models.scs" section=tt_mim
endsection

// === 电源 ===
Vvdd (vdd 0) vsource dc=1.8
Vvcm (vcm 0) vsource dc=0.9
Vvref (vref 0) vsource dc=0.9

// === 输入信号（差分）===
// 相干采样：fin = 61/128 * 10MHz = 4.765625MHz
Vvinp (vinp 0) vsource type=sine ampl=va sinedc=0.9 freq=4.765625e6
Vvinn (vinn 0) vsource type=sine ampl=va sinedc=0.9 freq=4.765625e6 phase=180

// === DUT ===
IDUT (vinp vinn vdd vcm clk vref ...) SAR_ADC_12b

// === 分析 ===
tran tran stop=12.5u maxstep=0.1n \
  strobeperiod=20n strobeoutput=all

// === 瞬态噪声 ===
// 带噪声仿真时启用：
// noisefmax=10G noiseseed=64261112 noisescale=10
// noiseon=[I1 I14]

// === 存储信号 ===
save vinp:3f vinn:3f vdd:2e clk:2e
```

**不同Corner的参数组合**（参照 sar-adc-skills `simulation-and-verification.md` PVT设置）：

| Corner | temp | 工艺section |
|--------|------|-------------|
| TT | 27 | tt + tt_res + tt_mim |
| FF | -40 | ff + ff_res + ff_mim |
| SS | 150 | ss + ss_res + ss_mim |
| SF | 27 | sf + sf_res + sf_mim |
| FS | 27 | fs + fs_res + fs_mim |

**通过 virtuoso-bridge-lite `run_parallel()` 并行提交5个角点**（参照 `spectre/runner.py`）：

```python
from virtuoso_bridge.spectre import SpectreSimulator

sim = SpectreSimulator.from_env(spectre_args=["+aps"], output_format="psfascii")

netlists = [
    ("tb_tt.scs", {"include_files": ["models_tt.scs"]}),
    ("tb_ff.scs", {"include_files": ["models_ff.scs"]}),
    ("tb_ss.scs", {"include_files": ["models_ss.scs"]}),
    ("tb_sf.scs", {"include_files": ["models_sf.scs"]}),
    ("tb_fs.scs", {"include_files": ["models_fs.scs"]}),
]

results = sim.run_parallel(
    [(Path(n), p) for n, p in netlists],
    max_workers=2  # VM 资源有限
)

for r in results:
    print(f"{r.status}: {r.metadata.get('returncode')} errors={len(r.errors)}")
```

### 4.6 仿真验证调试（sar-adc-skills 调试清单）

参照 [sar-adc-skills `simulation-and-verification.md` §1.6](sar-adc-skills/references/simulation-and-verification.md)：

| 症状 | 可能原因 | 修复 |
|------|---------|------|
| 只有2个码值 | 比较器极性错误 | 检查StrongArm输出，添加SR锁存 |
| 码值位序反转 | 总线`[N:0]`端口顺序 | 反转子电路例化引脚顺序 |
| ENOB接近理想但SFDR差 | 重采样时间未对齐 | 使用strobe输出或对齐时钟相位 |
| 码值范围 < 满量程 | 输入超参考/采样开关Vth压降 | 降低幅度或使用bootstrap |
| 码值均值大偏移 | CDAC初始状态不匹配 | 使用差分CDAC，匹配底板初始状态 |

---

## 第六章：数据提取（virtuoso-bridge + Ocean SKILL）

### 5.1 Ocean SKILL 频谱分析

参照 [sar-adc-skills `simulation-and-verification.md`](sar-adc-skills/references/simulation-and-verification.md) 的 ADC 性能提取方法。

**`spectrum()` 函数**（Cadence 原生函数，IC6.1.5+）：

```skill
; Ocean SKILL 脚本
;
; 用法：ocean -restore extract_metrics.ocn

; === 1. 打开结果 ===
openResults("/path/to/psf")
selectResult("tran-tran")

; === 2. 读信号 ===
sndr_dac = getData("SNDR_DAC")

; === 3. 频谱分析 ===
; spectrum(waveform tStart tStop nSamples window fStart fEnd measType)
spec = spectrum(sndr_dac 20n 12.5u 8192 "Rectangular" nil nil "all")

sinad_db = value(spec "sinad")
enob_bits = value(spec "enob")
snr_db = value(spec "snr")
sfdr_db = value(spec "sfdr")
thd_db  = value(spec "thd")

printf("=== ADC Performance ===\n")
printf("SINAD = %.2f dB\n" sinad_db)
printf("ENOB  = %.2f bits\n" enob_bits)
printf("SNR   = %.2f dB\n" snr_db)
printf("SFDR  = %.2f dBc\n" sfdr_db)
printf("THD   = %.2f dBc\n" thd_db)
printf("======================\n")

; === 4. 导出波形到文本（供ADCToolbox分析）===
ocnPrint(sndr_dac ?output "/tmp/sndr_dac.txt"
        ?numberNotion 'scientific ?from 20n ?to 12.5u ?step 20n)
```

**通过 virtuoso-bridge-lite 执行 Ocean**（参照 `virtuoso/maestro/reader/runs.py` 的 `export_waveform()`）：

```python
from virtuoso_bridge import VirtuosoClient

client = VirtuosoClient.from_env(timeout=120)

# 方式1: 直接用 SKILL 执行 ocean 命令
skill_code = '''
openResults("/path/to/psf")
selectResult("tran-tran")
sndr_dac = getData("SNDR_DAC")
spec = spectrum(sndr_dac 20n 12.5u 8192 "Rectangular" nil nil "all")
printf("ENOB = %.2f\\n" value(spec "enob"))
printf("SNDR = %.2f\\n" value(spec "sinad"))
'''
result = client.execute_skill(skill_code, timeout=120)
print(result.output)

# 方式2: 用 export_waveform() 导出到本地
from virtuoso_bridge.virtuoso.maestro.reader.runs import export_waveform

local_path = export_waveform(
    client,
    session="ExplorerRun.0",
    expression='getData("SNDR_DAC")',
    local_path="./waveforms/sndr_dac_p1.txt",
    analysis="tran",
)
print(f"Waveform exported to: {local_path}")
```

### 5.2 Maestro 表达式结果读取

参照 [virtuoso-bridge-lite `virtuoso/maestro/reader/runs.py`](virtuoso-bridge-lite/virtuoso_bridge/virtuoso/maestro/reader/runs.py) 的 `read_results()`：

```python
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro.reader.runs import read_results

client = VirtuosoClient.from_env()

# 读取 ExploreRun 所有结果
results = read_results(
    client,
    session="ExplorerRun.0",
    history="",  # 自动选最新
)

# 遍历每个仿真点
for pt in results["points"]:
    params = pt["parameters"]
    outputs = pt["outputs"]
    print(f"\nPoint {pt['point']}:")
    for k, v in params.items():
        print(f"  {k} = {v}")
    for name, info in outputs.items():
        print(f"  {name} = {info['value']} (spec: {info.get('spec', 'N/A')})")
```

### 5.3 PSF ASCII 解析（离线方式）

参照 [virtuoso-bridge-lite `spectre/parsers.py`](virtuoso-bridge-lite/virtuoso_bridge/spectre/parsers.py)：

```python
from virtuoso_bridge.spectre.parsers import parse_psf_ascii_directory

# 解析 PSF ASCII 目录
data = parse_psf_ascii_directory("/path/to/psf")
# 返回: {signal_name: [values]}

# transient 信号在 "tran-tran" 键下
if "tran-tran" in data:
    signals = data["tran-tran"]
    for name, values in signals.items():
        print(f"{name}: {len(values)} samples")
```

> **注意**：PSF ASCII 解析器支持 delta-compressed 格式，但**二进制 .psfxl 不支持**。
> 必须用 `-format psfascii` 运行 spectre 才能产生可解析输出。

### 5.4 Maestro Snapshot

参照 [virtuoso-bridge-lite `virtuoso/maestro/reader/snapshot.py`](virtuoso-bridge-lite/virtuoso_bridge/virtuoso/maestro/reader/snapshot.py)：

```bash
# Brief模式：快速探测（~150ms）
virtuoso-bridge snapshot

# 全量模式：拉取所有数据
virtuoso-bridge snapshot -o ./snapshots
# 会拉取: maestro.sdb, active.state, netlist/, psf/ 文件
```

Python调用：

```python
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.maestro.reader.snapshot import snapshot

client = VirtuosoClient.from_env()

# brief
info = snapshot(client, output_root=None)
print(f"Session: {info['session']}")
print(f"Mode: {info['mode']}")

# full
info = snapshot(client, output_root="./snapshots/run1")
print(f"Output: {info['output_dir']}")
print(f"Latest history: {info['latest_history']}")
```

---

## 第七章：ADCToolbox 数据分析

### 6.1 频谱分析核心

参照 [ADCToolbox `analyze_spectrum`](ADCToolbox/src/adctoolbox/analyze_spectrum.py) 和 [sar-adc-skills `simulation-and-verification.md` §1.5](sar-adc-skills/references/simulation-and-verification.md)：

```python
from adctoolbox import analyze_spectrum
import numpy as np

# 从Ocean导出的文本读数据
data = np.loadtxt("./waveforms/sndr_dac_p1.txt")
signal = data[:, 1]  # 幅值序列

# ADC 参数
fs = 50e6

# 分析频谱
result = analyze_spectrum(
    signal,
    fs=fs,
    max_harmonic=7,      # 7次谐波
    create_plot=True,    # 生成频谱图
)

print("=== ADC Performance (ADCToolbox) ===")
print(f"SNDR: {result['sndr_dbc']:.2f} dBc")
print(f"SNR:  {result['snr_dbc']:.2f} dBc")
print(f"SFDR: {result['sfdr_dbc']:.2f} dBc")
print(f"THD:  {result['thd_dbc']:.2f} dBc")
print(f"ENOB: {result['enob']:.2f} bits")
print(f"NSD:  {result['nsd']:.2f} dBFS/Hz")
```

### 6.2 多角点批量分析

```python
from adctoolbox import analyze_spectrum
import numpy as np
import json

# 8个仿真点
points = {
    "P1_TT_26.5n_noise":   {"file": "sndr_dac_p1.txt", "td": 26.5, "noise": True},
    "P2_FF_26.5n_noise":   {"file": "sndr_dac_p2.txt", "td": 26.5, "noise": True},
    "P3_SS_26.5n_noise":   {"file": "sndr_dac_p3.txt", "td": 26.5, "noise": True},
    "P4_SF_26.5n_noise":   {"file": "sndr_dac_p4.txt", "td": 26.5, "noise": True},
    "P5_FS_26.5n_noise":   {"file": "sndr_dac_p5.txt", "td": 26.5, "noise": True},
    "S1_TT_26.5n_nonoise": {"file": "sndr_dac_s1.txt", "td": 26.5, "noise": False},
    "S2_TT_24.05n_noise":  {"file": "sndr_dac_s2.txt", "td": 24.05, "noise": True},
    "S3_TT_24.05n_nonoise":{"file": "sndr_dac_s3.txt", "td": 24.05, "noise": False},
}

results = {}
for name, cfg in points.items():
    data = np.loadtxt(f"./waveforms/{cfg['file']}")
    signal = data[:, 1]
    result = analyze_spectrum(signal, fs=50e6, max_harmonic=7, create_plot=False)
    results[name] = {
        "enob":  float(result["enob"]),
        "sndr":  float(result["sndr_dbc"]),
        "snr":   float(result["snr_dbc"]),
        "sfdr":  float(result["sfdr_dbc"]),
        "thd":   float(result["thd_dbc"]),
        "td_ns": cfg["td"],
        "noise": cfg["noise"],
    }
    print(f"{name:25s}  ENOB={results[name]['enob']:.2f}  "
          f"SNDR={results[name]['sndr']:.2f}  SNR={results[name]['snr']:.2f}")

# 导出JSON供LaTeX生成
with open("simulation_results.json", "w") as f:
    json.dump(results, f, indent=2)
```

### 6.3 噪声对比分析

```python
# 噪声功率削减计算
snr_noise = results["P1_TT_26.5n_noise"]["snr"]
snr_ideal = results["S1_TT_26.5n_nonoise"]["snr"]
noise_ratio = 10 ** (-(snr_noise - snr_ideal) / 10)
print(f"Noise Power Ratio: {noise_ratio:.2f}x")
print(f"Noise Reduction Factor: {1/noise_ratio:.2f}x")

# td对比
snr_td265 = results["P1_TT_26.5n_noise"]["snr"]
snr_td2405 = results["S2_TT_24.05n_noise"]["snr"]
delta_snr = snr_td2405 - snr_td265
print(f"ΔSNR (td=24.05 - 26.5): {delta_snr:.2f} dB")
```

### 6.4 INL/DNL 提取

参照 [ADCToolbox `analyze_inl_from_sine`](ADCToolbox/src/adctoolbox/analyze_inl_from_sine.py)：

```python
from adctoolbox import analyze_inl_from_sine

# 需要数字码（非模拟重构信号）
# bits: shape (N_samples, N_bits)
codes = np.loadtxt("./waveforms/digital_codes.txt", dtype=int)

inl_result = analyze_inl_from_sine(codes, num_bits=12, create_plot=True)

print(f"INL: [{inl_result['inl'].min():.3f}, {inl_result['inl'].max():.3f}] LSB")
print(f"DNL: [{inl_result['dnl'].min():.3f}, {inl_result['dnl'].max():.3f}] LSB")
```

### 6.5 误差分析

参照 [ADCToolbox 误差分析模块](ADCToolbox/src/adctoolbox/analyze_error_*.py)：

```python
from adctoolbox import (
    analyze_error_pdf,
    analyze_error_spectrum,
    analyze_error_autocorr,
    analyze_error_envelope_spectrum,
)

# 误差PDF
pdf_result = analyze_error_pdf(signal, resolution=12, create_plot=True)
print(f"Error std: {pdf_result['sigma']:.3f} LSB")
print(f"KL divergence: {pdf_result['kl_divergence']:.4f}")

# 误差频谱
spec_result = analyze_error_spectrum(signal, fs=50e6, create_plot=True)

# 误差自相关
acf_result = analyze_error_autocorr(signal, max_lag=100, create_plot=True)

# 误差包络谱（AM检测）
env_result = analyze_error_envelope_spectrum(signal, fs=50e6, create_plot=True)
```

### 6.6 正弦拟合

参照 [ADCToolbox `fit_sine_4param`](ADCToolbox/src/adctoolbox/fit_sine_4param.py)：

```python
from adctoolbox import fit_sine_4param, analyze_decomposition_time

# 4参数正弦拟合
fit = fit_sine_4param(signal, frequency_estimate=4.765625e6/50e6)
print(f"DC: {fit['dc_offset']:.4f}")
print(f"Amplitude: {fit['amplitude']:.4f}")
print(f"Frequency: {fit['frequency']:.6f}")

# 谐波分解
decomp = analyze_decomposition_time(signal, harmonic=7, create_plot=True)
```

### 6.7 数字校准（参考）

参照 [ADCToolbox `calibrate_weight_sine`](ADCToolbox/src/adctoolbox/calibrate_weight_sine.py)：

```python
from adctoolbox import calibrate_weight_sine, analyze_spectrum

# bits: (N_samples, N_bits) of {0, 1}, fin归一化频率
cal = calibrate_weight_sine(bits, freq=fin/Fs, harmonic_order=5)

print("Calibrated weights:", cal["weight"])
print("Offset:", cal["offset"])

# 校准后信号分析
metrics = analyze_spectrum(cal["calibrated_signal"], fs=Fs, create_plot=False)
print(f"Post-cal ENOB: {metrics['enob']:.2f}")
```

---

## 第八章：Verilog-A 行为建模（veriloga-skills + EVAS）

### 7.1 Verilog-A 编码规则（veriloga-skills 8条强制规则）

参照 [veriloga-skills SKILL.md §Mandatory Rules](10_项目区/2026_12bit10Msar/04_辅助工具/veriloga-skills/veriloga/SKILL.md)：

| # | 规则 | 说明 |
|---|------|------|
| 1 | **所有信号用 `electrical`** | 禁止 `wire`/`logic`/`reg` |
| 2 | **电源端口声明为 `inout`** | 不是 `input`，否则破坏功耗感知仿真 |
| 3 | **电源电压从端口读取或参数化** | `vh = V(VDD)`，禁止硬编码 `1.8` |
| 4 | **所有声明在 `analog begin` 之前** | `parameter`/`real`/`integer` 不能在模块内部声明 |
| 5 | **严格区分 `integer` 与 `genvar`** | `integer`=运行时循环，`genvar`=展开贡献循环 |
| 6 | **在 `@(initial_step)` 初始化状态** | 未初始化=垃圾值 |
| 7 | **边沿检测用带方向的 `@(cross())`** | `+1`=上升，`-1`=下降 |
| 8 | **输出用 `transition()`，优先目标变量** | 多次 `V(out) <+` 会累加，应只赋值一次 |

### 7.2 SAR ADC 行为模型（电压域）

参照 [veriloga-skills `references/categories/adc-sar.md`](adc-sar.md) 和 [EVAS `examples/sar_adc_dac_weighted_8b/`](EVAS/evas/examples/sar_adc_dac_weighted_8b/)：

```verilog
// sar_adc_12b.va — 12-bit SAR ADC 行为模型
`include "constants.vams"
`include "disciplines.vams"
`default_transition 10p

module sar_adc_12b(
    inout electrical VDD,    // 1.8V
    inout electrical VSS,    // 0V
    inout electrical VREF,   // 参考电压
    input electrical VINP,
    input electrical VINN,
    input electrical CLK,
    output electrical [11:0] DOUT  // 数字输出
);

    // 参数
    parameter real vref = 1.8;
    parameter integer nbits = 12;

    // 变量 — 全部在 analog begin 之前声明
    real vh, vl, vth;
    real sample_val;
    real dac_out;
    integer bit_idx;
    integer decision;
    integer dout_arr[0:11];  // 0=LSB, 11=MSB
    integer i;
    genvar g;

    analog begin
        // 读取电源
        @(initial_step) begin
            vh = V(VDD);
            vl = V(VSS);
            vth = (vh + vl) / 2.0;
        end

        // 采样：CLK 上升沿
        @(cross(V(CLK) - vth, +1)) begin
            sample_val = V(VINP) - V(VINN);  // 差分采样
            dac_out = 0.0;
            bit_idx = nbits - 1;
        end

        // SAR 逐次逼近：CLK 下降沿
        @(cross(V(CLK) - vth, -1)) begin
            if (bit_idx >= 0) begin
                // 比较器判决
                decision = (sample_val - dac_out) > 0.0 ? 1 : 0;
                dout_arr[bit_idx] = decision;

                // DAC更新
                if (decision)
                    dac_out = dac_out + (vref / (1 << (nbits - bit_idx)));

                bit_idx = bit_idx - 1;
            end
        end

        // 驱动数字输出（使用 genvar 展开）
        for (g = 0; g < nbits; g = g + 1)
            V(DOUT[g]) <+ transition(dout_arr[g] * vh, 0);
    end
endmodule
```

### 7.3 StrongArm 比较器行为模型

参照 [veriloga-skills `references/categories/comparator.md`](10_项目区/2026_12bit10Msar/04_辅助工具/veriloga-skills/veriloga/references/categories/comparator.md)：

```verilog
// cmp_strongarm.va — StrongARM 比较器行为模型
`include "constants.vams"
`include "disciplines.vams"
`default_transition 10p

module cmp_strongarm(
    inout electrical VDD, inout electrical VSS,
    input electrical CLK,
    input electrical VINP, input electrical VINN,
    output electrical DOUTP, output electrical DOUTN
);
    parameter real trise = 20p;
    parameter real tfall = 20p;
    parameter real td_cmp = 50p;
    parameter real vos = 0.0;  // 输入失调

    real vh, vl, vth;
    integer xoutp, xoutn;

    analog begin
        @(initial_step) begin
            vh = V(VDD); vl = V(VSS);
            vth = (vh + vl) / 2.0;
            xoutp = 0; xoutn = 0;
        end

        // 感测上升沿
        @(cross(V(CLK) - vth, +1)) begin
            if ((V(VINP) - V(VINN) + vos) > 0.0) begin
                xoutp = 1; xoutn = 0;
            end else begin
                xoutp = 0; xoutn = 1;
            end
        end

        // 下降沿复位
        @(cross(V(CLK) - vth, -1)) begin
            xoutp = 0; xoutn = 0;
        end

        V(DOUTP) <+ transition(xoutp ? vh : vl, td_cmp, trise, tfall);
        V(DOUTN) <+ transition(xoutn ? vh : vl, td_cmp, trise, tfall);
    end
endmodule
```

### 7.4 用 EVAS 验证行为模型

参照 [EVAS CLI](10_项目区/2026_12bit10Msar/04_辅助工具/EVAS/evas/cli.py) 和 [EVAS SCS格式](spectre_parser.py)：

```bash
# 运行内置示例
evas run sar_adc_dac_weighted_8b
evas run dac_binary_clk_4b
evas run comparator/cmp_strongarm

# 仿真自定义行为模型
evas simulate tb_sar_12b.scs -o output/sar_12b -log sim.log
```

**SCS 测试台示例**（参照 EVAS 格式要求）：

```spectre
// tb_sar_12b.scs
simulator lang=spectre
global 0

ahdl_include "sar_adc_12b.va"
ahdl_include "dac_ideal_12b.va"

parameters fs=50M vdd=1.8
parameters fin=4.765625e6 va=0.85

Vvdd (vdd 0) vsource dc=vdd
Vclk (clk 0) vsource type=pulse val0=0 val1=vdd period=20n rise=100p fall=100p width=9.8n
Vvinp (vinp 0) vsource type=sine ampl=va sinedc=0.9 freq=fin
Vvinn (vinn 0) vsource type=sine ampl=va sinedc=0.9 freq=fin phase=180

ISAR (vinp vinn clk vdd vss dout_11 dout_10 dout_9 dout_8
       dout_7 dout_6 dout_5 dout_4 dout_3 dout_2 dout_1 dout_0) sar_adc_12b

tran tran stop=1u maxstep=1n
save clk:2e dout_11:d dout_10:d dout_9:d dout_8:d
     dout_7:d dout_6:d dout_5:d dout_4:d dout_3:d dout_2:d dout_1:d dout_0:d
```

### 7.5 Domain Routing 判定

参照 [veriloga-skills `references/domain-routing.md`](domain-routing.md)：

```
判断流程：
1. 包含 current-domain 结构？(I() <+, ddt, idt, laplace_nd, ...)
   ├─ YES → 也包含 voltage-only 结构？(@(cross), transition, genvar)
   │       ├─ YES → MIXED: 拆分为两个子模块
   │       └─ NO  → CURRENT-DOMAIN: OpenVAF + ngspice
   └─ NO  → VOLTAGE-DOMAIN: EVAS (本项目适用)
```

本项目典型模块：
- SAR逻辑 → **电压域** → EVAS 可验证
- 比较器 → **电压域** → EVAS 可验证
- CDAC → **电压域** → EVAS 可验证
- 自举开关 → **电压域** → EVAS 可验证

---

## 第九章：gm/ID 晶体管级设计（gmoverid-skill）

### 8.1 gm/ID 方法论核心

参照 [gmoverid-skill `SKILL.md`](10_项目区/2026_12bit10Msar/04_辅助工具/gmoverid-skill/gmoverid/SKILL.md)：

gm/ID 将晶体管所有工作区统一表达为 gm/ID 的函数：

```
gm/ID  ──►  Id/W   (电流密度 → 确定W)
       ──►  fT     (特征频率 → 速度)
       ──►  gm·ro  (本征增益)
       ──►  Vgs    (偏置点)
```

> 四条曲线**与W无关**——同一 gm/ID 点，不同W的器件共享完全相同的 Id/W、fT、gm·ro。

### 8.2 TSMC 18RF 表征

```bash
cd gmoverid-skill/gmoverid/assets

# 运行180nm单节点表征（生成设计图表）
python run_gmoverid.py

# 生成: nmos180_main.png, pmos180_main.png,
#        nmos180_caps.png, pmos180_caps.png,
#        nmos180_iv.png, pmos180_iv.png
```

### 8.3 查表设计示例

参照 [gmoverid-skill `design_gmoverid.py`](design_gmoverid.py)：

```python
from design_gmoverid import GmIdTable

# 创建NMOS查表对象
tbl = GmIdTable('nmos180', W=10.0, L=0.18, vds=0.9)

# 查表设计
# 场景1: 给定gm/ID=15, 求W
gmid_target = 15.0
ft = tbl.lookup('ft', gmid_target)
gmro = tbl.lookup('gmro', gmid_target)
id_w = tbl.lookup('id_w', gmid_target) * 1e6  # µA/µm
vgs = tbl.lookup('vgs', gmid_target)

print(f"gm/ID = {gmid_target}:")
print(f"  fT    = {ft*1e-9:.1f} GHz")
print(f"  gm·ro = {gmro:.1f}")
print(f"  Id/W  = {id_w:.1f} µA/µm")
print(f"  Vgs   = {vgs:.3f} V")

# 场景2: 已知Id=50µA, gm/ID=15 → 求W
result = tbl.size(gmid=gmid_target, Id=50e-6)
print(f"W = {result['W']*1e6:.2f} µm")
print(f"Id = {result['Id']*1e6:.2f} µA")
print(f"gm = {result['gm']*1e3:.3f} mS")

# 场景3: 已知W=20µm, 求Id
result = tbl.size(gmid=gmid_target, W=20.0)
print(f"Id = {result['Id']*1e6:.2f} µA")
```

### 8.4 gm/ID 快速参考（nmos180, Vds=0.9V, L=180nm）

参照 [gmoverid-skill `SKILL.md`](10_项目区/2026_12bit10Msar/04_辅助工具/gmoverid-skill/gmoverid/SKILL.md)：

| gm/ID [V⁻¹] | Id/W [µA/µm] | fT [GHz] | gm·ro | 典型用途 |
|:-----------:|:-------------:|:--------:|:-----:|----------|
| 5-8 | 42-81 | 20-25 | 27-36 | 高速电路、采样开关 |
| 10-12 | 20-29 | 15-18 | 39 | OTA输出级、驱动器 |
| 13-16 | 8-17 | 9-13 | 39-46 | OTA输入差分对（平衡） |
| 18-20 | 3-6 | 4-6 | 53 | 低功耗模拟 |

---

## 第十章：报告自动生成

### 9.1 完整Python报告生成

```python
#!/usr/bin/env python3
"""generate_report.py — 自动生成 LaTeX 仿真报告"""

import json
import subprocess
from pathlib import Path
from adctoolbox import analyze_spectrum
import numpy as np

# 1. 读取所有仿真数据
results = {}
point_names = {
    "P1": ("TT",  26.5, True),
    "P2": ("FF",  26.5, True),
    "P3": ("SS",  26.5, True),
    "P4": ("SF",  26.5, True),
    "P5": ("FS",  26.5, True),
    "S1": ("TT (no noise)", 26.5, False),
    "S2": ("TT", 24.05, True),
    "S3": ("TT (no noise)", 24.05, False),
}

for pt, (corner, td, noise) in point_names.items():
    data = np.loadtxt(f"./waveforms/sndr_dac_{pt.lower().replace(' ','_')}.txt")
    signal = data[:, 1]
    result = analyze_spectrum(signal, fs=50e6, max_harmonic=7, create_plot=False)
    results[pt] = {
        "corner": corner, "td": td, "noise": noise,
        "snr": result["snr_dbc"], "sndr": result["sndr_dbc"],
        "enob": result["enob"], "sfdr": result["sfdr_dbc"],
        "thd": result["thd_dbc"],
    }

# 2. 生成LaTeX片段
def pvt_table(results):
    """生成PVT结果表格"""
    lines = ["\\begin{table}[!t]", "\\centering",
             "\\caption{各工艺角 SNR/ENOB（$t_d=\\SI{26.5}{ns}$, 100$\\times$ 噪声）}",
             "\\label{tab:snr_enob}", "\\renewcommand{\\arraystretch}{1.2}",
             "\\begin{tabular}{lSSS}", "\\toprule",
             "\\textbf{Corner} & \\textbf{SNR (dB)} & \\textbf{SNDR (dB)} & \\textbf{ENOB (bit)} \\\\"]
    for pt in ["P1","P2","P3","P4","P5"]:
        r = results[pt]
        c = r["corner"]
        lines.append(f"{c} & {r['snr']:.2f} & {r['sndr']:.2f} & {r['enob']:.2f} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    return "\n".join(lines)

def noise_table(results):
    """生成噪声对比表格"""
    p1, s1 = results["P1"], results["S1"]
    lines = ["\\begin{table}[!t]", "\\centering",
             "\\caption{无噪声 vs 带噪声（TT, $t_d=\\SI{26.5}{ns}$）}",
             "\\label{tab:noise_comparison}", "\\renewcommand{\\arraystretch}{1.2}",
             "\\begin{tabular}{lSS}", "\\toprule",
             "\\textbf{Metric} & \\textbf{With Noise} & \\textbf{Without Noise} \\\\", "\\midrule",
             f"SNR (dB) & {p1['snr']:.2f} & {s1['snr']:.2f} \\\\",
             f"SNDR (dB) & {p1['sndr']:.2f} & {s1['sndr']:.2f} \\\\",
             f"ENOB (bit) & {p1['enob']:.2f} & {s1['enob']:.2f} \\\\",
             "\\bottomrule", "\\end{tabular}", "\\end{table}"]
    return "\n".join(lines)

def td_table(results):
    """生成采样时间对比表格"""
    p1, s2 = results["P1"], results["S2"]
    delta_snr = s2["snr"] - p1["snr"]
    noise_ratio = 10 ** (-delta_snr / 10)
    lines = ["\\begin{table}[!t]", "\\centering",
             "\\caption{$t_d$ 对比分析（TT, 100$\\times$ 噪声）}",
             "\\label{tab:td_comparison}", "\\renewcommand{\\arraystretch}{1.2}",
             "\\begin{tabular}{lSS}", "\\toprule",
             "\\textbf{Metric} & $t_d=\\SI{26.5}{ns}$ & $t_d=\\SI{24.05}{ns}$ \\\\", "\\midrule",
             f"SNR (dB) & {p1['snr']:.2f} & {s2['snr']:.2f} \\\\",
             f"SNDR (dB) & {p1['sndr']:.2f} & {s2['sndr']:.2f} \\\\",
             f"ENOB (bit) & {p1['enob']:.2f} & {s2['enob']:.2f} \\\\",
             "\\bottomrule", "\\end{tabular}",
             "\\vspace{1em}",
             f"$\\Delta \\text{{SNR}} = {delta_snr:+.2f}\\text{{ dB}}$",
             f"\\text{{Noise Power Ratio}} = 10^{{-\\Delta \\text{{SNR}}/10}} = {noise_ratio:.3f}",
             "\\end{table}"]
    return "\n".join(lines)

# 3. 写入文件
report_dir = Path("03_实验记录")
report_dir.mkdir(exist_ok=True)

with open(report_dir / "generated_tables.tex", "w") as f:
    f.write("% 自动生成 — 请勿手动修改\n")
    f.write(pvt_table(results) + "\n\n")
    f.write(noise_table(results) + "\n\n")
    f.write(td_table(results) + "\n")

print("Tables written to 03_实验记录/generated_tables.tex")
```

### 9.2 编译 PDF

```bash
cd "03_实验记录"
xelatex simulation_report.tex
xelatex simulation_report.tex  # 两次编译更新交叉引用
```

### 9.3 报告模板集成

在 `simulation_report.tex` 中引用自动生成的表格：

```latex
% 在需要表格的位置替换手动内容的占位符
\input{generated_tables.tex}
```

或者直接在 Python 脚本中通过替换模板占位符完成：

```python
# 用 Python 替换模板中的占位符
with open("simulation_report.tex", "r") as f:
    tex = f.read()

tex = tex.replace("%%PVT_TABLE%%", pvt_table(results))
tex = tex.replace("%%NOISE_TABLE%%", noise_table(results))
tex = tex.replace("%%TD_TABLE%%", td_table(results))

with open("simulation_report.tex", "w") as f:
    f.write(tex)
```

---

## 第十一章：当前项目状态（2026-05-12）

### 10.1 仿真完成进度

| 编号 | 类型 | Corner | td | 噪声 | 数据量 | 状态 |
|------|------|--------|-----|------|--------|------|
| P1 | PVT | TT / 27C | 26.5ns | 100x | 425 MB | ✅ **完成** |
| P2 | PVT | FF / -40C | 26.5ns | 100x | 中断 | ❌ ~11.8% |
| P3 | PVT | SS / 150C | 26.5ns | 100x | — | ❌ 未启动 |
| P4 | PVT | SF / 27C | 26.5ns | 100x | — | ❌ 未启动 |
| P5 | PVT | FS / 27C | 26.5ns | 100x | — | ❌ 未启动 |
| S1 | 对照 | TT | 26.5ns | 无噪声 | — | ❌ 未启动 |
| S2 | 对照 | TT | 24.05ns | 100x | — | ❌ 未启动 |
| S3 | 对照 | TT | 24.05ns | 无噪声 | — | ❌ 未启动 |

### 10.2 工具安装状态

| 工具 | 路径 | 安装 | 状态 |
|------|------|------|------|
| virtuoso-bridge-lite | `04_辅助工具/virtuoso-bridge-lite` | `pip install -e .` 待执行 | ❌ |
| ADCToolbox | `04_辅助工具/ADCToolbox` | `pip install adctoolbox` 待执行 | ❌ |
| EVAS | `04_辅助工具/EVAS` | 已克隆 | ✅ |
| analog-agents | `04_辅助工具/analog-agents` | 已克隆 | ✅ |
| sar-adc-skills | `04_辅助工具/sar-adc-skills` | 已克隆 | ✅ |
| veriloga-skills | `04_辅助工具/veriloga-skills` | 已克隆 | ✅ |
| gmoverid-skill | `04_辅助工具/gmoverid-skill` | 已克隆 | ✅ |
| ADC_Visualization | `04_辅助工具/ADC_Visualization` | 已克隆 | ✅ |

### 10.3 优先执行计划

```
Phase 1 — 环境就绪（30 min）
  ├── 安装 virtuoso-bridge-lite + ADCToolbox
  ├── 验证 SSH 连接 + Cadence 环境
  └── 清理 VM 锁文件 + 设置 CDS_LOG_PATH

Phase 2 — 仿真执行（预计 8-12 小时）
  ├── P1: 已完成 ✅
  ├── P2-P5: 修复 FF 中断问题后，用 run_parallel() 提交 5 角
  ├── S1: TT 无噪声 (td=26.5ns)
  ├── S2: TT 带噪声 (td=24.05ns)
  └── S3: TT 无噪声 (td=24.05ns)

Phase 3 — 数据提取（2 小时）
  ├── Ocean spectrum() 提取 SNR/SNDR/ENOB (8 组)
  ├── ADCToolbox analyze_spectrum() 验证
  └── ADCToolbox INL/DNL 分析

Phase 4 — 报告生成（1 小时）
  ├── 运行 generate_report.py
  ├── 填充 simulation_report.tex 占位符
  └── xelatex 编译 PDF
```

---

## 附录 A：virtuoso-bridge-lite CLI 速查

参照 [virtuoso-bridge-lite `cli.py`](virtuoso-bridge-lite/virtuoso_bridge/cli.py)：

| 命令 | 功能 |
|------|------|
| `virtuoso-bridge init [user@host]` | 创建 `.env` |
| `virtuoso-bridge start` | 启动SSH隧道 + daemon |
| `virtuoso-bridge stop` | 停止 |
| `virtuoso-bridge status` | 检查状态（tunnel/daemon/Spectre） |
| `virtuoso-bridge license` | 检查Spectre license |
| `virtuoso-bridge eval "skill_code"` | 执行SKILL表达式 |
| `virtuoso-bridge load file.il` | 加载SKILL文件 |
| `virtuoso-bridge snapshot` | Maestro快照（brief模式） |
| `virtuoso-bridge snapshot -o dir` | 全量快照拉取 |
| `virtuoso-bridge screenshot` | Virtuoso窗口截图 |
| `virtuoso-bridge windows` | 列出Virtuoso窗口 |
| `virtuoso-bridge dismiss-dialog` | 关闭弹窗 |

## 附录 B：ADCToolbox 核心 API 速查

| 函数 | 用途 |
|------|------|
| `analyze_spectrum(signal, fs, ...)` | 频谱分析 → enob/sndr/snr/sfdr/thd |
| `analyze_inl_from_sine(codes, num_bits)` | INL/DNL提取 |
| `analyze_error_pdf(signal, resolution)` | 误差概率分布 |
| `analyze_error_spectrum(signal, fs)` | 误差频谱 |
| `analyze_error_autocorr(signal, max_lag)` | 误差自相关 |
| `analyze_error_envelope_spectrum(signal, fs)` | 误差包络谱（AM检测） |
| `fit_sine_4param(signal, frequency_estimate)` | 4参数正弦拟合 |
| `analyze_decomposition_time(signal, harmonic)` | 谐波分解 |
| `calibrate_weight_sine(bits, freq, ...)` | 数字权重校准 |
| `find_coherent_frequency(fs, target, n)` | 相干频率选择 |

## 附录 C：Ocean SKILL 速查

| 函数 | 语法 | 说明 |
|------|------|------|
| `openResults()` | `openResults("path")` | 打开PSF结果 |
| `selectResult()` | `selectResult("tran-tran")` | 选择分析类型 |
| `getData()` | `getData("signal_name")` | 读信号波形 |
| `spectrum()` | `spectrum(wave tStart tStop nSamp win fS fE measType)` | 频谱分析 |
| `spectrumMeas()` | `spectrumMeas(wave tS tE nSamp nbins fS fE win span measType)` | 频谱测量(IC6.1.5+) |
| `value()` | `value(spec_obj "enob")` | 提取频谱指标 |
| `ocnPrint()` | `ocnPrint(sig ?output "file.txt")` | 导出波形 |

## 附录 D：VM 环境故障排除

参照历史故障记录和 [sar-adc-skills `robustness-and-system.md`](sar-adc-skills/references/robustness-and-system.md)：

| 症状 | 根本原因 | 解决方案 |
|------|---------|---------|
| Virtuoso 启动闪退 | CDS.log 锁文件冲突 | `rm -f ~/CDS.log* /tmp/psflck* /tmp/cdslck*`；设置 `CDS_LOG_PATH=/tmp` |
| `spectre: command not found` | `.cshrc` 中 CADHOME 路径错误 | 使用绝对路径：`/opt/cadence/SPECTRE231/tools/bin/spectre` |
| License 错误 | `CDS_LIC_FILE` 未设置 | `export CDS_LIC_FILE=/opt/cadence/IC618/share/license/license.dat` |
| 仿真结果无法解析 | 输出为二进制 PSF | Spectre 加 `-format psfascii` |
| Maestro 卡住 | 弹窗阻塞 SKILL 通道 | `virtuoso-bridge dismiss-dialog` |
