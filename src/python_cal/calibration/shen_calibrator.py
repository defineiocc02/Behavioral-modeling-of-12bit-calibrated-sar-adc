"""
shen_calibrator.py — Shen 2018 式逐级电容权重校准

本文件实现 Shen 2018 JSSC 的 force-0/force-1 半差协议在本项目
12-bit split-CDAC 上的移植:
  待校位 force-0 (VREFN) → 低位完整 SAR 子转换 → 输出码 C0
  待校位 force-1 (VREFP) → 低位完整 SAR 子转换 → 输出码 C1
  权重 = signed(C0 - C1) / 2

P/N 分侧扩展:
  P0: P-side target→VREFN, N-side target→VCM
  P1: P-side target→VREFP, N-side target→VCM
  N0: P-side target→VCM, N-side target→VREFN
  N1: P-side target→VCM, N-side target→VREFP

  W_P = mean(P0 - P1) / 2
  W_N = mean(N1 - N0) / 2

基础尺子 (BASE_RULER): L32C..L1C + 数字 terminal，不通过递归算法自校准.
The complete low segment is the matched seed ruler.
Calibration order: H1 -> H2 -> H4 -> H8-R -> H8-A -> H16 -> H32.

与旧 calDAC balance-search 方案的差异:
  - 残差通过正常 SAR 低位转换的完整输出码读出, 而非 calDAC 搜索
  - 不需要 calDAC 自校准或 calDAC 尺子精度
  - force 状态关于 VCM 对称；固定 dither 为可选项，正式矩阵默认关闭
  - stage 14 is a comparator-only terminal decision
"""
from dataclasses import dataclass, field
import math

from python_cal import config as cfg
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.comparator.dynamic_comparator import DynamicComparator
from python_cal.topology.switch_state import Rail, DifferentialSwitchState
from python_cal.topology.switching_policy import DifferentialSwitchingPolicy
from python_cal.async_control.timing import TimingParams
from python_cal.decode.sar_decoder import SARDecoder

from .calibration_fsm import ShenCalibrationState
from .shen_switching import (
    STAGE_TO_CAP,
    build_force_n_state,
    build_force_p_state,
)


# ===========================================================================
# lower-SAR 子转换
# ===========================================================================

def _lower_sar_trial_stages_sorted(lower_stages: list[int]) -> list[int]:
    """按标称权重降序排列 lower-SAR trial 阶段."""
    return sorted(lower_stages, key=lambda s: cfg.NOMINAL_WEIGHTS_Q0[s], reverse=True)


