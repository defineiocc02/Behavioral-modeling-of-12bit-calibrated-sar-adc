# v3.0 图表目录

全部图由 `python docs/figures/generate_modeling_figures.py` 生成，并同时输出
PNG、SVG、PDF。数据源记录在 `docs/assets/figures/figure_manifest.json`。

| 图 | 内容 | 数据源 |
|---|---|---|
| fig01 | 模型模块与数据流 | 活动代码结构 |
| fig02 | 138 Cu 整数 CDAC | `config.py` |
| fig03 | 有效权重与逐级冗余 | `config.py` |
| fig04 | 校准前/后/oracle SNDR | final pipeline CSV |
| fig05 | oracle gap CDF | final pipeline CSV |
| fig06 | DNL/INL 与形式化回退诊断 | final pipeline CSV |
| fig07 | 各 target 校准误差 | final summary JSON |
| fig08 | 电容、周期与校准工作量 | v2.1/v3.0 配置 |
| fig09 | 旧 95 Cu 与 v3.0 的 1000-seed 静态对比 | design audit JSON |

图表不从 README 手工录入性能数字，避免文档与结果文件漂移。
