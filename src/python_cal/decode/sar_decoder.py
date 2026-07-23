"""
sar_decoder.py — SAR 数字解码器

需求文档 §14: 数字解码与物理转换严格分离。
解码权重更新不得影响物理 decisions。
"""

from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class DecodeResult:
    """解码结果"""
    code: int
    clip_low: bool
    clip_high: bool
    raw_sum: float


class SARDecoder:
    """SAR ADC 数字解码器 (centered decoder)

    需求文档 §14: decoder 权重更新不得影响物理转换。

    解码公式:
      raw_sum = Σ d_i * w_i
      centered = raw_sum - aux_offset
      code = centered * max_code / signal_weight, 然后裁剪到 [0, max_code]
    """

    def __init__(self, weights=None, max_code=4095):
        """
        参数:
            weights: 14 个 Q0 浮点权重 [w0..w13], None = 标称理想权重
            max_code: 最大输出码值 (12-bit = 4095)
        """
        self.max_code = max_code

        if weights is None:
            weights = [
                2080, 1040, 520, 260, 130, 65, 65,  # H32C..H1C-A
                64, 32, 16, 8, 4, 2,                  # L32C..L1C
                1,                                      # terminal
            ]
        self.weights = list(weights)

        # 信号权重 (stage 0-4, 6) = 2080+1040+520+260+130+65 = 4095
        self.signal_stages = [0, 1, 2, 3, 4, 6]
        self.aux_stages = [5, 7, 8, 9, 10, 11, 12, 13]

        self.signal_weight = sum(self.weights[i] for i in self.signal_stages)
        self.aux_weight = sum(self.weights[i] for i in self.aux_stages)
        self.aux_offset = self.aux_weight / 2.0

    def update_weights(self, new_weights):
        """更新解码权重 (不影响物理转换)"""
        self.__init__(weights=new_weights, max_code=self.max_code)

    def decode(self, decisions, clip=True):
        """解码 decisions → ADC code

        参数:
            decisions: 14 个 SAR 决策 (0 或 1)
            clip: 是否裁剪到 [0, max_code]

        返回:
            int: ADC 输出码
        """
        result = self.decode_detailed(decisions)
        code = result.code
        if clip:
            code = max(0, min(self.max_code, code))
        return code

    def decode_detailed(self, decisions) -> DecodeResult:
        """解码并返回详细信息

        SAR decisions 语义 (bottom-plate sampling):
          d=0 → P-side cap 接 VREFP (提高 VTOP_P, 对应正向输入)
          d=1 → N-side cap 接 VREFP (提高 VTOP_N, 对应负向输入)

        signed_sum = Σ (1-2d) * w_i
        signed_sum 的 step = 2 Q0 (因为权重中有 3 个奇数，sum 恒为奇数)
        → 映射到 code [0, max_code] 需要除以 2:
           code = (signed_sum + signal_weight) / 2 * (max_code / signal_weight)
        
        当 max_code == signal_weight 时简化为:
           code = (signed_sum + signal_weight) / 2
        """
        signed_sum = sum((1 - 2 * d) * w for d, w in zip(decisions, self.weights))
        code_float = (signed_sum + self.signal_weight) * self.max_code / (2.0 * self.signal_weight)
        code = int(math.floor(code_float + 0.5))
        clip_low = code < 0
        clip_high = code > self.max_code
        return DecodeResult(
            code=code,
            clip_low=clip_low,
            clip_high=clip_high,
            raw_sum=signed_sum,
        )

    def decode_batch(self, decisions_array):
        """批量解码"""
        codes = np.zeros(len(decisions_array), dtype=np.int32)
        for i, d in enumerate(decisions_array):
            codes[i] = self.decode(list(d))
        return codes
