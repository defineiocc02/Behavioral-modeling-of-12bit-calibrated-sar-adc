import math

import numpy as np
import pytest

from python_cal.validation.fft_protocol import (
    FFTProtocol,
    build_coherent_differential_sine,
    measure_positive_vfs,
    validate_fft_stimulus,
)
from python_cal.fft_metrics import compute_fft_coherent, compute_fft_metrics


def test_default_protocol_is_coherent_and_safe_at_minus_half_dbfs():
    protocol = FFTProtocol()
    vin, metadata = build_coherent_differential_sine(0.8, protocol)
    assert math.gcd(protocol.n_fft, protocol.signal_bin) == 1
    assert metadata["coherent"]
    assert metadata["window"] == "rectangular"
    assert not metadata["clipping"]
    assert metadata["peak_ratio_to_vfs"] < 1.0
    assert validate_fft_stimulus(vin, 0.8, protocol)["clipping"] is False


def test_zero_dbfs_is_reported_as_nonclipping_for_discrete_phase_when_peak_is_below_vfs():
    protocol = FFTProtocol(amplitude_dbfs=0.0, phase_rad=0.123)
    vin, metadata = build_coherent_differential_sine(1.0, protocol)
    assert metadata["peak_ratio_to_vfs"] <= 1.0 + 1e-12
    assert not metadata["clipping"]
    assert np.max(np.abs(vin)) > 0.99


def test_measure_positive_vfs_uses_code_threshold_not_vref_magic():
    threshold = 0.73

    def code_from_vdiff(vdiff):
        return 4095 if vdiff >= threshold else 0

    measured = measure_positive_vfs(code_from_vdiff, 4095, guard_codes=1)
    assert measured == pytest.approx(threshold, abs=1e-9)


def test_protocol_rejects_noncoherent_bin():
    with pytest.raises(ValueError, match="coprime"):
        FFTProtocol(n_fft=4096, signal_bin=128).validate()


def test_sfdr_includes_harmonics_in_spur_search():
    n = 4096
    k = 127
    sample = np.arange(n)
    waveform = (
        np.sin(2.0 * np.pi * k * sample / n)
        + 0.1 * np.sin(2.0 * np.pi * 2 * k * sample / n)
    )
    metrics = compute_fft_coherent(waveform, n_fft=n, signal_bin=k)
    assert metrics["sfdr_db"] == pytest.approx(20.0, abs=0.05)
    assert metrics["window"] == "rectangular"
    assert metrics["enbw_bins"] == 1.0


def test_signoff_rejects_unknown_bin_instead_of_changing_window():
    waveform = np.sin(2.0 * np.pi * 7 * np.arange(64) / 64)
    with pytest.raises(ValueError, match="signal_bin_known is required"):
        compute_fft_metrics(waveform, n_fft=64)


def test_protocol_rejects_non_rectangular_window():
    with pytest.raises(ValueError, match="rectangular"):
        FFTProtocol(window="blackman").validate()
