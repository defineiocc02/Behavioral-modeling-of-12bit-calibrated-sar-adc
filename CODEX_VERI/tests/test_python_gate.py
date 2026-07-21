from __future__ import annotations

import math
from pathlib import Path
import tempfile
import unittest

from codex_veri.model import (
    calibrate_centered_recursive,
    calibrate_legacy_replay,
    estimates_by_name,
    huang_equation_pair,
    quantize_signed,
    SaturationError,
    signed_pair,
)
from codex_veri.parsers import (
    EvidenceFormatError,
    ParsedPair,
    parse_cal_pairs,
    validate_pair_coverage,
)


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
BASELINE_LOG = WORKSPACE / "spectre_sim" / "results" / "codex_20260722" / "calibration_full32_baseline_stdout.log"


class QuantizerTests(unittest.TestCase):
    def test_odd_symmetry_including_half_lsb(self) -> None:
        values = [i / 2 for i in range(-280, 281)]
        for tie in ("away", "toward"):
            for value in values:
                self.assertEqual(quantize_signed(-value, tie=tie), -quantize_signed(value, tie=tie))

    def test_exact_zero_has_no_terminal_increment(self) -> None:
        self.assertEqual(quantize_signed(0.0, tie="away"), 0.0)
        pair = signed_pair(65.0, wall=65.0, step=1.0)
        self.assertEqual(pair.residual, 0.0)
        self.assertEqual(pair.d_plus, 65.0)
        self.assertEqual(pair.d_minus, -65.0)
        self.assertEqual(pair.estimate, 65.0)

    def test_huang_continuous_offset_cancellation(self) -> None:
        for offset in (-5.0, -2.0, -0.5, 0.0, 0.5, 2.0, 5.0):
            pair = huang_equation_pair(65.25, offset_plus=offset, step=None)
            self.assertAlmostEqual(pair.estimate, 65.25, places=12)

    def test_huang_offset_drift_residual(self) -> None:
        pair = huang_equation_pair(65.0, offset_plus=1.0, offset_minus=0.5, step=None)
        self.assertAlmostEqual(pair.estimate, 65.25, places=12)

    def test_huang_saturation_is_reported_not_clipped(self) -> None:
        with self.assertRaises(SaturationError):
            huang_equation_pair(65.0, offset_plus=1.0, max_abs_code=65.5)

    def test_candidate_residual_range_is_enforced(self) -> None:
        with self.assertRaises(SaturationError):
            calibrate_centered_recursive({"H1C-A": 1.0e9})


class RecursiveTests(unittest.TestCase):
    def test_ideal_centered_all_stages_exact(self) -> None:
        stages = calibrate_centered_recursive(pairs=32, step=1.0)
        for stage in stages:
            self.assertEqual(stage.estimate, stage.physical, stage.name)
            self.assertEqual(stage.error, 0.0, stage.name)

    def test_negative_residual_corrects_wall_error(self) -> None:
        physical = {"H1C-R": 65.4}
        stages = calibrate_centered_recursive(physical, pairs=1, step=None)
        by_name = estimates_by_name(stages)
        self.assertAlmostEqual(by_name["H1C-R"], 65.4)
        self.assertAlmostEqual(by_name["H2C"], 130.0)
        self.assertAlmostEqual(by_name["H32C"], 2080.0)


class EvidenceReplayTests(unittest.TestCase):
    def test_parse_complete_32_pair_by_7_target_log(self) -> None:
        pairs = parse_cal_pairs(
            BASELINE_LOG, expected_targets=range(7), expected_pairs_per_target=32
        )
        self.assertEqual(len(pairs), 224)
        self.assertEqual({p.target for p in pairs}, set(range(7)))
        for target in range(7):
            self.assertEqual(len([p for p in pairs if p.target == target]), 32)

    def test_parser_rejects_internally_inconsistent_diff(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp_dir:
            path = Path(temp_dir) / "bad.log"
            path.write_text(
                "CAL PAIR target=0 pair=0 DPLUS=999 DMINUS=999 DIFF=130.9375\n",
                encoding="utf-8",
            )
            with self.assertRaises(EvidenceFormatError):
                parse_cal_pairs(path)

    def test_coverage_rejects_duplicate_and_missing_keys(self) -> None:
        pair = ParsedPair(0, 0, 1.0, -1.0, 2.0)
        with self.assertRaises(EvidenceFormatError):
            validate_pair_coverage((pair, pair), expected_targets=(0,), expected_pairs_per_target=2)

    def test_replay_observed_recursive_bias(self) -> None:
        pairs = parse_cal_pairs(BASELINE_LOG)
        h1r = [p.estimate for p in pairs if p.target == 1]
        stages = calibrate_legacy_replay(h1r)
        estimates = estimates_by_name(stages)
        self.assertAlmostEqual(sum(h1r) / len(h1r), 65.46875, places=12)
        self.assertAlmostEqual(estimates["H1C-R"], 65.46875, places=12)
        self.assertAlmostEqual(estimates["H32C"], 2087.5, places=12)


if __name__ == "__main__":
    unittest.main()
