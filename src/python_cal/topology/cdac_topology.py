"""
cdac_topology.py — CDAC 拓扑定义

需求文档 §4: 定义物理电容拓扑。
每侧 CDAC 包含: 低段 6 个, 桥接 1 个, 高段 7 个。
"""

import numpy as np
from dataclasses import dataclass, field
from .capacitor import Capacitor

# ===================================================================
#  物理常量
# ===================================================================

CU = 4e-15          # 单位电容 (F)
VREF = 1.8          # 参考电压 VREFP (V)
VREFN_ = 0.0        # 参考电压 VREFN (V)
VCM = 0.9           # 共模电压 (V)
N_STAGES = 14       # 总阶段数 (含 terminal)
N_PHYSICAL = 13     # 物理电容阶段数 (stage 0..12)
N_BITS = 12         # 输出分辨率


# ===================================================================
#  CDAC 拓扑
# ===================================================================

@dataclass(frozen=True)
class CDACTopology:
    """单侧 CDAC 拓扑 (电容列表 + 桥接定义)"""

    capacitors: tuple[Capacitor, ...]

    # 电容分类索引
    low_capacitors:   tuple[Capacitor, ...] = field(init=False)
    bridge_capacitor: Capacitor = field(init=False)
    high_capacitors:  tuple[Capacitor, ...] = field(init=False)

    # 总电容值
    c_low_total:   float = field(init=False)
    c_high_total:  float = field(init=False)
    c_bridge:      float = field(init=False)

    def __post_init__(self):
        caps = self.capacitors

        # 分类
        low_caps = [c for c in caps if c.name.startswith('low_')]
        bridge_cap = [c for c in caps if c.name == 'bridge'][0]
        high_caps = [c for c in caps if c.name.startswith('high_')]

        object.__setattr__(self, 'low_capacitors',   tuple(low_caps))
        object.__setattr__(self, 'bridge_capacitor', bridge_cap)
        object.__setattr__(self, 'high_capacitors',  tuple(high_caps))

        object.__setattr__(self, 'c_low_total',  sum(c.capacitance_f for c in low_caps))
        object.__setattr__(self, 'c_high_total', sum(c.capacitance_f for c in high_caps))
        object.__setattr__(self, 'c_bridge',     bridge_cap.capacitance_f)

    @property
    def total_capacitance(self) -> float:
        return self.c_low_total + self.c_bridge + self.c_high_total

    def get_cap_by_name(self, name: str) -> Capacitor:
        for c in self.capacitors:
            if c.name == name:
                return c
        raise KeyError(f"Capacitor '{name}' not found")

    def get_cap_by_stage(self, stage: int) -> Capacitor | None:
        if stage == 13:  # terminal
            return None
        for c in self.capacitors:
            if c.stage == stage:
                return c
        return None


def build_cdac_topology(side: str, mismatch: tuple[float, ...] | None = None,
                         caps_override: dict | None = None) -> CDACTopology:
    """构建单侧 CDAC 拓扑

    参数:
        side: 'P' 或 'N'
        mismatch: 高段 7 电容失配因子 [h1c_a, h1c_r, h2c, h4c, h8c, h16c, h32c]
        caps_override: 完整电容值字典 (提供后忽略 mismatch)

    电容规格 (Cu 数量):
      低段: L1C=1, L2C=2, L4C=4, L8C=8, L16C=16, L32C=32
      桥接: CB=2
      高段: H1C-A=1, H1C-R=1, H2C=2, H4C=4, H8C=8, H16C=16, H32C=32
    """
    top = f'VTOP_{side}'
    bridge = f'VBRIDGE_{side}'

    if caps_override is not None:
        cap_dict = caps_override
    else:
        if mismatch is None:
            mismatch = (1.0,) * 7
        mis = {name: factor for name, factor in zip(
            ['high_1c_a', 'high_1c_r', 'high_2c', 'high_4c', 'high_8c', 'high_16c', 'high_32c'],
            mismatch
        )}
        cap_dict = {
            'low_1c': 1 * CU, 'low_2c': 2 * CU, 'low_4c': 4 * CU,
            'low_8c': 8 * CU, 'low_16c': 16 * CU, 'low_32c': 32 * CU,
            'bridge': 2 * CU,
            'high_1c_a': 1 * CU * mis['high_1c_a'],
            'high_1c_r': 1 * CU * mis['high_1c_r'],
            'high_2c':   2 * CU * mis['high_2c'],
            'high_4c':   4 * CU * mis['high_4c'],
            'high_8c':   8 * CU * mis['high_8c'],
            'high_16c': 16 * CU * mis['high_16c'],
            'high_32c': 32 * CU * mis['high_32c'],
        }

    stage_map = {  # cap name → stage
        'high_32c': 0, 'high_16c': 1, 'high_8c':  2, 'high_4c': 3,
        'high_2c':  4, 'high_1c_r': 5, 'high_1c_a': 6,
        'low_32c':  7, 'low_16c': 8, 'low_8c':   9,
        'low_4c':  10, 'low_2c':  11, 'low_1c':  12,
        'bridge': None,
    }

    capacitors = []
    for name in ['low_1c', 'low_2c', 'low_4c', 'low_8c', 'low_16c', 'low_32c',
                  'bridge',
                  'high_1c_a', 'high_1c_r', 'high_2c', 'high_4c', 'high_8c', 'high_16c', 'high_32c']:
        top_node = bridge if name.startswith('low_') or name == 'bridge' else top
        bot_node = f'BOT_{side}_{name}'
        capacitors.append(Capacitor(
            name=name,
            capacitance_f=float(cap_dict[name]),
            top_node=top_node,
            bottom_node=bot_node,
            stage=stage_map[name],
        ))

    return CDACTopology(tuple(capacitors))


def build_differential_topology(md=None, mu=None, p_caps=None, n_caps=None):
    """构建全差分 CDAC 拓扑

    参数:
        md: P 侧高段失配因子 (7个)
        mu: N 侧高段失配因子 (7个)
        p_caps: P 侧完整电容字典 (可选)
        n_caps: N 侧完整电容字典 (可选)

    返回:
        (CDACTopology, CDACTopology)
    """
    p_top = build_cdac_topology('P', mismatch=md, caps_override=p_caps)
    n_top = build_cdac_topology('N', mismatch=mu, caps_override=n_caps)
    return p_top, n_top
