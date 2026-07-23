"""
test_charge_conservation.py — 电荷守恒测试

需求文档 §15.1: 采样后浮动节点电荷保持, 切换后总电荷不变。
"""

import pytest
import numpy as np

from python_cal.topology.cdac_topology import build_differential_topology, VCM, VREF
from python_cal.topology.switch_state import SideSwitchState, Rail, DifferentialSwitchState
from python_cal.topology.switching_policy import DifferentialSwitchingPolicy
from python_cal.physical.charge_solver import DifferentialChargeSolver
from python_cal.physical.differential_cdac import DifferentialCDAC


@pytest.fixture
def ideal_cdac():
    return DifferentialCDAC.ideal()


@pytest.fixture
def policy():
    return DifferentialSwitchingPolicy()


# ===================================================================
#  1. 采样后浮动节点电荷保持
# ===================================================================

def test_charge_conserved_after_sample_and_switch(ideal_cdac, policy):
    """采样后, 切换电容底板, 各节点总电荷不变"""
    vinp, vinn = 1.0, 0.8
    sampling_sw = policy.sampling_state(vinp, vinn)

    # 采样
    charge = ideal_cdac.sample(vinp, vinn, sampling_sw)

    # 保存初始电荷
    q_top_p0 = charge.p_top_charge_c
    q_bridge_p0 = charge.p_bridge_charge_c

    # 切换 P 侧 H32C 到 VREFP
    new_sw = DifferentialSwitchState(
        p_side=SideSwitchState(high_32c=Rail.VREFP),
        n_side=SideSwitchState(),
    )
    ideal_cdac.apply_switch_state(new_sw)
    sol = ideal_cdac.solve_current()

    # 重新计算电荷
    p_top = ideal_cdac.p_topology
    q_top_new = 0.0
    for cap in p_top.high_capacitors:
        rail = new_sw.p_side.get_rail(cap.name)
        vbot = rail.voltage(vrefp=VREF, vcm=VCM, vinp=vinp)
        q_top_new += cap.capacitance_f * (sol.vtop_p - vbot)
    q_top_new += p_top.c_bridge * (sol.vtop_p - sol.vbridge_p)

    assert q_top_new == pytest.approx(q_top_p0, rel=1e-9), \
        f"Top plate charge changed: {q_top_p0:.6e} → {q_top_new:.6e}"


# ===================================================================
#  2. P/N 对称性
# ===================================================================

def test_symmetric_circuit_vdiff_zero(ideal_cdac, policy):
    """VinP = VinN 时 Vdiff ≈ 0"""
    vin_cm = 0.9
    sampling_sw = policy.sampling_state(vin_cm, vin_cm)
    ideal_cdac.sample(vin_cm, vin_cm, sampling_sw)

    # 复位后
    sol = ideal_cdac.solve_current()
    assert sol.vtop_p == pytest.approx(sol.vtop_n, abs=1e-15), \
        f"Vdiff={sol.differential_input} should be 0"


# ===================================================================
#  3. 单电容开关
# ===================================================================

def test_single_cap_switch_direction(ideal_cdac, policy):
    """P 侧 H32C 切 VREFP → Vdiff 增大, N 侧切 VREFP → Vdiff 减小"""
    vinp = vinn = 0.9
    sampling_sw = policy.sampling_state(vinp, vinn)
    ideal_cdac.sample(vinp, vinn, sampling_sw)

    # P 侧 H32C → VREFP
    sw_p = DifferentialSwitchState(
        p_side=SideSwitchState(high_32c=Rail.VREFP),
        n_side=SideSwitchState(),
    )
    ideal_cdac.apply_switch_state(sw_p)
    sol_p = ideal_cdac.solve_current()
    assert sol_p.differential_input > 0, \
        f"P-side switch should increase Vdiff, got {sol_p.differential_input}"

    # N 侧 H32C → VREFP (P 侧回 VCM)
    sw_n = DifferentialSwitchState(
        p_side=SideSwitchState(),
        n_side=SideSwitchState(high_32c=Rail.VREFP),
    )
    ideal_cdac.apply_switch_state(sw_n)
    sol_n = ideal_cdac.solve_current()
    assert sol_n.differential_input < 0, \
        f"N-side switch should decrease Vdiff, got {sol_n.differential_input}"


# ===================================================================
#  4. 共模输入
# ===================================================================

def test_common_mode_rejection(ideal_cdac, policy):
    """VINP=VINN 时, 对称切换后 Vdiff 仍 ≈ 0"""
    for vcm_test in [0.7, 0.9, 1.1]:
        sampling_sw = policy.sampling_state(vcm_test, vcm_test)
        ideal_cdac.sample(vcm_test, vcm_test, sampling_sw)

        # 对称切换
        sw = DifferentialSwitchState(
            p_side=SideSwitchState(high_32c=Rail.VREFP, high_16c=Rail.VREFP),
            n_side=SideSwitchState(high_32c=Rail.VREFP, high_16c=Rail.VREFP),
        )
        ideal_cdac.apply_switch_state(sw)
        sol = ideal_cdac.solve_current()
        assert abs(sol.differential_input) < 1e-12, \
            f"VCM={vcm_test}: Vdiff={sol.differential_input} should be 0"


# ===================================================================
#  5. 输入反相
# ===================================================================

def test_input_inversion_antisymmetry(ideal_cdac, policy):
    """VINP-VINN = +x → 切换方向与 -x 反号"""
    vin_diff = 0.1
    vin_cm = 0.9

    # +x
    ideal_cdac.sample(vin_cm + vin_diff / 2, vin_cm - vin_diff / 2,
                       policy.sampling_state(vin_cm + vin_diff / 2, vin_cm - vin_diff / 2))
    sol_pos = ideal_cdac.solve_current()

    # -x
    ideal_cdac.sample(vin_cm - vin_diff / 2, vin_cm + vin_diff / 2,
                       policy.sampling_state(vin_cm - vin_diff / 2, vin_cm + vin_diff / 2))
    sol_neg = ideal_cdac.solve_current()

    assert sol_pos.differential_input == pytest.approx(-sol_neg.differential_input, abs=1e-15)
