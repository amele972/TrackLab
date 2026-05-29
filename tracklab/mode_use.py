"""
mode_use.py — TrackLab v1.0 CLI Modes
============================================
Merged command-line modes for all analysis types.

Includes mode4_enhanced and mode5_reference functionality folded in.
"""

import numpy as np


def run_mode1_vy_curve(ion="protons", energy=1.0, vb=None, y_max=50.0):
    """Mode 1: Plot V(y) curve for the given ion."""
    import matplotlib.pyplot as plt

    from .config import get_vb_for_ion
    from .vt_multiion import get_model
    from .vt_utils import vt_function

    if vb is None:
        vb = get_vb_for_ion(ion)

    model = get_model()
    y = np.linspace(0.01, y_max, 500)

    if ion == "protons":
        v = vt_function(y)
    else:
        v = model.V(y, ion=ion, energy=energy, vb=vb)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(y, v, "-", lw=2)
    ax.axhline(1, ls="--", alpha=0.5, color="gray")
    ax.set_xlabel("Residual range y (µm)")
    ax.set_ylabel("V(y) = VT(y) / VB")
    ax.set_title(f"V(y) for {ion} @ {energy:.2f} MeV")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def run_mode2_single_track(
    ion="protons", energy=1.5, angle=75.0, vb=None, time_etching=None, show_plot=True
):
    """Mode 2: Single track calculation and visualization."""
    import matplotlib.pyplot as plt
    from matplotlib import cm

    from .calculate_track_parameter import calculate_track_parameters
    from .config import TIME_ETCHING, get_vb_for_ion
    from .load_srim_data import load_srim_data
    from .vt_multiion import get_model
    from .vt_utils import build_vrint_interpolator

    if vb is None:
        vb = get_vb_for_ion(ion)
    if time_etching is None:
        time_etching = TIME_ETCHING

    print(f"\n{'=' * 60}")
    print(f"  Mode 2: Single Track — {ion} @ {energy:.2f} MeV, {angle:.1f}°")
    print(f"  VB = {vb:.2f} µm/h, t = {time_etching:.2f} h")
    print(f"{'=' * 60}")

    interps, _ = load_srim_data()
    range_interp = interps.get(ion)
    if range_interp is None:
        print(f"ERROR: No SRIM data for ion '{ion}'")
        return None

    vt_model = get_model()
    F_interp = build_vrint_interpolator(
        vt_model=vt_model, ion=ion, energy=energy, vb=vb
    )

    result = calculate_track_parameters(
        energy=energy,
        angle_deg=angle,
        vb=vb,
        time_etching=time_etching,
        range_interpolator=range_interp,
        F_interp=F_interp,
        ion=ion,
        vt_model=vt_model,
        debug=True,
    )

    print(f"\n  Status     : {result['status']}")
    print(f"  Depth      : {result['depth_um']:.4f} µm")
    print(f"  Major axis : {result['major_axis_um']:.4f} µm")
    print(f"  Minor axis : {result['minor_axis_um']:.4f} µm")
    print(f"  Black frac : {result['black_part']:.4f}")
    print(f"  Surface    : {result['total_surface']:.2f} µm²")
    print(f"  Range      : {result['range_um']:.3f} µm")
    print(f"  Removed    : {result['removed_um']:.3f} µm")
    print(f"  Xc         : {result['xc_um']:.3f} µm")
    print(f"  Rastd      : {result['rastd_um']:.3f} µm")

    if show_plot and result["X_surf"] is not None:
        X = result["X_surf"]
        Y = result["Y_surf"]
        Z = result["Z_surf"]
        B = result["B_faces"]

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        ax1 = fig.add_subplot(2, 2, 1, projection="3d")
        axes[0, 0].set_visible(False)
        if B is not None:
            ax1.plot_surface(
                X, Y, Z, facecolors=cm.gray(B), linewidth=0, antialiased=True
            )
        ax1.set_title(f"3D: {ion} {energy:.2f} MeV {angle:.1f}°")

        axes[0, 1].set_facecolor("#DCDCDC")
        if B is not None:
            axes[0, 1].pcolormesh(X, Y, B, cmap="gray", shading="flat")
        axes[0, 1].set_title("XY Microscope View")
        axes[0, 1].set_aspect("equal")

        axes[1, 0].fill(Y[-1, :], Z[-1, :], alpha=0.15)
        axes[1, 0].plot(Y[-1, :], Z[-1, :], lw=2)
        axes[1, 0].set_title("YZ Profile")
        axes[1, 0].set_aspect("equal")
        axes[1, 0].grid(True, alpha=0.3)

        axes[1, 1].fill(X[-1, :], Z[-1, :], alpha=0.15)
        axes[1, 1].plot(X[-1, :], Z[-1, :], lw=2)
        axes[1, 1].set_title("XZ Profile")
        axes[1, 1].set_aspect("equal")
        axes[1, 1].grid(True, alpha=0.3)

        fig.suptitle(f"{ion} Track: {energy:.2f} MeV, {angle:.1f}°", fontweight="bold")
        plt.tight_layout()
        plt.show()

    return result


