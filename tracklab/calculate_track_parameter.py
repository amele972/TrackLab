"""
calculate_track_parameter.py  —  TrackLab v1.0
=====================================================
Core track calculation engine for all ions in CR-39.

Changes from v1.0
-----------------
- calculate_grid_stats() replaced by track_optics_p_optimized():
    * full 3-D vector Snell's law (replaces scalar cos_i approximation)
    * obliquity-corrected Fresnel transmittance (Fortran DEO formula)
    * condenser cone averaging (smears TIR transition zone)
    * ANORMALA-convention diagonal normals (stable near the conical tip)
- Induction range refinement (10 steps, sub-µm accuracy).
- Optical constants read from config so one edit updates everything.
"""

import math

import numpy as np
from scipy.interpolate import interp1d

from .load_srim_data import interpolate_range
from .track_optics_p_optimized import track_optics_p_optimized
from .vt_utils import fast_dint3, vt_function

# Read optical constants from config; fall back to module-level defaults
try:
    from .config import CONDENSER_NA, N_CONE_RAYS, OPTICS_MODEL
except ImportError:
    CONDENSER_NA = 0.25
    N_CONE_RAYS = 8
    OPTICS_MODEL = "optimized"


def _intersect_surface(x1i, y1i, x2i, y2i, theta_rad, removed):
    """
    Find where the line through (x1,y1)-(x2,y2) intersects the surface plane
    y = -tan(theta)*x + removed/cos(theta).

    Returns (x_int, y_int).  Falls back to the segment start on degenerate input.
    """
    dx = x2i - x1i
    if abs(dx) < 1e-10:  # vertical segment
        return x1i, y1i
    m = (y2i - y1i) / dx  # slope of track segment
    denom = m + np.tan(theta_rad)  # denominator
    if abs(denom) < 1e-10:  # track parallel to surface
        return x1i, y1i
    x_int = (removed / np.cos(theta_rad) + m * x1i - y1i) / denom
    y_int = -np.tan(theta_rad) * x_int + removed / np.cos(theta_rad)
    return x_int, y_int


