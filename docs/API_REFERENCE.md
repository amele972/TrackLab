# TrackLab v1.0 — API Reference

## Core Modules

### `tracklab.config`

Central configuration file. All constants, paths, and mode parameters.

| Symbol | Type | Description |
|--------|------|-------------|
| `VB_BY_ION` | `dict` | Bulk etch rates per ion (µm/h) |
| `ALPHA_VT_MODEL` | `int` | Selection (1-7) for alpha particle V(y) model |
| `OPTICS_MODEL` | `str` | `"optimized"` or `"full_trace"` |
| `SRIM_FILENAME` | `str` | Path to unified SRIM data file |
| `VY_DATA_FILENAME` | `str` | Path to experimental V(y) Excel data |

---

### `tracklab.vt_utils`

Proton V(y) model (Nikezic/Dorschel) and integral helpers.

**Functions:**
- `vt_function(y) → float|array` — V(y) for protons (dimensionless ratio)
- `alpha_vt_function(y, model_index=None) → float|array` — Multi-model alpha support
- `build_vrint_interpolator(...) → PchipInterpolator` — Build cumulative ∫ 1/V(u) du
- `fast_dint3(R, el, d, F_interp) → float` — Evaluate integral on segment [el, d]

---

### `tracklab.vt_multiion`

Multi-ion V(y) model dispatcher using Broken Power Law (BPL) fits.

**Functions:**
- `V(y, ion, energy, vb=None) → float` — Primary dispatcher for all ions
- `get_model() → VTMultiIonModel` — Get/create the multi-ion fitting engine

**Class `VTMultiIonModel`:**
- `.V(y, ion, energy, vb=None)` — Returns dimensionless VT/VB ratio
- `.get_parameters(ion, energy)` — Get BPL {A, y0, alpha, beta}
- `.available_ions()` — List found in `Data_ions.xlsx`

---

### `tracklab.calculate_track_parameter`

Core track geometry engine using Z-slice logic.

**Function:**
```python
calculate_track_parameters(
    energy: float,          # MeV
    angle_deg: float,       # 0-90° (90=normal)
    vb: float,              # µm/h
    time_etching: float,    # h
    range_interpolator,     # SRIM interp
    F_interp,               # Integral interp
    ion: str = None,        # 'protons', 'alpha', 'Li', 'C', 'O'
    vt_model = None,        # VTMultiIonModel
    origin_z: float = 0.0,  # Depth origin (µm) for delayed etching
    from_bottom: bool = False, # Whether track originates from the bottom surface
    debug: bool = False,
) -> dict
```

**Returns dict with standardized English keys:**
- `energy`, `angle_deg`, `theta_rad`, `ion`
- `depth_um`: Geometric depth below etched surface
- `major_axis_um`, `minor_axis_um`: Opening dimensions
- `total_length_um`: projected length including tail
- `black_part`: Fraction of simulated pixels below TIR threshold
- `total_surface`: Geometric surface area (µm²)
- `removed_um`: Material removed from bulk (Vb * t)
- `range_um`: Initial projected range (SRIM)
- **`etched_dist_um`**: Distance etched along the track axis (formerly `rastd`)
- **`induct_range_um`**: Induction distance before track formation (formerly `xc`)
- `X_surf`, `Y_surf`, `Z_surf`: High-fidelity Z-slice mesh coordinates
- `B_faces`: Brightness map per face

---

### `tracklab.track_optics_p_optimized`

Vectorized Snell's Law optics engine.

**Function:**
```python
track_optics_p_optimized(
    X, Y, Z,                # Z-slice mesh
    condenser_na=0.25,      # Illumination aperture
    n_cone_rays=32,         # Searing resolution
    ...
) -> (black_part, total_surface, projected_surface, ...)
```

---

### `tracklab.lut_engine`

Fast Look-Up Table queries for batch processing.

**Class `LUTEngine(csv_path)`:**
- `.query(energy, angle)` — High-speed bicubic interpolation
- `.inverse_lookup(major, minor)` — Energy/Angle estimation
- `.process_fluka_file(path)` — Convert physics spectra to geom distributions

---

### `tracklab.mode_use`

Utility functions for mesh generation, subdivision, ambient occlusion, and CAD exports.

**Functions:**
- `subdivide_mesh(X, Y, Z, subdivisions=1) -> (X_sub, Y_sub, Z_sub)` — Smoothens analytical Z-slice surfaces by subdividing mesh quads.
- `calculate_ambient_occlusion(X, Y, Z, samples=16, radius=2.0) -> array` — Computes face-level ambient occlusion factors for depth shading.
- `export_to_obj(X, Y, Z, filepath, brightness=None)` — Exports 3D track mesh to Wavefront OBJ format with vertex color/brightness mappings.
- `export_to_stl(X, Y, Z, filepath)` — Exports 3D track mesh to stereolithography STL format.
- `create_blender_script(obj_filepath, output_dir)` — Generates a Python script for automated, high-quality rendering in Blender.
