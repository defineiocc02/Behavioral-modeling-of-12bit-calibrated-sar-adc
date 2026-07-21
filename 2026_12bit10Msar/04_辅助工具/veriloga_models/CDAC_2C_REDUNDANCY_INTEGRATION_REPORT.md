# 12-bit SAR CDAC 2C 冗余位顺序编号重构说明

本文档对应当前两份 Verilog-A：

- `SWITCH_CAL.va`
- `DEC_CAL_PHY.va`

这版采用**混合编号**，避免把 CDAC 物理电容端口反过来：

- `BITD/BITU` 保持 CDAC 物理电容编号：`C10` 仍然接 `BITD/U<10>`。
- `SET/BITP/BITN/BP/BITD_CAL/BITU_CAL` 使用真实转换顺序编号。
- 新增 2C 冗余支路 CR 使用物理端口 `BITD/U<13>`，但它的转换 stage 是 4。

## 1. 总映射表

| stage | 物理对象 | 权重 | 物理底板端口 | SET | SAR 决策 | Decoder 输入 | 校准控制 |
|---:|---|---:|---|---|---|---|---|
| 0 | C12 | 2048 | BITD/U<12> | SET<0> | BITP/N<0> | BP<0> | CAL<0> |
| 1 | C11 | 1024 | BITD/U<11> | SET<1> | BITP/N<1> | BP<1> | CAL<1> |
| 2 | C10 | 512 | BITD/U<10> | SET<2> | BITP/N<2> | BP<2> | CAL<2> |
| 3 | C9 | 256 | BITD/U<9> | SET<3> | BITP/N<3> | BP<3> | CAL<3> |
| 4 | CR | 256 | BITD/U<13> | SET<4> | BITP/N<4> | BP<4> | CAL<4> |
| 5 | C8 | 128 | BITD/U<8> | SET<5> | BITP/N<5> | BP<5> | CAL<5> |
| 6 | C7 | 48 | BITD/U<7> | SET<6> | BITP/N<6> | BP<6> | CAL<6> |
| 7 | C6 | 32 | BITD/U<6> | SET<7> | BITP/N<7> | BP<7> | CAL<7> |
| 8 | C5 | 20 | BITD/U<5> | SET<8> | BITP/N<8> | BP<8> | CAL<8> |
| 9 | C4 | 12 | BITD/U<4> | SET<9> | BITP/N<9> | BP<9> | CAL<9> |
| 10 | C3 | 8 | BITD/U<3> | SET<10> | BITP/N<10> | BP<10> | CAL<10> |
| 11 | C2 | 4 | BITD/U<2> | SET<11> | BITP/N<11> | BP<11> | CAL<11> |
| 12 | C1 | 2 | BITD/U<1> | SET<12> | BITP/N<12> | BP<12> | CAL<12> |
| 13 | terminal | 1 | 无电容 | SET<13> | terminal | BP<13> | 无 |

正常转换顺序：

```text
16C -> 8C -> 4C -> 2C -> 2C_R -> 1C -> C7 -> C6 -> C5 -> C4 -> C3 -> C2 -> C1 -> terminal
```

对应：

```text
SET<0> -> SET<1> -> SET<2> -> SET<3> -> SET<4> -> SET<5>
       -> SET<6> -> SET<7> -> SET<8> -> SET<9> -> SET<10>
       -> SET<11> -> SET<12> -> SET<13>
```

## 2. 各模块怎么改

### 2.1 CDAC

CDAC 不要重排原来的 C1..C12 端口，继续保持：

```text
BITD<1:13>
BITU<1:13>
```

原电容保持：

```text
C12 -> BITD/U<12>
C11 -> BITD/U<11>
C10 -> BITD/U<10>
C9  -> BITD/U<9>
C8  -> BITD/U<8>
...
C1  -> BITD/U<1>
```

新增 CR：

```text
P top plate -> 2C -> BITD<13>
N top plate -> 2C -> BITU<13>
```

所以你刚才说的判断是对的：**C10 应该接 `BITU<10>`，不能接 `BITU<2>`。**

### 2.2 SWITCH_CAL

当前 `SWITCH_CAL.va` 的端口是：

```text
BITD<1:13>
BITU<1:13>
BITP<0:12>
BITN<0:12>
SET<0:12>
BITD_CAL<0:12>
BITU_CAL<0:12>
```

它内部完成映射：