def run_lower_sar_subconversion(
    cdac: DifferentialCDAC,
    comparator: DynamicComparator,
    timing: TimingParams,
    force_state: DifferentialSwitchState,
    lower_stages: list[int],
    decoder: SARDecoder,
    current_time_s: float,
    rng=None,
    internal_dither_v: float = 0.0,
) -> tuple[int, float, float, dict]:
    """运行一次完整的 lower-SAR 子转换.

    所有高于 target 的阶段保持 VCM 不参与 trial.
    target 按 force_state 保持固定.
    lower_stages 运行正常的逐位 SAR trial (降序).

    参数:
        cdac: 差分 CDAC 模型
        comparator: 动态比较器 (含 noise/offset)
        timing: 时序参数
        force_state: 强制施加的开关状态 (target + higher)
        lower_stages: SAR trial 的阶段列表
        decoder: 解码器 (包含当前最佳可用权重)
        current_time_s: 当前仿真时间
        rng: numpy.random.Generator
        internal_dither_v: 片内 dither 的输入等效差分电压；外部输入仍接地

    返回:
        (code: int, signed_sum: float, elapsed_s: float, trace: dict)
        signed_sum 是解码器 raw_sum (Q0 单位), 用于权重计算.
    """
    start_time = current_time_s

    # 1. 外部输入接地；dither 由片内固定序列等效注入。
    vinp = cfg.VCM + internal_dither_v / 2.0
    vinn = cfg.VCM - internal_dither_v / 2.0
    sampling_sw = DifferentialSwitchingPolicy().sampling_state(vinp, vinn)
    cdac.sample(
        vinp,
        vinn,
        sampling_sw,
        cfg.VCM,
    )
    current_time_s += timing.sample_duration_s

    # 2. 施加强制状态 + 重置低位为 VCM
    cdac.apply_switch_state(force_state)

    # DAC settling
    if not timing.ideal_settling:
        current_time_s += 5.0 * timing.dac_settle_tau_s

    # 3. 全差分 SAR trial loop
    #     trial: P 侧和 N 侧同时 toggle 到 VREFP
    #     cmp=1 (VTOP_P > VTOP_N): N 侧保留 VREFP, P 侧回 VCM → Vdiff 减小
    #     cmp=0 (VTOP_P < VTOP_N): P 侧保留 VREFP, N 侧回 VCM → Vdiff 增大
    decisions = {}  # stage → decision (0 or 1)
    committed_p = force_state.p_side
    committed_n = force_state.n_side

    trial_stages = _lower_sar_trial_stages_sorted(lower_stages)

    for trial_stage in trial_stages:
        if trial_stage == cfg.N_STAGES - 1:
            # Digital terminal decision: compare the residual without toggling
            # any capacitor.  This must not depend on a synthetic low_term
            # entry in either the switch state or the CDAC topology.
            sol = cdac.solve_current()
            cmp_result = comparator.request(
                sol.vtop_p, sol.vtop_n,
                request_time_s=current_time_s,
                rng=rng,
            )
            current_time_s += cmp_result.decision_time_s
            decisions[trial_stage] = cmp_result.output
            continue

        cap_name = STAGE_TO_CAP[trial_stage]

        # Trial: P 侧和 N 侧同时 toggle 到 VREFP
        trial_p = committed_p.with_rail(cap_name, Rail.VREFP)
        trial_n = committed_n.with_rail(cap_name, Rail.VREFP)
        trial_state = DifferentialSwitchState(p_side=trial_p, n_side=trial_n)
        cdac.apply_switch_state(trial_state)

        if not timing.ideal_settling:
            current_time_s += 5.0 * timing.dac_settle_tau_s

        sol = cdac.solve_current()
        cmp_result = comparator.request(
            sol.vtop_p, sol.vtop_n,
            request_time_s=current_time_s,
            rng=rng,
        )
        current_time_s += cmp_result.decision_time_s

        if cmp_result.output == 1:
            # VTOP_P > VTOP_N: 降低 Vdiff → N 侧保留 VREFP, P 侧回 VCM
            committed_n = trial_n
            decisions[trial_stage] = 1
        else:
            # VTOP_P < VTOP_N: 提高 Vdiff → P 侧保留 VREFP, N 侧回 VCM
            committed_p = trial_p
            decisions[trial_stage] = 0

        # 应用已提交状态
        cdac.apply_switch_state(
            DifferentialSwitchState(p_side=committed_p, n_side=committed_n)
        )

    # 4. 将 decisions 展开为 14 位数组, 然后解码
    # decisions 只包含 lower_stages 的决策
    # higher stages + target 全部填 0 (表示未参与 switching)
    full_decisions = [0] * cfg.N_STAGES
    for stage, d in decisions.items():
        full_decisions[stage] = d

    code = decoder.decode(full_decisions)
    det = decoder.decode_detailed(full_decisions)

    elapsed = current_time_s - start_time
    trace = {
        'decisions': dict(decisions),
        'code': code,
        'signed_sum': det.raw_sum,
        'internal_dither_v': internal_dither_v,
    }

    return code, det.raw_sum, elapsed, trace


# ===========================================================================
# Shen 校准控制器
# ===========================================================================

