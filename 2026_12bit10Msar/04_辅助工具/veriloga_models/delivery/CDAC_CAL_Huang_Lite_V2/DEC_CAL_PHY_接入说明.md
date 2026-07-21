# 物理 CDAC 闭环权重校准模型接入说明

## 1. 交付模块

实际顶层只增加/替换两个模块：

1. `DEC_CAL_PHY`：前景校准状态机、比较器采样、权重寄存器、校准后解码器和比较器时钟选择器。
2. `SWITCH_CAL`：保留原 `SWITCH` 的全部端口和正常开关逻辑，并在 `CAL=1` 时让校准总线直接控制真实 CDAC 的 24 个底板节点。

`CAL_CMP_TB` 只用于独立回归测试。接入顶层时不要放置它，继续使用电路中的真实 `COM_IAZ`。

## 2. 与当前网表一致的原端口

### `SWITCH_CAL` 原端口

以下顺序和 `point1_input.scs` 中的原 `SWITCH` 一致：

```text
AGND AVDD
BITD<1:12> BITN<1:12> BITP<1:12> BITU<1:12>
N P RST RST1 SET<0:11>
VCM VIN VIP VREFN VREFP
```

仅在尾部增加：

```text
BITD_CAL<11:0> BITU_CAL<11:0> CAL
```

校准总线内部映射为：

```text
BITD_CAL<0>  -> BITD<1>     BITU_CAL<0>  -> BITU<1>
...
BITD_CAL<11> -> BITD<12>    BITU_CAL<11> -> BITU<12>
```

因此两个模块之间直接按同名整条总线连接，不需要在顶层逐位交叉连线。原来的 `SET<0:11>`、`BN<1:12>`、`BP<1:12>` 连接保持不变。

### `DEC_CAL_PHY` 端口

```text
output Bit<11:0>
input  BP<12:0>
inout  DGND DVDD
input  SOUT
input  COMP COMN RST1 CAL_RST
input  CLK_SAR CLK00
output CLK
output BITD_CAL<11:0> BITU_CAL<11:0>
output CAL DONE ERR
```

`BP<0>` 对应最终 1 LSB 比较结果；`BP<1>` 至 `BP<12>` 对应物理电容 1 至 12。若实际裸码极性相反，可设置 `RAW_INVERT=1`；若只有首个/最高位判决相反，可设置 `FIRST_INVERT=1`。

当前项目顶层网表已经验证比较器极性需要 `CMP_SWAP=1`，因此交付代码把它设为默认值。独立理想比较器测试台显式设置 `CMP_SWAP=0`。

## 3. 顶层最小改动

1. 用 `DEC_CAL_PHY` 替换当前 `I22/DEC`。原来的 `Bit<0:11>`、`BP<0:12>`、`DGND`、`DVDD`、`SOUT` 接到同名网络。
2. 用 `SWITCH_CAL` 替换当前 `I14/SWITCH`。原有端口和网络全部原样保留，仅连接新增的两条校准总线和 `CAL`。
3. 把原 `SYNC_asnyc` 输出到比较器的 `CLK` 网络在中间断开：
   - `SYNC_asnyc.CLK -> CLK_SAR -> DEC_CAL_PHY.CLK_SAR`
   - `DEC_CAL_PHY.CLK -> COM_IAZ.CLK`
   - 现有 `CLK00 -> DEC_CAL_PHY.CLK00`
4. 真实比较器的 `COMP`、`COMN` 同时接原 SAR 逻辑和 `DEC_CAL_PHY`，只是增加高阻电压检测支路，不改变比较器负载模型。
5. 现有 `RST1` 同时接 `SWITCH_CAL` 和 `DEC_CAL_PHY`。
6. 新增 `CAL_RST`。仿真时先保持高电平，再给下降沿启动一次校准。例如：

```spectre
VCALRST (CAL_RST DGND) vsource type=pulse val0=vdd val1=0 \
    period=1m delay=50n rise=10p fall=10p width=900u
```

7. `DONE`、`ERR` 接测试点并保存波形。`DONE=1, ERR=0` 后才使用 `Bit<11:0>`。

不要把原 `SWITCH` 和 `SWITCH_CAL` 并联放置，否则两个开关网络会同时驱动 CDAC 底板。

## 4. 校准时序

每个校准帧沿用现有 100 ns 周期：

```text
CAL_RST下降：进入校准，CAL=1，比较器时钟选择CLK00
RST1上升：P/N钳位VCM；装载墙电容、目标电容和搜索电容的预充状态
RST1下降：断开P/N钳位；延迟TD_CAL后改变底板，产生待比较残差
CLK00上升：真实COM_IAZ比较P/N
SOUT上升：采样COMP/COMN，更新下一步搜索状态
```

`CAL=1` 时，两根现有控制线的含义为：

