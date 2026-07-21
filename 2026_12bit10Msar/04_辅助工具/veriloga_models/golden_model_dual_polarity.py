#!/usr/bin/env python3
"""
centered offset-code SAR 双极性 golden model

支持两种物理极性假设, 由 polarity 参数选择:
  polarity = +1: F+ = R + V_calDAC  (mask 分析支持的假设)
  polarity = -1: F+ = R - V_calDAC  (报告原本假设的)

实验前用两种极性分别生成预期 D+/D-, 与 Spectre 对比确定正确极性。

calDAC 权重: [48, 32, 20, 12, 8, 4, 2]  (全偶数, sum=126)
01->10 切换: calDAC_out += 2*weight
初始 (全01): calDAC_out = -126
终态 (全10): calDAC_out = +126

V_calDAC = -126 + 2*S  (S = switched_sum)

中心码 D_CM = 64  (calDAC_out=0 时 D=64)

D = calDAC_out + D_CM + b_T = (2*S - 126) + 64 + b_T = 2*S - 62 + b_T
D 范围: 0+64-62=2 (S=0,bT=0) ... 126+64-62=128? 不对, 修正:
  S=0, bT=0: D = -126 + 64 + 0 = -62? 不对.

重新推导:
  calDAC_out = 2*S - 126  (S from 0 to 126)
  D = calDAC_out + D_CM + b_T = 2*S - 126 + 64 + b_T = 2*S - 62 + b_T

  S=0, bT=0: D = -62  (超出 0..127 范围!)
  S=0, bT=1: D = -61  (超出!)

这不对. 让我重新理解 offset-binary 编码.

实际上, D 不是 calDAC_out + D_CM. D 是 SAR 搜索的数字码, 定义为:
  D = S + b_T  (switched_sum + terminal_bit)

因为 calDAC_out = 2*S - 126, 所以:
  S = (calDAC_out + 126) / 2
  D = S + b_T = (calDAC_out + 126) / 2 + b_T

D 范围: 0 (S=0,bT=0) ... 127 (S=126,bT=1)
D_CM = 63.5 (中心)

但用户说 D_CM = 64, 这接近中心. 让我用 D = S + b_T.

对于 F+ = R + V_calDAC (polarity=+1):
  F+ = R + (2*S_trial - 126) = R + 2*S_trial - 126
  F+ > 0 -> S_trial > (126 - R) / 2
  F+ < 0 -> S_trial < (126 - R) / 2
  SAR 从 S=0 开始, F+ = R - 126 < 0 (假设 R < 126)
  要从负侧逼近零, 需要 S 增大 -> F+ 增大
  keep 条件: F+ < 0 (cmp_p_gt_n == 0) -> 继续增大 S

对于 F+ = R - V_calDAC (polarity=-1):
  F+ = R - (2*S_trial - 126) = R - 2*S_trial + 126
  F+ > 0 -> S_trial < (126 + R) / 2
  F+ < 0 -> S_trial > (126 + R) / 2
  SAR 从 S=0 开始, F+ = R + 126 > 0 (假设 R > -126)
  要从正侧逼近零, 需要 S 增大 -> F+ 减小
  keep 条件: F+ > 0 (cmp_p_gt_n != 0) -> 保持当前 S

最终残差:
  polarity=+1: R = D- - D+  (D- 对应 R 的反方向, S- > S+)
  polarity=-1: R = D+ - D-  (D+ 对应 R 的正方向, S+ > S-)

但等等, D+ 和 D- 的定义需要更仔细.

D+ 方向: target=+W, wall=-W -> 残差 R = W_target - W_wall > 0 (正常情况)
D- 方向: target=-W, wall=+W -> 残差 R = W_wall - W_target = -R < 0

对于 polarity=+1 (F+ = R + V_calDAC):
  D+ 方向: F+ = R + V_calDAC, 从 S=0 (F+=R-126<0) 增大 S 到 F+≈0
    S+ ≈ (126 - R) / 2
    D+ = S+ + bT+
  D- 方向: F+ = -R + V_calDAC, 从 S=0 (F+=-R-126<0) 增大 S 到 F+≈0
    S- ≈ (126 + R) / 2
    D- = S- + bT-
  D- - D+ ≈ (126+R)/2 - (126-R)/2 = R
  所以 R = D- - D+  ✓

对于 polarity=-1 (F+ = R - V_calDAC):
  D+ 方向: F+ = R - V_calDAC, 从 S=0 (F+=R+126>0) 增大 S 到 F+≈0
    S+ ≈ (126 + R) / 2
    D+ = S+ + bT+
  D- 方向: F+ = -R - V_calDAC, 从 S=0 (F+=-R+126>0) 增大 S 到 F+≈0
    S- ≈ (126 - R) / 2
    D- = S- + bT-
  D+ - D- ≈ (126+R)/2 - (126-R)/2 = R
  所以 R = D+ - D-  ✓

总结:
  polarity=+1: keep when F<0, R = D- - D+
  polarity=-1: keep when F>0, R = D+ - D-
"""

