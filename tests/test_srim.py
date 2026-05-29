"""Pytest tests for SRIM range-energy interpolation correctness in TrackLab."""

import pytest

from tracklab.load_srim_data import interpolate_range, load_srim_data


def test_srim_loading_and_ions():
    """Verify that SRIM data contains all five expected ions and loads successfully."""
    interps, data = load_srim_data()
    assert interps is not None
    assert isinstance(interps, dict)

    expected_ions = {"protons", "alpha", "Li", "C", "O"}
    assert expected_ions.issubset(interps.keys())


@pytest.mark.parametrize(
    "ion,energy,expected_range_um",
    [
        ("protons", 1.0, 19.6600),
        ("protons", 10.0, 958.9600),
        ("alpha", 5.0, 28.9900),
        ("Li", 3.0, 7.7800),
        ("C", 14.8, 16.2188),
        ("O", 5.0, 5.1700),
    ],
)
def test_srim_range_values(ion, energy, expected_range_um):
    """Verify range calculations at specific literature energies against expected values."""
    interps, _ = load_srim_data()
    r = interpolate_range(energy, ion, interps)
    # Check that ranges match expected values within 1% tolerance
    assert r == pytest.approx(expected_range_um, rel=0.01)


@pytest.mark.parametrize("ion", ["protons", "alpha", "Li", "C", "O"])
def test_srim_monotonicity(ion):
    """Ensure that range is strictly monotonically increasing with energy for all ions."""
    interps, _ = load_srim_data()
    energies = [0.5, 1.0, 2.0, 5.0, 10.0, 15.0]

    # Filter energies to valid range if required by the interpolator
    valid_energies = [e for e in energies if e >= 0.1]
    ranges = [interpolate_range(e, ion, interps) for e in valid_energies]

    # Assert each range is larger than the previous one
    for idx in range(1, len(ranges)):
        assert ranges[idx] > ranges[idx - 1], (
            f"Monotonicity failed for {ion} between {valid_energies[idx - 1]} and {valid_energies[idx]} MeV"
        )
