# 外部工具管理说明

`04_辅助工具` 下的工具目录是独立 Git 仓库，保留在本机用于开发和查阅，但不直接纳入当前 Obsidian 笔记库版本管理。这样可以避免把第三方仓库提交成无 `.gitmodules` 的 gitlink。

| 工具 | 当前用途 | 本地状态 |
| --- | --- | --- |
| ADCToolbox | ADC 指标分析与脚本参考 | 独立 Git 仓库 |
| ADC_Visualization | ADC 可视化资料 | 独立 Git 仓库 |
| analog-agents | 模拟电路 Agent 工作流参考 | 独立 Git 仓库 |
| EVAS | ADC 仿真与分析工具参考 | 独立 Git 仓库 |
| gmoverid-skill | gm/id 技能资料 | 独立 Git 仓库 |
| sar-adc-skills | SAR ADC 技能资料 | 独立 Git 仓库 |
| veriloga-skills | Verilog-A 技能资料 | 独立 Git 仓库 |
| virtuoso-bridge-lite | Virtuoso/Spectre 自动化桥接 | 独立 Git 仓库 |

## 维护规则

- 在各工具目录内单独执行 `git status`、`git pull` 和提交操作。
- 当前笔记库只记录工具用途、工作流和必要的使用说明。
- 如需把某个工具固定到项目版本，优先建立正式 submodule 并提交 `.gitmodules`，不要直接 `git add` 嵌套仓库目录。
- 清理缓存时可删除 `__pycache__/`、`*.pyc`、`*.log`、LaTeX `*.aux` 等生成物；不要把 `uv.lock` 当作临时文件删除。
