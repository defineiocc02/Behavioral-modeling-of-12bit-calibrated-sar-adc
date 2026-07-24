"""
switching_policy.py — 差分开关策略

需求文档 §8: 实现明确的开关策略。
All fourteen high/low capacitors participate in normal conversion.

SAR 开关策略 (compare-then-commit):
  1. 采样阶段: 信号电容底板接对应输入, 其余接 VCM
  2. 复位阶段: 全部底板接 VCM
  3. trial 状态: 当前 stage 电容底板试探性接到 VREFP 或 VREFN
  4. commit: 比较器 output=1 → 保留 N侧到VREF, P侧回VCM
             output=0 → 保留 P侧到VREF, N侧回VCM

比较器极性 (固定):
  output = 1 ⇔ VTOP_P > VTOP_N
"""

from .switch_state import (
    Rail, SideSwitchState, DifferentialSwitchState
)


class DifferentialSwitchingPolicy:
    """全差分 SAR 开关策略

    固定规则:
      - stage 0..6: high segment (including the duplicate 8-Cu branch)
      - stage 7..13: low segment (including the duplicate 2-Cu branch)
      - stage 14: comparator-only terminal decision

    比较器极性 (固定, 需求文档 §9):
      output = 1 ⇔ VTOP_P > VTOP_N
    """

    # Stage → cap name (固定顺序)
    STAGE_TO_CAP = SideSwitchState.STAGE_TO_FIELD

    def __init__(self, vcm_volt=0.9, vrefp=1.8, vrefn=0.0):
        self.vcm_volt = vcm_volt
        self.vrefp = vrefp
        self.vrefn = vrefn

    # ---- 采样阶段 ----

    def sampling_state(self, vinp: float, vinn: float) -> DifferentialSwitchState:
        """采样阶段开关状态

        Every physical high/low bottom plate samples its side input.
        """
        p_side = _make_side_sampling('P')
        n_side = _make_side_sampling('N')
        return DifferentialSwitchState(p_side=p_side, n_side=n_side)

    # ---- 复位阶段 ----

    def reset_state(self) -> DifferentialSwitchState:
        """复位: 全部底板接 VCM"""
        return DifferentialSwitchState.all_vcm()

    # ---- trial 状态 ----

    def trial_state(self, stage: int,
                    committed_state: DifferentialSwitchState
                    ) -> DifferentialSwitchState:
        """生成试探性开关状态

        trial: P 侧当前电容接 VREFP, N 侧当前电容也接 VREFP。
        比较器结果决定保留哪一侧:
          output=1 (P>N) → 保留 N侧VREFP, P侧回VCM (降低 Vdiff)
          output=0 (P<N) → 保留 P侧VREFP, N侧回VCM (提高 Vdiff)
        """
        if stage == 14:
            # 终端位由比较器对残差再判一次，不存在对应物理电容。
            return committed_state
        cap_name = self.STAGE_TO_CAP[stage]
        p_trial = committed_state.p_side.with_rail(cap_name, Rail.VREFP)
        n_trial = committed_state.n_side.with_rail(cap_name, Rail.VREFP)
        return DifferentialSwitchState(p_side=p_trial, n_side=n_trial)

    # ---- commit ----

    def commit_state(self, stage: int,
                     committed_state: DifferentialSwitchState,
                     trial_state: DifferentialSwitchState,
                     comparator_output: int,
                     ) -> DifferentialSwitchState:
        """根据比较器结果提交开关

        比较器 output = 1 (VTOP_P > VTOP_N):
          P 侧电容回 VCM (不保留), N 侧电容保留 VREFP
          → Vdiff 减小

        比较器 output = 0 (VTOP_P < VTOP_N):
          P 侧电容保留 VREFP, N 侧电容回 VCM
          → Vdiff 增大
        """
        if stage == 14:
            return committed_state
        cap_name = self.STAGE_TO_CAP[stage]

        if comparator_output == 1:
            # P > N: 降低 Vdiff → N 侧保留 VREFP, P 侧回 VCM
            p_new = committed_state.p_side  # P 侧不变 (保持 VCM)
            n_new = trial_state.n_side       # N 侧保留 VREFP
        else:
            # P < N: 提高 Vdiff → P 侧保留 VREFP, N 侧回 VCM
            p_new = trial_state.p_side       # P 侧保留 VREFP
            n_new = committed_state.n_side   # N 侧不变 (保持 VCM)

        return DifferentialSwitchState(p_side=p_new, n_side=n_new)

    # ---- decision 派生 ----

    @staticmethod
    def derive_decisions(final_state: DifferentialSwitchState) -> tuple[int, ...]:
        """从最终开关状态派生 decisions

        decision=1: N侧电容为VREFP (BITN=1)
        decision=0: P侧电容为VREFP (BITP=1)
        """
        decisions = []
        for stage in range(14):  # stage 0..13 physical switches
            cap_name = SideSwitchState.STAGE_TO_FIELD[stage]
            p_rail = final_state.p_side.get_rail(cap_name)
            n_rail = final_state.n_side.get_rail(cap_name)

            if n_rail == Rail.VREFP:
                decisions.append(1)
            elif p_rail == Rail.VREFP:
                decisions.append(0)
            else:
                decisions.append(0)  # VCM → 默认 0

        # terminal 不能从最终开关状态恢复；实际转换由控制器保存比较结果。
        decisions.append(0)
        return tuple(decisions)


def _make_side_sampling(side: str) -> SideSwitchState:
    """Connect every normal-conversion capacitor to the side input.

    The bridge is an internal series element and therefore has no bottom
    plate.  No low-segment capacitor is hidden at VCM.
    """
    rail = Rail.VINP if side == 'P' else Rail.VINN
    kwargs = {name: rail for name in SideSwitchState.CAP_NAMES}
    return SideSwitchState(**kwargs)