@dataclass
class ShenCalibrationController:
    """Shen 2018 式逐级电容权重校准控制器.

    核心流程 (每个 target):
      for pair in 1..N:
        P0 = lower_SAR(P target→VREFN)
        P1 = lower_SAR(P target→VREFP)
        N0 = lower_SAR(N target→VREFN)
        N1 = lower_SAR(N target→VREFP)

      W_P = mean(P0 - P1) / 2
      W_N = mean(N1 - N0) / 2
    """

    cdac: DifferentialCDAC
    comparator: DynamicComparator
    timing: TimingParams = field(default_factory=TimingParams)
    avg_pairs: int = cfg.AVG_PAIRS
    cal_noise_sigma: float = 0.0
    fixed_dither_lsb: tuple[float, ...] = cfg.SHEN_DITHER_LSB
    current_time_s: float = 0.0
    state: ShenCalibrationState = field(
        init=False, default=ShenCalibrationState.IDLE
    )

    def run(
        self, rng=None, base_ruler_wp=None, base_ruler_wn=None
    ) -> tuple[list[dict], list[float], list[float]]:
        """Run the seven-target high-segment calibration.

        参数:
            rng: numpy.random.Generator
            base_ruler_wp: 可选, 14元素列表, 覆盖 base ruler 的 P 侧初始权重.
                          若提供, 替代 cfg.NOMINAL_WEIGHTS_Q0 作为 decoder 初始权重.
            base_ruler_wn: 可选, 14元素列表, 覆盖 base ruler 的 N 侧初始权重.

        返回:
            list[dict]: 每个 target 的校准结果
              keys: target_name, stage, W_P, W_N, W_avg, valid
        """
        results = []
        self.state = ShenCalibrationState.TARGET_SETUP

        # 校准用比较器 (含校准噪声)
        cal_cmp = DynamicComparator(
            t0_s=self.comparator.t0_s,
            tau_s=self.comparator.tau_s,
            v_logic=self.comparator.v_logic,
            v_min=self.comparator.v_min,
            offset_v=self.comparator.offset_v,
            noise_sigma_v=self.cal_noise_sigma,
            max_wait_s=self.comparator.max_wait_s,
        )

        # 校准寄存器: 逐级填充
        calibrated_wp = {}
        calibrated_wn = {}

        # 初始 decoder 权重: 优先使用传入的 base_ruler, 否则用标称
        init_wp = list(base_ruler_wp) if base_ruler_wp is not None else list(cfg.NOMINAL_WEIGHTS_Q0)
        init_wn = list(base_ruler_wn) if base_ruler_wn is not None else list(cfg.NOMINAL_WEIGHTS_Q0)

        for target_info in cfg.SHEN_CAL_TARGETS:
            self.state = ShenCalibrationState.TARGET_SETUP
            target_stage = target_info['stage']
            target_name = target_info['name']
            target_nominal = target_info['nominal_q0']
            lower_stages = list(cfg.SHEN_LOWER_STAGES[target_stage])

            # 构建当前 decoder (使用已校准权重 + 初始权重)
            decoder_wp = list(init_wp)
            decoder_wn = list(init_wn)
            for s, wp in calibrated_wp.items():
                decoder_wp[s] = wp
                decoder_wn[s] = calibrated_wn.get(s, wp)
            decoder = SARDecoder(weights_p=decoder_wp, weights_n=decoder_wn)

            # P0/P1/N0/N1 累加器 (仅 signed_sum 差分)
            wp_sum = 0.0   # Σ (ss_P0 - ss_P1)
            wn_sum = 0.0   # Σ (ss_N1 - ss_N0)

            for pair_idx in range(self.avg_pairs):
                dither_lsb = (
                    self.fixed_dither_lsb[
                        pair_idx % len(self.fixed_dither_lsb)
                    ]
                    if self.fixed_dither_lsb else 0.0
                )
                dither_v = dither_lsb * cfg.VREF / (1 << cfg.N_BITS)

                # --- P0/P1: target P 从 VREFN force 到 VREFP ---
                self.state = ShenCalibrationState.P0_SUBCONVERSION
                force_p0 = build_force_p_state(target_stage, Rail.VREFN)
                _, ss_p0, elapsed, _ = run_lower_sar_subconversion(
                    self.cdac, cal_cmp, self.timing,
                    force_p0, lower_stages, decoder,
                    self.current_time_s, rng, dither_v,
                )
                self.current_time_s += elapsed

                self.state = ShenCalibrationState.P1_SUBCONVERSION
                force_p1 = build_force_p_state(target_stage, Rail.VREFP)
                _, ss_p1, elapsed, _ = run_lower_sar_subconversion(
                    self.cdac, cal_cmp, self.timing,
                    force_p1, lower_stages, decoder,
                    self.current_time_s, rng, dither_v,
                )
                self.current_time_s += elapsed

                wp_sum += (ss_p0 - ss_p1) / 2.0

                # --- N0/N1: target N 从 VREFN force 到 VREFP ---
                self.state = ShenCalibrationState.N0_SUBCONVERSION
                force_n0 = build_force_n_state(target_stage, Rail.VREFN)
                _, ss_n0, elapsed, _ = run_lower_sar_subconversion(
                    self.cdac, cal_cmp, self.timing,
                    force_n0, lower_stages, decoder,
                    self.current_time_s, rng, dither_v,
                )
                self.current_time_s += elapsed

                self.state = ShenCalibrationState.N1_SUBCONVERSION
                force_n1 = build_force_n_state(target_stage, Rail.VREFP)
                _, ss_n1, elapsed, _ = run_lower_sar_subconversion(
                    self.cdac, cal_cmp, self.timing,
                    force_n1, lower_stages, decoder,
                    self.current_time_s, rng, dither_v,
                )
                self.current_time_s += elapsed

                wn_sum += (ss_n1 - ss_n0) / 2.0
                self.state = ShenCalibrationState.PAIR_ACCUMULATE

            # 计算 P/N 分侧权重
            self.state = ShenCalibrationState.TARGET_ESTIMATE
            wp = wp_sum / self.avg_pairs
            wn = wn_sum / self.avg_pairs
            # Match the synthesizable register interface exactly.  RTL
            # lower-SAR sums are Q8 and its arithmetic shift truncates each
            # committed target back to Q8.  Retaining progressively finer
            # fractions here would give Python precision absent in hardware.
            q_scale = 1 << cfg.CAL_WEIGHT_FRAC_BITS
            wp = math.floor(wp * q_scale) / q_scale
            wn = math.floor(wn * q_scale) / q_scale
            w_avg = (wp + wn) / 2.0

            # 有效性检查
            self.state = ShenCalibrationState.TARGET_VALIDATE
            valid = True
            if target_nominal > 0:
                dev = abs(w_avg - target_nominal) / target_nominal
                if dev > cfg.WEIGHT_TOL:
                    valid = False

            # 写入已校准寄存器
            self.state = ShenCalibrationState.TARGET_COMMIT
            calibrated_wp[target_stage] = wp
            calibrated_wn[target_stage] = wn

            results.append({
                'target_name': target_name,
                'stage': target_stage,
                'W_P': wp,
                'W_N': wn,
                'W_avg': w_avg,
                'nominal': target_nominal,
                'valid': valid,
                'pairs': self.avg_pairs,
            })

            if not valid:
                self.state = ShenCalibrationState.FAILED
                break
            self.state = ShenCalibrationState.NEXT_TARGET

        # 构建完整权重数组
        full_wp = list(cfg.NOMINAL_WEIGHTS_Q0)
        full_wn = list(cfg.NOMINAL_WEIGHTS_Q0)
        for s, wp in calibrated_wp.items():
            full_wp[s] = wp
            full_wn[s] = calibrated_wn.get(s, wp)

        self.state = (
            ShenCalibrationState.DONE
            if all(result["valid"] for result in results)
            and len(results) == len(cfg.SHEN_CAL_TARGETS)
            else ShenCalibrationState.FAILED
        )
        return results, full_wp, full_wn
