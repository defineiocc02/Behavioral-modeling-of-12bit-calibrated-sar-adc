# CDAC_CAL_Huang_Lite_V2 交付清单

整理时间：2026-07-15

## 当前状态

- 本目录是稳定交付包，不包含可再生的 PSF/RAW 波形缓存。
- `DEC_CAL_PHY.va` 当前默认 `AVG_LOG2=3`，即 8 对正负测量；用户输入“0”后的参数修改因随后要求暂停而没有执行。
- 本次整理没有启动 Spectre、Virtuoso或任何仿真，也没有连接虚拟机。
- 虚拟机中此前安装的版本没有在本次整理中改动。

## 正式源文件

| 文件 | 作用 |
| --- | --- |
| `DEC_CAL_PHY.va` | 真实 CDAC 闭环前景校准、定点权重寄存和 12 位加权解码 |
| `SWITCH_CAL.va` | 正常 SAR/校准底板控制选择，端口保持现有项目结构 |
| `CAL_CMP_TB.va` | 仅供独立闭环测试使用的理想比较器，不应放入真实顶层 |

## 接入与复现文件

| 文件 | 作用 |
| --- | --- |
| `DEC_CAL_PHY_接入说明.md` | 端口、总线映射、时序、参数和验证结果 |
| `tb_DEC_CAL_PHY_compile.scs` | Verilog-A 编译冒烟测试网表 |
| `tb_DEC_CAL_PHY_closed_loop.scs` | 4 fF 分段桥接 CDAC 闭环功能测试网表 |
| `run_DEC_CAL_PHY_compile.py` | 编译测试运行脚本；只在明确需要仿真时手动执行 |
| `run_DEC_CAL_PHY_closed_loop.py` | 闭环测试运行脚本；只在明确需要仿真时手动执行 |

## 保留日志

| 文件 | 内容 |
| --- | --- |
| `logs/spectre_compile.out` | Spectre 23.1 编译结果，0 error、0 warning |
| `logs/spectre_ideal_8pairs.out` | 理想 CDAC、8 对测量，`DONE=1`、`ERR=0`、67.3001 µs 完成 |
| `logs/spectre_mismatch_md8_1p1.out` | D/P 侧 C8 临时增加 10% 的闭环失配验证，测得 `w8≈135` |

测试网表中的 C8 已恢复为名义值；10% 失配只保留在历史日志中。

## SHA-256

```text
2910471757f630730e9bb38493ee2e2245a27e3cbe1ad6d2b4389895ea7afd68  DEC_CAL_PHY.va
58070ee17a1b23da2ca1e1648baf59583880efca4a3bbfb0a1a2344f10cd3b84  SWITCH_CAL.va
9699046a2f26a88783f8f89cae46cb401ff72e15747815400529a2253263e3cb  CAL_CMP_TB.va
```

## 未收录内容

- PSF/RAW 瞬态波形：体积约 243.2 MiB，可由测试网表重新生成，因此不属于交付文件。
- `DEC_CAL.va` 与 `tb_DEC_CAL.scs`：属于早期非物理闭环版本，仍留在上一级开发目录，没有混入 V2 交付包。
- `CMP2SAR_IF.va`：属于项目中原有的其他接口模型，没有复制到本交付包。

