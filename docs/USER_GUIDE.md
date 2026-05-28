# TrackLab v1.0 — User Guide

## ⚙️ Installation

```bash
# Clone and enter directory
cd tracklab_unified

# Install required dependencies (PyQt6, NumPy, SciPy, Pandas)
pip install -r requirements.txt
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

### Mode 4: FLUKA Phase-Space Processor
Directly convert FLUKA transport output into track distributions. Ideal for validating detector response in complex radiation fields.

### Mode 5: Visualization & Export
Enables premium 3D operations:
- **Mesh Subdivision**: Smoothens the analytical Z-slice surfaces.
- **Ambient Occlusion**: Enhances depth perception in 3D plots.
- **CAD Export**: Save tracks as `.obj` or `.stl` for use in Blender or other modeling tools.

---

## 💻 Programmatic API Usage

You can integrate TrackLab physics directly into your Python scripts:

```python
from tracklab import (
    load_srim_data, build_vrint_interpolator, get_vt_model,
    calculate_track_parameters, get_vb_for_ion
)

# 1. Setup environment
interps, _ = load_srim_data()
vt_model = get_vt_model()

# 2. Define track parameters
ion, energy, angle = 'protons', 1.5, 75.0
vb = get_vb_for_ion(ion)

# 3. Precompute the cumulative integral
F = build_vrint_interpolator(vt_model=vt_model, ion=ion, energy=energy, vb=vb)

# 4. Run the high-fidelity geometry engine
result = calculate_track_parameters(
    energy=energy, 
    angle_deg=angle, 
    vb=vb, 
    time_etching=2.83,
    range_interpolator=interps[ion], 
    F_interp=F,
    ion=ion, 
    vt_model=vt_model
)

# 5. Extract English-standardized results
print(f"Track Depth:  {result['depth_um']:.3f} µm")
print(f"Major Axis:  {result['major_axis_um']:.3f} µm")
print(f"Etched Distance: {result['etched_dist_um']:.3f} µm")
```

---

## ❓ Troubleshooting

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| **"ModuleNotFoundError: PyQt6"** | Missing GUI libs | `pip install PyQt6` |
| **"SRIM file not found"** | Incorrect path | Verify `SRIM_FILENAME` in `config.py` |
| **Mesh Spikes or "Beaks"** | Numerical error | v1.0 uses Z-Slices to prevent this automatically. |
| **Simulations vs Experiment Shift** | Anchor mismatch | Ensure **Surface Anchoring** is consistent in your data script. |