| `BITD_CAL` | `BITU_CAL` | 真实 CDAC 底板状态 |
| ---: | ---: | --- |
| 1 | 0 | D/P 侧接 `VREFP`，U/N 侧接 `VREFN` |
| 0 | 1 | D/P 侧接 `VREFN`，U/N 侧接 `VREFP` |
| 0 | 0 | 两侧接 `VCM`，目标之外的电容停用 |
| 1 | 1 | 安全态，两侧接 `VCM` |

被校准的物理电容为 7 至 12。每个目标先做一次残差符号判断，再依次试探低位搜索 DAC 的 `16, 10, 6, 4, 2, 1`，共 7 次比较；D/P 侧和 U/N 侧构成一对正负测量。每个目标完成后，已校准低位会加入搜索墙，再递归测量下一位。

重复次数由 `AVG_LOG2` 设置，正负测量对数为 `2^AVG_LOG2`：

| `AVG_LOG2` | 正负测量对数 | 约校准时间（10 MHz） | 用途 |
| ---: | ---: | ---: | --- |
| 0 | 1 对 | 8.5 µs | 仅用于最快功能冒烟测试，无法平均噪声 |
| 1 | 2 对 | 16.9 µs | 快速连线/时序冒烟测试 |
| 2 | 4 对 | 33.7 µs | 较短仿真 |
| 3 | 8 对 | 67.3 µs | **默认推荐** |
| 4 | 16 对 | 134.5 µs | 高噪声或精度裕量不足时 |
| 5 | 32 对 | 269 µs | 仅作为研究/极端验证选项 |

所以不要求固定使用 16/32 对。对本 12 位、4 fF CDAC，默认 8 对是精度、仿真时间和数字开销之间更合适的折中。`CAL_BYPASS=1` 可完全旁路校准并立即使用名义权重。

重要：重复平均只有在真实比较器噪声或 Spectre transient noise 使阈值附近判决发生统计变化时，才会产生亚内部 LSB 信息。确定性、无噪声仿真中重复同一个判决不会凭空增加分辨率；代码会在临界端点无判决变化时保留名义权重，避免把量化偏差误写入权重。

当前 ADE 的 30 µs 仿真在默认 8 对设置下会在校准尚未结束时停止，因此 `Bit<11:0>` 看起来没有正常输出。只验证校准完成可把 `tran stop` 改为至少 70 µs；若校准后还要采集 128 个 10 MHz 输出样本，建议设为至少 82 µs。

## 5. 校准结果如何被使用

校准不是只做一次数学运算，也没有 `ACT_W*` 之类的隐藏实际权重参数：

1. `DEC_CAL_PHY` 通过 `BITD_CAL/BITU_CAL` 改变外部 CDAC 底板。
2. 真实 CDAC 在 `P/N` 产生残差。
3. 真实 `COM_IAZ` 输出 `COMP/COMN`。
4. 状态机根据比较结果得到 `w7...w12` 并保存在内部权重寄存器；`w0...w6` 是低位搜索基准。
5. 正常转换时，状态机退出 `CAL`，内部时钟选择器恢复 `CLK_SAR`，`SWITCH_CAL` 恢复原 SAR 开关路径。
6. 每次 `SOUT` 到来时，用实测的 `w0...w12` 对 `BP<12:0>` 加权求和，并归一化为 12 位 `Bit<11:0>`。

当前交付默认 `CMP_SWAP=1`，与正在仿真的实际顶层网表一致。如果另一个测试平台的比较器输出定义相反，只改该实例的 `CMP_SWAP` 参数，不需要改线。

## 6. 已完成回归

- Spectre 23.1 编译：0 error，0 warning。
- 默认 8 对、名义 4 fF 分段桥接 CDAC：`DONE=1, ERR=0`，在 67.3001 µs 安全退出校准，Q3 权重等效为
  `{1,2,4,8,12,20,32,48,128,256,512,1024,2048}`。
- 将真实测试网表中物理 `C8` 的 D/P 侧临时增大 10%（U/N 侧保持名义值）后，控制器测得 `w8≈135`，并据此递归更新后续权重。这证明结果来自 `BITD_CAL/BITU_CAL → 真实 CDAC → COMP/COMN` 闭环，而不是在 VA 中写死实际电容权重。

## 7. 模型边界

当前 `SWITCH_CAL` 是系统闭环验证用的开关行为模型，真实 CDAC 与真实比较器仍在环内。完成算法验证后，如果要评估晶体管开关导通电阻、馈通和电荷注入，应把同一 `CAL` 选择关系加入原晶体管级 `SWITCH`：`CAL=0` 走原 `RST/SET/BN/BP` 路径，`CAL=1` 关闭原路径并由 `BITD_CAL/BITU_CAL` 选择 `VREFN/VREFP`。校准控制器 `DEC_CAL_PHY` 不需要改变。

桥电容改为约 `1.02C～1.03C` 是物理 CDAC 的冗余设计建议，不属于 VA 文件自动修改内容。本次交付没有擅自改动原理图电容值；需要在版图/原理图确认参考范围和满量程定义后单独实施。
