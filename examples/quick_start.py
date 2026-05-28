"""
quick_start.py — TrackLab v1.0 Quick Start Example
========================================================
Demonstrates basic usage of the TrackLab API.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def example_proton():
    """Compute a single proton track."""
    from tracklab import (
        load_srim_data, build_vrint_interpolator, get_vt_model,
        calculate_track_parameters, get_vb_for_ion,
    )

    print("\n=== Example: Proton Track ===")

    # Load SRIM data
    interps, _ = load_srim_data()
    vt_model   = get_vt_model()

    # Parameters
    ion    = 'protons'
    energy = 1.5    # MeV
    angle  = 75.0   # degrees
    vb     = get_vb_for_ion(ion)  # 4.7 µm/h
    time   = 2.83   # hours

    # Build V(y) integral interpolator
    F_interp = build_vrint_interpolator(
        vt_model=vt_model, ion=ion, energy=energy, vb=vb)

    # Calculate track
    result = calculate_track_parameters(
        energy=energy, angle_deg=angle, vb=vb, time_etching=time,
        range_interpolator=interps[ion], F_interp=F_interp,
        ion=ion, vt_model=vt_model,
    )

    print(f"  Ion:        {ion}")
    print(f"  Energy:     {energy} MeV")
    print(f"  Angle:      {angle}°")
    print(f"  VB:         {vb} µm/h")
    print(f"  Status:     {result['status']}")
    print(f"  Depth:      {result['depth_um']:.4f} µm")
    print(f"  Major axis: {result['major_axis_um']:.4f} µm")
    print(f"  Minor axis: {result['minor_axis_um']:.4f} µm")
    print(f"  Black frac: {result['black_part']:.4f}")


def example_carbon():
    """Compute a single Carbon ion track."""
    from tracklab import (
        load_srim_data, build_vrint_interpolator, get_vt_model,
        calculate_track_parameters, get_vb_for_ion,
    )

    print("\n=== Example: Carbon Track ===")

    interps, _ = load_srim_data()
    vt_model   = get_vt_model()

    ion    = 'C'
    energy = 14.8   # MeV
    angle  = 90.0   # degrees (normal incidence)
    vb     = get_vb_for_ion(ion)  # 1.73 µm/h
    time   = 5.0    # hours

    F_interp = build_vrint_interpolator(
        vt_model=vt_model, ion=ion, energy=energy, vb=vb)

    result = calculate_track_parameters(
        energy=energy, angle_deg=angle, vb=vb, time_etching=time,
        range_interpolator=interps[ion], F_interp=F_interp,
        ion=ion, vt_model=vt_model,
    )

    print(f"  Ion:        {ion}")
    print(f"  Energy:     {energy} MeV")
    print(f"  Angle:      {angle}°")
    print(f"  VB:         {vb} µm/h")
    print(f"  Status:     {result['status']}")
    print(f"  Depth:      {result['depth_um']:.4f} µm")
    print(f"  Major axis: {result['major_axis_um']:.4f} µm")
    print(f"  Minor axis: {result['minor_axis_um']:.4f} µm")


def example_vy_comparison():
    """Compare V(y) models for different ions."""
    import numpy as np
    from tracklab.vt_utils import vt_function
    from tracklab.vt_multiion import get_model

    print("\n=== Example: V(y) Model Comparison ===")

    model = get_model()
    y_vals = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]

    print(f"\n{'y (µm)':>10}", end="")
    for name in ['protons', 'C', 'O', 'Li']:
        print(f"  {name:>10}", end="")
    print()
    print("-" * 54)

    for y in y_vals:
        print(f"{y:10.1f}", end="")
        for ion, energy in [('protons', 1.0), ('C', 14.8),
                            ('O', 22.0), ('Li', 6.75)]:
            if ion == 'protons':
                v = float(vt_function(y))
            else:
                v = float(model.V(y, ion=ion, energy=energy, vb=1.73))
            print(f"  {v:10.4f}", end="")
        print()


if __name__ == '__main__':
    example_proton()
    example_carbon()
    example_vy_comparison()
    print("\n✓ All examples completed successfully!")
