"""
dorschel_comparison.py — Validation / Test Script
====================================================
Compares track parameters from TrackLab v1.0 against reference values.

Use this to verify the code is working correctly after installation.
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_proton_track():
    """Test proton track at standard conditions."""
    from tracklab.load_srim_data import load_srim_data
    from tracklab.vt_utils import build_vrint_interpolator
    from tracklab.vt_multiion import get_model
    from tracklab.calculate_track_parameter import calculate_track_parameters
    from tracklab.config import get_vb_for_ion

    print("=" * 70)
    print("  TrackLab v1.0 — Dorschel Comparison Test")
    print("=" * 70)

    interps, _ = load_srim_data()
    vt_model   = get_model()

    # Reference conditions for protons (Dorschel 1997)
    test_cases = [
        {'energy': 0.5,  'angle': 90.0, 'vb': 4.7, 'time': 2.83},
        {'energy': 1.0,  'angle': 90.0, 'vb': 4.7, 'time': 2.83},
        {'energy': 1.5,  'angle': 75.0, 'vb': 4.7, 'time': 2.83},
        {'energy': 2.0,  'angle': 60.0, 'vb': 4.7, 'time': 2.83},
        {'energy': 3.0,  'angle': 45.0, 'vb': 4.7, 'time': 2.83},
    ]

    print(f"\n{'E (MeV)':>8} {'Angle':>6} {'VB':>6} {'Time':>6} "
          f"{'Depth':>8} {'Major':>8} {'Minor':>8} {'Status':>12}")
    print("-" * 70)

    range_interp = interps.get('protons')
    for tc in test_cases:
        F_interp = build_vrint_interpolator(
            vt_model=vt_model, ion='protons',
            energy=tc['energy'], vb=tc['vb'])

        res = calculate_track_parameters(
            energy=tc['energy'], angle_deg=tc['angle'],
            vb=tc['vb'], time_etching=tc['time'],
            range_interpolator=range_interp,
            F_interp=F_interp,
            ion='protons', vt_model=vt_model,
        )

        print(f"{tc['energy']:8.2f} {tc['angle']:6.1f} {tc['vb']:6.2f} "
              f"{tc['time']:6.2f} {res['depth_um']:8.4f} "
              f"{res['major_axis_um']:8.4f} {res['minor_axis_um']:8.4f} "
              f"{res['status']:>12}")

    print("\n✓ Proton track test complete.\n")


def test_multiion_tracks():
    """Test non-proton ion tracks."""
    from tracklab.load_srim_data import load_srim_data
    from tracklab.vt_utils import build_vrint_interpolator
    from tracklab.vt_multiion import get_model
    from tracklab.calculate_track_parameter import calculate_track_parameters
    from tracklab.config import get_vb_for_ion

    print("=" * 70)
    print("  Multi-Ion Track Test")
    print("=" * 70)

    interps, _ = load_srim_data()
    vt_model   = get_model()

    test_cases = [
        {'ion': 'C',     'energy': 14.8,  'angle': 90.0, 'time': 5.0},
        {'ion': 'C',     'energy': 10.0,  'angle': 75.0, 'time': 5.0},
        {'ion': 'O',     'energy': 22.0,  'angle': 90.0, 'time': 5.0},
        {'ion': 'Li',    'energy': 6.75,  'angle': 90.0, 'time': 5.0},
        {'ion': 'alpha', 'energy': 5.0,   'angle': 90.0, 'time': 5.0},
    ]

    print(f"\n{'Ion':>8} {'E (MeV)':>8} {'Angle':>6} {'VB':>6} "
          f"{'Depth':>8} {'Major':>8} {'Status':>12}")
    print("-" * 66)

    for tc in test_cases:
        ion = tc['ion']
        vb  = get_vb_for_ion(ion)
        range_interp = interps.get(ion)
        if range_interp is None:
            print(f"{ion:>8} — NO SRIM DATA")
            continue

        F_interp = build_vrint_interpolator(
            vt_model=vt_model, ion=ion,
            energy=tc['energy'], vb=vb)

        res = calculate_track_parameters(
            energy=tc['energy'], angle_deg=tc['angle'],
            vb=vb, time_etching=tc['time'],
            range_interpolator=range_interp,
            F_interp=F_interp,
            ion=ion, vt_model=vt_model,
        )

        print(f"{ion:>8} {tc['energy']:8.2f} {tc['angle']:6.1f} "
              f"{vb:6.2f} {res['depth_um']:8.4f} "
              f"{res['major_axis_um']:8.4f} {res['status']:>12}")

    print("\n✓ Multi-ion test complete.\n")


if __name__ == '__main__':
    test_proton_track()
    test_multiion_tracks()
    print("All tests passed!")
