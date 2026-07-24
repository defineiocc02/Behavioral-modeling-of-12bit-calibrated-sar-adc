# Response to Calibration Code Review — 2026-07-24

## 总体回应

感谢审查对 active Shen 半差、P/N 分侧、递归 ruler、digital terminal 和固定
dither 的确认。审查发现的“生产代码”和“本地未跟踪实验文件”边界需要
校正：`alpha_estimator.py` 与 `test_observable_alpha.py` 不属于 Git 提交，
也不属于 v2.1.0 生产入口。它们来自已经冻结的 observable-alpha 实验。

本回应按提交树而不是当前脏工作树确定产品范围。

## Finding 1 — `[CRITICAL] run_with_alpha_pre() 不存在`

**Disposition：接受症状，拒绝“生产功能漏实现”的定性。**

审查复现的 `AttributeError` 对本地 `test_observable_alpha.py` 是真实的；
但该脚本和 `alpha_estimator.py` 均未被 Git 跟踪：

```powershell
git ls-files src/python_cal/calibration/alpha_estimator.py `
              src/python_cal/test_observable_alpha.py
```

输出为空。`run_with_alpha_pre()` 是有意从 active controller 删除的冻结
实验接口，不应为了让旧脚本返回“有效样本”而恢复。该实验曾依赖尚未证明的
common-alpha 假设，不能作为生产 Shen 结果。

已完成的防回归措施：

- `ShenCalibrationController` 不定义 `run_with_alpha_pre()`；
- active module 不 import `alpha_estimator`；
- 新测试 `test_frozen_alpha_path_is_absent_from_active_controller` 将两者设为
  明确约束；
- README、Modeling Guide 和 CI 均不把 observable-alpha 列为生产方案。

因此本项的正确关闭方式是**隔离并禁止重新进入生产路径**，而不是补回一个
未经验证的方法。

## Finding 2 — `[HIGH] calibration_fsm.py 语义仍是旧 calDAC`

**Disposition：接受，已修复。**

完成内容：

- 保留 `CalibrationState` 和 `CalibrationEventType`，但明确标注为
  `[DEPRECATED]` legacy calDAC-search vocabulary；
- 新增 `ShenCalibrationState`：
  `P0_SUBCONVERSION`、`P1_SUBCONVERSION`、`N0_SUBCONVERSION`、
  `N1_SUBCONVERSION`、`PAIR_ACCUMULATE`、`TARGET_ESTIMATE`、
  `TARGET_VALIDATE`、`TARGET_COMMIT` 等；
- `ShenCalibrationController.state` 在 active `run()` 中实际更新；
- 理想校准回归明确断言最终状态为 `DONE`。

这使旧 DPLUS/DMINUS 搜索术语与 active P0/P1/N0/N1 半差协议不再混淆。

## Finding 3 — `[MEDIUM] 废弃文件未物理删除`

**Disposition：部分接受，采用隔离而不是在 2.1.0 破坏兼容。**

`calibration_controller.py` 和 `caldac_ruler_error.py` 仍是已发布兼容接口，
现有 legacy tests 仍覆盖它们。立即物理删除会把文档发布变成不必要的
breaking release。

本版本完成的隔离：

- `AsyncBehavioralSARADC` 顶层不再 import legacy controller；
- 只有显式调用 deprecated `run_calibration()` 时才 lazy import；
- 调用时继续发出 `DeprecationWarning`，指出 oracle leakage；
- active `run_shen_calibration()` 与正式 pipeline 只使用
  `ShenCalibrationController`；
- validation 文档禁止用 legacy 结果替代生产验收。

物理删除应放入未来 3.0 breaking release，并同时删除 legacy tests 和旧
trace/register compatibility，不应在本轮静默完成。

## Finding 4 — `[MEDIUM] calibration_switching.py 新旧接口混合`

**Disposition：接受，已修复。**

新增 `calibration/shen_switching.py`，只包含：

- stages 0–12 的物理 `STAGE_TO_CAP`；
- `build_force_p_state()`；
- `build_force_n_state()`。

它明确拒绝 stage 13，因为 terminal 没有物理电容。active calibrator 不再
import `calibration_switching.py`，后者只服务 legacy calDAC controller。

新增测试验证：

- active mapping 恰好是 `set(range(13))`；
- stage 13 不在 mapping；
- active Shen source 不引用 `calibration_switching` 或
  `apply_caldac_trial`。

## Finding 5 — `provenance.py 未被使用`

**Disposition：事实不成立，无代码修复。**

当前正式 pipeline 明确使用 provenance：

```text
run_final_calibration_pipeline.py
  -> generate_manifest(...)
  -> save_manifest_compact(...)
```

同时本次把 `python_cal.calibration.shen_switching` 加入 module hash 清单。
审查所称“未被使用”应是搜索范围或快照版本造成的误判。

## 对 alpha_estimator.py “逻辑正确”评价的说明

该判断不纳入 v2.1.0 接受结论。文件未提交、未进入 active import graph，
observable-alpha 结果也没有通过本项目的生产验证。一个公式在局部代数上
可计算，不等于其 common-alpha 假设、bridge 归因和 ruler 应用在当前
split-CDAC 上成立。

在完成独立可观测性证明、无 oracle leakage 测试、bridge-only/full-CDAC
对照和 100-seed 动态/静态验证之前，该方案保持 frozen。

## 最终验证

| 项目 | 结果 |
|---|---|
| Active Shen targeted tests | 6/6 PASS |
| Full Python regression | 60/60 PASS |
| Active alpha interface absent | PASS |
| Active switching isolated | PASS |
| Digital terminal absent from cap map | PASS |
| Shen state reaches DONE | PASS |
| Legacy controller top-level import removed | PASS |

## 关闭结论

审查意见已经形成代码修复、回归测试和范围说明。唯一没有执行的建议是
“立即物理删除 legacy 文件”，原因是它属于 breaking change；本版本采用
lazy import + warning + active-path isolation，且该决定已公开记录，不是
遗漏。
