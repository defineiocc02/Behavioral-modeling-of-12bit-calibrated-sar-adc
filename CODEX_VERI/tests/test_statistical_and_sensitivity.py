from __future__ import annotations

import math
import unittest

import numpy as np

from codex_veri.model import (
    NOMINAL_STAGES,
    calibrate_centered_recursive,
    calibrate_legacy_magnitude_recursive,
    estimates_by_name,
    signed_pair,
)


class StatisticalTests(unittest.TestCase):
    def test_noise_averaging_has_inverse_sqrt_slope(self) -> None:
        rng = np.random.default_rng(7319)
        pair_counts = np.array([1, 2, 4, 8, 16, 32], dtype=float)
        stds = []
        trials = 2000
        for pair_count_float in pair_counts:
            pair_count = int(pair_count_float)
            estimates = []
            for _ in range(trials):
                values = [
                    signed_pair(
                        65.25,
                        offset=0.3,
                        noise_plus=float(rng.normal(0.0, 0.75)),
                        noise_minus=float(rng.normal(0.0, 0.75)),
                    ).estimate
                    for _ in range(pair_count)
                ]
                estimates.append(float(np.mean(values)))
            stds.append(float(np.std(estimates, ddof=1)))
        slope = float(np.polyfit(np.log(pair_counts), np.log(stds), 1)[0])
        self.assertLessEqual(abs(slope + 0.5), 0.12)

    def test_centered_continuous_sensitivity_is_identity(self) -> None:
        for perturbed_name, nominal in NOMINAL_STAGES:
            delta = nominal * 0.01
            plus = estimates_by_name(
                calibrate_centered_recursive({perturbed_name: nominal + delta}, step=None)
            )
            minus = estimates_by_name(
                calibrate_centered_recursive({perturbed_name: nominal - delta}, step=None)
            )
            for output_name, _ in NOMINAL_STAGES:
                derivative = (plus[output_name] - minus[output_name]) / (2.0 * delta)
                expected = 1.0 if output_name == perturbed_name else 0.0
                self.assertAlmostEqual(derivative, expected, places=10)

    def test_half_lsb_offset_is_exposed_not_hidden(self) -> None:
        plus_half = signed_pair(65.0, offset=0.5, step=1.0, tie="away")
        minus_half = signed_pair(65.0, offset=-0.5, step=1.0, tie="away")
        self.assertEqual(plus_half.estimate, 65.5)
        self.assertEqual(minus_half.estimate, 65.5)
        self.assertNotEqual(plus_half.estimate, 65.0)

    def test_magnitude_zero_boundary_rectifies_symmetric_noise(self) -> None:
        rng = np.random.default_rng(44)
        noise = rng.normal(0.0, 0.75, size=(7, 32, 2))
        names = [name for name, _ in NOMINAL_STAGES]
        index = {name: i for i, name in enumerate(names)}

        def source(name: str, pair: int, direction: str) -> float:
            return float(noise[index[name], pair, 0 if direction == "+" else 1])

        legacy = calibrate_legacy_magnitude_recursive(pairs=32, noise_source=source)
        centered = calibrate_centered_recursive(pairs=32, noise_source=source)
        legacy_h32 = next(stage for stage in legacy if stage.name == "H32C")
        centered_h32 = next(stage for stage in centered if stage.name == "H32C")
        self.assertGreater(legacy_h32.error, centered_h32.error)


if __name__ == "__main__":
    unittest.main()
