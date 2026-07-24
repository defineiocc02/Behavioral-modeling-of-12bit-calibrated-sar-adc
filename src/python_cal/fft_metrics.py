"""
fft_metrics.py — 统一的 FFT 性能度量模块

单一真源 (single source of truth)。所有管线脚本必须从此 import，
禁止各自复制本地版本。

项目唯一签核模式:
  - 相干采样
  - 矩形窗（不作 taper）
  - 已知 signal bin
  - 单 bin 信号功率，ENBW=1.0

用法:
    from python_cal.fft_metrics import compute_fft_coherent

    # 相干采样（项目唯一签核协议）
    result = compute_fft_coherent(codes, n_bits=12, n_fft=4096, signal_bin=127)
    print(result["sndr_db"], result["sfdr_db"], result["enob"])
"""
import numpy as np
import math

FFT_WINDOW = "rectangular"
FFT_ENBW_BINS = 1.0


def compute_fft_metrics(digital_codes, n_bits=12, n_fft=None,
                        signal_bin_known=None):
    """按项目相干矩形窗协议计算 ADC 的 SNDR/SFDR/ENOB。

    ``signal_bin_known`` 必须显式给出。未知频率或非相干数据不属于签核
    协议，应先重新生成相干 stimulus，而不是在这里隐式切换窗函数。

    Parameters
    ----------
    digital_codes : array-like
        ADC 输出码 (整数或浮点), 已解码。
    n_bits : int
        ADC 位数, 用于确定满量程。仅作参考，不影响 SNDR 计算。
    n_fft : int, optional
        FFT 点数, 默认取 len(digital_codes)。
    signal_bin_known : int
        已知相干采样信号 bin。

    Returns
    -------
    dict
        {"sndr_db": float, "sfdr_db": float, "enob": float, "signal_bin": int}
    """
    codes = np.asarray(digital_codes, dtype=np.float64)
    if n_fft is None:
        n_fft = len(codes)
    if signal_bin_known is None:
        raise ValueError(
            "signal_bin_known is required: project FFT sign-off uses a "
            "coherent tone and rectangular window"
        )
    if len(codes) < n_fft:
        raise ValueError(
            f"need at least n_fft={n_fft} codes, got {len(codes)}"
        )
    signal_bin = int(signal_bin_known)
    if not 0 < signal_bin < n_fft // 2:
        raise ValueError("signal_bin_known must lie in the positive rFFT band")

    # 去均值 (去除 DC)
    codes_centered = codes[:n_fft] - np.mean(codes[:n_fft])

    # 矩形窗等价于不作 taper；coherent gain=1，ENBW=1 bin。
    spectrum = np.fft.rfft(codes_centered) / n_fft
    spectrum_mag = np.abs(spectrum)
    spectrum_pow = spectrum_mag ** 2

    # 相干矩形窗：载波只占一个 bin。
    signal_power = spectrum_pow[signal_bin]

    # 噪声功率：只排除 DC、载波和单-bin 谐波。邻近 bin 仍是噪声，
    # 不能用宽保护带把它们从 SNDR 中删掉。
    noise_mask = np.ones(len(spectrum_pow), dtype=bool)
    noise_mask[0] = False
    noise_mask[signal_bin] = False

    # 谐波功率 H2-H7
    harmonic_power = 0.0
    for h in range(2, 8):
        harm_bin = signal_bin * h
        if harm_bin >= n_fft:
            harm_bin %= n_fft
        if harm_bin > n_fft // 2:
            harm_bin = n_fft - harm_bin
        if 0 < harm_bin < len(spectrum_pow):
            harmonic_power += spectrum_pow[harm_bin]
            noise_mask[harm_bin] = False

    noise_power = np.sum(spectrum_pow[noise_mask])

    # SNDR = Signal / (Noise + Distortion)
    total_error = noise_power + harmonic_power
    if signal_power <= 0 or total_error <= 0:
        return {"sndr_db": -999.0, "sfdr_db": -999.0,
                "enob": 0.0, "signal_bin": int(signal_bin),
                "window": FFT_WINDOW, "enbw_bins": FFT_ENBW_BINS}

    sndr = 10.0 * math.log10(signal_power / total_error)

    # SFDR: 最大杂散必须包含谐波。不能复用 noise_mask，因为该 mask
    # 为噪声积分排除了 H2-H7，复用会系统性高估 SFDR。
    sfdr_mask = np.ones(len(spectrum_mag), dtype=bool)
    sfdr_mask[0] = False
    sfdr_mask[signal_bin] = False
    peak_spur = np.max(spectrum_mag[sfdr_mask]) if np.any(sfdr_mask) else 0
    sfdr = 20.0 * math.log10(spectrum_mag[signal_bin] / (peak_spur + 1e-30))

    # ENOB = (SNDR - 1.76) / 6.02
    enob = (sndr - 1.76) / 6.02

    return {
        "sndr_db": round(sndr, 3),
        "sfdr_db": round(sfdr, 3),
        "enob": round(enob, 3),
        "signal_bin": int(signal_bin),
        "window": FFT_WINDOW,
        "enbw_bins": FFT_ENBW_BINS,
    }


def compute_fft_coherent(codes, n_bits=12, n_fft=4096, signal_bin=127):
    """相干采样 FFT 快捷接口（矩形窗，ENBW=1 bin）。

    等价于 compute_fft_metrics(codes, n_bits, n_fft, signal_bin_known=signal_bin).
    """
    return compute_fft_metrics(codes, n_bits=n_bits, n_fft=n_fft,
                               signal_bin_known=signal_bin)
