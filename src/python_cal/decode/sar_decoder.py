"""
sar_decoder.py — SAR 数字解码器

需求文档 §14: 数字解码与物理转换严格分离。
解码权重更新不得影响物理 decisions。

GPT 建议: P/N 分侧 decoder。
  d=0 → +W_P (P 侧贡献)
  d=1 → -W_N (N 侧贡献)
  code = (signed_sum + signal_n) * max_code / (signal_p + signal_n)
"""
from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class DecodeResult:
    """解码结果"""
    code: int
    code_float: float
    clip_low: bool
    clip_high: bool
    raw_sum: float


class SARDecoder:
    """SAR ADC 数字解码器 (分侧 centered decoder)

    需求文档 §14: decoder 权重更新不得影响物理转换。
    GPT 建议: P/N 分侧 — wp for d=0, wn for d=1。

    解码公式:
      signed_sum = Σ (wp_i if d_i==0 else -wn_i)
      total_range = signal_p + signal_n
      code = (signed_sum + signal_n) * max_code / total_range, 裁剪到 [0, max_code]

    对称时 signal_p == signal_n, 退化为原公式。
    """

    def __init__(self, weights_p=None, weights_n=None, max_code=4095,
                 weights=None):
        """
        参数:
            weights_p: 14 个 P 侧 Q0 浮点权重 [w0..w13], None = 标称
            weights_n: 14 个 N 侧 Q0 浮点权重 [w0..w13], None = 标称
            max_code: 最大输出码值 (12-bit = 4095)
        """
        if weights is not None:
            if weights_p is not None or weights_n is not None:
                raise ValueError("use either weights or weights_p/weights_n")
            weights_p = weights
            weights_n = weights
        self.max_code = max_code

        nominal = [
            2080, 1040, 520, 260, 130, 65, 65,  # H32C..H1C-A
            64, 32, 16, 8, 4, 2,                  # L32C..L1C
            1,                                      # terminal
        ]
        self.weights_p = list(weights_p) if weights_p is not None else list(nominal)
        self.weights_n = list(weights_n) if weights_n is not None else list(nominal)

        # 信号阶段 (stage 0-4, 6)
        self.signal_stages = [0, 1, 2, 3, 4, 6]
        self.aux_stages = [5, 7, 8, 9, 10, 11, 12, 13]

        self.signal_p = sum(self.weights_p[i] for i in self.signal_stages)
        self.signal_n = sum(self.weights_n[i] for i in self.signal_stages)

        # 兼容旧接口: 均值权重
        self.weights = [(wp + wn) / 2.0 for wp, wn in zip(self.weights_p, self.weights_n)]
        self.signal_weight = sum(self.weights[i] for i in self.signal_stages)
        self.aux_weight = sum(self.weights[i] for i in self.aux_stages)
        self.aux_offset = self.aux_weight / 2.0

    def update_weights(self, new_weights):
        """更新解码权重 (兼容旧接口, 对称权重)"""
        self.__init__(weights_p=new_weights, weights_n=new_weights, max_code=self.max_code)

    def update_weights_per_side(self, weights_p, weights_n):
        """更新解码权重 (分侧)"""
        self.__init__(weights_p=weights_p, weights_n=weights_n, max_code=self.max_code)

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

    def decode_float(self, decisions, clip=True) -> float:
        """返回未做第二次整数舍入的重构码。

        SAR 比较器已经完成一次量化。校准权重通常是分数值；若再强制
        舍入到整数码，会额外加入约 1/12 LSB² 的量化噪声。此接口用于
        算法 oracle 与浮点参考，不代表增加物理比较次数。
        """
        code_float, _ = self._decode_code_float(decisions)
        if clip:
            code_float = max(0.0, min(float(self.max_code), code_float))
        return float(code_float)

    def decode_q(self, decisions, fractional_bits=2, clip=True) -> int:
        """返回带 ``fractional_bits`` 个保留小数位的定点整数。

        例如 ``fractional_bits=2`` 时，返回值除以 4 即 ADC 码值。
        Q2 只扩展数字累加/输出精度，不改变 12-bit CDAC 或转换周期数。
        """
        if fractional_bits < 0:
            raise ValueError("fractional_bits must be non-negative")
        scale = 1 << fractional_bits
        code_float, _ = self._decode_code_float(decisions)
        code_q = int(math.floor(code_float * scale + 0.5))
        if clip:
            code_q = max(0, min(self.max_code * scale, code_q))
        return code_q

    def decode_fixed(self, decisions, fractional_bits=2, clip=True) -> float:
        """返回定点量化后的普通码值（Q2 默认步长为 0.25 LSB）。"""
        scale = 1 << fractional_bits
        return self.decode_q(decisions, fractional_bits, clip) / scale

    def _decode_code_float(self, decisions) -> tuple[float, float]:
        if len(decisions) != len(self.weights_p):
            raise ValueError(
                f"expected {len(self.weights_p)} decisions, got {len(decisions)}"
            )
        signed_sum = 0.0
        for d, wp, wn in zip(decisions, self.weights_p, self.weights_n):
            if d == 0:
                signed_sum += wp
            elif d == 1:
                signed_sum -= wn
            else:
                raise ValueError(f"decision must be 0 or 1, got {d!r}")

        total_range = self.signal_p + self.signal_n
        if total_range <= 0:
            raise ValueError("decoder signal range must be positive")
        code_float = (
            (signed_sum + self.signal_n) * self.max_code / total_range
        )
        return float(code_float), float(signed_sum)

    def decode_detailed(self, decisions) -> DecodeResult:
        """解码并返回详细信息

        SAR decisions 语义 (bottom-plate sampling):
          d=0 → P-side cap 接 VREFP (提高 VTOP_P, +W_P 贡献)
          d=1 → N-side cap 接 VREFP (提高 VTOP_N, -W_N 贡献)

        signed_sum = Σ (wp_i if d_i==0 else -wn_i)
        范围: [-signal_n, +signal_p]
        映射: code = (signed_sum + signal_n) * max_code / (signal_p + signal_n)

        对称时 signal_p == signal_n, 退化为:
          code = (signed_sum + signal_weight) * max_code / (2 * signal_weight)
        """
        code_float, signed_sum = self._decode_code_float(decisions)
        code = int(math.floor(code_float + 0.5))
        clip_low = code < 0
        clip_high = code > self.max_code
        return DecodeResult(
            code=code,
            code_float=code_float,
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


class CentroidLUTDecoder:
    """Transition-centroid LUT 解码器 (P1)

    基于转换阈值查找表 (LUT) 实现最优重构:
      - 使用二分搜索或直接查表确定 code
      - 重构值 = transition centroid = (T_k + T_{k+1}) / 2
      - 最小化量化误差 MSE

    LUT 格式:
      transitions[k] = 使 code >= k 的最小输入电压 (k=0..N+1)
      其中 transitions[0] = -VFS, transitions[N+1] = +VFS
    """

    def __init__(self, transitions: list[float], max_code: int = 4095):
        """
        参数:
            transitions: transition thresholds [T_0, T_1, ..., T_{N+1}]
            max_code: 最大输出码
        """
        self.max_code = max_code
        self.transitions = np.array(transitions, dtype=np.float64)
        self._vfs_neg = float(transitions[0])
        self._vfs_pos = float(transitions[-1])
        self._span = self._vfs_pos - self._vfs_neg

    def decode_voltage(self, voltage: float) -> float:
        """输入电压 → 重构值（centroid）

        查表确定 code，然后返回对应 transition centroid。
        """
        # 二分查找 transition
        idx = int(np.searchsorted(self.transitions[1:-1], voltage))
        code = max(0, min(idx, self.max_code))

        t0 = self.transitions[code]
        t1 = self.transitions[code + 1]
        return (t0 + t1) / 2.0

    def decode(self, voltage: float) -> int:
        """输入电压 → code"""
        idx = int(np.searchsorted(self.transitions[1:-1], voltage))
        return max(0, min(idx, self.max_code))

    def decode_from_code(self, nominal_code: int) -> float:
        """从 nominal code 获取 centroid 重构值"""
        c = max(0, min(nominal_code, self.max_code))
        t0 = self.transitions[c]
        t1 = self.transitions[c + 1]
        return (t0 + t1) / 2.0

    def decode_batch(self, voltages) -> np.ndarray:
        """批量 voltage → centroid 重构值"""
        voltages = np.asarray(voltages, dtype=np.float64)
        indices = np.searchsorted(self.transitions[1:-1], voltages)
        codes = np.clip(indices, 0, self.max_code)
        centroids = np.array([
            (self.transitions[c] + self.transitions[c + 1]) / 2.0
            for c in codes
        ])
        return centroids

    def decode_batch_codes(self, voltages) -> np.ndarray:
        """批量 voltage → integer codes"""
        voltages = np.asarray(voltages, dtype=np.float64)
        indices = np.searchsorted(self.transitions[1:-1], voltages)
        return np.clip(indices, 0, self.max_code).astype(np.int32)
