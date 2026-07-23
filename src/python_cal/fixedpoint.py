"""
fixedpoint.py — 统一定点舍入函数（严格对齐 VA 语义）
======================================================

Verilog-A 关键语义:
  - $rtoi() = 向零截断 (math.trunc)
  - 整数除法 = 向零截断 (trunc_div, 不是 Python 的 //)
  - 解码表达式: $rtoi(scaled_code + 0.5) → 先加 0.5 再向零截断

本模块是所有定点转换的唯一入口。任何地方需要做定点舍入
都必须调用本模块的函数，不得使用 Python 内置 int() 或 //。
"""

import math


def trunc_div(num: int, den: int) -> int:
    """向零截断整数除法 (对齐 Verilog-A 整数除法语义)

    Verilog-A 整数除法是向零截断：
      -3 / 2 → -1 (trunc)
      3 / 2 → 1

    Python // 是向负无穷取整：
      -3 // 2 → -2 (floor)

    示例:
      >>> trunc_div(-3, 2)
      -1
      >>> trunc_div(3, 2)
      1
      >>> trunc_div(-5, 2)
      -2
    """
    if den == 0:
        raise ZeroDivisionError("denominator must not be zero")
    return math.trunc(num / den)


def decode_round_like_va(scaled_code: float) -> int:
    """对齐 VA 表达式 $rtoi(scaled_code + 0.5)

    先加 0.5，再向零截断。这是 VA 解码器第 819 行的精确行为。

    注意：这不是标准的"四舍五入"（ties-to-even 或 ties-away-from-zero），
    而是 $rtoi(x+0.5) 的逐字复现。

    验证表:
      scaled_code   VA $rtoi(x+0.5)   错误 int(x+0.5)   本函数
      -----------   ---------------   ---------------   ------
      -0.4          0                 0                 0
      -0.6          0                 -1                0
      -1.6          -1                -2                -1
      -2.6          -2                -3                -2
      +0.5          1                 1                 1
      +1.5          2                 2                 2
    """
    return math.trunc(scaled_code + 0.5)


def va_aux_center(aux_weight_q: int) -> int:
    """对齐 VA 的辅助位中心偏移 (REdundancy offset)

    VA 代码 (第 804-808 行):
        if (redundancy_offset_q >= 0)
            redundancy_offset_q = (aux_weight_q + 1) / 2;
        else
            redundancy_offset_q = (aux_weight_q - 1) / 2;

    其中整数除法是向零截断。

    正数: (aux_weight_q + 1) // 2 在正数域内与 trunc 等价
    负数: (aux_weight_q - 1) / 2 必须用 trunc_div

    验证表:
      aux_weight_q    VA trunc((w±1)/2)    错误 Python (w-1)//2    本函数
      -------------   ------------------    --------------------    ------
      -2              trunc((-3)/2) = -1    (-3)//2 = -2           -1
      -4              trunc((-5)/2) = -2    (-5)//2 = -3           -2
      +192            96                    96                     96
      0               0                     0                      0
    """
    if aux_weight_q >= 0:
        return trunc_div(aux_weight_q + 1, 2)
    else:
        return trunc_div(aux_weight_q - 1, 2)


def to_q(value: float, frac_bits: int = 6) -> int:
    """浮点数 → Q 定点表示 (向零截断)

    用于将浮点权重转换为 VA 内部 Q6 格式。"""
    scale = 1 << frac_bits
    return math.trunc(value * scale)


def from_q(q_value: int, frac_bits: int = 6) -> float:
    """Q 定点表示 → 浮点数"""
    scale = 1 << frac_bits
    return q_value / scale


def to_q_round(value: float, frac_bits: int = 6) -> int:
    """浮点数 → Q 定点 (四舍五入到最近，ties away from zero)

    使用 $rtoi(x+0.5) 语义。"""
    scale = 1 << frac_bits
    return decode_round_like_va(value * scale)


def decode_va_exact(decisions, weights_q, signal_idx, aux_idx, max_code=4095):
    """与 VA 第 802-829 行 bit-exact 对齐的解码器

    这是 Python 端最底层的解码实现。所有更高层的 decode 调用最终必须
    穿过这个函数（或与之等价的行为）。

    参数:
        decisions: list[int], 14 个 SAR 判决 (0 或 1)
        weights_q: list[int], 14 个 Q6 权重
        signal_idx: list[int], 信号阶段的索引
        aux_idx: list[int], 辅助阶段的索引
        max_code: int, 最大输出码值

    返回:
        tuple: (code, clip_low, clip_high)
    """
    # raw_sum = Σ d_i * w_i
    raw_sum = sum(d * w for d, w in zip(decisions, weights_q))

    # 辅助权重
    aux_w = sum(weights_q[i] for i in aux_idx)

    # 冗余偏移量 (对齐 VA 第 804-808 行)
    offset = va_aux_center(aux_w)

    # 中心化
    centered = raw_sum - offset

    # 信号权重归一化 (始终用标称值 4095×64 = 262080 Q6)
    # 输出码域定义为 0-4095, 归一化分母必须是标称 signal_weight,
    # 不能随失配/校准改变。否则除法压缩+舍入引入 ~3 dB 额外损失。
    from . import config as _cfg
    signal_w_nominal_q = _cfg.SIGNAL_WEIGHT_NOMINAL * _cfg.Q_SCALE
    if signal_w_nominal_q > 0:
        scaled = 4095.0 * centered / signal_w_nominal_q
    else:
        scaled = 0.0

    # VA 舍入 (对齐 VA 第 819 行 $rtoi(scaled_code+0.5))
    code = decode_round_like_va(scaled)

    # clipping (对齐 VA 第 822-824 行)
    clip_low = 0
    clip_high = 0
    if code < 0:
        code = 0
        clip_low = 1
    elif code > max_code:
        code = max_code
        clip_high = 1

    return code, clip_low, clip_high


def decode_va_q2_exact(decisions, weights_q, signal_idx, aux_idx):
    """Q2 分数解码器（可选，用于高精度分析）

    返回 Q2 分数码值 (0..16383)，即 4 倍标准码值。
    用于 Python MC 统计时评估 pair 数不足的 margin。
    归一化分母始终用标称 signal_weight, 不做 gain 压缩。
    """
    raw_sum = sum(d * w for d, w in zip(decisions, weights_q))
    aux_w = sum(weights_q[i] for i in aux_idx)

    offset = va_aux_center(aux_w)
    centered = raw_sum - offset

    from . import config as _cfg
    signal_w_nominal_q = _cfg.SIGNAL_WEIGHT_NOMINAL * _cfg.Q_SCALE
    if signal_w_nominal_q > 0:
        # 16383 = 4*4095 - 1, 对应 Q2 最大码
        scaled = 16383.0 * centered / signal_w_nominal_q
    else:
        scaled = 0.0

    code = decode_round_like_va(scaled)
    clip_low = 0
    clip_high = 0
    if code < 0:
        code = 0
        clip_low = 1
    elif code > 16383:
        code = 16383
        clip_high = 1

    return code, clip_low, clip_high