```text
physical C12 BITD/U<12> <= stage 0
physical C11 BITD/U<11> <= stage 1
physical C10 BITD/U<10> <= stage 2
physical C9  BITD/U<9>  <= stage 3
physical CR  BITD/U<13> <= stage 4
physical C8  BITD/U<8>  <= stage 5
...
physical C1  BITD/U<1>  <= stage 12
```

### 2.3 SAR_LOGIC

SAR_LOGIC 输出按转换顺序编号：

```text
SET<0:13>
BITP<0:12>
BITN<0:12>
```

时序必须是：

```text
SET<0>  C12
SET<1>  C11
SET<2>  C10
SET<3>  C9
SET<4>  CR
SET<5>  C8
SET<6>  C7
SET<7>  C6
SET<8>  C5
SET<9>  C4
SET<10> C3
SET<11> C2
SET<12> C1
SET<13> terminal compare / SOUT
```

`SET<13>` 只用于转换结束，不接 `SWITCH_CAL`。

### 2.4 PN_BUF

PN_BUF 也按 stage-order：

```text
BITP/N<0:12> -> BP/BN<0:12>
terminal compare -> BP<13>
```

也就是说 `BP<2>` 是 C10 决策，不是物理 `BITU<2>`。

### 2.5 DEC_CAL_PHY

`DEC_CAL_PHY.va` 使用 stage-order：

```text
BP<0:13>
BITD_CAL<0:12>
BITU_CAL<0:12>
Bit<11:0>
```

`BP<0:13>` 对应：

```text
BP<0>  C12
BP<1>  C11
BP<2>  C10
BP<3>  C9
BP<4>  CR
BP<5>  C8
...
BP<12> C1
BP<13> terminal
```

FFT/SNDR 仍然读取 `Bit<11:0>`。

注意：`weights_q` 是已经换算到输出 LSB 的 Q 格式权重，最终码值应当按：

```text
code = round(raw_sum / 2^FRAC_BITS)
```

再限幅到 0..4095。不要用 `sum(weights)` 把结果重新归一化到 4095；新增 CR 的 256 LSB 是冗余重叠区，不是新的 ADC 满量程。若用 `4095/sum(weights)` 缩放，理想 MSB-only 码会从 2048 被压到约 1928，输出会明显异常。

## 3. 权重日志

`FRAC_BITS=4` 时，理想 `weights_q` 是：

```text
weights_q={32768,16384,8192,4096,4096,2048,768,512,320,192,128,64,32,16}
```

除以 16 后是：

```text
{2048,1024,512,256,256,128,48,32,20,12,8,4,2,1}
```

顺序是：

```text
C12, C11, C10, C9, CR, C8, C7, C6, C5, C4, C3, C2, C1, terminal
```

## 4. 校准顺序

默认 `CAL_C7=0`：

```text
C9 -> CR -> C10 -> C11 -> C12
```

对应 stage：

```text
3 -> 4 -> 2 -> 1 -> 0
```

`CAL_C7=1` 时：

```text
C7 -> C8 -> C9 -> CR -> C10 -> C11 -> C12
```

对应 stage：

```text
6 -> 5 -> 3 -> 4 -> 2 -> 1 -> 0
```

校准状态机中，`invalid comparator` 不一定代表比较器或接线错误。这个冗余结构有两类本来就可能接近零残差的情况：

```text
C10 = C9 + CR
C11 = C10 + C9 + CR
C12 = C11 + C10 + C9 + CR
```

这些会在 phase0 出现近零比较器输入；另外 C9/CR 对 `C1..C8` 墙的标称残差是 `256 - 254 = 2 LSB`，在 phase1 最后用 C1 半权重搜索时也可能精确命中零。`DEC_CAL_PHY.va` 现在把连续 invalid 的 phase0 记为 `zero-residue`，把连续 invalid 的 phase1 记为 `exact-search-hit`，这两类日志是正常的零残差处理，不应触发 ERR 回退。

## 5. 首次 netlist 检查

只 generate netlist，先检查：

```text
1. CDAC 仍然有 BITD/U<1:13>。
2. C10 接 BITD/U<10>。
3. CR 接 BITD/U<13>。
4. SWITCH_CAL 的 BITD/U 是 <1:13>，BITP/N 是 <0:12>。
5. SAR_LOGIC 的 SET 顺序是 0,1,2,3,4,5,...,13。
6. SET<4> 控制 CR。
7. SET<13> 只作为 terminal/SOUT，不进入 SWITCH_CAL。
8. DEC_CAL_PHY 接 BP<0:13>，且 BP<2> 是 C10 决策。
```
