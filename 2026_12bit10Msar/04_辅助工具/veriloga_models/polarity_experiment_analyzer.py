#!/usr/bin/env python3
"""
F+ 极性实验分析工具

用途:
  1. 解析 Spectre 日志中的 OFFSAR FDIAG 行
  2. 提取 S (switched_sum) 和 F+ (cmp_delta) 的对应关系
  3. 判定 F+ 随 S 增大时的趋势 (增大 or 减小)
  4. 据此确定物理极性:
       F+ 随 S 增大 -> F+ = R + V_calDAC -> keep 条件应取反 (F<0 时 keep)
       F+ 随 S 减小 -> F+ = R - V_calDAC -> keep 条件正确 (F>0 时 keep)

使用方法:
  python polarity_experiment_analyzer.py <spectre_log_file>

  或直接传入日志内容:
  cat spectre.log | python polarity_experiment_analyzer.py -

FDIAG 行格式 (来自 VA 的 $strobe):
  OFFSAR FDIAG tgt=2 dir=0 st=2 step=0 S=0 trW=48 S_tr=48 F+=-0.45V cmp=0 t=1.2e-6
"""

import sys
import re
import os
from collections import defaultdict


def parse_fdiag_line(line):
    """解析一行 FDIAG 输出"""
    if "OFFSAR FDIAG" not in line:
        return None

    pattern = (
        r"tgt=(\d+)\s+dir=(\d+)\s+st=(\d+)\s+step=(\d+)\s+"
        r"S=(\d+)\s+trW=(\d+)\s+S_tr=(\d+)\s+F+=([+-]?[\d.eE]+)V\s+cmp=(\d+)"
    )
    m = re.search(pattern, line)
    if not m:
        return None

    return {
        "target": int(m.group(1)),
        "direction": int(m.group(2)),
        "state": int(m.group(3)),
        "step": int(m.group(4)),
        "S": int(m.group(5)),
        "trial_w": int(m.group(6)),
        "S_trial": int(m.group(7)),
        "F_plus": float(m.group(8)),
        "cmp": int(m.group(9)),
    }


