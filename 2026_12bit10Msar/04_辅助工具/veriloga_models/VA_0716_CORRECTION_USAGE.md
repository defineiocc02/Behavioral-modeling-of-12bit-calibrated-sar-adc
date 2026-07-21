# 0716 CDAC 校正 VA 使用说明

## 文件

- `SWITCH_CAL_0716_CORRECTED.va`：替换现有 `SWITCH_CAL/veriloga`。
- `DEC_CAL_PHY_0716_CORRECTED.va`：替换现有 `DEC_CAL_PHY/veriloga`。

两个文件中的 module 名称仍分别是 `SWITCH_CAL` 和 `DEC_CAL_PHY`，不能与旧
版本同时被同一个 Spectre 网表 `ahdl_include`。

## 已修正的实际映射

| SAR阶段 | SET | SAR决定 | 物理底板 | 电容权重 |
|---:|---:|---:|---:|---:|
| 0 | SET<0> | BITP/N<13> | BITD/U<13> | 16C |
| 1 | SET<1> | BITP/N<12> | BITD/U<12> | 8C |
| 2 | SET<2> | BITP/N<11> | BITD/U<11> | 4C |
| 3 | SET<3> | BITP/N<10> | BITD/U<10> | 2C |
| 4 | SET<4> | BITP/N<9> | BITD/U<9> | 2C 冗余 |
| 5 | SET<5> | BITP/N<8> | BITD/U<8> | 1C |
| 6...12 | SET<6:12> | BITP/N<7:1> | BITD/U<7:1> | 分裂阵列 |
| 13 | SET<13> | BITP/N<0> | 无物理电容 | 终止决定 |

`BITD_CAL/BITU_CAL<0:12>` 仍采用阶段顺序：校准位0控制物理13，校准位12
控制物理1。

## 必须由你在 Virtuoso 中完成的改动

### 1. 更新 SWITCH_CAL 的 Verilog-A 和 symbol

1. 打开 `12bit_50M_SAR/SWITCH_CAL/veriloga`。
2. 用 `SWITCH_CAL_0716_CORRECTED.va` 的内容完整替换并执行 Check and Save。
3. 由新的 veriloga view 重新生成 symbol，或者至少把以下两个输入总线扩成14位：
   - `BITN<13:0>`
   - `BITP<13:0>`
4. 保持以下接口不变：
   - `BITD<13:1>`、`BITU<13:1>`
   - `SET<12:0>`
   - `BITD_CAL<12:0>`、`BITU_CAL<12:0>`
5. 在 `test_12bit50MSAR_AMS_final_0716` 中，将 SWITCH_CAL 的 BITP/BITN
   输入直接接到 SAR_LOGIC_0716 的完整 `BITP<13:0>`、`BITN<13:0>` 总线。

VA 无法从现有13位 symbol 中读取缺失的 `BITP/N<13>`，所以这一步不能只靠
代码内部修复。

### 2. 更新 DEC_CAL_PHY

1. 打开 `12bit_50M_SAR/DEC_CAL_PHY/veriloga`。
2. 用 `DEC_CAL_PHY_0716_CORRECTED.va` 完整替换并 Check and Save。
3. symbol 引脚无需变化。

新 decoder 已在 VA 内部按如下方式读取现有 BP 总线：

```text
r0/w0   <- BP<13>  (BITP<13>, MSB)
r1/w1   <- BP<12>
...
r12/w12 <- BP<1>
r13/w13 <- BP<0>   (terminal)
```

因此使用这份 decoder 时不要再反接 PN buffer 的 BP 总线；现有
`BP<i>=BITP<i>` 可以保留。

## 重新网表化检查

在 ADE 中强制重新生成网表。第一次验证建议关闭 AHDL 复用，或使用新的
Interactive run。生成的 `input.scs` 必须满足：

```text
SWITCH_CAL 实例包含 BITN<0>...BITN<13>
SWITCH_CAL 实例包含 BITP<0>...BITP<13>
ahdl_include 指向刚更新的 SWITCH_CAL/veriloga/veriloga.va
ahdl_include 指向刚更新的 DEC_CAL_PHY/veriloga/veriloga.va
```

如果仍只有 `BITP/N<0:12>`，说明 symbol/CDF termOrder 没有更新，禁止继续
跑长仿真。

## 分两步验证

### A. 先验证普通 SAR

将 `DEC_CAL_PHY.CAL_BYPASS=1`，保存：

```text
P N RST RST1
SET<0:13>
BITP<13:0> BITN<13:0>
BITD<13:1> BITU<13:1>
CAL DONE ERR
```

检查一个转换周期：

1. `SET<0>` 激活时，必须由 `BITP/N<13>` 控制 `BITD/U<13>`。
2. `SET<4>` 激活时，必须由 `BITP/N<9>` 控制 `BITD/U<9>`。
3. `BITP/N<0>` 不能引起任何底板切换。
4. 每一步后应满足 `abs(P-N)`总体收敛，不应在第五步突然出现16C大跳变。

### B. 再打开校准

将 `CAL_BYPASS=0`。正确日志应满足：

```text
target=3 -> 物理 BITD/U<10> 的普通2C
target=4 -> 物理 BITD/U<9> 的冗余2C
DONE=1
ERR=0
```

旧日志中的以下组合不应再次出现：

```text
target=4 ... q=624
DONE=1 ERR=1
```

## 建议保留的参数

```text
SWITCH_CAL:
  TD_RSTT=20p TD_RST11=20p TCLK_EDGE=10p
  NORMAL_REF_SWAP=1

DEC_CAL_PHY:
  TD_CAL=200p TD_CMP_CAL=2n
  CMP_SWAP=1
  CAL_BYPASS=0
  ZERO_ON_INVALID_PHASE0=1
  ZERO_ON_INVALID_PHASE1=1
```
