"""
quick_start.py — TrackLab v1.0 Quick Start Example
========================================================
Demonstrates basic usage of the TrackLab API.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def example_proton():
    """Compute a single proton track."""
    from tracklab import calculate_track_parameters, get_vb_for_ion

    print("\n=== Example: Proton Track ===")

    ion = "protons"
    energy = 1.5  # MeV
    angle = 75.0  # degrees
    vb = get_vb_for_ion(ion)  # 4.7 µm/h
    time = 2.83  # hours

    # Calculate track (interpolators handled automatically internally)
    result = calculate_track_parameters(
        energy_MeV_u=energy, angle_deg=angle, vb_um_h=vb, time_etching_h=time, ion=ion
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
    from tracklab import calculate_track_parameters, get_vb_for_ion

    print("\n=== Example: Carbon Track ===")

    ion = "C"
    energy = 14.8  # MeV
    angle = 90.0  # degrees (normal incidence)
    vb = get_vb_for_ion(ion)  # 1.73 µm/h
    time = 5.0  # hours

    result = calculate_track_parameters(
        energy_MeV_u=energy, angle_deg=angle, vb_um_h=vb, time_etching_h=time, ion=ion
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
    from tracklab.vt_multiion import get_model
    from tracklab.vt_utils import vt_function

    print("\n=== Example: V(y) Model Comparison ===")

    model = get_model()
    y_vals = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]

    print(f"\n{'y (µm)':>10}", end="")
    for name in ["protons", "C", "O", "Li"]:
        print(f"  {name:>10}", end="")
    print()
    print("-" * 54)

    for y in y_vals:
        print(f"{y:10.1f}", end="")
        for ion, energy in [("protons", 1.0), ("C", 14.8), ("O", 22.0), ("Li", 6.75)]:
            if ion == "protons":
                v = float(vt_function(y))
            else:
                v = float(model.V(y, ion=ion, energy=energy, vb=1.73))
            print(f"  {v:10.4f}", end="")
        print()


if __name__ == "__main__":
    example_proton()
    example_carbon()
    example_vy_comparison()
    print("\nAll examples completed successfully!")
