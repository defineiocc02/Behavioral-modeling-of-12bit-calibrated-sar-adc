"""现行 Shen 校准链路的 SRM-off 回归测试。

这些测试只约束当前生产候选入口；旧版 calDAC 测试另行标记为 legacy，
不得用旧入口的结果替代本组证据。
"""

import inspect

import numpy as np

from python_cal.calibration.shen_calibrator import ShenCalibrationController
from python_cal.comparator.dynamic_comparator import DynamicComparator
from python_cal.physical.differential_cdac import DifferentialCDAC
from python_cal.async_control.timing import TimingParams
from python_cal.calibration.calibration_fsm import ShenCalibrationState
from python_cal.calibration.shen_switching import STAGE_TO_CAP
from python_cal import config as cfg


def _controller(cdac, pairs=1):
    return ShenCalibrationController(
        cdac=cdac,
        comparator=DynamicComparator(noise_sigma_v=0.0, offset_v=0.0),
        timing=TimingParams(),
        avg_pairs=pairs,
        cal_noise_sigma=0.0,
    )


def test_srm_symbols_are_absent_from_active_controller():
    source = inspect.getsource(ShenCalibrationController)
    assert "srm_samples" not in source
    assert "measure_srm_residue" not in source
    assert "erfinv" not in source
    assert not hasattr(ShenCalibrationController, "srm_samples")


def test_frozen_alpha_path_is_absent_from_active_controller():
    """The rejected observable-alpha experiment must not silently return."""
    source = inspect.getsource(ShenCalibrationController)
    module_source = inspect.getsource(
        inspect.getmodule(ShenCalibrationController)
    )
    assert not hasattr(ShenCalibrationController, "run_with_alpha_pre")
    assert "alpha_estimator" not in module_source
    assert "estimate_alpha" not in source


def test_active_shen_switching_has_no_physical_terminal_or_legacy_search():
    """Active Shen switching is isolated from deprecated calDAC helpers."""
    assert set(STAGE_TO_CAP) == set(range(cfg.N_PHYSICAL))
    assert cfg.N_STAGES - 1 not in STAGE_TO_CAP
    module_source = inspect.getsource(
        inspect.getmodule(ShenCalibrationController)
    )
    assert "calibration_switching" not in module_source
    assert "apply_caldac_trial" not in module_source


def test_shen_does_not_read_physical_oracle(monkeypatch):
    cdac = DifferentialCDAC.ideal()

    def forbidden_oracle(*_args, **_kwargs):
        raise AssertionError("production Shen calibration must not read physical weights")

    monkeypatch.setattr(cdac, "get_physical_weights_q0", forbidden_oracle)
    targets, wp, wn = _controller(cdac, pairs=1).run(rng=np.random.default_rng(7))

    assert len(targets) == len(cfg.SHEN_CAL_TARGETS)
    assert len(wp) == cfg.N_STAGES and len(wn) == cfg.N_STAGES
    assert all(t["valid"] for t in targets)


def test_ideal_shen_is_direction_symmetric_without_srm():
    controller = _controller(DifferentialCDAC.ideal(), pairs=2)
    targets, wp, wn = controller.run(
        rng=np.random.default_rng(11)
    )
    assert all(t["valid"] for t in targets)
    # Per-side quantization may differ by 1 Q0; the average remains nominal.
    nominal = list(cfg.NOMINAL_WEIGHTS_Q0)
    for stage in range(cfg.N_STAGES):
        assert abs((wp[stage] + wn[stage]) / 2.0 - nominal[stage]) < 1e-9
        assert abs(wp[stage] - wn[stage]) <= 2.0
    assert controller.state is ShenCalibrationState.DONE


def test_half_difference_and_fixed_dither_cancel_offset():
    """VREFN/VREFP 半差 + 对称固定 dither 不应把 offset 写进权重。"""
    controller = ShenCalibrationController(
        cdac=DifferentialCDAC.ideal(),
        comparator=DynamicComparator(noise_sigma_v=0.0, offset_v=0.003),
        timing=TimingParams(),
        avg_pairs=4,
        cal_noise_sigma=0.0,
        fixed_dither_lsb=(-1.5, -0.5, 0.5, 1.5),
    )
    targets, wp, wn = controller.run(rng=np.random.default_rng(19))
    nominal = list(cfg.NOMINAL_WEIGHTS_Q0)
    assert all(t["valid"] for t in targets)
    assert wp == nominal
    assert wn == nominal


def test_every_requested_calibration_pair_is_executed(monkeypatch):
    """The average must consume all P0/P1/N0/N1 lower-SAR comparisons."""
    original_request = DynamicComparator.request
    request_count = 0

    def counted_request(self, *args, **kwargs):
        nonlocal request_count
        request_count += 1
        return original_request(self, *args, **kwargs)

    monkeypatch.setattr(DynamicComparator, "request", counted_request)
    pairs = 3
    targets, _, _ = _controller(
        DifferentialCDAC.ideal(),
        pairs=pairs,
    ).run(rng=np.random.default_rng(23))

    comparisons_per_four_phases = 4 * sum(
        len(cfg.SHEN_LOWER_STAGES[target["stage"]])
        for target in cfg.SHEN_CAL_TARGETS
    )
    assert all(target["pairs"] == pairs for target in targets)
    assert request_count == pairs * comparisons_per_four_phases


def test_every_committed_weight_is_on_the_rtl_q8_lattice():
    """Recursive Python calibration must not retain sub-Q8 ideal precision."""
    controller = ShenCalibrationController(
        cdac=DifferentialCDAC.ideal(),
        comparator=DynamicComparator(noise_sigma_v=0.0, offset_v=0.0),
        timing=TimingParams(),
        avg_pairs=4,
        cal_noise_sigma=0.0003,
    )
    targets, _, _ = controller.run(rng=np.random.default_rng(29))
    scale = 1 << cfg.CAL_WEIGHT_FRAC_BITS
    for target in targets:
        for field in ("W_P", "W_N"):
            scaled = target[field] * scale
            assert abs(scaled - round(scaled)) < 1e-9
