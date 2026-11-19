# TrackLab v1.0 — User Guide

## ⚙️ Installation

```bash
# Clone and enter directory
git clone https://github.com/amele972/TrackLab.git
cd TrackLab

# Install required dependencies in editable mode
pip install -e ".[dev]"
```

## 🚀 Execution

### Launching the Graphical Interface
```bash
python run_gui.py
```
This opens the **Unified Multi-Ion Dashboard**, featuring:
- **Left Panel**: Centralized parameter entry (Ion selection, Energy, Angle, Etching parameters).
- **Right Panel**: Analysis tabs for 7 distinctive modes of operation.

### Using the Command Line
```bash
python -m tracklab.main
```
Follow the interactive menu to select automated batch modes or configuration checks.

---

## 📊 Analysis Modes

### Mode 1: V(y) Curve Explorer
Visualize the etch-rate ratio $V(y) = V_T(y)/V_B$. Select an ion and energy to see the damage profile. You can compare different ions or overlay different alpha-particle models to validate physics assumptions.

### Mode 2: Single Track Calculation
Generate a high-fidelity 4-panel diagnostic for a specific particle.
1. **3D Interactive**: View the track surface with Snells-vector brightness.
2. **Microscope View**: 2D top-down simulation of what you would see under a lens.
3. **YZ/XZ Profiles**: Precise longitudinal cross-sections showing the overetch envelope.

### Mode 3: Reference Dataset (LUT)
Perform large-scale sweeps over energy and angle. This generates a **Lookup Table (LUT)** used for rapid detection-response mapping.

### Mode 4: FLUKA Multi-Ion Phase-Space Processor
Directly convert FLUKA Monte Carlo phase-space outputs into etched track distributions. Automatically parses particle species (protons, tritons, alpha particles, lithium, carbon, oxygen), computes effective etching times based on particle origin depth, and models detector response across complex radiation fields.

### Mode 5: Visualization & Export
Enables 3D operations:
- **Mesh Subdivision**: Smoothens the analytical surface mesh.
- **Ambient Occlusion**: Enhances depth perception in 3D plots.
- **CAD Export**: Save tracks as `.obj` or `.stl` for use in Blender or other 3D software.

---

## 💻 Programmatic API Usage

### 1. Simple Single-Track Simulation

TrackLab automatically handles SRIM interpolation and cumulative integrals internally:

```python
from tracklab import calculate_track_parameters, get_vb_for_ion

# Calculate track parameters for a 1.5 MeV proton at 75° incidence
result = calculate_track_parameters(
    energy_MeV_u=1.5,
    angle_deg=75.0,
    vb_um_h=4.7,
    time_etching_h=2.83,
    ion="protons"
)

print(f"Status:     {result['status']}")
print(f"Depth:      {result['depth_um']:.3f} µm")
print(f"Major Axis: {result['major_axis_um']:.3f} µm")
print(f"Minor Axis: {result['minor_axis_um']:.3f} µm")
print(f"Black Part: {result['black_part']:.3f}")
```

### 2. Multi-Ion FLUKA Phase-Space Processing

Process large-scale Monte Carlo transport outputs with automatic particle identification:

```python
from tracklab import process_fluka_file

# Process phase-space data across all supported ions
summary = process_fluka_file(
    file_path="examples/AmBe_01001_Phase-space_BXDRAW.txt",
    time_etching=2.83,
    output_csv="fluka_tracks.csv"
)

print(f"Simulated: {summary['processed']} particles")
print(f"Developed: {summary['developed']} etched pits")
for ion, counts in summary["ion_counts"].items():
    if counts["total"] > 0:
        print(f"  {ion:8s}: {counts['developed']}/{counts['total']} developed")
```

### 3. High-Performance Precomputed Interpolators

For large parameter sweeps or custom loops, precompute the interpolators once:

```python
from tracklab import (
    load_srim_data, build_vrint_interpolator, get_vt_model,
    calculate_track_parameters, get_vb_for_ion
)

# 1. Setup physics engine
interps, _ = load_srim_data()
vt_model = get_vt_model()

# 2. Define track parameters
ion, energy, angle = "tritons", 2.73, 90.0
vb = get_vb_for_ion(ion)

# 3. Precompute cumulative integral
F = build_vrint_interpolator(vt_model=vt_model, ion=ion, energy=energy, vb=vb)

# 4. Fast calculation
res = calculate_track_parameters(
    energy=energy,
    angle_deg=angle,
    vb=vb,
    time_etching=2.83,
    range_interpolator=interps[ion],
    F_interp=F,
    ion=ion,
    vt_model=vt_model
)

print(f"Triton Depth: {res['depth_um']:.3f} µm | Opening: {res['major_axis_um']:.3f} µm")
```

---

## ❓ Troubleshooting

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| **"ModuleNotFoundError: PyQt6"** | Missing GUI libs | `pip install PyQt6` |
| **"SRIM file not found"** | Incorrect path | Verify `SRIM_FILENAME` in `config.py` |
| **Mesh Spikes or "Beaks"** | Numerical error | v1.0 uses Z-Slices to prevent this automatically. |
| **Simulations vs Experiment Shift** | Anchor mismatch | Ensure **Surface Anchoring** is consistent in your data script. |
