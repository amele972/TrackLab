# ⚛️ TrackLab v1.0 — High-Fidelity Nuclear Track Analysis

[![Standard: CR-39](https://img.shields.io/badge/Detector-CR--39-blue.svg)](https://en.wikipedia.org/wiki/CR-39)
[![Physics: Snells Law Vector](https://img.shields.io/badge/Optics-3D_Snells_Vector-orange.svg)]()
[![Ion: Multi-Ion](https://img.shields.io/badge/Ions-Proton%2C%20Alpha%2C%20Li%2C%20C%2C%20O-green.svg)]()

**TrackLab v1.0** is the state-of-the-art suite for simulating and analyzing nuclear track development in CR-39 detectors. It integrates high-fidelity physical modeling with a premium PyQt6 interface, enabling research-grade analysis of particle energy and incidence spectra.

---

## 🚀 Key Innovations in v1.0

> [!IMPORTANT]
> **Z-Slice Parametric Engine**: TrackLab v1.0 completely eliminates "beak" artifacts and unphysical mesh spikes by using a horizontal slicing algorithm. 3D meshes are now generated via high-resolution analytical intersections, ensuring 100% physical accuracy even at extreme overetching or shallow angles.

> [!TIP]
> **Multi-Ion Physics Routing**: The engine automatically detects the particle type and selects the optimal $V(y)$ model:
> - **Protons**: Nikezic/Dorschel analytical model.
> - **Alpha**: Selection of 7 world-class models (Brun, Green, Yu, etc.).
> - **Heavy Ions (Li, C, O)**: Broken Power Law (BPL) fitted to experimental datasets.

---

## 🛠 Features & Analysis Modes

| Mode | Name | Capability |
| :--- | :--- | :--- |
| **01** | **V(y) explorer** | Analyze etch-rate ratios with multi-model overlays and experimental data fitting. |
| **02** | **Single Track** | 4-panel diagnostic view (3D Rendering, XY Top-view, Longitudinal YZ/XZ Profiles). |
| **03** | **Reference LUT** | Generate massive Look-Up Tables with sub-µm geometric precision. |
| **04** | **FLUKA Processor** | Batch process high-energy physics phase-space files into detector responses. |
| **05** | **Ultra-3D High** | Premium visualization with Ambient Occlusion, Catmull-Clark subdivision, and Blender export. |

---

## 🧬 Physics Deep-Dive

### Snells' Law Vector Optics
Unlike legacy scalar models, TrackLab v1.0 uses a full 3D vector implementation of Snells' law. Each face on the track interior calculates transmittance based on:
1. **Geometric incident angle** (local normal vs illumination ray).
2. **Obliquity-Corrected Fresnel loss** (DEO formula).
3. **Condenser Cone Searing**: A 32-ray cone average that naturally smears the TIR transition zone, matching real microscope observations.

### Experimental Anchoring
Simulated tracks are automatically "anchored" to the experimental material surface. This eliminates vertical offset errors and ensures that depth comparisons are physically meaningful (measured from the etched surface).

---

## 💻 Quick Start

### Installation
```bash
# Clone the repository and install dependencies
pip install -r requirements.txt
```

### Execution
```bash
# Launch the premium multi-tab GUI
python run_gui.py

# Run verification tests
pytest tests/
```

---

## 📁 Project Architecture

The **TrackLab v1.0** repository is organized to maintain a clean separation between the core simulation package and the automated validation suite:

- `tracklab_unified/`: The primary simulation package (Installable via `setup.py`).
    - `tracklab/`: Core physics engine, geometry solvers, and PyQt6 UI logic.
    - `data/`: High-resolution SRIM range-energy tables and ion-specific calibration data.
    - `run_gui.py`: Main launcher for the unified multi-mode GUI.
- `validation/`: (External Peer Directory) Automated suite for quantitative benchmarking.
    - `script/`: Core validation scripts (e.g., `gen_v4_comprehensive_validation.py`).
    - `outputs/`: High-fidelity PNG/PDF reports comparing simulation vs experimental literature.
    - `reference_code/`: For-reference Fortran implementation baseline.

---

## 📜 Authors & References
Developed for nuclear physics research. If you use this software in your research, please refer to the documentation for citation guidelines.

**TrackLab v1.0 — High-Fidelity Physics, Beautifully Rendered.**
