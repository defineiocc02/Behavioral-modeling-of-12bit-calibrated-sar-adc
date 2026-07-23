"""
dynamic_comparator.py — 动态比较器

需求文档 §9: 实现动态比较器, 至少支持:
  - 输入失调
  - 输入等效噪声
  - 有限决策时间
  - 差分越小, 决策越慢
  - metastability threshold
  - 最大等待时间

比较器极性 (固定):
  output = 1 ⇔ VTOP_P > VTOP_N

决策时间模型:
  t_decision = t0 + τ * ln(V_logic / max(|Vdiff + V_offset + V_noise|, V_min))
"""

import math
import numpy as np

from .comparator_result import ComparatorResult


class DynamicComparator:
    """动态比较器

    参数:
        t0_s: 基础延迟 (s)
        tau_s: 再生时间常数 (s)
        v_logic: 逻辑摆幅 (V)
        v_min: 最小有效差分 (V), 低于此值触发 metastability
        offset_v: 输入失调电压 (V)
        noise_sigma_v: 输入等效噪声 RMS (V)
        max_wait_s: 最大等待时间 (s), 超时后强制输出
        rng_seed: 噪声随机种子
    """

    def __init__(self, t0_s=2e-9, tau_s=0.5e-9, v_logic=0.9,
                 v_min=1e-6, offset_v=0.0, noise_sigma_v=0.0,
                 max_wait_s=10e-9, rng_seed=None):
        self.t0_s = t0_s
        self.tau_s = tau_s
        self.v_logic = v_logic
        self.v_min = v_min
        self.offset_v = offset_v
        self.noise_sigma_v = noise_sigma_v
        self.max_wait_s = max_wait_s
        self._rng = np.random.default_rng(rng_seed)

    def request(self, vtop_p: float, vtop_n: float,
                request_time_s: float = 0.0,
                rng: np.random.Generator | None = None
                ) -> ComparatorResult:
        """发起一次比较

        参数:
            vtop_p, vtop_n: 顶板电压 (V)
            request_time_s: 请求时间 (用于事件时间线)
            rng: 外部随机数生成器 (优先于内部 rng)

        返回:
            ComparatorResult
        """
        r = rng if rng is not None else self._rng

        # 差分输入 + 失调 + 噪声
        vdiff_raw = vtop_p - vtop_n
        v_noise = r.normal(0, self.noise_sigma_v) if self.noise_sigma_v > 0 else 0.0
        vdiff_eff = vdiff_raw + self.offset_v + v_noise

        # 亚稳态检测
        abs_veff = abs(vdiff_eff)
        metastable = abs_veff < self.v_min

        # 决策时间
        if metastable or abs_veff == 0:
            decision_time = self.max_wait_s
        else:
            arg = self.v_logic / max(abs_veff, self.v_min)
            decision_time = self.t0_s + self.tau_s * math.log(arg)
            decision_time = min(decision_time, self.max_wait_s)

        # 极性: 1 ⇔ VTOP_P > VTOP_N
        output = 1 if vdiff_eff > 0 else 0

        return ComparatorResult(
            output=output,
            differential_v=vdiff_raw,
            decision_time_s=decision_time,
            metastable=metastable,
        )
