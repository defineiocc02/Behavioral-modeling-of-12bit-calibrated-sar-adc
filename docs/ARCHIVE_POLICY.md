# 归档与发布策略

当前工作树只维护一条活动发布线：`v3.1.0`。详细的版本字段、证据冻结和
脏工作树处理规则见 [`VERSION_MANAGEMENT.md`](VERSION_MANAGEMENT.md)。

## 活动内容

- `src/python_cal/`：当前 Python 行为模型、PER-UNIT 失配、校准、解码与验收；
- `rtl/`：当前 Q8 校准控制与低位 SAR 子转换器；
- `va/`：当前 CDAC 与比较器 Verilog-A 映射；
- `evidence/mismatch_matrix/`：从正式运行中冻结的 v3.1 原始证据；
- `docs/figures/mismatch_report/`：只由上述冻结证据重绘的 v3.1 图；
- `docs/final_report.tex` 与 `docs/final_report.pdf`：当前报告源文件和交付件。

## 历史内容

v3.0 的结果说明、绘图脚本和图件统一保存在
`docs/archive/v3.0/`。它们只用于追溯，不得被 v3.1 报告、CI 或复现脚本
读取。Git 在提交前应把旧路径删除与新归档路径新增识别为显式迁移。

不再使用且没有追溯价值的重复 RTL/Verilog-A 模块不复制进活动树；它们仍可
从 Git 历史恢复。大型仿真中间文件、Vivado 数据库、缓存与临时运行器只留在
被忽略的工作目录中，不进入版本库。

目录 `2026_12bit10Msar` 明确不属于本仓库发布内容。即使本机存在副本，也不得
暂存或推送。

## 发布前检查

1. 等待全部正式运行结束，确认 stderr 为空且运行清单完整；
2. 冻结五个声明用例，并由冻结树重绘当前图和生成 PDF；
3. 检查 `git status --short`、`git diff --check` 和完整 staged diff；
4. 确认 `git ls-files | rg 2026_12bit10Msar` 无输出；
5. 运行 Python、XSIM、综合报告、PDF 字体与逐页视觉 QA；
6. 核对 `VERSION`、`pyproject.toml`、`spec.yml`、`CHANGELOG.md` 和
   `python_cal.__version__` 均为同一版本；
7. 只暂存已审查的源代码、冻结证据、当前图、报告和明确的历史迁移；
8. 提交并推送当前分支；发布标签只指向通过上述检查的提交。
