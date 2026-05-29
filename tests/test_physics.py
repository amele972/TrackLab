"""Pytest physics validation tests for TrackLab."""

import pytest

from tracklab.calculate_track_parameter import calculate_track_parameters
from tracklab.load_srim_data import load_srim_data
from tracklab.vt_multiion import get_model
from tracklab.vt_utils import build_vrint_interpolator


def test_proton_track_physics():
    """Verify physics calculations for a 1.5 MeV proton track at 75 degrees."""
    interps, _ = load_srim_data()
    vt_model = get_model()

    # Test proton: 1.5 MeV, 75 deg, vb=4.7, etching time = 2.83
    F = build_vrint_interpolator(vt_model=vt_model, ion="protons", energy=1.5, vb=4.7)
    res = calculate_track_parameters(
        energy=1.5,
        angle_deg=75.0,
        vb=4.7,
        time_etching=2.83,
        range_interpolator=interps["protons"],
        F_interp=F,
        ion="protons",
        vt_model=vt_model,
    )

    assert res["status"] == "Developed"
    assert res["depth_um"] == pytest.approx(4.8471, abs=1e-3)
    assert res["major_axis_um"] == pytest.approx(10.7126, abs=1e-3)
    assert res["minor_axis_um"] == pytest.approx(9.8960, abs=1e-3)
    assert res["black_part"] == pytest.approx(0.7872, abs=1e-3)


def test_carbon_track_physics():
    """Verify physics calculations for a 14.8 MeV carbon track at 90 degrees."""
    interps, _ = load_srim_data()
    vt_model = get_model()

    # Test Carbon: 14.8 MeV, 90 deg, vb=1.73, etching time = 5.0
    F = build_vrint_interpolator(vt_model=vt_model, ion="C", energy=14.8, vb=1.73)
    res = calculate_track_parameters(
        energy=14.8,
        angle_deg=90.0,
        vb=1.73,
        time_etching=5.0,
        range_interpolator=interps["C"],
        F_interp=F,
        ion="C",
        vt_model=vt_model,
    )

    assert res["status"] == "Developed"
    assert res["depth_um"] == pytest.approx(14.7762, abs=1e-3)
    assert res["major_axis_um"] == pytest.approx(15.4906, abs=1e-3)
    assert res["minor_axis_um"] == pytest.approx(15.4906, abs=1e-3)


def test_critical_angle():
    """Verify that tracks are not developed if the incidence angle is below the critical angle."""
    interps, _ = load_srim_data()
    vt_model = get_model()

    # Proton at a very shallow angle (10 deg), which is below the critical angle (~27 deg)
    F = build_vrint_interpolator(vt_model=vt_model, ion="protons", energy=1.5, vb=4.7)
    res = calculate_track_parameters(
        energy=1.5,
        angle_deg=10.0,
        vb=4.7,
        time_etching=2.83,
        range_interpolator=interps["protons"],
        F_interp=F,
        ion="protons",
        vt_model=vt_model,
    )
    assert res["status"] == "Angle < Critical"
    assert res["depth_um"] == 0.0
    assert res["major_axis_um"] == 0.0
    assert res["minor_axis_um"] == 0.0


def test_v_function_bounds():
    """Verify that V(y) ratio is always strictly >= 1.0 (physical boundary condition)."""
    vt_model = get_model()
    y_test_points = [0.0, 0.1, 1.0, 5.0, 10.0, 50.0, 100.0]

    for ion in ["protons", "alpha", "Li", "C", "O"]:
        for energy in [1.0, 5.0, 15.0]:
            for y in y_test_points:
                v = vt_model.V(y, ion=ion, energy=energy, vb=1.73)
                assert v >= 1.0, (
                    f"V-ratio below 1.0 boundary for {ion} at y={y} um, E={energy} MeV: V={v}"
                )


def test_track_symmetry():
    """Verify that normal incidence (90 deg) tracks are symmetric, but oblique ones are asymmetric."""
    interps, _ = load_srim_data()
    vt_model = get_model()

    # 1. Normal incidence (90 deg) -> Symmetric
    F_norm = build_vrint_interpolator(
        vt_model=vt_model, ion="protons", energy=1.5, vb=4.7
    )
    res_norm = calculate_track_parameters(
        energy=1.5,
        angle_deg=90.0,
        vb=4.7,
        time_etching=2.83,
        range_interpolator=interps["protons"],
        F_interp=F_norm,
        ion="protons",
        vt_model=vt_model,
    )
    assert res_norm["status"] == "Developed"
    # Major and minor axis must be equal for normal incidence
    assert res_norm["major_axis_um"] == pytest.approx(
        res_norm["minor_axis_um"], rel=1e-5
    )

    # 2. Oblique incidence (75 deg) -> Asymmetric
    F_obl = build_vrint_interpolator(
        vt_model=vt_model, ion="protons", energy=1.5, vb=4.7
    )
    res_obl = calculate_track_parameters(
        energy=1.5,
        angle_deg=75.0,
        vb=4.7,
        time_etching=2.83,
        range_interpolator=interps["protons"],
        F_interp=F_obl,
        ion="protons",
        vt_model=vt_model,
    )
    assert res_obl["status"] == "Developed"
    # Major axis must be strictly greater than the minor axis for oblique tracks
    assert res_obl["major_axis_um"] > res_obl["minor_axis_um"]
