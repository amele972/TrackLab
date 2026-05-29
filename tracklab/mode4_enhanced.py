"""
mode4_enhanced.py  —  TrackLab Proton v2.0
================================================
Mode 4b: Advanced Track Visualization with Blender-Inspired Features.
"""

import os

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm, gridspec
from mpl_toolkits.mplot3d import Axes3D  # noqa
from scipy.ndimage import gaussian_filter

from .calculate_track_parameter import calculate_track_parameters
from .config import CONDENSER_NA, MODE4_DPI, N_CONE_RAYS
from .track_optics_p_optimized import track_optics_p_optimized
from .utils import ensure_directory, format_angle, format_energy


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
        f.write("# Track mesh — TrackLab Proton v2.0\n\n# Vertices\n")
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
    script_path = obj_filename.replace(".obj", "_blender.py")
    script = f'''"""
Blender script — TrackLab Proton v2.0
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


def run_mode4_enhanced(range_interpolator, F_interp, vb, time_etching, outdir=None):
    """
    MODE 4b: Advanced Track Visualization with Blender-Inspired Features.

    Features: mesh subdivision, ambient occlusion, OBJ/STL export,
    Blender script generation, v2.0 optics model.
    """
    print("\n" + "=" * 70)
    print("MODE 4b: ADVANCED TRACK VISUALIZATION")
    print("=" * 70)
    print(f"  VB (constant) : {vb} µm/h")
    print(f"  Etching time  : {time_etching} h")
    print(f"  Condenser NA  : {CONDENSER_NA}  ({N_CONE_RAYS} rays/face)")
    print("=" * 70)

    try:
        energy = float(input("\nEnter proton energy (MeV): ").strip())
        if energy <= 0:
            raise ValueError("Energy must be positive")
    except ValueError as e:
        print(f"  Invalid energy: {e}")
        return

    try:
        angle_deg = float(input("Enter incident angle (0-90 deg): ").strip())
        if not 0 <= angle_deg <= 90:
            raise ValueError("Angle must be 0-90")
    except ValueError as e:
        print(f"  Invalid angle: {e}")
        return

    print("\n  Advanced options:")
    use_sub = input("  Apply mesh subdivision? [Y/n]: ").strip().lower() != "n"
    use_ao = input("  Calculate ambient occlusion?  [Y/n]: ").strip().lower() != "n"
    export_3d = input("  Export OBJ/STL?               [Y/n]: ").strip().lower() != "n"

    print(f"\n  Simulating proton track: {energy} MeV at {angle_deg} deg ...")

    res = calculate_track_parameters(
        energy=energy,
        angle_deg=angle_deg,
        vb=vb,
        time_etching=time_etching,
        range_interpolator=range_interpolator,
        F_interp=F_interp,
        debug=False,
    )

    if res.get("indicator", -1) != 1:
        print(f"\n  Track did not develop: {res.get('status')}")
        return

    X_surf = res["X_surf"]
    Y_surf = res["Y_surf"]
    Z_surf = res["Z_surf"]
    B_faces = res["B_faces"]
    if X_surf is None:
        print("  No mesh data available")
        return

    print("\n" + "=" * 70)
    print("  TRACK PARAMETERS")
    print("=" * 70)
    print(f"  Energy        : {energy:.2f} MeV")
    print(f"  Angle         : {angle_deg:.2f} deg")
    print(f"  Depth         : {res['depth_um']:.3f} µm")
    print(f"  Major axis    : {res['major_axis_um']:.3f} µm")
    print(f"  Minor axis    : {res['minor_axis_um']:.3f} µm")
    print(f"  Total length  : {res['total_length_um']:.3f} µm")
    print(f"  Range         : {res['range_um']:.3f} µm")
    print(f"  Black portion : {res['black_part']:.2%}")
    print(f"  Surface area  : {res['total_surface']:.2f} µm²")
    print(f"  Projected SA  : {res['projected_surface']:.2f} µm²")
    print("=" * 70)

    if use_sub:
        print("\n  Applying mesh subdivision...")
        X_surf, Y_surf, Z_surf = subdivide_mesh(X_surf, Y_surf, Z_surf, subdivisions=1)
        bp, ts, ps, _v, _n, brt = track_optics_p_optimized(
            X_surf, Y_surf, Z_surf, condenser_na=CONDENSER_NA, n_cone_rays=N_CONE_RAYS
        )
        N_rows, N_cols = X_surf.shape
        Nq = (N_rows - 1) * (N_cols - 1)
        n_valid = len(brt)
        brt_q = (
            0.5 * (brt[:Nq] + brt[Nq : 2 * Nq])
            if n_valid >= 2 * Nq
            else (brt[:Nq] if n_valid >= Nq else np.zeros(Nq))
        )
        B_faces = brt_q.reshape(N_rows - 1, N_cols - 1)
        print(f"  Mesh refined: {X_surf.shape}  black_part={bp:.4f}")

    if use_ao and B_faces is not None:
        print("\n  Calculating ambient occlusion...")
        ao = calculate_ambient_occlusion(X_surf, Y_surf, Z_surf, radius=2.0)
        ao_f = (ao[:-1, :-1] + ao[1:, :-1] + ao[:-1, 1:] + ao[1:, 1:]) / 4.0
        B_faces = B_faces * (0.3 + 0.7 * ao_f)
        print("  AO applied.")

    if export_3d and outdir:
        ensure_directory(outdir)
        base = f"track_{format_energy(energy)}MeV_{format_angle(angle_deg)}deg"
        print("\n  Exporting 3D formats...")
        export_to_obj(
            X_surf, Y_surf, Z_surf, os.path.join(outdir, f"{base}.obj"), B_faces
        )
        export_to_stl(X_surf, Y_surf, Z_surf, os.path.join(outdir, f"{base}.stl"))
        create_blender_script(os.path.join(outdir, f"{base}.obj"), outdir)

    print("\n  Generating visualization...")
    fig = plt.figure(figsize=(16, 12))
    gs = gridspec.GridSpec(2, 2)

    x_min, x_max = X_surf.min(), X_surf.max()
    y_min, y_max = Y_surf.min(), Y_surf.max()
    z_min = Z_surf.min()
    pad = (x_max - x_min) * 0.2
    lim_x = (x_min - pad, x_max + pad)
    lim_y = (y_min - pad, y_max + pad)
    lim_z = (z_min * 1.1, 0)

    ax3d = fig.add_subplot(gs[0, 0], projection="3d")
    xx, yy = np.meshgrid(np.linspace(*lim_x, 2), np.linspace(*lim_y, 2))
    ax3d.plot_surface(xx, yy, np.zeros_like(xx), color="lightblue", alpha=0.15)
    if B_faces is not None:
        ax3d.plot_surface(
            X_surf,
            Y_surf,
            Z_surf,
            facecolors=cm.gray(B_faces),
            linewidth=0,
            antialiased=True,
            shade=True,
            rstride=1,
            cstride=1,
        )
    tx = lim_x[1] - lim_x[0]
    ty = lim_y[1] - lim_y[0]
    tz = max(abs(lim_z[0]), 0.1)
    ax3d.set_box_aspect((tx, ty, tz))
    ax3d.set_xlim(lim_x)
    ax3d.set_ylim(lim_y)
    ax3d.set_zlim(lim_z)
    ax3d.set_title(f"3D  proton {energy:.1f} MeV, {angle_deg:.0f}°", fontweight="bold")
    ax3d.set_xlabel("X (µm)")
    ax3d.set_ylabel("Y (µm)")
    ax3d.set_zlabel("Z (µm)")
    ax3d.view_init(elev=20, azim=-55)
    ax3d.grid(True, alpha=0.3)

    ax_xy = fig.add_subplot(gs[0, 1])
    ax_xy.set_facecolor("#DCDCDC")
    if B_faces is not None:
        im = ax_xy.pcolormesh(
            X_surf,
            Y_surf,
            B_faces,
            cmap="gray",
            shading="flat",
            rasterized=True,
            vmin=0,
            vmax=1,
        )
        plt.colorbar(im, ax=ax_xy, fraction=0.046, pad=0.04).set_label(
            "Brightness", rotation=270, labelpad=15, fontsize=9
        )
    ax_xy.plot(X_surf[0, :], Y_surf[0, :], "r-", lw=2, label="Opening", alpha=0.7)
    ax_xy.set_xlim(lim_x)
    ax_xy.set_ylim(lim_y)
    ax_xy.set_aspect("equal")
    ax_xy.set_title("XY Microscope View", fontweight="bold")
    ax_xy.set_xlabel("X (µm)")
    ax_xy.set_ylabel("Y (µm)")
    ax_xy.legend(loc="upper right", fontsize=8)
    ax_xy.grid(True, alpha=0.3)

    ax_yz = fig.add_subplot(gs[1, 0])
    ax_yz.plot(Y_surf, Z_surf, color="black", alpha=0.05)
    ax_yz.set_xlim(lim_y)
    ax_yz.set_ylim(lim_z)
    ax_yz.set_aspect("equal")
    ax_yz.set_title("YZ Front Profile", fontweight="bold")
    ax_yz.set_xlabel("Y (µm)")
    ax_yz.set_ylabel("Z (µm)")
    ax_yz.grid(True, alpha=0.3)

    ax_xz = fig.add_subplot(gs[1, 1])
    ax_xz.plot(X_surf, Z_surf, color="black", alpha=0.05)
    ax_xz.set_xlim(lim_x)
    ax_xz.set_ylim(lim_z)
    ax_xz.set_aspect("equal")
    ax_xz.set_title("XZ Side Profile", fontweight="bold")
    ax_xz.set_xlabel("X (µm)")
    ax_xz.set_ylabel("Z (µm)")
    ax_xz.grid(True, alpha=0.3)

    fig.suptitle(
        f"Proton Track  {energy:.2f} MeV  {angle_deg:.1f}°  "
        f"(black={res['black_part']:.1%}  condenser NA={CONDENSER_NA})",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.97])

    # Save figure
    if outdir:
        # Ensure directory exists - critical for first run
        try:
            ensure_directory(outdir)
        except Exception as e:
            print(f"⚠️  Could not ensure directory: {e}")
            # Fallback: create manually
            import os as _os

            _os.makedirs(outdir, exist_ok=True)

        filename = (
            f"track_4panel_{format_energy(energy)}MeV_{format_angle(angle_deg)}deg.png"
        )
        filepath = os.path.join(outdir, filename)

        # Double-check: ensure parent directory exists before saving
        save_dir = os.path.dirname(filepath)
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except Exception as e:
                print(f"❌ ERROR: Could not create directory {save_dir}: {e}")
                print(f"   Skipping save of {filename}")
                plt.show()
                print("\n✅ Mode 4 Enhanced complete!")
                return

        try:
            plt.savefig(filepath, dpi=MODE4_DPI, bbox_inches="tight")
            print(f"\n  ✅ Saved visualization: {filepath}")
        except Exception as e:
            print(f"❌ ERROR: Could not save figure: {e}")
            print(f"   Check write permissions for {save_dir}")

    plt.show()
    print("\n  Mode 4b complete.")
    if export_3d:
        print(
            "\n  TIP: import the .obj into Blender, or run the generated _blender.py script."
        )
