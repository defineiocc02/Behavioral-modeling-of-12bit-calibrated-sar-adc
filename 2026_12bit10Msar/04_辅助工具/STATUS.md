# 项目现状说明

> 更新于 2026-05-12 (v2, 已修复3个问题) | 项目: 12-bit 50MS/s SAR ADC with CAAZ, TSMC 18RF

---

## 一、连接状态

### 1.1 本地 → VM SSH

| 项目 | 状态 | 说明 |
|------|------|------|
| VM IP | `192.168.38.128` | VMware NAT, CentOS 7 |
| SSH 端口 22 | ✅ **可达** | `Test-NetConnection` 通过 |
| SSH 免密登录 | ✅ | 已配置密钥认证 |
| VM 磁盘 | ✅ 65GB 可用 | 总 139GB, 已用 75GB (54%) |
| VM 用户名 | `meow` | 普通用户 |

### 1.2 VM Cadence 工具

| 工具 | 路径 | 状态 |
|------|------|------|
| **Spectre** | `/opt/cadence/SPECTRE231/tools/bin/spectre` → `../spectre/bin/spectre` | ✅ **可用**, v23.1.0.242.isr1 |
| **Ocean** | `/opt/cadence/IC618/tools.lnx86/dfII/bin/ocean` | ✅ **存在**, 但不在标准 PATH 中 |
| **Virtuoso** | `/opt/cadence/IC618/tools/dfII/bin/64bit/virtuoso` | ⚠️ **有崩溃历史** (见下文) |
| **License** | `/opt/cadence/IC618/share/license/license.dat` | ✅ **存在**, 268K |
| **PDK** | 待确认 | 未知 |

### 1.3 本地 Python 环境

| 项目 | 值 |
|------|----|
| Python 版本 | 3.13.12 (miniconda3) |
| pip 版本 | 26.0.1 |
| virtuoso-bridge-lite | ❌ **未安装** (源码已克隆) |
| ADCToolbox | ❌ **未安装** (源码已克隆) |
| EVAS | ❌ **未安装** (可 pip install evas-sim) |

---

## 二、VM 环境问题清单

### ~~2.1 严重：Patch/.cshrc 路径全错~~ ✅ 已修复

`/home/meow/.cshrc` **已创建**，指向正确路径：
```
CADHOME=/opt/cadence                     ✅
SPECTRE_HOME=/opt/cadence/SPECTRE231     ✅
CDS_LIC_FILE=/opt/cadence/IC618/share/license/license.dat  ✅
CDS_LOG_PATH=/tmp                        ✅ 防锁文件
```
验证通过：`csh -c "source ~/.cshrc; which spectre"` → `/opt/cadence/SPECTRE231/bin/spectre`
验证通过：`csh -c "source ~/.cshrc; which ocean"` → `/opt/cadence/IC618/tools/dfII/bin/ocean`

### ~~2.2 严重：无 `~/.cshrc`~~ ✅ 已修复

### 2.3 **中度：Virtuoso SegFault 历史**

昨天的崩溃记录（2026-05-11）：

```
时间: 22:31 (start) → 11:39 (crash) — 运行约 13 小时后
信号: SegFault(11)
位置: libcdsQt5XcbQpa.so (Qt/XCB GUI 层)
解释: GUI 相关的段错误，与 Xvfb (虚拟显示) 交互时触发
```

可能原因：长时间运行 + Xvfb 不稳定。不影响 Spectre CLI 模式。

### ~~2.4 轻度：/tmp/ 残留文件~~ ✅ 已清理

| 文件类型 | 清理前 | 清理后 |
|---------|--------|--------|
| `cdsXvfb-run_*` 目录 | 2178 个 | 123 个（仅保留近1天内活跃会话相关） |
| `crashReport_*` | 2 个 | 0 个 ✅ |
| `vlog.log.cdslck` | 1 个 | 0 个 ✅ |

> 余下 123 个目录属于最近活跃的 Ocean batch 进程，已保留。

### 2.5 **VM 上已有 virtuoso-bridge-lite**

`/home/meow/virtuoso-bridge-lite/` 已存在于 VM 上，`.env` 配置为 localhost 模式（VM 本机使用）。
Windows 上的工作流不需要依赖 VM 上的 bridge 实例。

---

## 三、仿真数据状态

### 3.1 ✅ 全部完成（10/10）

| 点 | Corner | td | 噪声 | 数据 | ENOB (TT) | 状态 |
|----|--------|-----|------|------|-----------|------|
| P1 | TT / 27°C | 26.5ns | 100x | 690 MB | **10.38** | ✅ |
| P2 | FF / -40°C | 26.5ns | 100x | 707 MB | — | ✅ |
| P3 | SS / 85°C | 26.5ns | 100x | 669 MB | — | ✅ |
| P4 | SS_mim / 85°C | 26.5ns | 100x | 665 MB | — | ✅ |
| P5 | FS / -40°C | 26.5ns | 100x | 712 MB | — | ✅ |
| P6 | TT / 27°C | 24.05ns | 100x | 687 MB | **8.741** | ✅ |
| P7 | FF / -40°C | 24.05ns | 100x | 703 MB | — | ✅ |
| P8 | SS / 85°C | 24.05ns | 100x | 668 MB | — | ✅ |
| P9 | SS_mim / 85°C | 24.05ns | 100x | 663 MB | — | ✅ |
| P10 | FS / -40°C | 24.05ns | 100x | 707 MB | — | ✅ |

