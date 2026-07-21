from __future__ import annotations

from pathlib import Path
import unittest

from codex_veri.model import calibrate_centered_recursive, calibrate_legacy_replay
from codex_veri.parsers import parse_cal_pairs
from codex_veri.search import magnitude_search, signed_search
from codex_veri.timing import centered_candidate_count, legacy_direct_count


ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT.parent / "spectre_sim" / "results" / "codex_20260722" / "calibration_full32_baseline_stdout.log"
TRIALS = (64.0, 32.0, 16.0, 8.0, 4.0, 2.0)


class PolicyTests(unittest.TestCase):
    def test_trial_exact_tie_stops_before_terminal(self) -> None:
        trace = magnitude_search(64.0, TRIALS, terminal_tie="upper", exact_trial_stop=True)
        self.assertTrue(trace.exact_trial)
        self.assertFalse(trace.terminal_reached)
        self.assertEqual(trace.output, 64.0)

    def test_terminal_policy_cannot_change_exact_trial(self) -> None:
        lower = magnitude_search(64.0, TRIALS, terminal_tie="lower", exact_trial_stop=True)
        upper = magnitude_search(64.0, TRIALS, terminal_tie="upper", exact_trial_stop=True)
        self.assertEqual(lower.output, upper.output)

    def test_disabling_exact_stop_exposes_upper_tie_error(self) -> None:
        lower = magnitude_search(64.0, TRIALS, terminal_tie="lower", exact_trial_stop=False)
        upper = magnitude_search(64.0, TRIALS, terminal_tie="upper", exact_trial_stop=False)
        self.assertEqual(lower.output, 64.0)
        self.assertEqual(upper.output, 65.0)

    def test_signed_search_is_odd(self) -> None:
        for i in range(0, 1121):
            value = i / 16.0
            self.assertEqual(signed_search(-value, TRIALS).output, -signed_search(value, TRIALS).output)

    def test_deterministic_one_and_32_pairs_are_identical(self) -> None:
        one = calibrate_centered_recursive(pairs=1, step=1.0)
        thirty_two = calibrate_centered_recursive(pairs=32, step=1.0)
        self.assertEqual([s.estimate for s in one], [s.estimate for s in thirty_two])

    def test_signed_and_magnitude_half_difference_are_identical_representations(self) -> None:
        for pair in parse_cal_pairs(LOG):
            self.assertLessEqual(pair.d_minus, 0.0)
            signed = (pair.d_plus - pair.d_minus) / 2.0
            magnitude = (pair.d_plus + (-pair.d_minus)) / 2.0
            self.assertEqual(signed, magnitude)

    def test_h1r_causal_ablation_and_propagation(self) -> None:
        ideal = calibrate_legacy_replay([65.0] * 32)
        self.assertEqual([s.error for s in ideal], [0.0] * 7)
        delta = 0.25
        injected = calibrate_legacy_replay([65.0 + delta] * 32)
        errors = [s.error for s in injected]
        self.assertEqual(errors, [0.0, delta, delta, 2 * delta, 4 * delta, 8 * delta, 16 * delta])

    def test_quantized_offset_error_does_not_recursively_grow_in_candidate(self) -> None:
        for offset in (-5.0, -2.0, -0.5, 0.0, 0.5, 2.0, 5.0):
            stages = calibrate_centered_recursive(pairs=32, step=1.0, offset=offset)
            self.assertLessEqual(max(abs(stage.error) for stage in stages), 0.5)
            self.assertEqual([stage.error for stage in stages[1:]], [0.0] * 6)


class TimingOracleTests(unittest.TestCase):
    def test_frame_and_decision_counts_are_mode_specific(self) -> None:
        direct = legacy_direct_count()
        centered = centered_candidate_count()
        self.assertEqual(direct.frames, 448)
        self.assertEqual(centered.frames, 448)
        self.assertEqual(direct.maximum_decisions, 4480)
        self.assertEqual(centered.maximum_decisions, 3584)
        self.assertEqual(direct.frame_slot_time_us, 67.2)
        self.assertEqual(centered.frame_slot_time_us, 67.2)


if __name__ == "__main__":
    unittest.main()
