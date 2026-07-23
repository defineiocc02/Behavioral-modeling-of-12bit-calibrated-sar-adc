"""
calibration_controller.py — 异步校准控制器

需求文档 33 §4-8: 使用真实 CDAC 开关、电荷守恒和异步比较器进行校准。

核心流程:
  对每个 target (H1C-A → H32C):
    对每个 pair:
      D+ 测量: target P→VREFP, calDAC 搜索
      D- 测量: target N→VREFP, calDAC 搜索
    计算: W_hat = (D+_avg + D-_avg) / 2

calDAC 搜索使用低段物理电容 (L32C→L1C) 进行升序二进制搜索。
"""
import numpy as np
from dataclasses import dataclass, field

from python_cal import config as cfg
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.physical.charge_solver import CDACNodeSolution
from python_cal.comparator.dynamic_comparator import DynamicComparator
from python_cal.topology.switch_state import Rail, SideSwitchState, DifferentialSwitchState
from python_cal.async_control.timing import TimingParams

from .calibration_fsm import (
    CalibrationState, CalibrationEventType, ADCOperatingMode
)
from .calibration_registers import CalibrationRegisters
from .calibration_switching import (
    STAGE_TO_CAP, CALDAC_STAGES,
    build_cal_sampling_state,
    build_target_dplus_state,
    build_target_dminus_state,
    apply_caldac_trial,
    commit_caldac_bit,
)
from .calibration_trace import (
    CalibrationSearchStepTrace,
    TargetCalibrationResult,
    CalibrationReport,
)


