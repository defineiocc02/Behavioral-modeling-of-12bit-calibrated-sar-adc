# v3.1 图表目录

最终报告只使用下列七组 v3.1 当前图。性能图从冻结 CSV/JSON
直接生成，不从 README 手工抄录数据；架构图从当前仓库接口重绘，不复用
v3.0 旧图。

| 图文件 | 内容 | 权威数据 |
|---|---|---|
| `fig_project_architecture` | Python、RTL、Verilog-A、证据链与复现边界 | 当前仓库结构与接口 |
| `fig_cdac_topology` | P/N split-CDAC、top-node sampling、floating bridge 与 bottom-plate rails | 当前 Python/Verilog-A 方程 |
| `fig_validation_flow` | 物理 decisions、nominal/calibrated/oracle 三路解码及校准测量边界 | 当前代码结构 |
| `fig_mismatch_performance` | 理想、0.5%/1.0% PER-UNIT 失配下 pre/cal/oracle SNDR 分布 | `evidence/mismatch_matrix/` |
| `fig_noise_secondary` | 0 与 0.3 mV calibration-only 条件的 CDF 和配对差值 | 同一 100 seeds 的冻结 CSV |
| `fig_monotonicity_mechanism` | 1-LSB 局部回退示意与受影响输入区间统计 | 冻结 transfer-integrity 汇总 |
| `fig_rtl_architecture` | 校准 RTL 数据流、AMS 边界、Q8 递归寄存器及未完成边界 | 当前 RTL、XSIM 与综合报告 |

每组输出 PDF、SVG 和 300 dpi PNG：

```text
docs/figures/mismatch_report/
```

生成命令：

```powershell
python scripts/generate_report_figures.py `
  --matrix-root evidence/mismatch_matrix
```

图内模块名、端口、箭头、坐标轴、图例和注释统一使用英文；中文只出现在
报告正文与图注。当前生成器及 SVG 必须通过汉字零命中扫描，避免图内中英文
混排。生成器固定使用仓库内绘图 helper、DejaVu Sans 和
`requirements/report-render-py313.txt`，避免调用用户级 Figura 或发生
Windows/Linux 字体回退。PDF 是 LaTeX 嵌入源，SVG 用于审阅，PNG 用于视觉 QA。

`docs/archive/v3.0/figures/fig01` 至 `fig09` 是 v3.0 建模和历史架构
审查图，连同对应生成脚本一起版本化归档，不作为 v3.1 最终 PDF 的
性能证据，也不会由当前 CI/复现入口重新生成。