def analyze_polarity(records):
    """
    分析 F+ 与 S 的关系, 判定极性

    核心逻辑:
      calDAC_out = -126 + 2*S  (S = switched_sum)
      F+ = V(COMP) - V(COMN) = 比较器差分输入

      如果 F+ = R + V_calDAC = R - 126 + 2*S  -> F+ 随 S 增大
      如果 F+ = R - V_calDAC = R + 126 - 2*S  -> F+ 随 S 减小

    判定方法:
      取同一 target/dir 的所有 (S_trial, F+) 数据点
      计算相关系数: 正相关 -> F+随S增大, 负相关 -> F+随S减小
    """
    # 按 target+dir 分组
    groups = defaultdict(list)
    for r in records:
        key = (r["target"], r["direction"])
        groups[key].append((r["S_trial"], r["F_plus"]))

    print("=" * 80)
    print("F+ 极性分析报告")
    print("=" * 80)

    overall_increasing = 0
    overall_decreasing = 0

    for key in sorted(groups.keys()):
        target, direction = key
        data = groups[key]
        dir_label = "D+" if direction == 0 else "D-"
        target_label = {2: "C10", 1: "C11", 0: "C12"}.get(target, f"T{target}")

        print(f"\n--- {target_label} {dir_label} ({len(data)} 个数据点) ---")
        print(f"  {'S_trial':>8}  {'F+(V)':>12}  {'cmp':>4}")
        print(f"  {'-'*8}  {'-'*12}  {'-'*4}")

        for s, f in sorted(data, key=lambda x: x[0]):
            cmp_val = next((r["cmp"] for r in records
                           if r["target"] == target and r["direction"] == direction
                           and r["S_trial"] == s), -1)
            print(f"  {s:>8}  {f:>12.6f}  {cmp_val:>4}")

        # 计算趋势: 线性回归斜率
        n = len(data)
        if n >= 2:
            xs = [d[0] for d in data]
            ys = [d[1] for d in data]
            x_mean = sum(xs) / n
            y_mean = sum(ys) / n

            num = sum((x - x_mean) * (y - y_mean) for x, y in data)
            den = sum((x - x_mean) ** 2 for x in xs)

            if den != 0:
                slope = num / den
                print(f"\n  线性回归斜率: {slope:.6f} V/LSB")

                if slope > 0:
                    print(f"  >>> F+ 随 S 增大而增大 (正相关)")
                    print(f"  >>> 物理关系: F+ = R + V_calDAC = R - 126 + 2*S")
                    print(f"  >>> keep 条件应取反: F<0 时 keep (cmp_p_gt_n == 0)")
                    print(f"  >>> 残差公式: R = D- - D+ (而非 D+ - D-)")
                    overall_increasing += 1
                else:
                    print(f"  >>> F+ 随 S 增大而减小 (负相关)")
                    print(f"  >>> 物理关系: F+ = R - V_calDAC = R + 126 - 2*S")
                    print(f"  >>> keep 条件正确: F>0 时 keep (cmp_p_gt_n != 0)")
                    print(f"  >>> 残差公式: R = D+ - D- (当前公式正确)")
                    overall_decreasing += 1

                # 理论交点
                # F+ = 0 时: R - 126 + 2*S = 0 -> S = (126 - R) / 2
                # 或: R + 126 - 2*S = 0 -> S = (126 + R) / 2
                if slope > 0:
                    # F+ = R - 126 + 2*S, F+=0 -> S = (126-R)/2
                    # 从数据估算 R: F+ = R - 126 + 2*S -> R = F+ + 126 - 2*S
                    R_estimates = [f + 126 - 2 * s for s, f in data]
                    R_avg = sum(R_estimates) / len(R_estimates)
                    print(f"  >>> 估算残差 R ≈ {R_avg:.2f} LSB")
                    print(f"  >>> 理想交点 S+ ≈ {(126 - R_avg) / 2:.2f}")
                else:
                    # F+ = R + 126 - 2*S, F+=0 -> S = (126+R)/2
                    R_estimates = [f - 126 + 2 * s for s, f in data]
                    R_avg = sum(R_estimates) / len(R_estimates)
                    print(f"  >>> 估算残差 R ≈ {R_avg:.2f} LSB")
                    print(f"  >>> 理想交点 S+ ≈ {(126 + R_avg) / 2:.2f}")
            else:
                print(f"  (所有 S 值相同, 无法判定趋势)")
        else:
            print(f"  (数据点不足, 无法判定)")

    print("\n" + "=" * 80)
    print("总体判定")
    print("=" * 80)
    print(f"  F+随S增大: {overall_increasing} 组")
    print(f"  F+随S减小: {overall_decreasing} 组")

    if overall_increasing > overall_decreasing:
        print(f"\n  结论: F+ = R + V_calDAC")
        print(f"  需要修复:")
        print(f"    1. keep 条件取反: cmp_p_gt_n == 0 时 keep")
        print(f"    2. 残差公式: R = D- - D+ (翻转 accum_d_plus/minus)")
        print(f"    3. terminal bit 同步重新定义")
    elif overall_decreasing > overall_increasing:
        print(f"\n  结论: F+ = R - V_calDAC")
        print(f"  当前 keep 条件和残差公式正确, 无需修改极性")
    else:
        print(f"\n  结论: 无法判定 (需要更多数据点)")


def main():
    if len(sys.argv) < 2:
        print(f"用法: python {sys.argv[0]} <spectre_log_file>")
        print(f"      cat spectre.log | python {sys.argv[0]} -")
        sys.exit(1)

    filename = sys.argv[1]
    records = []

    if filename == "-":
        for line in sys.stdin:
            r = parse_fdiag_line(line)
            if r:
                records.append(r)
    else:
        if not os.path.exists(filename):
            print(f"错误: 文件不存在: {filename}")
            sys.exit(1)
        with open(filename, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                r = parse_fdiag_line(line)
                if r:
                    records.append(r)

    if not records:
        print("未找到 FDIAG 行. 请确认日志中包含 'OFFSAR FDIAG' 行.")
        print(f"\n示例 FDIAG 行:")
        print(f"  OFFSAR FDIAG tgt=2 dir=0 st=2 step=0 S=0 trW=48 S_tr=48 F+=-0.45V cmp=0 t=1.2e-6")
        sys.exit(1)

    print(f"共解析到 {len(records)} 条 FDIAG 记录")
    analyze_polarity(records)


if __name__ == "__main__":
    main()
