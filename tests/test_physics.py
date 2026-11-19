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
    assert res["black_part"] == pytest.approx(1.0, abs=1e-3)


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

    for ion in ["protons", "tritons", "alpha", "Li", "C", "O"]:
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


def test_triton_track_physics():
    """Verify physics calculations for a 2.73 MeV triton track from 6Li(n,alpha)3H."""
    interps, _ = load_srim_data()
    vt_model = get_model()

    F = build_vrint_interpolator(vt_model=vt_model, ion="tritons", energy=2.73, vb=4.7)
    res = calculate_track_parameters(
        energy=2.73,
        angle_deg=90.0,
        vb=4.7,
        time_etching=2.83,
        range_interpolator=interps["tritons"],
        F_interp=F,
        ion="tritons",
        vt_model=vt_model,
    )

    assert res["status"] == "Developed"
    assert res["depth_um"] > 0.0
    assert res["major_axis_um"] > 0.0
    assert res["major_axis_um"] == pytest.approx(
        res["minor_axis_um"], abs=1e-3
    )  # normal incidence is circular


def test_triton_model_selection():
    """Verify switching between Hermsdorf (1) and Fromm (2) triton V(y) models."""
    from tracklab.vt_utils import triton_vt_function

    y = 5.0  # residual range in um
    v_hermsdorf = float(triton_vt_function(y, model_index=1))
    v_fromm = float(triton_vt_function(y, model_index=2))

    assert v_hermsdorf >= 1.0
    assert v_fromm >= 1.0
    # Both models should yield plausible peak etch-rate ratios between 1.5 and 2.5
    assert 1.5 <= v_hermsdorf <= 2.5
    assert 1.5 <= v_fromm <= 2.5


def test_alpha_models_switching():
    """Verify switching between Brun et al. (model 2) and Hermsdorf (model 5) for alphas."""
    from tracklab.vt_utils import alpha_vt_function

    y_vals = [1.0, 5.0, 15.0]
    for y in y_vals:
        v_brun = float(alpha_vt_function(y, model_index=2))
        v_herms = float(alpha_vt_function(y, model_index=5))
        assert v_brun >= 1.0
        assert v_herms >= 1.0


def test_bottom_track_physics():
    """Verify reverse-side / bottom-surface entrance track calculation."""
    interps, _ = load_srim_data()
    vt_model = get_model()

    # Particle entering from bottom surface
    F = build_vrint_interpolator(vt_model=vt_model, ion="protons", energy=1.5, vb=4.7)
    res_bottom = calculate_track_parameters(
        energy=1.5,
        angle_deg=75.0,
        vb=4.7,
        time_etching=2.83,
        range_interpolator=interps["protons"],
        F_interp=F,
        ion="protons",
        vt_model=vt_model,
        is_bottom_track=True,
    )
    assert res_bottom["status"] == "Developed"
    assert res_bottom["depth_um"] > 0.0


def test_optics_ray_tracing():
    """Verify 3D Snell's law optics and Total Internal Reflection calculation."""
    from tracklab.track_optics_p_optimized import track_optics_p_optimized

    interps, _ = load_srim_data()
    vt_model = get_model()

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

    X_surf = res.get("X_surf")
    Y_surf = res.get("Y_surf")
    Z_surf = res.get("Z_surf")

    assert X_surf is not None and len(X_surf) > 0

    black_part, total_surf, proj_surf, vertices, normals_r, brightness = (
        track_optics_p_optimized(
            X_surf, Y_surf, Z_surf, condenser_na=0.25, n_cone_rays=8
        )
    )

    assert 0.0 <= black_part <= 1.0
    assert total_surf > 0.0
    assert proj_surf > 0.0
    assert len(brightness) > 0
