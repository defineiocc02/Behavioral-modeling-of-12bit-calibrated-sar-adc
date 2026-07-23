"""
switch_state.py — 底板开关状态定义

需求文档 §5: 底板开关状态必须显式保存。
每个物理电容必须拥有独立开关状态。
decisions 只能由已提交的实际开关动作派生。
"""

from dataclasses import dataclass
from enum import Enum


class Rail(Enum):
    """底板连接电压轨"""
    VREFP = "vrefp"
    VREFN = "vrefn"
    VCM   = "vcm"
    VINP  = "vinp"
    VINN  = "vinn"
    FLOAT = "float"

    def voltage(self, vrefp=1.8, vrefn=0.0, vcm=0.9, vinp=0.9, vinn=0.9):
        """返回该 Rail 对应的电压值 (V)"""
        mapping = {
            Rail.VREFP: vrefp,
            Rail.VREFN: vrefn,
            Rail.VCM:   vcm,
            Rail.VINP:  vinp,
            Rail.VINN:  vinn,
        }
        return mapping.get(self, 0.0)


@dataclass(frozen=True)
class SideSwitchState:
    """单侧 (P 或 N) CDAC 的全部电容开关状态

    每个字段对应一个物理电容的底板连接。
    """
    low_1c:   Rail = Rail.VCM
    low_2c:   Rail = Rail.VCM
    low_4c:   Rail = Rail.VCM
    low_8c:   Rail = Rail.VCM
    low_16c:  Rail = Rail.VCM
    low_32c:  Rail = Rail.VCM

    high_1c_a: Rail = Rail.VCM
    high_1c_r: Rail = Rail.VCM
    high_2c:   Rail = Rail.VCM
    high_4c:   Rail = Rail.VCM
    high_8c:   Rail = Rail.VCM
    high_16c:  Rail = Rail.VCM
    high_32c:  Rail = Rail.VCM

    # Stage → field name 映射 (对齐需求文档 §8 开关顺序)
    STAGE_TO_FIELD = {
        0:  'high_32c',
        1:  'high_16c',
        2:  'high_8c',
        3:  'high_4c',
        4:  'high_2c',
        5:  'high_1c_r',
        6:  'high_1c_a',
        7:  'low_32c',
        8:  'low_16c',
        9:  'low_8c',
        10: 'low_4c',
        11: 'low_2c',
        12: 'low_1c',
    }

    CAP_NAMES = [
        'low_1c', 'low_2c', 'low_4c', 'low_8c', 'low_16c', 'low_32c',
        'high_1c_a', 'high_1c_r', 'high_2c', 'high_4c', 'high_8c', 'high_16c', 'high_32c',
    ]

    def get_rail(self, cap_name: str) -> Rail:
        """读取指定电容的底板连接"""
        return getattr(self, cap_name)

    def with_rail(self, cap_name: str, rail: Rail) -> 'SideSwitchState':
        """返回修改单个电容底板后的新状态"""
        return SideSwitchState(**{**self.__dict__, cap_name: rail})

    @classmethod
    def all_vcm(cls):
        """所有电容底板接 VCM (复位状态)"""
        return cls()

    @classmethod
    def all_rail(cls, rail: Rail):
        """所有电容底板接同一 Rail"""
        kwargs = {name: rail for name in cls.CAP_NAMES}
        return cls(**kwargs)


@dataclass(frozen=True)
class DifferentialSwitchState:
    """全差分开关状态 (P 侧 + N 侧)"""
    p_side: SideSwitchState = SideSwitchState()
    n_side: SideSwitchState = SideSwitchState()

    @classmethod
    def all_vcm(cls):
        return cls(SideSwitchState.all_vcm(), SideSwitchState.all_vcm())
