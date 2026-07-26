# Cadence VM 远程操作与空间治理规范

> 版本：1.0
> 生效日期：2026-07-26
> 适用对象：所有通过 Windows 主机远程操作 `meow` CentOS7/Cadence VM 的人工或自动化任务

## 1. 目标

本规范解决四类问题：

1. AI 或脚本进入错误目录，误把沙箱、OA库和仿真结果当成同一工程；
2. 临时文件散落在 `/home/meow`、`/home/meow/jxy` 或 `/tmp/vm_output`；
3. 未做归档、进程检查和路径解析便清理数据；
4. 依赖交互式 shell 的 PATH，导致同一命令在 SSH、Virtuoso 和本机表现不同。

核心原则是：**源、运行、归档、临时输出四区分离；路径、版本、空间、删除均可追溯。**

## 2. 权威路径与保护级别

### 2.1 永久保护路径

以下路径不得作为普通整理或清理目标：

| 路径 | 内容 | 规则 |
|---|---|---|
| `/home/meow/jxy/12bit_50M_SAR` | 活跃 Cadence OA 库 | 不移动、不改名、不递归删除 |
| `/home/meow/jxy/simulation` | 活跃/历史 Maestro 与 Spectre 主结果 | 未获得单独明确授权时不动 |
| `/home/meow/jxy/cds.lib` | Cadence 库定义 | Virtuoso 关闭且用户批准后才可改 |
| `/home/meow/Desktop/TSMC18RF` | PDK | 禁止作为任务写入或清理区 |
| `/opt/cadence` | EDA 安装 | 只读 |
| `/home/meow/.cdsinit`、`.bashrc`、`.cshrc` | 用户环境 | 只读检查；修改须备份和单独批准 |
| `/home/meow/zhaoyi` | 持久归档根 | 不递归删除整个根目录 |

“根目录整理”默认指 `/home/meow` 顶层，不是 Linux `/`，更不授权移动上述保护路径。

### 2.2 标准工作区

```text
/home/meow/
├── jxy/
│   ├── 12bit_50M_SAR/               protected OA library
│   ├── simulation/                  protected main simulator results
│   ├── trae_sandbox/
│   │   ├── current_git_<shortsha>/  one current standalone run package
│   │   └── _archive/                verified legacy source/netlist bundles
│   └── cds.lib                      protected library definition
├── zhaoyi/
│   └── vm_archives/                 persistent archives and manifests
├── VM_FILE_STRUCTURE.md             workspace map
└── VM_REMOTE_OPERATIONS_STANDARD.md this standard

/tmp/vm_output/
├── YYYYMMDD_<task_slug>/            one task, one output directory
├── YYYYMMDD_workspace_audit/        dated read-only inventories
└── _legacy_flat_pre_YYYYMMDD/       old flat reports awaiting expiry
```

不得在 `/home/meow` 或 `/home/meow/jxy` 顶层新建 `test*`、`tmp*`、`codex*`、
`agent*`、`psf*`、`raw*`、`*.ahdlSimDB` 目录。

## 3. 连接与命令执行

### 3.1 唯一远程入口

Windows 端统一使用：

```text
D:\ReedZhao\vm-remote\vm_base.py
VMConnection
```

禁止为任务另写裸 Paramiko 连接、硬编码密码或依赖普通 `ssh` 的多行 stdout。
大输出必须使用 `VMConnection.run_to_file()` 写入任务目录，再用 `read_file()` 读取。
`run_to_file()` 会在命令末尾追加重定向；多条 shell 命令必须放入任务脚本或包装成单个
`bash -lc`/`csh -fc` 调用，否则重定向可能只捕获最后一条命令。短小状态量才允许直接
读取 `VMConnection.run()` 的 stdout。

### 3.2 非交互环境

SSH 非交互 shell 不保证加载 PATH。任务脚本必须使用已验证的绝对工具路径，或者只在
当前进程中加载现有用户环境；不得为一次运行修改 `.bashrc/.cshrc`。

当前验证路径：

