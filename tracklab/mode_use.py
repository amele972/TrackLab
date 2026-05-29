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
        lines = [line.strip() for line in f if line.strip()]
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


def subdivide_mesh(X, Y, Z, subdivisions=1):
    """Catmull-Clark-style mesh subdivision for smoother surfaces."""
    for _ in range(subdivisions):
        N, M = X.shape
        N2, M2 = 2 * N - 1, 2 * M - 1
        Xn = np.zeros((N2, M2))
        Yn = np.zeros((N2, M2))
        Zn = np.zeros((N2, M2))
        Xn[::2, ::2] = X
        Yn[::2, ::2] = Y
        Zn[::2, ::2] = Z
        Xn[::2, 1::2] = (X[:, :-1] + X[:, 1:]) / 2
        Yn[::2, 1::2] = (Y[:, :-1] + Y[:, 1:]) / 2
        Zn[::2, 1::2] = (Z[:, :-1] + Z[:, 1:]) / 2
        Xn[1::2, ::2] = (X[:-1, :] + X[1:, :]) / 2
        Yn[1::2, ::2] = (Y[:-1, :] + Y[1:, :]) / 2
        Zn[1::2, ::2] = (Z[:-1, :] + Z[1:, :]) / 2
        Xn[1::2, 1::2] = (X[:-1, :-1] + X[1:, :-1] + X[:-1, 1:] + X[1:, 1:]) / 4
        Yn[1::2, 1::2] = (Y[:-1, :-1] + Y[1:, :-1] + Y[:-1, 1:] + Y[1:, 1:]) / 4
        Zn[1::2, 1::2] = (Z[:-1, :-1] + Z[1:, :-1] + Z[:-1, 1:] + Z[1:, 1:]) / 4
        X, Y, Z = Xn, Yn, Zn
    return X, Y, Z


def calculate_ambient_occlusion(X, Y, Z, samples=16, radius=1.0):
    """Screen-space ambient occlusion approximation."""
    from scipy.ndimage import gaussian_filter

    N, M = Z.shape
    ao_map = np.ones((N, M))
    di_r = int(radius * 2)
    for i in range(1, N - 1):
        for j in range(1, M - 1):
            z_c = Z[i, j]
            occ = 0.0
            cnt = 0
            for di in range(-di_r, di_r + 1):
                for dj in range(-di_r, di_r + 1):
                    ni, nj = i + di, j + dj
                    if 0 <= ni < N and 0 <= nj < M:
                        dist = np.sqrt(di**2 + dj**2)
                        if 0 < dist <= radius:
                            if Z[ni, nj] > z_c:
                                occ += 1.0 / dist
                            cnt += 1
            if cnt > 0:
                ao_map[i, j] = 1.0 - min(occ / cnt, 1.0)
    return gaussian_filter(ao_map, sigma=1.0)


def export_to_obj(X, Y, Z, filename, B_faces=None):
    """Export mesh to Wavefront OBJ format."""
    N, M = X.shape
    with open(filename, "w") as f:
        f.write("# Track mesh — TrackLab\n\n# Vertices\n")
        for i in range(N):
            for j in range(M):
                f.write(f"v {X[i, j]:.6f} {Y[i, j]:.6f} {Z[i, j]:.6f}\n")
        f.write("\n# Normals\n")
        for i in range(N):
            for j in range(M):
                if i < N - 1 and j < M - 1:
                    v1 = np.array(
                        [
                            X[i + 1, j] - X[i, j],
                            Y[i + 1, j] - Y[i, j],
                            Z[i + 1, j] - Z[i, j],
                        ]
                    )
                    v2 = np.array(
                        [
                            X[i, j + 1] - X[i, j],
                            Y[i, j + 1] - Y[i, j],
                            Z[i, j + 1] - Z[i, j],
                        ]
                    )
                    n = np.cross(v1, v2)
                    m = np.linalg.norm(n)
                    n = n / m if m > 0 else np.array([0, 0, 1])
                else:
                    n = np.array([0, 0, 1])
                f.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")
        f.write("\n# Faces\n")
        for i in range(N - 1):
            for j in range(M - 1):
                v1 = i * M + j + 1
                v2 = i * M + j + 2
                v3 = (i + 1) * M + j + 2
                v4 = (i + 1) * M + j + 1
                f.write(f"f {v1}//{v1} {v2}//{v2} {v3}//{v3} {v4}//{v4}\n")
    print(f"  Exported OBJ: {filename}")


