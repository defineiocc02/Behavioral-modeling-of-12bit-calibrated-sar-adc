"""
handshake.py — 异步握手协议

需求文档 §10-11: 实现事件驱动的异步控制。
每阶段流程: trial → dac_settled → cmp_done → commit → next。
"""

import math
from dataclasses import dataclass, field

from .events import AsyncEvent, AsyncEventType
from .sar_fsm import SARState
from .timing import TimingParams

from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.physical.charge_solver import CDACNodeSolution
from python_cal.comparator.dynamic_comparator import DynamicComparator, ComparatorResult
from python_cal.topology.switching_policy import DifferentialSwitchingPolicy
from python_cal.topology.switch_state import DifferentialSwitchState
from python_cal.topology.cdac_topology import VCM, VREF, N_STAGES


@dataclass
class AsyncSARController:
    """异步 SAR 控制器

    需求文档 §11: 主控制器, 每阶段执行 trial/compare/commit 流程。

    使用方式:
      controller = AsyncSARController(cdac, comparator, policy)
      result = controller.start_conversion(vinp, vinn)
    """

    cdac: DifferentialCDAC
    comparator: DynamicComparator
    switching_policy: DifferentialSwitchingPolicy
    timing: TimingParams = field(default_factory=TimingParams)

    # 运行时状态
    state: SARState = SARState.IDLE
    current_stage: int = 0
    current_time_s: float = 0.0
    committed_state: DifferentialSwitchState = DifferentialSwitchState.all_vcm()
    trial_state: DifferentialSwitchState = DifferentialSwitchState.all_vcm()
    decisions: list[int] = field(default_factory=list)
    events: list[AsyncEvent] = field(default_factory=list)
    steps: list = field(default_factory=list)

    def start_conversion(self, vinp: float, vinn: float,
                          start_time_s: float = 0.0,
                          rng=None) -> 'AsyncSARConversionResult':
        """启动一次完整转换

        需求文档 §11: 入口方法, 执行完整异步转换。

        返回:
            AsyncSARConversionResult
        """
        self.current_time_s = start_time_s
        self.events = []
        self.steps = []
        self.decisions = []

        # ---- 采样 ----
        self._log_event(AsyncEventType.SAMPLE_START, None)
        self.state = SARState.SAMPLING

        sampling_sw = self.switching_policy.sampling_state(vinp, vinn)
        self.cdac.sample(vinp, vinn, sampling_sw, VCM)

        self.current_time_s += self.timing.sample_duration_s
        self._log_event(AsyncEventType.SAMPLE_DONE, None)

        # ---- 复位底板到 VCM ----
        self.state = SARState.RESET
        self.committed_state = self.switching_policy.reset_state()
        self.cdac.apply_switch_state(self.committed_state)
        self.current_time_s += self.timing.reset_duration_s
        self._log_event(AsyncEventType.RESET_DONE, None)

        # 记录复位后、首次 trial 前的初始电压
        sol_initial = self.cdac.solve_current()
        initial_vtop_p = sol_initial.vtop_p
        initial_vtop_n = sol_initial.vtop_n

        # ---- 14 阶段转换 ----
        self.state = SARState.HOLD
        for stage in range(N_STAGES):
            self.current_stage = stage

            if stage == 13:
                # terminal: 仅比较, 无物理切换
                trial_start_time = self.current_time_s
                self._log_event(AsyncEventType.DAC_TRIAL_START, stage)
                sol = self.cdac.solve_current()
                # ideal settling: trial=settled=cmp_request
                self._log_event(AsyncEventType.DAC_SETTLED, stage)
                self._log_event(AsyncEventType.CMP_REQUEST, stage)
                cmp_request_time = self.current_time_s
                cmp_result = self.comparator.request(
                    sol.vtop_p, sol.vtop_n,
                    request_time_s=self.current_time_s,
                    rng=rng,
                )
                self.current_time_s += cmp_result.decision_time_s
                cmp_done_time = self.current_time_s
                self._log_event(AsyncEventType.CMP_DONE, stage)
                commit_time = self.current_time_s
                self._log_event(AsyncEventType.BIT_COMMIT, stage)

                self.decisions.append(cmp_result.output)
                self._record_step(stage, sol, cmp_result, self.committed_state,
                                  self.committed_state, sol,
                                  trial_start_time=trial_start_time,
                                  dac_settled_time=trial_start_time,
                                  cmp_request_time=cmp_request_time,
                                  cmp_done_time=cmp_done_time,
                                  commit_time=commit_time)
                continue

            # ---- trial ----
            self._log_event(AsyncEventType.DAC_TRIAL_START, stage)
            self.state = SARState.APPLY_TRIAL
            trial_start_time = self.current_time_s
            self.trial_state = self.switching_policy.trial_state(
                stage, self.committed_state
            )
            self.cdac.apply_switch_state(self.trial_state)

            self.state = SARState.WAIT_DAC
            if not self.timing.ideal_settling:
                settle_time = self._compute_settle_time(stage)
                self.current_time_s += settle_time
            dac_settled_time = self.current_time_s
            self._log_event(AsyncEventType.DAC_SETTLED, stage)

            # 读取 trial 后电压
            sol_trial = self.cdac.solve_current()

            # ---- 比较 ----
            self.state = SARState.REQUEST_COMPARE
            cmp_request_time = self.current_time_s
            self._log_event(AsyncEventType.CMP_REQUEST, stage)
            self.state = SARState.WAIT_COMPARE
            cmp_result = self.comparator.request(
                sol_trial.vtop_p, sol_trial.vtop_n,
                request_time_s=self.current_time_s,
                rng=rng,
            )
            self.current_time_s += cmp_result.decision_time_s
            cmp_done_time = self.current_time_s
            self._log_event(AsyncEventType.CMP_DONE, stage)

            # ---- commit ----
            self.state = SARState.COMMIT_BIT
            committed_before = self.committed_state   # 保存 commit 前状态
            self.committed_state = self.switching_policy.commit_state(
                stage, self.committed_state, self.trial_state,
                comparator_output=cmp_result.output,
            )
            self.cdac.apply_switch_state(self.committed_state)
            commit_time = self.current_time_s
            self._log_event(AsyncEventType.BIT_COMMIT, stage)

            # 读取 commit 后电压 (用于 trace)
            sol_commit = self.cdac.solve_current()

            self.decisions.append(cmp_result.output)
            self._record_step(stage, sol_commit, cmp_result,
                              self.committed_state, self.trial_state, sol_trial,
                              sol_commit=sol_commit,
                              committed_before=committed_before,
                              trial_start_time=trial_start_time,
                              dac_settled_time=dac_settled_time,
                              cmp_request_time=cmp_request_time,
                              cmp_done_time=cmp_done_time,
                              commit_time=commit_time)

            self.state = SARState.NEXT_BIT

        # ---- 完成 ----
        self.state = SARState.DONE
        self._log_event(AsyncEventType.CONVERSION_DONE, None)

        from python_cal.conversion.conversion_result import AsyncSARConversionResult
        from python_cal.conversion.trace import AsyncSARStepTrace

        trace_entries = []
        from python_cal.topology.switching_policy import DifferentialSwitchingPolicy
        _policy = DifferentialSwitchingPolicy()
        for s in self.steps:
            trace_entries.append(AsyncSARStepTrace(
                stage=s['stage'],
                stage_name=_policy.STAGE_TO_CAP.get(s['stage'], 'terminal'),
                trial_start_time_s=s.get('trial_start', 0.0),
                dac_settled_time_s=s.get('dac_settled', 0.0),
                cmp_request_time_s=s.get('cmp_request', 0.0),
                comparator_done_time_s=s.get('cmp_done', 0.0),
                commit_time_s=s.get('commit_time', 0.0),
                committed_before=s.get('committed_before', DifferentialSwitchState.all_vcm()),
                trial_state=s.get('trial_state', DifferentialSwitchState.all_vcm()),
                committed_after=s.get('committed_after', DifferentialSwitchState.all_vcm()),
                vtop_p=s.get('vtop_p', 0.0),
                vtop_n=s.get('vtop_n', 0.0),
                vbridge_p=s.get('vbridge_p', 0.0),
                vbridge_n=s.get('vbridge_n', 0.0),
                differential_v=s.get('differential_v', 0.0),
                vtop_p_trial=s.get('vtop_p_trial', 0.0),
                vtop_n_trial=s.get('vtop_n_trial', 0.0),
                vdiff_trial=s.get('vdiff_trial', 0.0),
                comparator_output=s.get('cmp_output', 0),
                comparator_metastable=s.get('cmp_metastable', False),
                decision=s.get('decision', 0),
            ))

        return AsyncSARConversionResult(
            sampled_charge=self.cdac.sampled_charge,
            final_switch_state=self.committed_state,
            decisions=tuple(self.decisions),
            steps=tuple(trace_entries),
            events=tuple(self.events),
            start_time_s=start_time_s,
            done_time_s=self.current_time_s,
            initial_vtop_p=initial_vtop_p,
            initial_vtop_n=initial_vtop_n,
        )

    # ---- 内部方法 ----

    def _log_event(self, event_type: AsyncEventType, stage: int | None):
        self.events.append(AsyncEvent(
            time_s=self.current_time_s,
            event_type=event_type,
            stage=stage,
        ))

    def _record_step(self, stage, sol, cmp_result, committed_after,
                     trial_state, sol_trial, sol_commit=None,
                     committed_before=None,
                     trial_start_time=0.0, dac_settled_time=0.0,
                     cmp_request_time=0.0, cmp_done_time=0.0,
                     commit_time=0.0):
        sol_for_trace = sol_commit if sol_commit is not None else sol
        sol_trial_for_trace = sol_trial if sol_trial is not None else sol
        self.steps.append({
            'stage': stage,
            'trial_start': trial_start_time,
            'dac_settled': dac_settled_time,
            'cmp_request': cmp_request_time,
            'cmp_done': cmp_done_time,
            'commit_time': commit_time,
            'committed_before': committed_before if committed_before is not None else committed_after,
            'trial_state': trial_state,
            'committed_after': committed_after,
            # commit-state voltages (legacy)
            'vtop_p': sol_for_trace.vtop_p,
            'vtop_n': sol_for_trace.vtop_n,
            'vbridge_p': sol_for_trace.vbridge_p,
            'vbridge_n': sol_for_trace.vbridge_n,
            'differential_v': sol_for_trace.differential_input,
            # trial-state voltages (comparator input)
            'vtop_p_trial': sol_trial_for_trace.vtop_p,
            'vtop_n_trial': sol_trial_for_trace.vtop_n,
            'vdiff_trial': sol_trial_for_trace.differential_input,
            'cmp_output': cmp_result.output,
            'cmp_metastable': cmp_result.metastable,
            'decision': cmp_result.output,
        })

    def _compute_settle_time(self, stage: int) -> float:
        """计算 DAC settling 时间 (RC 衰减模型)"""
        return 5.0 * self.timing.dac_settle_tau_s  # 5τ → ~99.3%