def run_mode3_reference_dataset(
    ion="protons",
    e_min=0.1,
    e_max=10.0,
    n_energies=20,
    a_min=0.0,
    a_max=90.0,
    n_angles=15,
    vb=None,
    time_etching=None,
    output_csv=None,
):
    """Mode 3: Energy × Angle sweep to generate reference dataset."""
    import csv

    from .calculate_track_parameter import calculate_track_parameters
    from .config import TIME_ETCHING, get_vb_for_ion
    from .load_srim_data import load_srim_data
    from .vt_multiion import get_model
    from .vt_utils import build_vrint_interpolator

    if vb is None:
        vb = get_vb_for_ion(ion)
    if time_etching is None:
        time_etching = TIME_ETCHING
    if output_csv is None:
        output_csv = f"reference_dataset_{ion}.csv"

    energies = np.linspace(e_min, e_max, int(n_energies))
    angles = np.linspace(a_min, a_max, int(n_angles))
    total = len(energies) * len(angles)

    print(f"\nMode 3: Reference Dataset for {ion}")
    print(f"  {len(energies)} energies × {len(angles)} angles = {total} tracks")
    print(f"  VB = {vb:.2f} µm/h, t = {time_etching:.2f} h")

    interps, _ = load_srim_data()
    range_interp = interps.get(ion)
    if range_interp is None:
        print(f"ERROR: No SRIM data for ion '{ion}'")
        return

    vt_model = get_model()
    results = []
    count = 0

    for energy in energies:
        F_interp = build_vrint_interpolator(
            vt_model=vt_model, ion=ion, energy=energy, vb=vb
        )
        for angle in angles:
            res = calculate_track_parameters(
                energy=energy,
                angle_deg=angle,
                vb=vb,
                time_etching=time_etching,
                range_interpolator=range_interp,
                F_interp=F_interp,
                ion=ion,
                vt_model=vt_model,
            )
            results.append(
                {
                    "ion": ion,
                    "energy_MeV": energy,
                    "angle_deg": angle,
                    "depth_um": res["depth_um"],
                    "major_axis_um": res["major_axis_um"],
                    "minor_axis_um": res["minor_axis_um"],
                    "total_length_um": res["total_length_um"],
                    "black_part": res["black_part"],
                    "total_surface": res["total_surface"],
                    "status": res["status"],
                }
            )
            count += 1
            if count % max(1, total // 10) == 0:
                print(f"  {count}/{total} ({100 * count / total:.0f}%)")

    developed = sum(1 for r in results if r["status"] == "Developed")
    print(f"\n  Done: {developed}/{total} tracks developed")

    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"  Saved to: {output_csv}")
    return results


