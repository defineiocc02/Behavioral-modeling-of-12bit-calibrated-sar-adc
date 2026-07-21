---
title: Verilog-A 行为模型目录
created: 2026-06-01
updated: 2026-07-15
tags:
  - VerilogA
  - 行为模型
  - SAR_ADC
---

# Verilog-A 行为模型目录

本目录用于保存 12-bit 50-MS/s SAR ADC 项目中可被 Spectre/ADE 直接 include 的行为模型。

| 文件 | 用途 |
| --- | --- |
| `CMP2SAR_IF.va` | 将比较器 `COMP/COMN` 转换为原 `SAR_LOGIC` 可安全读取的单端低有效 `DEC_N` |
| `DEC_CAL.va` | 沿用 `DEC` 原网络名的 CDAC 前台权重校准和 12-bit 总线解码模型 |
| `tb_DEC_CAL.scs` | 独立 Spectre 编译、校准时序和四组解码向量冒烟测试 |
| `DEC_CAL_PHY.va` | 驱动真实 CDAC、读取真实比较器的轻量 Huang 式正负前景权重校准与加权解码 |
| `SWITCH_CAL.va` | 保留原开关端口，并在 `CAL=1` 时接管真实 CDAC 底板 |
| `DEC_CAL_PHY_接入说明.md` | 当前项目的端口、总线映射、时序、参数和验证结果 |
| `delivery/CDAC_CAL_Huang_Lite_V2/` | 稳定交付包：正式源码、测试依赖、测试台、运行脚本、关键日志和 SHA-256 清单 |

`spectre_closed_loop/` 与 `spectre_compile_smoke/` 原始结果目录属于可再生缓存，已在 2026-07-15 整理时删除；三份必要的文本日志已保存在交付包的 `logs/` 中。`DEC_CAL.va` 和 `tb_DEC_CAL.scs` 是早期非物理闭环版本，只作为历史参考保留在本开发目录，不属于 V2 交付文件。

## 使用原则

1. 行为模型用于快速功能验证、时序窗口验证和参数 sweep。
2. 进入最终版图前，关键接口应替换为晶体管级实现。
3. 每个行为模型应在 `02_文档与报告/IP规格` 中保留对应说明书。
