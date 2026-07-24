# Chen 2024 参考边界

参考文献：

> Chen et al., “A 16-bit 4-MS/s SAR ADC With Dual-Segmental Bit Weight
> Self-Calibration,” IEEE Transactions on Circuits and Systems I, 2024.
> DOI: 10.1109/TCSI.2024.3408228.

本项目只采用下列设计判断，不复制论文电路：

1. 冗余必须按被测位的局部 backend range 检查。论文式条件可写为
   `VREF × (sum(lower weights) - target weight) > |offset| + peak noise`。
2. 最低小电容组可作为匹配基准，从失配开始影响精度的更高位开始校准。
3. 正常转换时，主 CDAC 的高、低段电容都应参与输入采样。
4. conversion redundancy 与 calibration redundancy 应分别核算。

论文没有被复制的部分：

- auxiliary lower-segment comparator；
- 三个 bridge capacitors；
- 16-bit/4-MS/s 数组比例；
- calibration sub-DAC；
- 论文的具体 switching sequence 和时序。

本项目据此选择：

- 一个 2-Cu bridge；
- 138 Cu/side 的 12-bit integer array；
- 一个主比较器；
- 15 次普通异步比较；
- 7 个高段校准目标；
- 普通 P/N weighted-sum decoder。

因此准确表述是“参考 Chen 的冗余核算思想”，不是“复现 Chen 2024”。
