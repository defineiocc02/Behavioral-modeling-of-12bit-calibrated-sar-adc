"""
fft_metrics.py — 统一的 FFT 性能度量模块

单一真源 (single source of truth)。所有管线脚本必须从此 import，
禁止各自复制本地版本。

支持两种模式:
  - 矩形窗 (signal_bin_known 指定): 用于相干采样, 单 bin 信号功率
  - Hann 窗 (signal_bin_known=None): 用于非相干采样, 多 bin 积分

用法:
    from python_cal.fft_metrics import compute_fft_metrics, compute_fft_coherent

    # 相干采样 (推荐)
    result = compute_fft_coherent(codes, n_bits=12, n_fft=4096, signal_bin=127)
    print(result["sndr_db"], result["sfdr_db"], result["enob"])

    # 通用接口
    result = compute_fft_metrics(codes, n_bits=12, n_fft=4096, signal_bin_known=127)
"""
import numpy as np
import math


def compute_fft_metrics(digital_codes, n_bits=12, n_fft=None,
                        signal_bin_known=None):
    """从 ADC codes 计算 SNDR/SFDR/ENOB.

    矩形窗模式 (signal_bin_known 指定): 相干采样, 单 bin 信号功率, ENBW=1.0
    Hann 窗模式 (signal_bin_known=None):  非相干采样, ±1 bin 信号积分, ENBW=1.5

    Parameters
    ----------
    digital_codes : array-like
        ADC 输出码 (整数或浮点), 已解码。
    n_bits : int
        ADC 位数, 用于确定满量程。仅作参考，不影响 SNDR 计算。
    n_fft : int, optional
        FFT 点数, 默认取 len(digital_codes)。
    signal_bin_known : int, optional
        已知相干采样信号 bin。若为 None 则自动检测并使用 Hann 窗。

    Returns
    -------
    dict
        {"sndr_db": float, "sfdr_db": float, "enob": float, "signal_bin": int}
    """
    codes = np.asarray(digital_codes, dtype=np.float64)
    if n_fft is None:
        n_fft = len(codes)

    # 去均值 (去除 DC)
    codes_centered = codes[:n_fft] - np.mean(codes[:n_fft])

    if signal_bin_known is not None:
        # ---- 矩形窗模式（相干采样） ----
        window = np.ones(n_fft)
        coherent_gain = 1.0
        enbw = 1.0
        signal_bin = signal_bin_known
    else:
        # ---- Hann 窗模式（非相干采样） ----
        window = np.hanning(n_fft)
        coherent_gain = np.mean(window)
        enbw = 1.5
        signal_bin = None

    # 加窗 + FFT + coherent gain 归一化
    windowed = codes_centered * window
    spectrum = np.fft.rfft(windowed) / n_fft
    if coherent_gain > 1e-12:
        spectrum /= coherent_gain
    spectrum_mag = np.abs(spectrum)
    spectrum_pow = spectrum_mag ** 2

    # 信号 bin 检测 (Hann 模式)
    if signal_bin is None:
        signal_bin = int(np.argmax(spectrum_pow[1:]) + 1)

    # 信号功率
    if signal_bin_known is not None:
        signal_power = spectrum_pow[signal_bin]
    else:
        lo = max(1, signal_bin - 1)
        hi = min(len(spectrum_pow) - 1, signal_bin + 1)
        signal_power = np.sum(spectrum_pow[lo:hi + 1])

    # 噪声功率: 排除 DC、信号 bin±span、谐波 bin±span (H1~H7)
    exclude_span = 2 if signal_bin_known is not None else 3
    noise_mask = np.ones(len(spectrum_pow), dtype=bool)
    noise_mask[0] = False  # DC
    for h in range(7):
        harm_bin = signal_bin * (h + 1)
        if harm_bin >= len(spectrum_pow):
            break
        lo = max(1, harm_bin - exclude_span)
        hi = min(len(spectrum_pow) - 1, harm_bin + exclude_span)
        noise_mask[lo:hi + 1] = False
    noise_power = np.sum(spectrum_pow[noise_mask]) * enbw

    # 谐波功率 H2-H7
    harmonic_power = 0.0
    for h in range(2, 8):
        harm_bin = signal_bin * h
        if harm_bin >= len(spectrum_pow):
            break
        if signal_bin_known is not None:
            harmonic_power += spectrum_pow[harm_bin]
        else:
            lo = max(1, harm_bin - 1)
            hi = min(len(spectrum_pow) - 1, harm_bin + 1)
            harmonic_power += np.sum(spectrum_pow[lo:hi + 1])

    # SNDR = Signal / (Noise + Distortion)
    total_error = noise_power + harmonic_power
    if signal_power <= 0 or total_error <= 0:
        return {"sndr_db": -999.0, "sfdr_db": -999.0,
                "enob": 0.0, "signal_bin": int(signal_bin) if signal_bin else 0}

    sndr = 10.0 * math.log10(signal_power / total_error)

    # SFDR: 最大杂散必须包含谐波。不能复用 noise_mask，因为该 mask
    # 为噪声积分排除了 H2-H7，复用会系统性高估 SFDR。
    sfdr_mask = np.ones(len(spectrum_mag), dtype=bool)
    sfdr_mask[0] = False
    sfdr_lo = max(1, signal_bin - exclude_span)
    sfdr_hi = min(len(spectrum_mag) - 1, signal_bin + exclude_span)
    sfdr_mask[sfdr_lo:sfdr_hi + 1] = False
    peak_spur = np.max(spectrum_mag[sfdr_mask]) if np.any(sfdr_mask) else 0
    sfdr = 20.0 * math.log10(spectrum_mag[signal_bin] / (peak_spur + 1e-30))

    # ENOB = (SNDR - 1.76) / 6.02
    enob = (sndr - 1.76) / 6.02

    return {
        "sndr_db": round(sndr, 3),
        "sfdr_db": round(sfdr, 3),
        "enob": round(enob, 3),
        "signal_bin": int(signal_bin),
    }


def compute_fft_coherent(codes, n_bits=12, n_fft=4096, signal_bin=127):
    """相干采样 FFT 快捷接口 (矩形窗).

    等价于 compute_fft_metrics(codes, n_bits, n_fft, signal_bin_known=signal_bin).
    """
    return compute_fft_metrics(codes, n_bits=n_bits, n_fft=n_fft,
                               signal_bin_known=signal_bin)
