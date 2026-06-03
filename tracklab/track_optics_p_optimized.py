import numpy as np

# =============================================================================
# PHYSICAL CONSTANTS  (all tunable at the top)
# =============================================================================
N_PLASTIC = 1.504  # CR-39 refractive index (green illumination)
N_AIR = 1.000
MICROSCOPE_NA = 0.45  # objective numerical aperture

# Condenser NA — controls the half-angle of the illumination cone.
#   0.00  -> single axial +z ray  (identical to the legacy single-ray code, fastest)
#   0.10  -> narrow cone ~5.7 deg   (iris stopped down)
#   0.25  -> moderate cone ~14.5 deg (typical CR-39 scanning setup)
#   0.40  -> wide cone ~23.6 deg    (fully open condenser)
CONDENSER_NA = 0.25

# Rays sampled from the cone per face.
#   1  -> axial only (fast, recovers old single-ray behaviour)
#   8  -> good default for scanning datasets
#   16 -> higher accuracy near the TIR transition zone
N_CONE_RAYS = 32


# =============================================================================
# FRESNEL TRANSMITTED INTENSITY  (includes obliquity factor — Fortran DEO)
# =============================================================================


def fresnel_transmittance(n1, n2, cos_i, sin_i_sq):
    """
    Unpolarised Fresnel transmitted *intensity* (energy per unit area),
    including the beam-cross-section obliquity correction.

    This is physically equivalent to the Fortran DEO function, expressed in
    the standard form used in modern optics textbooks:

        T = 0.5 * (|ts|^2 + |tp|^2) * (n2*cos_t) / (n1*cos_i)

    where:
        ts = 2*n1*cos_i / (n1*cos_i + n2*cos_t)    [s-polarisation]
        tp = 2*n1*cos_i / (n1*cos_t + n2*cos_i)    [p-polarisation]
        cos_t = sqrt(1 - (n1/n2)^2 * sin_i^2)

    The factor (n2*cos_t)/(n1*cos_i) is the obliquity correction: it accounts
    for the change in beam cross-section as the ray crosses from a denser to a
    less-dense medium.  Without it the formula over-estimates brightness for
    oblique wall sections by ~10-20% near the critical angle.

    Parameters
    ----------
    n1, n2   : float -- incident / transmitted refractive indices  (n1 > n2)
    cos_i    : array -- cos of incident angle in medium n1  (>= 0, below TIR)
    sin_i_sq : array -- sin^2(incident angle)

    Returns
    -------
    T : array in [0, 1]
    """
    sin_t_sq = (n1 / n2) ** 2 * sin_i_sq
    sin_t_sq = np.minimum(sin_t_sq, 1.0 - 1e-9)
    cos_t = np.sqrt(np.maximum(0.0, 1.0 - sin_t_sq))

    denom_s = n1 * cos_i + n2 * cos_t
    denom_p = n1 * cos_t + n2 * cos_i
    denom_s = np.where(np.abs(denom_s) < 1e-12, 1e-12, denom_s)
    denom_p = np.where(np.abs(denom_p) < 1e-12, 1e-12, denom_p)

    ts = (2.0 * n1 * cos_i) / denom_s
    tp = (2.0 * n1 * cos_i) / denom_p

    # Obliquity factor: (n2*cos_t) / (n1*cos_i)
    safe_cos_i = np.where(cos_i < 1e-12, 1e-12, cos_i)
    obliquity = (n2 * cos_t) / (n1 * safe_cos_i)

    return np.clip(0.5 * (ts**2 + tp**2) * obliquity, 0.0, 1.0)


# =============================================================================
# VECTOR SNELL'S LAW  (equivalent to Fortran PRELOM / PRELOMGR)
# =============================================================================


