# Virtuoso Bridge 部署状态与 CLAW 模式移交方案

**日期**：2026-05-11
**目标**：通过 virtuoso-bridge-lite 实现 AI Agent 远程操控 Virtuoso，完成 COM_IAZ 功耗优化与噪声仿真

---

## 一、当前已完成状态

### 1.1 网络连通性
- VM IP 已从 `192.168.1.8` 变更为 `192.168.38.128`（VMware NAT 网段）
- 本机 `192.168.38.1` 与 VM 同网段，Ping 正常（<1ms）
- SSH 连接正常（密钥认证 `id_ed25519`，用户 `meow`）
- ⚠️ MSYS2 bash 的 SSH stdout 管道捕获有 bug，需通过 Python subprocess + 写文件中转

### 1.2 virtuoso-bridge-lite 部署
- **仓库位置**：`D:\ReedZhao\virtuoso-bridge-lite`（main 分支，v0.7.0）
- **虚拟环境**：`D:\ReedZhao\virtuoso-bridge-lite\.venv`
- **配置文件**：`C:\Users\Administrator\.virtuoso-bridge\.env`
  - `VB_REMOTE_HOST=192.168.38.128`
  - `VB_REMOTE_USER=meow`
  - `VB_REMOTE_PORT=65440`
  - `VB_LOCAL_PORT=65441`
- **SSH 隧道**：✅ 已建立（tunnel running）

### 1.3 Virtuoso Daemon 状态
- **[daemon] NO RESPONSE** — SKILL 桥接脚本已部署到 VM，但 CIW 加载时端口冲突
- **错误**：`Port 65440 is already in use. Another daemon may be running.`
- **原因**：之前 `virtuoso-bridge start` 已部署了 daemon 进程占用 65440 端口
- **解决**：等用户仿真完成后，在 VM 上 `fuser -k 65440/tcp` 杀掉旧进程，再在 CIW 重新 `load()`

### 1.4 Spectre 状态
- **[spectre] NOT FOUND** — spectre 不在远程 shell 默认 PATH 中
- **需要**：找到设置 Cadence 环境的 cshrc 文件路径，配到 `.env` 的 `VB_CADENCE_CSHRC`
- **已知线索**：用户之前通过 bash 脚本设置环境变量：
  ```bash
  export CDS_LIC_FILE=/opt/cadence/IC618/share/license/license.dat
  export PATH=/opt/cadence/IC618/bin:$PATH
  export CDS_AUTO_64BIT=ALL
  ```
  但 spectre 可能另有安装路径（如 SPECTRE181 或 MMSIM151），需在 VM 上 `find /opt/cadence -name spectre` 确认

### 1.5 旧脚本已清理
- VM 上 `/home/meow/jxy/` 下的 `read_com*.py`、`dump_com*.py`、`dump_all_com.il` 均已删除

---

## 二、用户当前操作
- ⚠️ 用户正在 Virtuoso 中运行仿真，**不要杀任何进程**

---

## 三、CLAW 模式移交方案（仿真完成后执行）

### Step 1：修复 Daemon 端口冲突
```bash
# 在 VM 上杀掉占用 65440 端口的旧 daemon
ssh meow@192.168.38.128 "fuser -k 65440/tcp"
```
然后在 Virtuoso CIW 重新加载：
```
load("/tmp/virtuoso_bridge_meow/virtuoso_bridge/virtuoso_setup.il")
```
预期输出：`[RAMIC Bridge ipc=ipc:XX] launching daemon (bind=0.0.0.0:65440)` 且无 exit

### Step 2：配置 Spectre 路径（cshrc 已确认）
cshrc 路径已在 VM 内部署时确认：`/home/meow/Downloads/Patch/.cshrc`

更新 Windows 侧 `.env`（如尚未添加）：
```
VB_CADENCE_CSHRC=/home/meow/Downloads/Patch/.cshrc
```
同时确认 VM 侧 `~/.virtuoso-bridge/.env` 也包含该配置。

若 Spectre 仍 NOT FOUND，在 VM 上补充搜索：
```bash
ssh meow@192.168.38.128 "find /opt/cadence -name spectre -type f 2>/dev/null"
```