def calculate_track_parameters(
    energy=None,
    angle_deg=None,
    vb=None,
    time_etching=None,
    range_interpolator=None,
    F_interp=None,
    ion=None,
    vt_model=None,
    debug: bool = False,
    plot: bool = False,
):
    """
    Calculate complete track parameters for one ion at one (energy, angle).

    Parameters (v1.0 — Multi-Ion API)
    ----------
    energy : float
        Ion kinetic energy (MeV).
    angle_deg : float
        Incident angle (degrees, 0-90).  90 = normal incidence.
    vb : float
        Bulk etch rate (µm/h).
    time_etching : float
        Etching time (hours).
    range_interpolator : PchipInterpolator
        SRIM range interpolator from load_srim_data().
    F_interp : PchipInterpolator
        Cumulative VT integral from build_vrint_interpolator().
    ion : str, optional
        Ion symbol ('protons', 'Li', 'C', 'O'). Default='protons'.
    vt_model : VTMultiIonModel, optional
        Multi-ion V(y) model. If None, uses legacy proton model.
    debug : bool
        Print diagnostic output.

    Returns
    -------
    dict with keys mapping physical parameters to their µm values.
    """
    # Default ion to proton for backward compatibility
    if ion is None:
        ion = "protons"

    # Create a V(y) = VT(y)/VB_user wrapper.
    if vt_model is not None:

        def V(y):
            return vt_model.V(y, ion=ion, energy=energy, vb=vb)
    else:
        # Legacy proton path (no vt_model initialized)
        def V(y):
            return vt_function(y)

    pi = math.pi
    theta_rad = angle_deg * pi / 180.0

    # ------------------------------------------------------------------
    # 1. Physics setup
    # ------------------------------------------------------------------
    range_val = interpolate_range(energy, range_interpolator)
    removed = vb * time_etching
    original_removed = removed
    original_range = range_val

    # Find VMAX and theoretical critical angle.
    scan_y = np.linspace(0.0, max(range_val, 10.0), 2000)
    scan_v = V(scan_y)  # V is natively vectorized
    vmax = float(np.max(scan_v))
    thetag = np.arcsin(1.0 / vmax) if vmax > 1.0 else 0.0

    if debug:
        print(f"[calc] E={energy:.3f} MeV  angle={angle_deg:.1f} deg")
        print(f"[calc] range={range_val:.3f} µm  removed={removed:.3f} µm")

    if theta_rad < thetag or energy < 0.1:
        return _result_template(
            energy, angle_deg, range_val, removed, "Angle < Critical"
        )

    # ------------------------------------------------------------------
    # 2. Induction range induct_range (bisection)
    # ------------------------------------------------------------------
    vp = V(range_val)
    induct_range = 0.0
    total_induct_range = 0.0

    if vp * np.sin(theta_rad) < 1.0:
        # Vectorized search for crossing point
        search_y = np.linspace(0.0, range_val, 4001)
        search_v = V(range_val - search_y)
        crossings = np.where(search_v * np.sin(theta_rad) >= 1.0)[0]

        if crossings.size == 0:
            return _result_template(
                energy, angle_deg, range_val, removed, "No Track Formed"
            )

        induct_range = search_y[crossings[0]]
        found = True

        if not found:
            return _result_template(
                energy, angle_deg, range_val, removed, "No Track Formed"
            )

        # 10-step bisection for sub-µm accuracy
        high, low = induct_range, max(0.0, induct_range - 0.01)
        for _ in range(10):
            mid = (low + high) / 2.0
            if V(range_val - mid) * np.sin(theta_rad) >= 1.0:
                high = mid
            else:
                low = mid
        induct_range = high

        hc = induct_range * np.sin(theta_rad)
        if hc >= removed:
            return _result_template(
                energy, angle_deg, range_val, removed, "Track below surface"
            )

        range_val -= induct_range
        removed -= hc
        time_etching -= hc / vb
        total_induct_range = induct_range

    # ------------------------------------------------------------------
    # 3. Etched distance along track
    # ------------------------------------------------------------------
    etched_dist = 0.0
    while etched_dist < range_val:
        db = fast_dint3(range_val, 0.0, etched_dist, F_interp)
        if (db / vb) >= time_etching:
            break
        etched_dist += 0.01

    etched_dist = min(etched_dist, range_val)
    rastd = etched_dist

    # ------------------------------------------------------------------
    # 4. Track profile (wall coordinates)
    # ------------------------------------------------------------------
    # Using high-resolution sampling to ensure smooth splines for slicing
    ainterval = 0.001 if rastd < 5.0 else 0.005
    nstep = max(100, int(rastd / ainterval))

    x1_arr = np.linspace(0, rastd, nstep + 1)
    y1_wall = range_val - x1_arr
    vt_arr = V(y1_wall)
    vt_arr[vt_arr < 1.0] = 1.0
    delta_wall = np.arcsin(1.0 / vt_arr)

    # Wall coordinates (envelope of spheres along trajectory)
    t_vals = np.array([fast_dint3(range_val, 0.0, xx, F_interp) for xx in x1_arr]) / vb
    overetch_w = (time_etching - t_vals) * vb
    tragx = x1_arr + overetch_w * np.sin(delta_wall)
    tragy1 = overetch_w * np.cos(delta_wall)

    # ------------------------------------------------------------------
    # 5. Build Unified Profile Envelope (Wall + Bulb)
    # ------------------------------------------------------------------
    x_prof = tragx.copy()
    r_prof = tragy1.copy()

    time_to_range = fast_dint3(range_val, 0.0, range_val, F_interp) / vb
    if time_etching > time_to_range:
        # Explicit Spherical Bulb calculation
        R_bulb = vb * (time_etching - time_to_range)
        x_bulb_center = range_val
        n_bulb = 1000
        # alpha goes from -pi/2 to pi/2 (front-facing hemisphere)
        alpha_arr = np.linspace(-np.pi / 2, np.pi / 2, n_bulb)
        x_sphere = x_bulb_center + R_bulb * np.sin(alpha_arr)
        r_sphere = R_bulb * np.cos(alpha_arr)

        # Merge using Mathematical Envelope: result = max(Wall, Bulb)
        # Use high resolution for the merged x-grid to preserve conicity
        x_all = np.unique(np.concatenate([x_prof, x_sphere]))
        if len(x_all) > 2000:
            x_all = np.linspace(np.min(x_all), np.max(x_all), 2000)

        r_wall_interp = np.interp(x_all, x_prof, r_prof, left=0.0, right=0.0)
        r_bulb_interp = np.interp(x_all, x_sphere, r_sphere, left=0.0, right=0.0)

        r_all = np.maximum(r_wall_interp, r_bulb_interp)
        x_prof, r_prof = x_all, r_all
    else:
        # Close conical tip at end of range
        if r_prof[-1] > 0.01:
            x_prof = np.append(x_prof, x_prof[-1] + 1e-4)
            r_prof = np.append(r_prof, 0.0)

    if len(x_prof) > 5:
        ux, u_idx = np.unique(x_prof, return_index=True)
        ur = r_prof[u_idx]
        if len(ux) > 3:
            f_smooth = interp1d(ux, ur, kind="linear", fill_value="extrapolate")
            x_prof = np.linspace(ux[0], ux[-1], 1000)
            r_prof = f_smooth(x_prof)
            r_prof[r_prof < 0] = 0.0

    # ------------------------------------------------------------------
    # 5. Axes and depth
    # ------------------------------------------------------------------
    tx, y_up = x_prof, r_prof
    y_low = -y_up

    depth_um = 0.0
    major_axis_um = 0.0
    minor_axis_um = 0.0
    x_int1 = x_int2 = y_int1 = y_int2 = 0.0
    total_x_list = []
    total_y_list = []

    if abs(theta_rad - pi / 2.0) < 1e-6:
        # Normal incidence
        j = 0
        while j < len(tx) and removed >= tx[j]:
            j += 1
        if j > 0:
            x_int1, y_int1 = removed, y_up[j - 1]
            x_int2, y_int2 = removed, -y_up[j - 1]
        else:
            x_int1, y_int1 = tx[0], y_up[0]
            x_int2, y_int2 = tx[0], y_low[0]

        major_axis_um = np.sqrt((x_int1 - x_int2) ** 2 + (y_int1 - y_int2) ** 2)
        minor_axis_um = major_axis_um

        start = max(0, j - 1)
        for i in range(start, len(tx)):
            total_x_list.append(tx[i])
            total_y_list.append(y_up[i])
        for k in range(1, len(tx) - start):
            idx = len(tx) - k
            if idx >= 0:
                total_x_list.append(tx[idx])
                total_y_list.append(y_low[idx])
    else:
        # Oblique incidence
        surf_line = -np.tan(theta_rad) * tx + removed / np.cos(theta_rad)

        idx_up = 0
        while idx_up < len(tx) and surf_line[idx_up] >= y_up[idx_up]:
            idx_up += 1
        idx_up = min(idx_up, len(tx) - 1)

        if idx_up > 0:
            x1i, y1i = tx[idx_up - 1], y_up[idx_up - 1]
            x2i, y2i = tx[idx_up], y_up[idx_up]
            x_int1, y_int1 = _intersect_surface(x1i, y1i, x2i, y2i, theta_rad, removed)
        else:
            x_int1, y_int1 = tx[0], y_up[0]

        idx_low = idx_up
        branch_found = True
        while idx_low < len(tx) and surf_line[idx_low] >= y_low[idx_low]:
            idx_low += 1
        if idx_low >= len(tx):
            branch_found = False

        if branch_found and idx_low < len(tx) and idx_low > 0:
            x1i, y1i = tx[idx_low - 1], y_low[idx_low - 1]
            x2i, y2i = tx[idx_low], y_low[idx_low]
            x_int2, y_int2 = _intersect_surface(x1i, y1i, x2i, y2i, theta_rad, removed)
        else:
            j_sec = len(tx) - 1
            while j_sec >= 0 and surf_line[j_sec] >= y_up[j_sec]:
                j_sec -= 1
            j_sec = max(j_sec, 0)
            if j_sec < len(tx) - 1:
                x1i, y1i = tx[j_sec], y_up[j_sec]
                x2i, y2i = tx[j_sec + 1], y_up[j_sec + 1]
                x_int2, y_int2 = _intersect_surface(
                    x1i, y1i, x2i, y2i, theta_rad, removed
                )
            else:
                x_int2, y_int2 = x_int1, y_int1

        major_axis_um = np.sqrt((x_int1 - x_int2) ** 2 + (y_int1 - y_int2) ** 2)

        ymax = 0.0
        for i in range(len(tx)):
            if abs(y_low[i]) > 1e-10 and abs(surf_line[i]) > 1e-10:
                tmp = y_up[i] ** 2 - surf_line[i] ** 2
                if tmp > 0 and np.sqrt(tmp) > ymax:
                    ymax = np.sqrt(tmp)
        minor_axis_um = 2.0 * ymax

        j_end = idx_low if branch_found else len(tx) - 1
        # --- REVERTED TO FORTRAN STEP-BY-STEP LOGIC ---
        # Prepend the exact intersection point (x_int1, y_int1)
        total_x_list = [x_int1]
        total_y_list = [y_int1]

        # Upper branch from the first point below surface to the end
        for i in range(idx_up, len(tx)):
            total_x_list.append(tx[i])
            total_y_list.append(y_up[i])

        # Lower branch from the end back to the intersection point
        for i in range(len(tx) - 1, j_end - 1, -1):
            total_x_list.append(tx[i])
            total_y_list.append(y_low[i])

        # Append the second intersection point (x_int2, y_int2)
        total_x_list.append(x_int2)
        total_y_list.append(y_int2)

    if len(total_x_list) > 0:
        rtx = np.array(total_x_list)
        rty = np.array(total_y_list)
        rot_angle = pi - theta_rad
        ry_rot = -rtx * np.sin(rot_angle) + rty * np.cos(rot_angle)
        ry_shifted = ry_rot - ry_rot[0]
        depth_um = abs(float(np.min(ry_shifted)))

    # ------------------------------------------------------------------
    # 6. Stable 3-D mesh generation (Z-Slice Engine)
    # ------------------------------------------------------------------
    X_surf = Y_surf = Z_surf = B_faces = None
    black_part = total_surface = projected_surface = total_length_um = 0.0
    mean_brightness = 0.0

    if len(x_prof) > 5:
        N_z = 150
        N_alpha = 181
        Z_levels = np.linspace(0.0, -depth_um + 1e-4, N_z)

        X_mesh = np.zeros((N_z, N_alpha))
        Y_mesh = np.zeros((N_z, N_alpha))
        Z_mesh = np.zeros((N_z, N_alpha))

        theta_eff = max(theta_rad, 1e-5)
        sin_T = np.sin(theta_eff)
        cos_T = np.cos(theta_eff)

        alpha = np.linspace(0, 2 * np.pi, N_alpha)
        cos_alpha = np.cos(alpha)
        sign_sin = np.sign(np.sin(alpha))

        x_pa = x_prof + total_induct_range

        for i, Z_k in enumerate(Z_levels):
            if abs(cos_T) < 1e-5:
                x_L = original_removed - Z_k
                r_val = np.interp(x_L, x_pa, r_prof)
                X_mesh[i, :] = -r_val * cos_alpha
                Y_mesh[i, :] = r_val * np.sin(alpha)
                Z_mesh[i, :] = Z_k
                continue

            C_vals = (original_removed - Z_k - x_pa * sin_T) / cos_T
            f_vals = r_prof**2 - C_vals**2

            idx_pos = np.where(f_vals >= 0)[0]
            if len(idx_pos) == 0:
                idx_max = np.argmax(f_vals)
                x_min = x_max = x_pa[idx_max]
            else:
                x_min_idx = idx_pos[0]
                x_min = x_pa[x_min_idx]
                if x_min_idx > 0:
                    x0, x1 = x_pa[x_min_idx - 1], x_pa[x_min_idx]
                    f0, f1 = f_vals[x_min_idx - 1], f_vals[x_min_idx]
                    if f1 - f0 != 0:
                        x_min = x0 - f0 * (x1 - x0) / (f1 - f0)

                x_max_idx = idx_pos[-1]
                x_max = x_pa[x_max_idx]
                if x_max_idx < len(x_pa) - 1:
                    x0, x1 = x_pa[x_max_idx], x_pa[x_max_idx + 1]
                    f0, f1 = f_vals[x_max_idx], f_vals[x_max_idx + 1]
                    if f1 - f0 != 0:
                        x_max = x0 - f0 * (x1 - x0) / (f1 - f0)

            if x_min > x_max:
                x_min, x_max = x_max, x_min

            x_ring = 0.5 * (x_max + x_min) + 0.5 * (x_max - x_min) * cos_alpha
            r_ring = np.interp(x_ring, x_pa, r_prof)
            C_ring = (original_removed - Z_k - x_ring * sin_T) / cos_T

            arg = np.clip(r_ring**2 - C_ring**2, 0, None)
            y_L = sign_sin * np.sqrt(arg)
            z_L = C_ring
            x_L = x_ring

            X_mesh[i, :] = x_L * cos_T - z_L * sin_T
            Y_mesh[i, :] = y_L
            Z_mesh[i, :] = Z_k

        X_surf, Y_surf, Z_surf = X_mesh, Y_mesh, Z_mesh
        total_length_um = float(np.max(X_surf) - np.min(X_surf))

        optics_func = track_optics_p_optimized
        bp, ts, ps, _v, _n, brt = optics_func(
            X_surf,
            Y_surf,
            Z_surf,
            debug_mode=debug,
            condenser_na=CONDENSER_NA,
            n_cone_rays=N_CONE_RAYS,
        )
        black_part, total_surface, projected_surface = bp, ts, ps

        N_rows, N_cols = X_surf.shape
        Nq = (N_rows - 1) * (N_cols - 1)
        if len(brt) >= 2 * Nq:
            B_faces = 0.5 * (brt[:Nq] + brt[Nq : 2 * Nq]).reshape(
                N_rows - 1, N_cols - 1
            )
        elif len(brt) >= Nq:
            B_faces = brt[:Nq].reshape(N_rows - 1, N_cols - 1)
        else:
            B_faces = np.zeros((N_rows - 1, N_cols - 1))

        if B_faces is not None and B_faces.size > 0:
            mean_brightness = float(np.mean(B_faces))

    return {
        "energy": energy,
        "angle_deg": angle_deg,
        "theta_rad": theta_rad,
        "ion": ion,
        "depth_um": depth_um,
        "major_axis_um": major_axis_um,
        "minor_axis_um": minor_axis_um,
        "black_part": black_part,
        "total_surface": total_surface,
        "projected_surface": projected_surface,
        "total_length_um": total_length_um,
        "mean_brightness": mean_brightness,
        "X_surf": X_surf,
        "Y_surf": Y_surf,
        "Z_surf": Z_surf,
        "B_faces": B_faces,
        "indicator": 1,
        "status": "Developed",
        "removed_um": original_removed,
        "range_um": original_range,
        "etched_dist_um": etched_dist,
        "induct_range_um": total_induct_range,
        "x_prof": x_prof,
        "r_prof": r_prof,
    }


def _result_template(energy, angle, range_v, rem_v, status):
    """Return a failed-track result dict."""
    return {
        "energy": energy,
        "angle_deg": angle,
        "theta_rad": angle * math.pi / 180.0,
        "range_um": range_v,
        "removed_um": rem_v,
        "depth_um": 0.0,
        "black_part": 0.0,
        "projected_surface": 0.0,
        "major_axis_um": 0.0,
        "minor_axis_um": 0.0,
        "total_surface": 0.0,
        "total_length_um": 0.0,
        "mean_brightness": 0.0,
        "indicator": -1,
        "status": status,
        "X_surf": None,
        "Y_surf": None,
        "Z_surf": None,
        "B_faces": None,
        "etched_dist_um": 0.0,
        "induct_range_um": 0.0,
        "x_prof": None,
        "r_prof": None,
    }