```text
Python   /home/meow/miniconda3/bin/python
Spectre  /opt/cadence/SPECTRE231/tools.lnx86/spectre/bin/spectre
Xcelium  /opt/cadence/XCELIUM2309/tools.lnx86/inca/bin/64bit/xrun
```

启动仿真前必须确认 license 环境已由现有配置提供。当前有效环境入口是
`/home/meow/.cshrc`；`/home/meow/Downloads/Patch/.cshrc` 仍指向旧的
`/opt/eda/cadence`，不得用于当前自动化。出现 license error 时停止并报告，禁止
绕过、伪造或修改许可证配置。

## 4. 每个任务的目录与命名

任务 ID 使用：

```text
YYYYMMDD_<project>_<purpose>[_<gitsha>]
```

例如：

```text
20260726_sar_adc_va_rtl_74e7366
```

每个独立沙箱必须具有：

```text
source/       immutable uploaded sources
tb/           task-owned standalone testbenches
runs/         simulator-generated output
reports/      status, metrics, hashes, space report
README.md     scope, commit, rerun command, claim boundary
run_all.sh    reproducible entrypoint
```

禁止把运行生成物写回 `source/` 或覆盖 OA cellview。

## 5. 版本与来源校验

上传前记录本机：

- Git 根、branch、full commit SHA；
- `git status --porcelain`；
- 上传文件清单；
- 本机 SHA-256。

上传后在 VM 重新生成 `reports/source_manifest.sha256`。两端 hash 不一致时不得运行。
VM 当前没有 Git 的 OA 库不能用 mtime 单独判定版本，至少需要 cell/view、mtime、hash、
Maestro run ID 四项。

## 6. 空间预算

### 6.1 任务开始前

必须记录：

```bash
df -h /home/meow
du -sh <task-root>
```

### 6.2 默认限额

| 对象 | 软限制 | 硬停止条件 |
|---|---:|---:|
| 单个 standalone 沙箱 | 2 GB | 5 GB |
| 单次 VA/RTL smoke run | 500 MB | 1 GB |
| `/tmp/vm_output/<task>` | 50 MB | 200 MB |
| 新建持久归档 | 500 MB | 必须先报告预估大小 |

超过软限制先分析 `du`；超过硬停止条件立即停止生成，不能靠继续运行“等结果”。
主 Maestro campaign 的容量由独立任务另行批准，不适用在沙箱中偷偷扩容。

## 7. 临时文件策略

1. 一个任务只能写 `/tmp/vm_output/<task-id>/`，不得写平铺散文件。
2. 成功任务的临时输出默认保留3天；已复制到持久报告后可立即删除。
3. 失败诊断默认保留14天；必须在 README/交接中写明失败原因。
4. `.va/.scs/.sv/.py/.sh/.log` 中具有复现价值的文件不得只留在 `/tmp`。
5. 不创建无清理责任人的后台 nohup campaign。

## 8. 仿真前置检查

每次运行依次执行：

1. `readlink -f` 确认任务根在 `trae_sandbox/current_*`；
2. 检查 Virtuoso、Spectre、Xcelium 进程；
3. 检查源 hash；
4. 检查 `df/du` 与配额；
5. 检查工具版本和 license；
6. 为每个用例建立独立 `runs/<case>`；
7. 日志写入该 case，禁止多个运行共用同一 raw 目录。

## 9. 验证层级与结论边界

| 层级 | 可证明 | 不可外推 |
|---|---|---|
| VA compile/smoke | 语法、AHDL编译、有限激励下运行 | full ADC、PVT、噪声、流片 |
| RTL self-check | 指定算术/FSM契约 | 完整 normal SAR、CDC、STA、ASIC功耗 |
| OA/AMS integration | 指定 cellview/top 的混合信号闭环 | post-layout、silicon |
| transistor campaign | 指定网表/角/seed 的性能 | 未覆盖角落和统计良率 |

失配是当前 SAR ADC 主验证轴；噪声只作为校准稳健性附加轴。不得用高倍噪声压力
测试覆盖或歪曲失配结论。

