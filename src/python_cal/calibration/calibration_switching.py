"""
calibration_switching.py — 校准开关策略

需求文档 33 §5-8: D+/D- 校准通过真实开关完成。

为每个 target 生成 D+ 和 D- 的开关配置:
  D+: 目标电容 P 侧接 VREFP, N 侧接 VCM (正激励)
  D-: 目标电容 P 侧接 VCM, N 侧接 VREFP (负激励)

Wall 电容使用先前已校准的物理开关状态。
calDAC 使用低段电容 (L32C→L1C) 进行残差搜索。
"""
from python_cal.topology.switch_state import (
    Rail, SideSwitchState, DifferentialSwitchState
)


# Stage 到 cap name 的映射
STAGE_TO_CAP = {
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

# calDAC stages (search order: L32C → L1C)
CALDAC_STAGES = [7, 8, 9, 10, 11, 12]


def build_cal_sampling_state() -> DifferentialSwitchState:
    """校准采样状态: 所有电容底板接 VCM (零差分输入)"""
    return DifferentialSwitchState.all_vcm()


def build_target_dplus_state(target_stage: int,
                              wall_stages: list[int],
                              committed_wall_state: DifferentialSwitchState,
                              caldac_state: DifferentialSwitchState
                              ) -> DifferentialSwitchState:
    """D+ 方向: 目标 P 侧接 VREFP, N 侧接 VCM

    参数:
        target_stage: 当前校准目标的 stage
        wall_stages: 已校准的 wall stage 列表
        committed_wall_state: wall 电容的已提交开关状态
        caldac_state: calDAC 低段电容的开关状态

    返回:
        DifferentialSwitchState
    """
    cap_name = STAGE_TO_CAP[target_stage]
    # D+: P 侧目标电容 → VREFP, N 侧 → VCM
    p_state = SideSwitchState.all_vcm().with_rail(cap_name, Rail.VREFP)
    n_state = SideSwitchState.all_vcm()  # N 侧目标电容保持 VCM

    # 应用 wall 电容状态
    for ws in wall_stages:
        wcap = STAGE_TO_CAP[ws]
        p_state = SideSwitchState(**{**p_state.__dict__,
                                     wcap: committed_wall_state.p_side.get_rail(wcap)})
        n_state = SideSwitchState(**{**n_state.__dict__,
                                     wcap: committed_wall_state.n_side.get_rail(wcap)})

    # 应用 calDAC 状态
    for cs in CALDAC_STAGES:
        ccap = STAGE_TO_CAP[cs]
        p_state = SideSwitchState(**{**p_state.__dict__,
                                     ccap: caldac_state.p_side.get_rail(ccap)})
        n_state = SideSwitchState(**{**n_state.__dict__,
                                     ccap: caldac_state.n_side.get_rail(ccap)})

    return DifferentialSwitchState(p_side=p_state, n_side=n_state)


def build_target_dminus_state(target_stage: int,
                               wall_stages: list[int],
                               committed_wall_state: DifferentialSwitchState,
                               caldac_state: DifferentialSwitchState
                               ) -> DifferentialSwitchState:
    """D- 方向: 目标 N 侧接 VREFP, P 侧接 VCM

    参数:
        target_stage: 当前校准目标的 stage
        wall_stages: 已校准的 wall stage 列表
        committed_wall_state: wall 电容的已提交开关状态
        caldac_state: calDAC 低段电容的开关状态

    返回:
        DifferentialSwitchState
    """
    cap_name = STAGE_TO_CAP[target_stage]
    # D-: N 侧目标电容 → VREFP, P 侧 → VCM
    p_state = SideSwitchState.all_vcm()  # P 侧目标电容保持 VCM
    n_state = SideSwitchState.all_vcm().with_rail(cap_name, Rail.VREFP)

    # 应用 wall 电容状态
    for ws in wall_stages:
        wcap = STAGE_TO_CAP[ws]
        p_state = SideSwitchState(**{**p_state.__dict__,
                                     wcap: committed_wall_state.p_side.get_rail(wcap)})
        n_state = SideSwitchState(**{**n_state.__dict__,
                                     wcap: committed_wall_state.n_side.get_rail(wcap)})

    # 应用 calDAC 状态
    for cs in CALDAC_STAGES:
        ccap = STAGE_TO_CAP[cs]
        p_state = SideSwitchState(**{**p_state.__dict__,
                                     ccap: caldac_state.p_side.get_rail(ccap)})
        n_state = SideSwitchState(**{**n_state.__dict__,
                                     ccap: caldac_state.n_side.get_rail(ccap)})

    return DifferentialSwitchState(p_side=p_state, n_side=n_state)


def apply_caldac_trial(current_caldac: DifferentialSwitchState,
                       caldac_step: int,
                       trial: bool) -> DifferentialSwitchState:
    """在 calDAC 上尝试切换一位

    caldac_step: 0=L32C, 1=L16C, ... 5=L1C
    trial=True: P 侧接 VREFP (增加 P 侧电压)
    """
    stage = CALDAC_STAGES[caldac_step]
    cap_name = STAGE_TO_CAP[stage]

    if trial:
        p_new = current_caldac.p_side.with_rail(cap_name, Rail.VREFP)
        n_new = current_caldac.n_side  # N 侧保持 VCM
    else:
        p_new = current_caldac.p_side  # P 侧保持 VCM
        n_new = current_caldac.n_side.with_rail(cap_name, Rail.VREFP)

    return DifferentialSwitchState(p_side=p_new, n_side=n_new)


def commit_caldac_bit(current_caldac: DifferentialSwitchState,
                      caldac_step: int,
                      keep: bool) -> DifferentialSwitchState:
    """提交 calDAC 位: keep=True 保留 trial, keep=False 回退"""
    stage = CALDAC_STAGES[caldac_step]
    cap_name = STAGE_TO_CAP[stage]

    p_rail = current_caldac.p_side.get_rail(cap_name)
    n_rail = current_caldac.n_side.get_rail(cap_name)

    if keep:
        return current_caldac  # 保留 trial 状态
    else:
        # 回退: 将当前 cap 的 P 和 N 都设回 VCM
        p_new = current_caldac.p_side.with_rail(cap_name, Rail.VCM)
        n_new = current_caldac.n_side.with_rail(cap_name, Rail.VCM)
        return DifferentialSwitchState(p_side=p_new, n_side=n_new)