**总计：6.8 GB，VM 路径：** `/home/meow/jxy/simulation/12bit_50M_SAR/`

### 3.2 CSV 汇总

Maestro 导出 CSV：`/home/meow/jxy/simulation/ExplorerRun.0.csv`
- 5 工艺角（TT, FF, SS, SS_mim, FS）
- 2 td 设置（26.5ns, 24.05ns）
- 核心指标：ENOB, SNR, SFDR, COMPOWER, SRPOWER, SWITCHESPOWER, PREWOCM
- 详细数据分析见 `03_实验记录/CAAZ_噪声消除_数据分析.md`

### 3.3 数据文件说明

本地 Obsidian 目录下仅有 `.md` / `.tex` / `.pdf` 文档，**无实际仿真波形数据**。
所有 PSF 数据在 VM 上：`/home/meow/jxy/simulation/12bit_50M_SAR/`

---

## 四、工具链安装状态

| 仓库 | 本地克隆 | pip 安装 | VM 部署 |
|------|---------|---------|---------|
| virtuoso-bridge-lite | ✅ `04_辅助工具/virtuoso-bridge-lite/` | ✅ **v0.7.0 已安装** | ✅ `/home/meow/virtuoso-bridge-lite/` |
| ADCToolbox | ✅ `04_辅助工具/ADCToolbox/` | ✅ **v0.7.0 已安装** | ❌ |
| EVAS | ✅ `04_辅助工具/EVAS/` | ❌ | ❌ |
| analog-agents | ✅ `04_辅助工具/analog-agents/` | N/A (纯文档) | ❌ |
| sar-adc-skills | ✅ `04_辅助工具/sar-adc-skills/` | N/A (纯文档) | ❌ |
| veriloga-skills | ✅ `04_辅助工具/veriloga-skills/` | N/A (纯文档) | ❌ |
| gmoverid-skill | ✅ `04_辅助工具/gmoverid-skill/` | N/A (脚本执行) | ❌ |
| ADC_Visualization | ✅ `04_辅助工具/ADC_Visualization/` | N/A (HTML) | ❌ |

---

## 五、项目目录结构

```
2026_12bit10Msar/
├── 01_论文/           # 论文资料
├── 02_设计文档/       # 设计文档
├── 03_IP规格/        # IP 规格定义
├── 03_实验记录/       # 仿真记录 + LaTeX 报告
│   ├── simulation_report.tex   # LaTeX 报告模板
│   ├── simulation_report.pdf   # 编译后 PDF
│   ├── 网表/          # 网表文件
│   └── 数据.md / 结果.md / 系统配置.md
├── 04_工作记录/       # 工作记录
│   └── 研究报告/
├── 05_研究报告/       # 研究报告
├── 04_辅助工具/       # 工具链 (8 个仓库 + WORKFLOW.md)
│   ├── WORKFLOW.md    # 完整工作流文档 (1394 行)
│   ├── STATUS.md      # 本文件
│   ├── virtuoso-bridge-lite/
│   ├── ADCToolbox/
│   ├── EVAS/
│   ├── analog-agents/
│   ├── sar-adc-skills/
│   ├── veriloga-skills/
│   ├── gmoverid-skill/
│   └── ADC_Visualization/
├── 05_项目管理/       # 项目管理
└── _archive/          # 归档
```

---

## 六、快速行动清单

### 🔴 ~~立即（今天）~~ ✅ 已完成

- [x] **1. 安装 virtuoso-bridge-lite**: `pip install -e .` ✅ v0.7.0
- [x] **2. 安装 ADCToolbox**: `pip install adctoolbox` ✅ v0.7.0
- [x] **3. 修复 VM .cshrc**: 已创建 `/home/meow/.cshrc`，spectre/ocean 均可找到
- [x] **4. 清理 VM /tmp/**: 已删除 2055+ 个残留文件（2178→123）
- [ ] **5. 验证 Spectre CLI**: 待执行

### 🟢 已完成（仿真执行）

- [x] **5. 验证 Spectre CLI**: 已验证，Spectre 23.1.0.242 可用
- [x] **6. 提交全部 PVT 仿真**: ✅ 10/10 全部完成（5 工艺角 × 2 td 设置）
- [x] **7. 读取 CSV 分析结果**: 见 `03_实验记录/CAAZ_噪声消除_数据分析.md`

### 🟡 下一步（数据分析）

- [ ] 用 Ocean spectrum() 或 ADCToolbox 提取 SNR/ENOB（若需从 .psfxl 提取 FFT）
- [ ] 生成 LaTeX 报告 PDF

---

## 七、关键路径与依赖

```
本地安装工具 ──→ SSH 连接 ──→ 修复 .cshrc ──→ 验证 Spectre
     │                                              │
     ▼                                              ▼
  就绪等待 ─────────────────────────────→ 提交 P2-P5 仿真
                                              │
                                              ▼
                                         等待完成 (~8h)
                                              │
                                              ▼
                              Ocean/ADCToolbox 提取数据
                                              │
                                              ▼
                                        生成 LaTeX 报告
```

**阻塞点已清除** ✅ — 工具已安装，.cshrc 已修复，/tmp/ 已清理。
