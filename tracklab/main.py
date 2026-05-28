"""
main.py — TrackLab v1.0 CLI Menu
=======================================
"""

import sys


def main():
    from .config import SUPPORTED_IONS, print_config_summary

    print("\n" + "=" * 60)
    print("  TrackLab v1.0 — Unified Multi-Ion Package")
    print("  Supported ions:", ", ".join(SUPPORTED_IONS))
    print("=" * 60)

    modes = {
        '1': ("V(y) Curve Explorer",          _mode1),
        '2': ("Single Track Calculation",      _mode2),
        '3': ("Reference Dataset Generation",  _mode3),
        '4': ("FLUKA Phase-Space Processing",  _mode4),
        '5': ("3D Enhanced + Export",           _mode5),
        '6': ("LUT Fast Simulation",            _mode6),
        '7': ("Configuration Summary",          _mode7),
        'g': ("Launch GUI",                     _gui),
        'q': ("Quit",                           None),
    }

    while True:
        print("\n  Available modes:")
        for key, (desc, _) in modes.items():
            if key == 'q':
                print(f"    [{key}] {desc}")
            else:
                print(f"    [{key}] Mode {key}: {desc}" if key.isdigit()
                      else f"    [{key}] {desc}")

        choice = input("\n  Select mode: ").strip().lower()
        if choice == 'q':
            break
        if choice in modes and modes[choice][1] is not None:
            try:
                modes[choice][1]()
            except KeyboardInterrupt:
                print("\n  Cancelled.")
            except Exception as e:
                print(f"\n  Error: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("  Invalid choice.")


def _get_ion():
    from .config import SUPPORTED_IONS
    print(f"  Available ions: {', '.join(SUPPORTED_IONS)}")
    ion = input("  Ion [protons]: ").strip() or 'protons'
    return ion


def _mode1():
    from .mode_use import run_mode1_vy_curve
    ion = _get_ion()
    energy = float(input("  Energy (MeV) [1.0]: ").strip() or 1.0)
    run_mode1_vy_curve(ion=ion, energy=energy)


def _mode2():
    from .mode_use import run_mode2_single_track
    ion = _get_ion()
    energy = float(input("  Energy (MeV) [1.5]: ").strip() or 1.5)
    angle  = float(input("  Angle (deg)  [75]: ").strip() or 75.0)
    run_mode2_single_track(ion=ion, energy=energy, angle=angle)


def _mode3():
    from .mode_use import run_mode3_reference_dataset
    ion = _get_ion()
    run_mode3_reference_dataset(ion=ion)


def _mode4():
    from .mode_use import run_mode4_fluka
    ion = _get_ion()
    run_mode4_fluka(ion=ion)


def _mode5():
    from .mode_use import run_mode5_3d_enhanced
    ion = _get_ion()
    energy = float(input("  Energy (MeV) [1.5]: ").strip() or 1.5)
    angle  = float(input("  Angle (deg)  [75]: ").strip() or 75.0)
    run_mode5_3d_enhanced(ion=ion, energy=energy, angle=angle)


def _mode6():
    from .mode_use import run_mode6_lut
    run_mode6_lut()


def _mode7():
    from .config import print_config_summary, validate_config
    print_config_summary()
    try:
        validate_config()
        print("\n  ✅ Configuration is valid.")
    except ValueError as e:
        print(f"\n  ❌ {e}")


def _gui():
    from .gui import launch
    launch()


if __name__ == '__main__':
    main()