def run_mode4_fluka(
    ion="protons",
    input_file=None,
    vb=None,
    time_etching=None,
    output_csv=None,
    skip_header=1,
):
    """Mode 4: Process FLUKA phase-space file."""
    import csv

    from .calculate_track_parameter import calculate_track_parameters
    from .config import TIME_ETCHING, get_vb_for_ion
    from .load_srim_data import load_srim_data
    from .vt_multiion import get_model
    from .vt_utils import build_vrint_interpolator

    if vb is None:
        vb = get_vb_for_ion(ion)
    if time_etching is None:
        time_etching = TIME_ETCHING
    if input_file is None:
        input_file = input("FLUKA file path: ").strip()
    if output_csv is None:
        output_csv = f"fluka_results_{ion}.csv"

    print(f"\nMode 4: FLUKA Processing for {ion}")
    print(f"  File: {input_file}")

    interps, _ = load_srim_data()
    range_interp = interps.get(ion)
    if range_interp is None:
        print(f"ERROR: No SRIM data for ion '{ion}'")
        return

    vt_model = get_model()

    with open(input_file, "r") as f:
        lines = [l.strip() for l in f if l.strip()]
    lines = lines[skip_header:]
    total = len(lines)
    print(f"  {total} particles")

    results, developed, skipped = [], 0, 0
    for idx, line in enumerate(lines):
        try:
            parts = line.split()
            if len(parts) < 8:
                skipped += 1
                continue
            energy_mev = float(parts[1]) * 1000.0
            cosz = np.clip(float(parts[7]), -1.0, 1.0)
            if energy_mev <= 0:
                skipped += 1
                continue
            angle_deg = 90.0 - np.degrees(np.arccos(cosz))

            F_interp = build_vrint_interpolator(
                vt_model=vt_model, ion=ion, energy=energy_mev, vb=vb
            )
            res = calculate_track_parameters(
                energy=energy_mev,
                angle_deg=angle_deg,
                vb=vb,
                time_etching=time_etching,
                range_interpolator=range_interp,
                F_interp=F_interp,
                ion=ion,
                vt_model=vt_model,
            )
            results.append(
                {
                    "energy_MeV": energy_mev,
                    "angle_deg": angle_deg,
                    "depth_um": res["depth_um"],
                    "major_axis_um": res["major_axis_um"],
                    "minor_axis_um": res["minor_axis_um"],
                    "total_length_um": res["total_length_um"],
                    "status": res["status"],
                }
            )
            if res.get("indicator", -1) == 1:
                developed += 1
        except Exception:
            skipped += 1

        if (idx + 1) % max(1, total // 10) == 0:
            print(f"  {idx + 1}/{total}")

    print(f"\n  Processed: {len(results)}  Developed: {developed}  Skipped: {skipped}")
    if results:
        with open(output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"  Saved to: {output_csv}")
    return results


def run_mode5_3d_enhanced(
    ion="protons", energy=1.5, angle=75.0, vb=None, export_dir=None
):
    """Mode 5: 3D enhanced visualization with mesh export."""
    res = run_mode2_single_track(ion, energy, angle, vb, show_plot=True)
    if res is None or res.get("indicator", -1) != 1:
        print("Track not developed — skip 3D enhanced.")
        return

    if export_dir:
        try:
            import os

            from .mode4_enhanced import (
                create_blender_script,
                export_to_obj,
                export_to_stl,
                subdivide_mesh,
            )

            X, Y, Z = subdivide_mesh(
                res["X_surf"], res["Y_surf"], res["Z_surf"], subdivisions=1
            )
            base = os.path.join(
                export_dir, f"track_{ion}_{energy:.1f}MeV_{angle:.0f}deg"
            )
            export_to_obj(X, Y, Z, base + ".obj")
            export_to_stl(X, Y, Z, base + ".stl")
            create_blender_script(base + ".obj", export_dir)
            print(f"\n  Exported to: {export_dir}")
        except Exception as e:
            print(f"  Export error: {e}")
    return res


def run_mode6_lut(csv_path=None):
    """Mode 6: LUT-based fast simulation."""
    from .lut_engine import LUTEngine

    if csv_path is None:
        csv_path = input("Reference CSV path: ").strip()

    lut = LUTEngine(csv_path)
    print(f"\nLUT loaded: {lut.n_points} points")
    print(f"  Energy: {lut.energy_range[0]:.2f}–{lut.energy_range[1]:.2f} MeV")
    print(f"  Angle : {lut.angle_range[0]:.1f}–{lut.angle_range[1]:.1f}°")

    while True:
        cmd = input("\n[q]uit / [l]ookup / [i]nverse: ").strip().lower()
        if cmd == "q":
            break
        elif cmd == "l":
            e = float(input("Energy (MeV): "))
            a = float(input("Angle (deg): "))
            r = lut.query(e, a)
            print(f"  Major = {r['major_axis_um']:.3f} µm")
            print(f"  Minor = {r['minor_axis_um']:.3f} µm")
            print(f"  Total = {r['total_length_um']:.3f} µm")
            print(f"  Depth = {r['depth_um']:.3f} µm")
        elif cmd == "i":
            maj = float(input("Major axis (µm): "))
            mi = float(input("Minor axis (µm): "))
            sol = lut.inverse_lookup(maj, mi)
            print(sol.to_string())