## 10. 归档与删除流程

所有删除必须遵循：

```text
inventory -> process check -> source/netlist archive -> manifest/hash verify
          -> exact target list -> path resolve/protection check -> delete
          -> df/du after -> deletion log
```

归档至少保留：

- `.va/.vams/.scs/.sv/.v/.py/.sh/.csh/.il/.ocn`；
- 关键 `.log/.json/.csv/.md`；
- SHA-256 manifest；
- 原相对路径；
- 删除目标、字节数和时间戳。

可删除生成物包括已确认的 `psf*`、`raw*`、`*.ahdlSimDB` 和 simulator cache。
禁止使用未展开的 glob 删除；禁止递归删除 `/home/meow`、`/home/meow/jxy`、OA根、
simulation根或归档根。

## 11. `/home/meow` 顶层治理

顶层只保留：用户配置、标准系统目录、EDA/PDK入口、工作区、归档根和两份运维文档。

- 散落的 `CDS.log*`、`spectre.out`、Ocean脚本和历史诊断日志移动到
  `/home/meow/zhaoyi/vm_archives/<dated-folder>/`；
- 顶层 `*.ahdlSimDB` 作为生成缓存，在进程关闭、来源确认后删除；
- 不清理 `.cache/.mozilla/.local/miniconda3`，除非有单独的软件环境治理任务；
- 不移动 `Desktop/Downloads` 中的 PDK、补丁和启动配置。

## 12. 失败、回滚与交接

失败时必须保留：命令、exit code、短错误摘要、工具版本、源 hash、日志路径和空间。
不得为了“跑通”直接修改已上传的设计 `source/`。设计修复必须回到本机 Git，形成新
commit，再进入新的 `current_git_<sha>` 沙箱。任务自有 testbench 或 runner 若有语法、
路径问题，应先在本机修订，重新上传、更新 manifest，并在同一任务日志中记录修订前后
结果；不得在 VM 上无记录地热改。

每次交接至少报告：

- 实际操作路径与保护路径；
- 新增、移动、归档、删除的完整目标；
- 空间 before/after；
- 每项运行 PASS/FAIL；
- Git SHA、VM source manifest、归档 SHA；
- 未完成项和不允许外推的结论。

## 13. 当前落实状态

2026-07-26 已完成：

- 历史 `trae_sandbox` 源码/网表/日志共139项归档并生成 SHA-256 manifest；
- 旧沙箱生成数据约706 MB删除，沙箱降至约1 MB归档基线；
- 新建 `current_git_74e7366` 作为当前 Git VA/RTL 唯一 standalone 沙箱；
- `/home/meow` 顶层11个散落日志/脚本移入统一持久归档；
- 删除2个顶层 AHDL cache，约6.8 MB；
- `/tmp/vm_output` 改为按日期/任务分目录。

当前 `current_git_74e7366` standalone 复核结果：

| 项目 | 结果 | 证据边界 |
|---|---|---|
| StrongARM comparator VA | PASS | Spectre 0 errors、0 warnings、2 notices |
| split-CDAC VA | PASS | Spectre 0 errors、4 warnings、2 notices |
| calibration RTL self-check | PASS | 7/7 targets，运行至4065 ns |
| lower-SAR RTL self-check | PASS | side-specific Q8 weights，运行至705 ns |
| `cal_top` compile/elaborate | PASS | `xrun -elaborate` 返回0，0 error/warning/fatal |

CDAC VA 的4条 warning 均为 `VACOMP-1116`，对应 `cdac_behavioral.va` 第153--156行
对连续信号表达式使用 `transition()`。它们没有导致本次 smoke run 失败，但属于模型
语义风险，后续应评估是否改为离散目标更新或使用适合连续信号的平滑方式；不得据此把
standalone PASS 外推为 AMS、PVT、噪声或流片验证通过。

本次运行后沙箱为15 MB，低于500 MB smoke-run软限制；运行后主工程
`/home/meow/jxy/12bit_50M_SAR` 中晚于运行前标记的文件数为0。
