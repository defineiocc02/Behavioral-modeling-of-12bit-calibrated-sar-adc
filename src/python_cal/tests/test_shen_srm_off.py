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
    assert set(STAGE_TO_CAP) == set(range(13))
    assert 13 not in STAGE_TO_CAP
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

    assert len(targets) == 7
    assert len(wp) == 14 and len(wn) == 14
    assert all(t["valid"] for t in targets)


def test_ideal_shen_is_direction_symmetric_without_srm():
    controller = _controller(DifferentialCDAC.ideal(), pairs=2)
    targets, wp, wn = controller.run(
        rng=np.random.default_rng(11)
    )
    assert all(t["valid"] for t in targets)
    # H1C-R/H1C-A 的两侧量化结果可能互换 1 Q0，但平均值必须保持理想权重。
    nominal = [2080, 1040, 520, 260, 130, 65, 65, 64, 32, 16, 8, 4, 2, 1]
    for stage in range(14):
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
    nominal = [2080, 1040, 520, 260, 130, 65, 65, 64, 32, 16, 8, 4, 2, 1]
    assert all(t["valid"] for t in targets)
    assert wp == nominal
    assert wn == nominal