WEIGHTS = [48, 32, 20, 12, 8, 4, 2]
TOTAL = sum(WEIGHTS)  # 126


def offset_sar(R, Vos=0, noise=0, polarity=+1):
    """
    模拟 offset-binary SAR 搜索

    参数:
      R: 残差 (LSB)
      Vos: 比较器固定失调 (LSB)
      noise: 比较器噪声 (LSB, 高斯)
      polarity: +1 或 -1

    返回:
      D: 数字码 (0..127)
      S: switched_sum
      bT: terminal bit
      F_final: 最终 F+ 电压 (LSB)
    """
    S = 0
    for w in WEIGHTS:
        S_trial = S + w
        V_calDAC = 2 * S_trial - TOTAL
        if polarity == +1:
            F = R + V_calDAC + Vos + noise
        else:
            F = R - V_calDAC + Vos + noise

        if polarity == +1:
            keep = (F < 0)
        else:
            keep = (F > 0)

        if keep:
            S = S_trial

    V_calDAC_final = 2 * S - TOTAL
    if polarity == +1:
        F_final = R + V_calDAC_final + Vos + noise
    else:
        F_final = R - V_calDAC_final + Vos + noise

    if polarity == +1:
        bT = 1 if F_final < 0 else 0
    else:
        bT = 1 if F_final > 0 else 0

    D = S + bT
    return D, S, bT, F_final


def measure_weight(R, Vos=0, polarity=+1):
    """
    测量一个 target 的权重残差

    返回:
      D_plus, D_minus, R_estimated
    """
    D_plus, S_plus, _, _ = offset_sar(R, Vos, 0, polarity)
    D_minus, S_minus, _, _ = offset_sar(-R, Vos, 0, polarity)

    if polarity == +1:
        R_est = D_minus - D_plus
    else:
        R_est = D_plus - D_minus

    return D_plus, D_minus, R_est


