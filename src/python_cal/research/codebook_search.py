"""
codebook_search.py — 排序码本最近电平搜索 (研究工具)
======================================================

不是"电路的最终方案", 而是将贪心 SAR 的算法上限与物理 DAC 上限
分离的诊断工具。BinarySearchSAR 搜索的不是 DAC 实际情况, 而是
"如果数字逻辑可以做完全排序+LUT, SNDR 能到多少"。

电路实现状态:
  - VA / 实际电路: 固定顺序 signed compare-then-commit SAR
                    (SAR_LOGIC_0716.va)
  - 本模块: 码本枚举 + 排序 + 中点二分 (研究诊断)

本模块不应作为 Entry Gate 或稳定 API 使用。
"""

import numpy as np
from .. import config as cfg
from ..fixedpoint import va_aux_center, to_q, decode_va_exact


class CodebookNearestSearch:
    """排序码本最近电平搜索

    枚举全部 2^14 个 DAC 电平组合, 排序后用二分搜索找到最近电平。

    与 Oracle 最近电平不等价:
      - 如果搜索时比较器无噪声且不做额外中点比较, 与 Oracle 一致
      - 带中点比较时可能因中点不可达而产生微小误差

    参数:
        cdac: DifferentialCDAC 模型
        weights_q0: 解码权重列表 (校准后), None 用标称
        conv_noise_sigma: 比较器噪声 RMS (LSB)
        vfs_v: 满量程电压 VFS (V), 用于 vin→DAC 归一化。None=用 2*VREF
    """

    def __init__(self, cdac, weights_q0=None, conv_noise_sigma=0.15,
                 vfs_v=None):
        self.cdac = cdac
        self.conv_noise_sigma = conv_noise_sigma

        if weights_q0 is None:
            weights_q0 = list(cfg.NOMINAL_WEIGHTS_Q0)
        self.weights_q0 = list(weights_q0)

        # 物理 DAC 权重 (含失配)
        self.dac_weights_q0 = list(cdac.get_physical_weights_q0())

        # DAC 域映射参数
        self._dac_signal_weight = sum(
            self.dac_weights_q0[i] for i in cfg.SIGNAL_STAGES)
        self._dac_aux_weight = sum(
            self.dac_weights_q0[i] for i in cfg.AUX_STAGES)
        self._dac_aux_center = va_aux_center(
            to_q(self._dac_aux_weight, 6)) / cfg.Q_SCALE

        # VFS 归一化 (文档 40 R3): 用实际 VFS 而非 VREF
        if vfs_v is not None and vfs_v > 0:
            self._vfs_v = vfs_v
        else:
            self._vfs_v = 2.0 * cfg.VREF  # fallback: 2*VREF

        # 解码域参数
        self.signal_weight = sum(
            weights_q0[i] for i in cfg.SIGNAL_STAGES)
        self.aux_weight = sum(
            weights_q0[i] for i in cfg.AUX_STAGES)
        self.aux_center = va_aux_center(
            to_q(self.aux_weight, 6)) / cfg.Q_SCALE

        self.n_stages = 14

        # 预计算排序码本
        self._build_codebook()

    def _build_codebook(self):
        """枚举全部 2^14 组合, 排序, 构建 search space"""
        cal_wq = [to_q(w, 6) for w in self.weights_q0]

        levels = []
        codes = []
        for combo in range(1 << self.n_stages):
            decisions = [(combo >> s) & 1 for s in range(self.n_stages)]
            level = sum(d * w for d, w in zip(decisions, self.dac_weights_q0))
            code, _, _ = decode_va_exact(
                decisions, cal_wq,
                cfg.SIGNAL_STAGES, cfg.AUX_STAGES, max_code=4095)
            levels.append(level)
            codes.append(code)

        levels = np.array(levels)
        codes = np.array(codes)

        sort_idx = np.argsort(levels)
        self._sorted_levels = levels[sort_idx]
        self._sorted_codes = codes[sort_idx]
        self._n_levels = len(self._sorted_levels)
        self._n_search_steps = int(np.ceil(np.log2(self._n_levels)))

    def _target_from_vin(self, vin_diff):
        """将差分输入电压映射到 DAC 目标值

        文档 40 R3: 用实际 VFS 而非 2*VREF 做归一化。
        vin_diff ∈ [-VFS, +VFS] → normalized ∈ [0, 1] → DAC target。
        """
        normalized = vin_diff / self._vfs_v + 0.5
        return self._dac_aux_center + normalized * self._dac_signal_weight

    def convert(self, vin_diff, rng=None):
        """执行一次排序码本二分搜索转换

        使用 ceil(log2(N)) 次比较, 末尾做 1 次额外最近邻中点比较。
        """
        target_dac = self._target_from_vin(vin_diff)

        # 二分搜索
        lo, hi = 0, self._n_levels - 1

        for _ in range(self._n_search_steps):
            mid = (lo + hi) // 2
            residue = target_dac - self._sorted_levels[mid]

            if rng is not None and self.conv_noise_sigma > 0:
                residue += rng.normal(0, self.conv_noise_sigma)

            if residue > 0:
                lo = mid + 1
            else:
                hi = mid

            if lo >= hi:
                break

        # 末尾: lo 和 lo-1 中取最近 (1 次额外中点比较)
        if lo > 0:
            mid_level = (self._sorted_levels[lo] +
                         self._sorted_levels[lo - 1]) / 2.0
            residue = target_dac - mid_level
            if rng is not None and self.conv_noise_sigma > 0:
                residue += rng.normal(0, self.conv_noise_sigma)
            if residue > 0:
                code = int(self._sorted_codes[lo])
            else:
                code = int(self._sorted_codes[lo - 1])
        else:
            code = int(self._sorted_codes[lo])

        code = max(0, min(4095, code))

        return {
            'decisions': None,
            'code': code,
            'clip_low': 1 if code == 0 else 0,
            'clip_high': 1 if code == 4095 else 0,
            'raw_sum': 0.0,
            'centered_sum': 0.0,
        }

    def convert_batch(self, vin_samples, rng=None, return_codes_only=True):
        """批量转换"""
        codes = np.zeros(len(vin_samples), dtype=np.int32)
        clip_low_total = 0
        clip_high_total = 0

        for i, vin in enumerate(vin_samples):
            result = self.convert(vin, rng=rng)
            codes[i] = result['code']
            clip_low_total += result['clip_low']
            clip_high_total += result['clip_high']

        if return_codes_only:
            return codes
        else:
            return codes, clip_low_total, clip_high_total, []


    def verify_residual_advantage(self, vin_samples, sar_decisions,
                                  sar_decoder=None):
        """逐样本残差优势断言 (文档 40 R3)

        对每个输入, 比较 codebook 最近电平残差与固定 SAR 残差:
            |codebook_residual| ≤ |fixed_sar_residual| + 1e-12

        由于 codebook 是穷举最优搜索, SAR 是贪心, 不等式必然成立。
        若违反 → codebook 的 decision→decoder 映射有误。

        参数:
            vin_samples: array[N] 差分输入电压
            sar_decisions: list[N] of list[14] SAR 判决
            sar_decoder: SARDecoder 实例 (用于计算 SAR 残差)

        返回:
            dict: {"pass": bool, "violations": int, "max_advantage": float}
        """
        if sar_decoder is None:
            from ..decode.sar_decoder import SARDecoder
            sar_decoder = SARDecoder()

        violations = 0
        max_advantage = 0.0  # SAR 残差 - codebook 残差 (应为正)

        for vin, decisions in zip(vin_samples, sar_decisions):
            # SAR code & residual
            code_sar = sar_decoder.decode(decisions, clip=True)
            target = self._target_from_vin(vin)
            dac_sar = self._dac_level_for_code(code_sar)
            residual_sar = abs(target - dac_sar)

            # Codebook code & residual
            cb_result = self.convert(vin, rng=None)
            code_cb = cb_result["code"]
            dac_cb = self._dac_level_for_code(code_cb)
            residual_cb = abs(target - dac_cb)

            advantage = residual_sar - residual_cb
            if advantage > max_advantage:
                max_advantage = advantage

            if residual_cb > residual_sar + 1e-12:
                violations += 1

        return {
            "pass": violations == 0,
            "violations": violations,
            "total": len(vin_samples),
            "max_advantage_dac_q0": round(max_advantage, 9),
        }

    def _dac_level_for_code(self, code):
        """查找 code 对应的 DAC 电平 (物理 Q0 域)"""
        idx = np.searchsorted(self._sorted_codes, code, side='left')
        if idx < len(self._sorted_codes) and self._sorted_codes[idx] == code:
            return self._sorted_levels[idx]
        # 未精确匹配: 返回最近电平
        if idx == 0:
            return self._sorted_levels[0]
        if idx >= len(self._sorted_levels):
            return self._sorted_levels[-1]
        lo = self._sorted_levels[idx - 1]
        hi = self._sorted_levels[idx]
        return lo if (code - self._sorted_codes[idx - 1]) <= (self._sorted_codes[idx] - code) else hi


# 向后兼容别名 (deprecated, 下一版删除)
BinarySearchSAR = CodebookNearestSearch
