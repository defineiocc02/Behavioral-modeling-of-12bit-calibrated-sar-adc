from __future__ import annotations

import math
import unittest

import numpy as np

from codex_veri.adc_performance import (
    MAX_CODE,
    NOMINAL_WEIGHTS,
    SIGNAL_INDICES,
    coherent_sine,
    convert,
    decode_decisions,
    dynamic_metrics,
    enob_to_sinad_db,
    fractional_cancellation_codes,
    folded_harmonic_bin,
    generate_split_cdac_weights,
    sar_decisions,
)


class ArchitectureTests(unittest.TestCase):
    def test_nominal_partition(self) -> None:
        signal = float(np.sum(NOMINAL_WEIGHTS[SIGNAL_INDICES]))
        auxiliary = float(np.sum(NOMINAL_WEIGHTS) - signal)
        self.assertEqual(signal, 4095.0)
        self.assertEqual(auxiliary, 192.0)
        self.assertEqual(float(np.sum(NOMINAL_WEIGHTS)), 4287.0)

    def test_physical_and_decoder_are_separate(self) -> None:
        x = coherent_sine(1024, 127)
        physical = NOMINAL_WEIGHTS.copy()
        bits = sar_decisions(x, physical)
        changed_decoder = physical.copy()
        changed_decoder[0] *= 1.01
        code_a = decode_decisions(bits, physical)
        code_b = decode_decisions(bits, changed_decoder)
        np.testing.assert_array_equal(bits, sar_decisions(x, physical))
        self.assertTrue(np.any(code_a != code_b))

    def test_unit_cap_generator_matches_nominal_when_sigma_zero(self) -> None:
        physical = generate_split_cdac_weights(np.random.default_rng(1), sigma_unit_relative=0.0)
        np.testing.assert_allclose(physical, NOMINAL_WEIGHTS, rtol=0.0, atol=0.0)

    def test_exact_weight_fractional_cancellation_is_single_quantization(self) -> None:
        rng = np.random.default_rng(18)
        physical = generate_split_cdac_weights(rng, sigma_unit_relative=0.01)
        x = coherent_sine(8192, 997)
        _, codes = fractional_cancellation_codes(x, physical, physical)
        self.assertGreater(dynamic_metrics(codes, 997).enob, 11.75)


class DynamicAnalyzerTests(unittest.TestCase):
    def test_ideal_twelve_bit_sndr(self) -> None:
        x = coherent_sine(8192, 997, amplitude_dbfs=-0.915)
        _, codes = convert(x, NOMINAL_WEIGHTS, NOMINAL_WEIGHTS)
        metrics = dynamic_metrics(codes, 997)
        self.assertGreater(metrics.enob, 11.75)
        self.assertLess(metrics.enob, 12.05)
        self.assertAlmostEqual(metrics.sndr_db, metrics.time_domain_sndr_db, places=6)
        self.assertEqual(metrics.clip_count, 0)

    def test_noncoherent_bin_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            coherent_sine(8192, 1024)
        with self.assertRaises(ValueError):
            dynamic_metrics(np.arange(8192, dtype=float), 1024)

    def test_enob_threshold_is_unrounded(self) -> None:
        self.assertAlmostEqual(enob_to_sinad_db(11.5), 70.99, places=12)
        self.assertGreater(enob_to_sinad_db(11.500001), enob_to_sinad_db(11.5))

    def test_harmonic_is_not_removed_from_sndr(self) -> None:
        n_samples = 8192
        tone_bin = 997
        n = np.arange(n_samples)
        fundamental = np.sin(2 * np.pi * tone_bin * n / n_samples)
        second = 10 ** (-65.0 / 20.0) * np.sin(2 * np.pi * 2 * tone_bin * n / n_samples)
        metrics = dynamic_metrics(2048.0 + 1800.0 * (fundamental + second), tone_bin)
        self.assertAlmostEqual(metrics.sndr_db, 65.0, delta=0.05)
        self.assertAlmostEqual(metrics.enob, (65.0 - 1.76) / 6.02, delta=0.01)

    def test_folded_harmonic_near_nyquist(self) -> None:
        self.assertEqual(folded_harmonic_bin(2, 3641, 8192), 910)
        self.assertEqual(folded_harmonic_bin(3, 3641, 8192), 2731)

    def test_no_amplitude_correction_can_create_pass(self) -> None:
        n_samples = 8192
        tone_bin = 997
        n = np.arange(n_samples)
        y = 2048.0 + 180.0 * np.sin(2 * np.pi * tone_bin * n / n_samples)
        rng = np.random.default_rng(8)
        y += rng.normal(0.0, 0.4, n_samples)
        raw = dynamic_metrics(y, tone_bin)
        self.assertLess(raw.enob, 11.5)
        # The analyzer returns the raw record result; it has no dBFS correction input.
        self.assertTrue(math.isfinite(raw.enob))


if __name__ == "__main__":
    unittest.main()