def export_to_stl(X, Y, Z, filename):
    """Export mesh to ASCII STL format."""
    N, M = X.shape
    with open(filename, "w") as f:
        f.write("solid TrackMesh\n")
        for i in range(N - 1):
            for j in range(M - 1):
                v1 = np.array([X[i, j], Y[i, j], Z[i, j]])
                v2 = np.array([X[i, j + 1], Y[i, j + 1], Z[i, j + 1]])
                v3 = np.array([X[i + 1, j + 1], Y[i + 1, j + 1], Z[i + 1, j + 1]])
                v4 = np.array([X[i + 1, j], Y[i + 1, j], Z[i + 1, j]])
                for va, vb, vc in [(v1, v2, v3), (v1, v3, v4)]:
                    n = np.cross(vb - va, vc - va)
                    mg = np.linalg.norm(n)
                    n = n / mg if mg > 0 else n
                    f.write(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n")
                    f.write("    outer loop\n")
                    f.write(f"      vertex {va[0]:.6e} {va[1]:.6e} {va[2]:.6e}\n")
                    f.write(f"      vertex {vb[0]:.6e} {vb[1]:.6e} {vb[2]:.6e}\n")
                    f.write(f"      vertex {vc[0]:.6e} {vc[1]:.6e} {vc[2]:.6e}\n")
                    f.write("    endloop\n  endfacet\n")
        f.write("endsolid TrackMesh\n")
    print(f"  Exported STL: {filename}")


def create_blender_script(obj_filename, output_dir):
    """Generate a Blender Python script for PBR rendering."""
    import os

    script_path = obj_filename.replace(".obj", "_blender.py")
    script = f'''"""
Blender script — TrackLab
Usage: blender --background --python {os.path.basename(script_path)}
"""
import bpy, os, math
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
bpy.ops.import_scene.obj(filepath=r"{obj_filename}")
track = bpy.context.selected_objects[0]; track.name = "ProtonTrack"
bpy.ops.object.shade_smooth()
sub = track.modifiers.new("Subdivision", "SUBSURF"); sub.levels = 2; sub.render_levels = 3
mat = bpy.data.materials.new("TrackMaterial"); mat.use_nodes = True
nodes = mat.node_tree.nodes; links = mat.node_tree.links; nodes.clear()
out = nodes.new("ShaderNodeOutputMaterial"); prin = nodes.new("ShaderNodeBsdfPrincipled")
prin.inputs["Base Color"].default_value = (0.9,0.9,0.95,1.0)
prin.inputs["Roughness"].default_value  = 0.3
prin.inputs["IOR"].default_value        = 1.504
prin.inputs["Transmission"].default_value = 0.8
links.new(prin.outputs["BSDF"], out.inputs["Surface"])
track.data.materials.clear(); track.data.materials.append(mat)
bpy.ops.object.camera_add(location=(50,-50,30))
cam = bpy.context.object; cam.rotation_euler=(math.radians(60),0,math.radians(45))
c = cam.constraints.new("TRACK_TO"); c.target=track; c.track_axis="TRACK_NEGATIVE_Z"; c.up_axis="UP_Y"
bpy.context.scene.camera = cam
for pos,en in [((30,-30,40),500),((-20,-20,20),200),((0,30,30),300)]:
    bpy.ops.object.light_add(type="AREA",location=pos); bpy.context.object.data.energy=en
scene = bpy.context.scene; scene.render.engine="CYCLES"; scene.cycles.samples=128
scene.render.resolution_x=1920; scene.render.resolution_y=1080; scene.render.film_transparent=True
os.makedirs(r"{output_dir}", exist_ok=True)
scene.render.filepath=os.path.join(r"{output_dir}","track_render.png")
bpy.ops.render.render(write_still=True); print("Render complete.")
'''
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"  Blender script: {script_path}")
    print(f"    Run: blender --background --python {script_path}")


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