def refract_rays(ray_dirs, normals, n1, n2):
    """
    Vectorised Snell's law in 3-D vector form.

    Mathematically equivalent to the Fortran PRELOM / PRELOMGR subroutines
    (which use Cramer's rule on 3x3 determinants), expressed in the compact
    vector form standard in modern ray-tracing:

        t = (n1/n2)*d + [(n1/n2)*cos_i - cos_t]*n_hat

    where d is the incident unit direction, n_hat is the surface normal
    pointing into the incident medium, and cos_i = -dot(d, n_hat).

    Parameters
    ----------
    ray_dirs : (N, 3) -- unit incident direction vectors
    normals  : (N, 3) -- unit surface normals
    n1, n2   : float  -- incident / transmitted refractive indices

    Returns
    -------
    refracted : (N, 3) -- unit refracted ray directions (NaN rows = TIR)
    tir_mask  : (N,)   -- True where total internal reflection occurs
    cos_i     : (N,)   -- cos of incident angle (always >= 0)
    """
    ratio = n1 / n2

    cos_i_raw = -np.einsum("ij,ij->i", ray_dirs, normals)
    flip = cos_i_raw < 0
    n_eff = normals.copy()
    n_eff[flip] *= -1
    cos_i = np.abs(cos_i_raw)

    sin2_t = ratio**2 * (1.0 - cos_i**2)
    tir_mask = sin2_t >= 1.0
    cos_t = np.sqrt(np.maximum(0.0, 1.0 - sin2_t))

    refracted = ratio * ray_dirs + (ratio * cos_i - cos_t)[:, np.newaxis] * n_eff
    norms_r = np.linalg.norm(refracted, axis=1, keepdims=True)
    refracted /= np.where(norms_r < 1e-12, 1.0, norms_r)
    refracted[tir_mask] = np.nan

    return refracted, tir_mask, cos_i


# =============================================================================
# CONDENSER CONE RAYS
# =============================================================================


def build_cone_rays(condenser_na, n_rays):
    """
    Unit ray directions sampling the illumination cone from below (+z).

    Returns [[0,0,1]] when n_rays <= 1 or condenser_na ~ 0, recovering the
    old axial-only behaviour exactly.  Otherwise returns 1 axial ray plus
    (n_rays-1) marginal rays evenly spaced in azimuth at half-angle
    alpha = arcsin(condenser_na).
    """
    if n_rays <= 1 or condenser_na < 1e-6:
        return np.array([[0.0, 0.0, 1.0]])

    alpha = np.arcsin(np.clip(condenser_na, 0.0, 1.0))
    rays = [[0.0, 0.0, 1.0]]
    for k in range(n_rays - 1):
        phi = 2.0 * np.pi * k / (n_rays - 1)
        rays.append(
            [np.sin(alpha) * np.cos(phi), np.sin(alpha) * np.sin(phi), np.cos(alpha)]
        )
    return np.array(rays, dtype=np.float64)


# =============================================================================
# QUAD NORMALS  (true-diagonal convention for numerical stability)
# =============================================================================


def compute_quad_normals(X, Y, Z):
    """
    Face normals for a structured N x M grid via the cross product of the
    two TRUE DIAGONALS of each quad (T1-T3 and T2-T4).

    Corner labelling:
        T1 = top-left   X[i,   j  ]
        T2 = top-right  X[i,   j+1]
        T3 = bot-right  X[i+1, j+1]
        T4 = bot-left   X[i+1, j  ]

    Using the true diagonals (T1->T3 and T2->T4) rather than parallel edges
    (Legacy Fortran ANORMALA used T1-T4 and T2-T3, which are PARALLEL EDGES and give
    a zero normal on a flat grid).  The true-diagonal cross product is always
    non-zero for a non-degenerate quad and is more stable near the track tip.

    Returns
    -------
    nx, ny, nz : (N-1, M-1) unit normal components (from diagonal cross product, for stability)
    areas      : (N-1, M-1) face area from parallel edge cross product (um^2)
    projected_z : (N-1, M-1) Z-component of parallel edge cross product (for projected area calculation)
    """
    T1x, T1y, T1z = X[:-1, :-1], Y[:-1, :-1], Z[:-1, :-1]
    T2x, T2y, T2z = X[:-1, 1:], Y[:-1, 1:], Z[:-1, 1:]
    T3x, T3y, T3z = X[1:, 1:], Y[1:, 1:], Z[1:, 1:]
    T4x, T4y, T4z = X[1:, :-1], Y[1:, :-1], Z[1:, :-1]

    # Diagonal T1 -> T3 (for more stable normal computation)
    d1x = T3x - T1x
    d1y = T3y - T1y
    d1z = T3z - T1z
    # Diagonal T2 -> T4
    d2x = T4x - T2x
    d2y = T4y - T2y
    d2z = T4z - T2z

    enx = d1y * d2z - d1z * d2y
    eny = d1z * d2x - d1x * d2z
    enz = d1x * d2y - d1y * d2x

    norm = np.sqrt(enx**2 + eny**2 + enz**2)
    norm = np.where(norm < 1e-12, 1.0, norm)

    # Face area via standard edge cross-product (parallel edges)
    v1x = T2x - T1x
    v1y = T2y - T1y
    v1z = T2z - T1z
    v2x = T4x - T1x
    v2y = T4y - T1y
    v2z = T4z - T1z
    cx = v1y * v2z - v1z * v2y
    cy = v1z * v2x - v1x * v2z
    cz = v1x * v2y - v1y * v2x
    areas = 0.5 * np.sqrt(cx**2 + cy**2 + cz**2)

    # For projected surface (Fortran-compatible): use Z-component of parallel edge cross product
    # Projected area = |cz| where cz = (T2-T1) × (T4-T1).z
    projected_z = cz  # This is the Z-component we need for projected area

    return enx / norm, eny / norm, enz / norm, areas, projected_z