### Step 3：验证桥接全通
```python
from virtuoso_bridge import VirtuosoClient
client = VirtuosoClient.from_env()
client.execute_skill("1+2")  # 应返回 VirtuosoResult(status=SUCCESS, output='3')
```

### Step 4：通过 SKILL 读取 COM_IAZ 电路结构
```python
client = VirtuosoClient.from_env()

# 列出 COM_IAZ 的所有 instance
client.execute_skill('cv = dbOpenCellViewByType("12bit_50M_SAR" "COM_IAZ" "schematic" "" "r")')
client.execute_skill('foreach(inst cv~>instances printf("%s %s %s\n" inst~>name inst~>cellName inst~>cellType))')

# 读取器件参数
client.execute_skill('foreach(inst cv~>instances printf("%s: W=%L L=%L m=%L\n" inst~>name inst~>prop~>w inst~>prop~>l inst~>prop~>m)')
```

### Step 5：修改 COM_IAZ 器件参数（IB 降低优化）
```python
# 示例：修改某个 MOS 管的宽长比
client.execute_skill('inst = car(setof(x cv~>instances x~>name == "M0"))')
client.execute_skill('inst~>prop~>w = 2u')  # 修改 W
```

### Step 6：跑 8 组噪声/无噪声仿真
通过 virtuoso-bridge 的 SpectreSimulator 或直接修改网表：

| 序号 | N | td (ns) | noise | corner |
|------|---|---------|-------|--------|
| 1 | 13 | 24.05 | ✅ | SS |
| 2 | 13 | 26 | ✅ | SS |
| 3 | 61 | 24.05 | ✅ | SS |
| 4 | 61 | 26 | ✅ | SS |
| 5 | 13 | 24.05 | ❌ | SS |
| 6 | 13 | 26 | ❌ | SS |
| 7 | 61 | 24.05 | ❌ | SS |
| 8 | 61 | 26 | ❌ | SS |

网表修改项：
- `section=ss`（工艺角）
- `noisescale=1`（开噪声）/ `noisescale=0`（关噪声）
- `N=13` 或 `N=61`
- `td=24.05n` 或 `td=26n`

### Step 7：COM_IAZ IB 扫描
在 Step 4 读取的电路结构基础上，通过修改设计变量 `IB` 扫描功耗下限：
- 从当前 `IB=1.7u` 逐步降低
- 监控比较器输出（`I28.VOP1`, `I28.VON1`）判断比较功能是否正常
- 确认不成为整体 ADC 的带宽瓶颈

---

## 四、关键文件索引

| 文件 | 路径 | 说明 |
|------|------|------|
| VB 配置 | `C:\Users\Administrator\.virtuoso-bridge\.env` | SSH/端口/Cadence配置 |
| VB 仓库 | `D:\ReedZhao\virtuoso-bridge-lite\` | Python包+SKILL脚本 |
| VB venv | `D:\ReedZhao\virtuoso-bridge-lite\.venv\` | Python虚拟环境 |
| SKILL桥接(远程) | `/tmp/virtuoso_bridge_meow/virtuoso_bridge/virtuoso_setup.il` | 需在CIW加载 |
| SSH调试输出 | `C:\Users\Administrator\ssh_debug.log` | SSH连接详细日志 |
| VB状态记录 | `C:\Users\Administrator\vb_status.txt` | bridge status输出 |

---

## 五、已知问题与注意事项

1. **MSYS2 SSH stdout 捕获 bug**：bash 直接调 SSH 不显示 stdout，需通过 Python `subprocess.run()` + 写文件中转
2. **端口 65440 冲突**：`virtuoso-bridge start` 启动的 daemon 和 CIW 加载的 daemon 竞争同一端口，需先杀旧的
3. **Virtuoso 正在运行仿真**：当前有仿真任务在跑，**不要杀任何进程、不要重启 Virtuoso**
4. **Spectre 路径**：cshrc 已确认为 `/home/meow/Downloads/Patch/.cshrc`，需确认 `.env` 已配 `VB_CADENCE_CSHRC`
5. **COM_IAZ 为晶体管级电路**（nch/pch），通过 SKILL 桥接可直接修改器件参数，无需 OA Python 绑定

---

## 六、模式说明

- **当前（PLAN 模式）**：仅分析和记录，不执行任何操作
- **CLAW 模式**：仿真完成后切换，按 Step 1-7 顺序执行所有操作