def run_test_suite():
    """运行用户指定的测试用例"""
    print("=" * 90)
    print("centered offset-code SAR golden model (dual polarity)")
    print("=" * 90)

    for polarity in [+1, -1]:
        pol_label = f"F+ = R {'+' if polarity > 0 else '-'} V_calDAC"
        keep_label = "F<0" if polarity > 0 else "F>0"
        residual_label = "D- - D+" if polarity > 0 else "D+ - D-"

        print(f"\n{'='*90}")
        print(f"极性: {pol_label}  (keep when {keep_label}, R = {residual_label})")
        print(f"{'='*90}")

        test_cases = [
            (0, 0, "R=0, Vos=0 -> R_hat=0"),
            (1, 0, "R=+1, Vos=0"),
            (-1, 0, "R=-1, Vos=0"),
            (2, 0, "R=+2, Vos=0"),
            (-2, 0, "R=-2, Vos=0"),
            (3, 0, "R=+3, Vos=0"),
            (5, 0, "R=+5, Vos=0"),
            (5.8, 0, "R=+5.8, Vos=0"),
            (8, 0, "R=+8, Vos=0"),
            (-8, 0, "R=-8, Vos=0"),
            (10, 0, "R=+10, Vos=0"),
            (50, 0, "R=+50, Vos=0"),
            (-50, 0, "R=-50, Vos=0"),
            (0, 5, "R=0, Vos=+5 -> R_hat=0 (Vos 消除)"),
            (8, 5, "R=+8, Vos=+5 -> R_hat=+8"),
            (-8, 5, "R=-8, Vos=+5 -> R_hat=-8"),
            (0, -5, "R=0, Vos=-5 -> R_hat=0"),
            (5.8, 5, "R=+5.8, Vos=+5 -> R_hat=+5.8"),
            (5.8, -3, "R=+5.8, Vos=-3 -> R_hat=+5.8"),
        ]

        print(f"\n{'R':>8} {'Vos':>6} {'D+':>5} {'D-':>5} {'R_hat':>8} {'R_ideal':>8} {'err':>8}  备注")
        print(f"{'-'*8} {'-'*6} {'-'*5} {'-'*5} {'-'*8} {'-'*8} {'-'*8}  {'-'*30}")

        all_pass = True
        for R, Vos, desc in test_cases:
            D_plus, D_minus, R_hat = measure_weight(R, Vos, polarity)
            err = R_hat - R
            status = "OK" if abs(err) <= 2 else "FAIL"
            if abs(err) > 2:
                all_pass = False
            print(f"{R:>8.1f} {Vos:>6.1f} {D_plus:>5} {D_minus:>5} {R_hat:>8.2f} {R:>8.2f} {err:>+8.2f}  {desc} [{status}]")

        print(f"\n结论: {'全部通过 (|err| <= 2 LSB)' if all_pass else '存在失败用例'}")

        # 关键验证: Vos 消除
        print(f"\n--- 比较器失调消除验证 ---")
        for R in [0, 8, -8, 5.8]:
            D_p0, D_m0, R0 = measure_weight(R, 0, polarity)
            D_p5, D_m5, R5 = measure_weight(R, 5, polarity)
            D_p5n, D_m5n, R5n = measure_weight(R, -5, polarity)
            print(f"  R={R:>5.1f}: Vos=0 -> R_hat={R0:>6.2f}, Vos=+5 -> R_hat={R5:>6.2f}, Vos=-5 -> R_hat={R5n:>6.2f}")


def simulate_fdiag(R, polarity=+1):
    """
    模拟 FDIAG 输出, 用于与 Spectre 日志对比

    返回 list of (step, S, trial_w, S_trial, F_plus, cmp)
    """
    results = []
    S = 0
    for step, w in enumerate(WEIGHTS):
        S_trial = S + w
        V_calDAC = 2 * S_trial - TOTAL
        if polarity == +1:
            F = R + V_calDAC
            keep = (F < 0)
            cmp_val = 0 if F < 0 else 1  # cmp_p_gt_n
        else:
            F = R - V_calDAC
            keep = (F > 0)
            cmp_val = 1 if F > 0 else 0

        results.append((step, S, w, S_trial, F, cmp_val))

        if keep:
            S = S_trial

    return results


if __name__ == "__main__":
    run_test_suite()

    print(f"\n{'='*90}")
    print("FDIAG 模拟输出 (R=5.8, 两种极性对比)")
    print(f"{'='*90}")

    for polarity in [+1, -1]:
        pol_label = f"F+ = R {'+' if polarity > 0 else '-'} V_calDAC"
        print(f"\n--- {pol_label} ---")
        print(f"  {'step':>4} {'S':>5} {'trW':>5} {'S_tr':>5} {'F+':>10} {'cmp':>4}")
        results = simulate_fdiag(5.8, polarity)
        for step, S, w, S_tr, F, cmp_val in results:
            print(f"  {step:>4} {S:>5} {w:>5} {S_tr:>5} {F:>10.2f} {cmp_val:>4}")