# =============================================================================
# MAIN OPTICS FUNCTION
# =============================================================================


def track_optics_p_optimized(
    X_lab,
    Y_lab,
    Z_lab,
    debug_mode=False,
    condenser_na=CONDENSER_NA,
    n_cone_rays=N_CONE_RAYS,
    is_bottom_track=False,
):
    """
    Compute per-face optical brightness and statistics for a 3-D track mesh,
    using full vector ray tracing, obliquity-corrected Fresnel transmittance,
    and condenser cone averaging.

    Physics pipeline (per face, per cone ray)
    ------------------------------------------
    1. Compute incident angle from the dot product of ray direction and face
       normal (in the plastic, incident medium).
    2. TIR check: if (n_plastic/n_air)*sin_i >= 1, the face is dark for that
       ray.
    3. NA check: the refracted ray's angle in air must satisfy sin_t <= NA_obj;
       rays that miss the objective contribute zero brightness.
    4. Fresnel intensity T = 0.5*(ts^2+tp^2)*(n_air*cos_t)/(n_plastic*cos_i)
       includes the obliquity (beam-area) correction missing from the old code.
    5. Brightness per face = average T over all cone rays.

    Parameters
    ----------
    X_lab, Y_lab, Z_lab : (N, M) float arrays  -- mesh coordinates (um)
    debug_mode    : bool  -- print per-run diagnostics
    condenser_na  : float -- NA of illumination condenser (0 = axial only)
    n_cone_rays   : int   -- rays sampled from condenser cone per face

    Returns
    -------
    black_part    : float    -- area-weighted fraction of dark faces (B < 0.01)
    total_surface : float    -- total mesh surface area (um^2)
    vertices      : (F,3,3) -- triangle vertices for rendering
    normals       : (F,3)   -- unit face normals for rendering
    brightness    : (F,)    -- per-face brightness in [0, 1]
    """

    # 1. Quad normals (diagonal convention, stable at tip)
    nx_q, ny_q, nz_q, areas_q, projected_z_q = compute_quad_normals(X_lab, Y_lab, Z_lab)

    # Stabilize normals by preventing nearly-zero magnitudes
    # (This handles singularities at apex without creating visible artifacts)
    norm_magnitude = np.sqrt(nx_q**2 + ny_q**2 + nz_q**2)

    # For nearly-degenerate quads (very small normal magnitude),
    # blend toward the local vertical normal to avoid numerical issues
    min_norm = 1e-3
    needs_stabilization = norm_magnitude < min_norm

    if np.any(needs_stabilization):
        # For degenerate quads, use vertical normal (0, 0, 1) instead
        # This is physically reasonable at the apex where surface is nearly vertical
        nx_q[needs_stabilization] = 0.0
        ny_q[needs_stabilization] = 0.0
        nz_q[needs_stabilization] = 1.0

    Nq = nx_q.size
    normals_q = np.stack([nx_q.ravel(), ny_q.ravel(), nz_q.ravel()], axis=1)

    # Calculate projected surface from parallel edge cross product Z-component (Fortran-compatible)
    # Projected area = |projected_z_q| for each quad
    projected_surface_q = np.abs(projected_z_q.ravel())

    # 2. Triangulate for rendering
    def get_triangles(arr):
        p0 = arr[:-1, :-1]
        p1 = arr[1:, :-1]
        p2 = arr[1:, 1:]
        p3 = arr[:-1, 1:]
        return np.concatenate(
            [np.stack([p0, p1, p2], axis=-1), np.stack([p0, p2, p3], axis=-1)], axis=0
        )

    verts_all = np.stack(
        [
            get_triangles(X_lab).reshape(-1, 3),
            get_triangles(Y_lab).reshape(-1, 3),
            get_triangles(Z_lab).reshape(-1, 3),
        ],
        axis=-1,
    )

    v1r = verts_all[:, 1] - verts_all[:, 0]
    v2r = verts_all[:, 2] - verts_all[:, 0]
    nraw = np.cross(v1r, v2r)
    nmag = np.linalg.norm(nraw, axis=1)
    valid = nmag > 1e-12
    vertices = verts_all[valid]
    normals_r = nraw[valid] / nmag[valid, np.newaxis]
    areas_tri = 0.5 * nmag[valid]

    # 3. Condenser cone
    cone_rays = build_cone_rays(condenser_na, n_cone_rays)
    n_rays = len(cone_rays)

    # 4. Brightness averaged over cone rays
    brightness_q = np.zeros(Nq)

    for ray in cone_rays:
        ray_tiled = np.tile(ray, (Nq, 1))

        cos_i = np.abs(np.einsum("ij,ij->i", ray_tiled, normals_q))
        sin_i_sq = np.maximum(0.0, 1.0 - cos_i**2)

        n1 = N_AIR if is_bottom_track else N_PLASTIC
        n2 = N_PLASTIC if is_bottom_track else N_AIR

        # TIR
        tir = (n1 / n2) ** 2 * sin_i_sq >= 1.0
        # NA check (n1 * sin(i) is conserved across boundary, so we compare directly)
        na_miss = n1 * np.sqrt(sin_i_sq) > MICROSCOPE_NA

        can = ~tir & ~na_miss
        T = np.zeros(Nq)
        if np.any(can):
            T[can] = fresnel_transmittance(n1, n2, cos_i[can], sin_i_sq[can])
        brightness_q += T

    brightness_q /= n_rays

    # 5. Map quad brightness to triangles
    brt_raw = np.concatenate([brightness_q, brightness_q])
    brightness = brt_raw[valid]

    # 6. Statistics
    total_surface = float(np.sum(areas_tri))
    dark_mask = brightness < 0.01
    black_part = (
        float(np.sum(areas_tri[dark_mask])) / total_surface
        if total_surface > 0
        else 0.0
    )

    # Sum the projected surface (quad-based, matches Fortran code)
    projected_surface = float(np.sum(projected_surface_q))

    if debug_mode:
        crit_deg = np.degrees(np.arcsin(N_AIR / N_PLASTIC))
        print(
            f"[track_optics] faces={len(brightness)}  cone_rays={n_rays}"
            f"  condenser_NA={condenser_na:.2f}"
        )
        print(
            f"[track_optics] crit_angle={crit_deg:.2f} deg"
            f"  surface={total_surface:.2f} um^2  black_part={black_part:.4f}"
        )
        print(f"[track_optics] projected_surface={projected_surface:.2f} um^2")

        bright = brightness[~dark_mask]
        if len(bright):
            print(
                f"[track_optics] bright faces: mean={bright.mean():.3f}"
                f"  min={bright.min():.3f}  max={bright.max():.3f}"
            )

    return black_part, total_surface, projected_surface, vertices, normals_r, brightness