@dataclass
class AsyncCalibrationController:
    """异步校准控制器

    需求文档 33 §4: 使用与正常转换相同的物理模型。

    使用方式:
      controller = AsyncCalibrationController(adc)
      report = controller.run(rng=cal_rng)
      adc.apply_calibration(report)
    """

    cdac: DifferentialCDAC
    comparator: DynamicComparator
    timing: TimingParams = field(default_factory=TimingParams)
    avg_pairs: int = 128
    cal_noise_sigma: float = 0.0  # 校准期间比较器噪声 (V RMS), 0=无噪声 (terminal comparison 处理截断)
    registers: CalibrationRegisters = field(default_factory=CalibrationRegisters.default)
    current_time_s: float = 0.0

    def run(self, rng=None) -> CalibrationReport:
        """执行完整 7-target 校准

        返回:
            CalibrationReport
        """
        self.current_time_s = 0.0
        start_time = self.current_time_s

        # 创建带噪声的校准比较器: 微小噪声提供 dithering,
        # 避免 Vdiff=0 时二进制搜索卡死 (真实电路始终有噪声)
        cal_cmp = DynamicComparator(
            t0_s=self.comparator.t0_s,
            tau_s=self.comparator.tau_s,
            v_logic=self.comparator.v_logic,
            v_min=self.comparator.v_min,
            offset_v=self.comparator.offset_v,
            noise_sigma_v=self.cal_noise_sigma,
            max_wait_s=self.comparator.max_wait_s,
        )

        targets = []
        all_valid = True

        for target_id in range(7):
            target_info = cfg.CAL_TARGETS[target_id]
            target_stage = target_info['stage']
            target_name = target_info['name']
            wall_stages = cfg.WALL_STAGES[target_id]
            target_start_time = self.current_time_s

            # 获取当前 wall 开关状态 (从已校准的电容)
            # D+ 和 D- 的 wall 在不同侧, 分别构建
            wall_state_dplus = self._build_wall_state(wall_stages, direction=0)
            wall_state_dminus = self._build_wall_state(wall_stages, direction=1)

            # 累积量
            dplus_sum_q0 = 0.0
            dminus_sum_q0 = 0.0
            completed_pairs = 0
            all_traces = []

            for pair_idx in range(self.avg_pairs):
                # ---- D+ 测量 ----
                dplus_val, dplus_traces = self._measure_one_direction(
                    target_id=target_id,
                    target_stage=target_stage,
                    target_name=target_name,
                    wall_stages=wall_stages,
                    wall_state=wall_state_dplus,
                    direction=0,  # D+
                    pair_idx=pair_idx,
                    cal_cmp=cal_cmp,
                    rng=rng,
                )
                dplus_sum_q0 += dplus_val

                # ---- D- 测量 ----
                dminus_val, dminus_traces = self._measure_one_direction(
                    target_id=target_id,
                    target_stage=target_stage,
                    target_name=target_name,
                    wall_stages=wall_stages,
                    wall_state=wall_state_dminus,
                    direction=1,  # D-
                    pair_idx=pair_idx,
                    cal_cmp=cal_cmp,
                    rng=rng,
                )
                dminus_sum_q0 += dminus_val

                all_traces.extend(dplus_traces)
                all_traces.extend(dminus_traces)
                completed_pairs += 1

            # 计算测量权重
            # D+/D- 测量返回的 signed code = target_physical - wall_physical
            # 因此 measured_weight_q0 = Σ(wall_calibrated) + avg_residual
            dplus_mean = dplus_sum_q0 / completed_pairs
            dminus_mean = dminus_sum_q0 / completed_pairs
            avg_residual_q0 = (dplus_mean + dminus_mean) / 2.0
            # 加回 wall 已校准权重
            cal_weights_q0 = self.registers.get_calibrated_weights_q0()
            wall_sum_q0 = sum(cal_weights_q0[s] for s in wall_stages)
            measured_weight_q0 = wall_sum_q0 + avg_residual_q0
            measured_weight_q = int(round(measured_weight_q0 * cfg.Q_SCALE))

            # 物理参考权重 (仅测试验证用, 不进入控制逻辑)
            phys_w_q0 = self._get_physical_weight(target_stage)
            nominal_w_q0 = target_info['nominal_q0']

            # 有效性验证
            valid = True
            sat = False
            if nominal_w_q0 > 0:
                deviation = abs(measured_weight_q0 - nominal_w_q0) / nominal_w_q0
                if deviation > cfg.WEIGHT_TOL:
                    valid = False
            if measured_weight_q > 200000 or measured_weight_q < -200000:
                sat = True
                valid = False

            # 写入寄存器
            self.registers.write_target(
                target_id, target_stage, measured_weight_q, valid, sat
            )

            target_done_time = self.current_time_s
            target_result = TargetCalibrationResult(
                target_id=target_id,
                target_name=target_name,
                stage=target_stage,
                measured_weight_q0=measured_weight_q0,
                measured_weight_q=measured_weight_q,
                nominal_weight_q0=nominal_w_q0,
                physical_weight_q0=phys_w_q0,
                dplus_mean_q0=dplus_mean,
                dminus_mean_q0=dminus_mean,
                valid=valid,
                saturated=sat,
                completed_pairs=completed_pairs,
                start_time_s=target_start_time,
                done_time_s=target_done_time,
                traces=tuple(all_traces),
            )
            targets.append(target_result)

            if not valid:
                all_valid = False
                break

        self.registers.calibration_done = all_valid

        return CalibrationReport(
            weights_q=tuple(self.registers.weights_q),
            weights_q0=tuple(self.registers.get_calibrated_weights_q0()),
            targets=tuple(targets),
            all_targets_complete=len(targets) == 7,
            valid=all_valid,
            calibration_start_time_s=start_time,
            calibration_done_time_s=self.current_time_s,
        )

    def _measure_one_direction(self, target_id, target_stage, target_name,
                                wall_stages, wall_state, direction, pair_idx,
                                cal_cmp, rng=None):
        """测量一个方向 (D+ 或 D-) 的 calDAC 码值

        D+ (direction=0): 目标 P→VREFP, 用 calDAC 平衡
        D- (direction=1): 目标 N→VREFP, 用 calDAC 平衡

        返回:
            (code_q0, list[CalibrationSearchStepTrace])
        """
        traces = []
        # calDAC 初始状态: 所有低段电容 P 和 N 都接 VCM
        caldac_state = DifferentialSwitchState.all_vcm()

        # 构建目标配置
        if direction == 0:
            config_state = build_target_dplus_state(
                target_stage, wall_stages, wall_state, caldac_state
            )
        else:
            config_state = build_target_dminus_state(
                target_stage, wall_stages, wall_state, caldac_state
            )

        # 采样 (零输入)
        sampling_sw = build_cal_sampling_state()
        self.cdac.sample(cfg.VCM, cfg.VCM, sampling_sw, cfg.VCM)
        self.current_time_s += self.timing.sample_duration_s

        # 应用目标+wall+calDAC 配置
        self.cdac.apply_switch_state(config_state)

        # 确定残差符号: 需要加 P 侧还是 N 侧 calDAC
        if not self.timing.ideal_settling:
            self.current_time_s += 5.0 * self.timing.dac_settle_tau_s
        sol = self.cdac.solve_current()
        initial_vdiff = sol.differential_input

        # 残差 > 0 (P>N): 需要降低 P 或 提高 N → calDAC 加 N 侧
        # 残差 < 0 (P<N): 需要提高 P → calDAC 加 P 侧
        put_caldac_on_p_side = (initial_vdiff < 0)

        # 记录 trace
        traces.append(CalibrationSearchStepTrace(
            target_id=target_id, target_name=target_name,
            pair_index=pair_idx, direction=direction,
            caldac_stage=-1,  # initial
            committed_before=config_state,
            trial_state=config_state,
            committed_after=config_state,
            vtop_p=sol.vtop_p, vtop_n=sol.vtop_n,
            vbridge_p=sol.vbridge_p, vbridge_n=sol.vbridge_n,
            differential_v=sol.differential_input,
            comparator_output=0,
            trial_start_time_s=self.current_time_s,
            dac_settled_time_s=self.current_time_s,
            comparator_done_time_s=self.current_time_s,
            commit_time_s=self.current_time_s,
        ))

        # calDAC 升序搜索 (L32C → L1C)
        accepted_caldac_state = DifferentialSwitchState.all_vcm()
        committed_before = config_state

        for cal_step in range(len(CALDAC_STAGES)):
            # Trial: 添加当前 calDAC 位
            trial_caldac = apply_caldac_trial(
                accepted_caldac_state, cal_step,
                trial=put_caldac_on_p_side
            )

            # 更新配置: 目标+wall+trial_caldac
            if direction == 0:
                trial_config = build_target_dplus_state(
                    target_stage, wall_stages, wall_state, trial_caldac
                )
            else:
                trial_config = build_target_dminus_state(
                    target_stage, wall_stages, wall_state, trial_caldac
                )

            self.cdac.apply_switch_state(trial_config)

            # DAC settling
            trial_start_time = self.current_time_s
            if not self.timing.ideal_settling:
                self.current_time_s += 5.0 * self.timing.dac_settle_tau_s
            settle_time = self.current_time_s

            # 比较
            sol_trial = self.cdac.solve_current()
            cmp_result = cal_cmp.request(
                sol_trial.vtop_p, sol_trial.vtop_n,
                request_time_s=self.current_time_s,
                rng=rng,
            )
            self.current_time_s += cmp_result.decision_time_s
            cmp_done_time = self.current_time_s

            # 决策:
            # put_caldac_on_p_side=True → 加 P 侧 calDAC 使 VTOP_P 上升
            #   cmp=1 (VTOP_P > VTOP_N) → 加过了, 不需要这一位 → 回退
            #   cmp=0 (VTOP_P < VTOP_N) → 还不够, 保留这一位
            # put_caldac_on_p_side=False → 加 N 侧 calDAC 使 VTOP_N 上升
            #   cmp=1 (VTOP_P > VTOP_N) → 还不够(N侧还不够高), 保留这一位
            #   cmp=0 (VTOP_P < VTOP_N) → 加过了, 回退

            if put_caldac_on_p_side:
                keep = (cmp_result.output == 0)  # P 还不够高 → 保留 trial
            else:
                keep = (cmp_result.output == 1)  # N 还不够高 → 保留 trial

            if keep:
                accepted_caldac_state = trial_caldac
            # else: 保持原 accepted_caldac_state (已回退)

            # 更新配置为 committed
            if direction == 0:
                committed_config = build_target_dplus_state(
                    target_stage, wall_stages, wall_state, accepted_caldac_state
                )
            else:
                committed_config = build_target_dminus_state(
                    target_stage, wall_stages, wall_state, accepted_caldac_state
                )
            self.cdac.apply_switch_state(committed_config)

            commit_time = self.current_time_s
            sol_commit = self.cdac.solve_current()

            traces.append(CalibrationSearchStepTrace(
                target_id=target_id, target_name=target_name,
                pair_index=pair_idx, direction=direction,
                caldac_stage=cal_step,
                committed_before=committed_before,
                trial_state=trial_config,
                committed_after=committed_config,
                vtop_p=sol_commit.vtop_p,
                vtop_n=sol_commit.vtop_n,
                vbridge_p=sol_commit.vbridge_p,
                vbridge_n=sol_commit.vbridge_n,
                differential_v=sol_commit.differential_input,
                comparator_output=cmp_result.output,
                trial_start_time_s=trial_start_time,
                dac_settled_time_s=settle_time,
                comparator_done_time_s=cmp_done_time,
                commit_time_s=commit_time,
            ))
            committed_before = committed_config

        # === Terminal 比较: calDAC 最小步进 L1C=2 Q0, terminal=1 Q0 ===
        # 文档 41 C1: terminal_adj 必须加幅度门限。
        # L1C=2 Q0 的物理差分电压/2 = 1 Q0 门限。
        # 仅当 |final_vdiff| ≥ 1 Q0 且残差与初始同号时才 ±1 Q0。
        # 微量残差 (如 0.08 Q0) 不触发 —— 否则造成 wall 链偏差放大。
        sol_final = self.cdac.solve_current()
        final_vdiff = sol_final.differential_input

        # 用 L1C toggle 计算 1-Q0 电压门限
        l1c_cap = 'low_1c'  # stage 12, caldac min step = 2 Q0
        threshold_1q0_v = self._compute_1q0_threshold_v(l1c_cap)

        initial_sign = 1 if initial_vdiff > 0 else -1
        final_sign = 1 if final_vdiff > 0 else (-1 if final_vdiff < 0 else 0)

        # 幅度门限 + 同号判定
        if abs(final_vdiff) >= threshold_1q0_v and initial_sign == final_sign and final_sign != 0:
            terminal_adj = 1
        else:
            terminal_adj = 0

        # Terminal 比较器请求 (含校准噪声)
        terminal_cmp_result = cal_cmp.request(
            sol_final.vtop_p, sol_final.vtop_n,
            request_time_s=self.current_time_s,
            rng=rng,
        )
        self.current_time_s += terminal_cmp_result.decision_time_s

        traces.append(CalibrationSearchStepTrace(
            target_id=target_id, target_name=target_name,
            pair_index=pair_idx, direction=direction,
            caldac_stage=len(CALDAC_STAGES),  # terminal step
            committed_before=committed_config,
            trial_state=committed_config,
            committed_after=committed_config,
            vtop_p=sol_final.vtop_p,
            vtop_n=sol_final.vtop_n,
            vbridge_p=sol_final.vbridge_p,
            vbridge_n=sol_final.vbridge_n,
            differential_v=sol_final.differential_input,
            comparator_output=terminal_cmp_result.output,
            trial_start_time_s=self.current_time_s,
            dac_settled_time_s=self.current_time_s,
            comparator_done_time_s=self.current_time_s,
            commit_time_s=self.current_time_s,
        ))

        # 计算 calDAC 码值: 已接受的 calDAC 状态对应的权重和
        # calDAC 权重: 标称低段权重 (L32C..L1C)
        caldac_nominal = [cfg.NOMINAL_WEIGHTS_Q0[s] for s in CALDAC_STAGES]
        accepted_code_q0 = 0.0
        for cal_step in range(len(CALDAC_STAGES)):
            cap_name = STAGE_TO_CAP[CALDAC_STAGES[cal_step]]
            if put_caldac_on_p_side:
                rail = accepted_caldac_state.p_side.get_rail(cap_name)
            else:
                rail = accepted_caldac_state.n_side.get_rail(cap_name)
            if rail == Rail.VREFP:
                accepted_code_q0 += caldac_nominal[cal_step]

        # 带符号的残差码值: target_physical - wall_physical
        # D+ (direction=0): target P→VREFP, wall N→VREFP
        #   put_caldac_on_p_side=True  → P侧需要抬高 → target < wall → 负
        #   put_caldac_on_p_side=False → N侧需要抬高 → target > wall → 正
        # D- (direction=1): target N→VREFP, wall P→VREFP
        #   put_caldac_on_p_side=True  → P侧需要抬高 → target > wall → 正
        #   put_caldac_on_p_side=False → N侧需要抬高 → target < wall → 负
        if direction == 0:  # D+
            signed_code_q0 = -accepted_code_q0 if put_caldac_on_p_side else accepted_code_q0
        else:  # D-
            signed_code_q0 = accepted_code_q0 if put_caldac_on_p_side else -accepted_code_q0

        # 应用 terminal 调整: terminal_adj 增大 |signed_code_q0|
        if signed_code_q0 >= 0:
            signed_code_q0 += terminal_adj
        else:
            signed_code_q0 -= terminal_adj

        return signed_code_q0, traces

    def _build_wall_state(self, wall_stages: list[int], direction: int) -> DifferentialSwitchState:
        """根据已校准的权重构建 wall 开关状态

        D+ (direction=0): target 在 P 侧, wall 在 N 侧 → wall caps N→VREFP
        D- (direction=1): target 在 N 侧, wall 在 P 侧 → wall caps P→VREFP
        """
        from .calibration_switching import STAGE_TO_CAP
        p_side = SideSwitchState.all_vcm()
        n_side = SideSwitchState.all_vcm()

        for ws in wall_stages:
            cap_name = STAGE_TO_CAP[ws]
            if direction == 0:  # D+: wall on N-side
                n_side = SideSwitchState(**{**n_side.__dict__, cap_name: Rail.VREFP})
            else:  # D-: wall on P-side
                p_side = SideSwitchState(**{**p_side.__dict__, cap_name: Rail.VREFP})

        return DifferentialSwitchState(p_side=p_side, n_side=n_side)

    def _get_physical_weight(self, stage: int) -> float:
        """获取指定阶段的物理权重 (测试 oracle 用)

        通过 CDAC 电荷求解器测量实际物理权重，不是名义值。
        """
        phys_weights = self.cdac.get_physical_weights_q0()
        return phys_weights[stage]

    def compute_noise_sigma_v_from_lsb(self, noise_sigma_lsb: float) -> float:
        """将 LSB 单位的校准噪声转换为 V RMS

        使用 CDAC 物理特性测量 V/Q0 (signed):
          V/Q0_signed = VFS_signed / signal_weight_Q0

        参数:
            noise_sigma_lsb: 噪声标准差 (LSB), 如 config.CAL_NOISE_SIGMA=0.50
        返回:
            float: 噪声标准差 (V RMS)
        """
        phys_weights = self.cdac.get_physical_weights_q0()
        total_signal_q0 = sum(phys_weights[s] for s in cfg.SIGNAL_STAGES)
        # 测量 signed VFS: 使用全部 signal stages 的 complementary delta
        from python_cal.topology.switching_policy import DifferentialSwitchingPolicy
        from python_cal.topology.switch_state import Rail, SideSwitchState, DifferentialSwitchState

        policy = DifferentialSwitchingPolicy()
        total_complementary_delta_v = 0.0

        # 临时保存 CDAC 状态
        old_sw_state = self.cdac.current_switch_state
        old_charge = self.cdac.sampled_charge

        try:
            sampling_sw = policy.sampling_state(cfg.VCM, cfg.VCM)
            self.cdac.sample(cfg.VCM, cfg.VCM, sampling_sw, cfg.VCM)
            sol_base = self.cdac.solve_current()

            for s in cfg.SIGNAL_STAGES:
                cap_name = policy.STAGE_TO_CAP[s]
                p_comp = SideSwitchState.all_vcm().with_rail(cap_name, Rail.VREFP)
                n_comp = SideSwitchState.all_vcm().with_rail(cap_name, Rail.VREFN)
                self.cdac.apply_switch_state(
                    DifferentialSwitchState(p_side=p_comp, n_side=n_comp))
                sol_comp = self.cdac.solve_current()
                total_complementary_delta_v += abs(
                    sol_comp.differential_input - sol_base.differential_input)
                # 恢复基线
                self.cdac.apply_switch_state(
                    DifferentialSwitchState.all_vcm())
        finally:
            # 恢复 CDAC 状态
            self.cdac.sampled_charge = old_charge
            self.cdac.current_switch_state = old_sw_state

        volts_per_q0_signed = total_complementary_delta_v / (2.0 * total_signal_q0)
        return noise_sigma_lsb * volts_per_q0_signed

    def _compute_1q0_threshold_v(self, cap_name: str = 'low_1c') -> float:
        """用物理 CDAC 测量 1 Q0 的差分电压门限

        文档 41 C1: 通过 toggle L1C (2 Q0) 计算 ΔV/2 = 1 Q0。
        结果缓存于 self._1q0_threshold_v_，仅首次调用时计算。
        """
        cached = getattr(self, '_1q0_threshold_v_', None)
        if cached is not None:
            return cached

        from python_cal.topology.switch_state import Rail, SideSwitchState, DifferentialSwitchState

        old_sw_state = self.cdac.current_switch_state
        old_charge = self.cdac.sampled_charge

        try:
            # 构建采样 + 复位到 VCM
            from python_cal.topology.switching_policy import DifferentialSwitchingPolicy
            policy = DifferentialSwitchingPolicy()
            sampling_sw = policy.sampling_state(cfg.VCM, cfg.VCM)
            self.cdac.sample(cfg.VCM, cfg.VCM, sampling_sw, cfg.VCM)

            # 基线 (全部 VCM)
            self.cdac.apply_switch_state(DifferentialSwitchState.all_vcm())
            sol_base = self.cdac.solve_current()

            # toggle L1C P-side VCM → VREFP
            p_toggle = SideSwitchState.all_vcm().with_rail(cap_name, Rail.VREFP)
            self.cdac.apply_switch_state(
                DifferentialSwitchState(p_side=p_toggle, n_side=SideSwitchState.all_vcm()))
            sol_toggle = self.cdac.solve_current()

            delta_v = abs(sol_toggle.differential_input - sol_base.differential_input)
            threshold = delta_v / 2.0  # L1C = 2 Q0 → ΔV/2 = 1 Q0
            self._1q0_threshold_v_ = threshold
            return threshold
        finally:
            self.cdac.sampled_charge = old_charge
            self.cdac.current_switch_state = old_sw_state
