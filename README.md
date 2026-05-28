# ⚛️ TrackLab — High-Fidelity Nuclear Track Analysis in PADC (CR-39)

[![Standard: CR-39](https://img.shields.io/badge/Detector-CR--39-blue.svg)](https://en.wikipedia.org/wiki/CR-39)
[![Language: Python](https://img.shields.io/badge/Language-Python%203.9+-green.svg)](https://www.python.org/)
[![Physics: Snells Law Vector](https://img.shields.io/badge/Optics-3D_Snells_Vector-orange.svg)]()
[![Ions: Multi-Ion](https://img.shields.io/badge/Ions-Protons%2C%20Alphas%2C%20Li%2C%20C%2C%20O-red.svg)]()

**TrackLab** is a modern, unified Python-based framework designed to simulate the formation, geometric development, and optical microscope appearance of charged particle tracks in poly-allyl diglycol carbonate (PADC / CR-39) detectors. 

---

## 🎯 What is TrackLab needed for?

In many nuclear physics, neutron dosimetry, space radiation protection, and hadron therapy applications, solid-state nuclear track detectors (SSNTDs) like CR-39 are used to detect charged particles. When a charged particle passes through the detector, it leaves a latent damage trail (track). Chemical etching then removes the damaged material at a faster rate than the undamaged bulk, forming sub-micrometric cavities (etched tracks) that are visible under a microscope.

**TrackLab** solves two main challenges in modern dosimetry workflows:
1. **Bridging the Gap with Monte Carlo Simulations**:
   Particle transport codes like **FLUKA**, **GEANT4**, and **MCNP** yield detailed phase-space records (energy, position, angle) of radiation fields, but these outputs cannot be directly compared to experimental microscope measurements. TrackLab acts as a physical converter, translating simulated particle phase-spaces into tangible, observable track geometries and microscope-like images.
2. **Unified Multi-Ion Modeling**:
   It unifies calculations for a wide range of ion species (protons, alpha particles, lithium, carbon, oxygen) under a single modern framework, bypassing the need for separate legacy programs.

---

## 📜 Scientific Foundations & Citations

TrackLab is a modernization, optimization, and expansion of the analytical track formation models originally developed by **D. Nikezić and K. N. Yu** and implemented in the legacy Fortran codes **TRACK_P** and **TRACK_VISION**. 

If you use TrackLab in your research, please cite both the original foundation papers and this implementation:

### Legacy Foundations (TRACK_P & TRACK_VISION)
* **Proton Tracks**:
  > D. Nikezic and K. N. Yu, *"A computer program TRACK_p for studying proton tracks in PADC detectors"*, **SoftwareX**, 5, 74–79, (2016). [DOI: 10.1016/j.softx.2016.04.006](https://doi.org/10.1016/j.softx.2016.04.006)
* **Optical Simulation**:
  > D. Nikezic and K. N. Yu, *"Computer program TRACK_vision for simulating optical appearance of etched tracks in CR-39 nuclear track detectors"*, **Computer Physics Communications**, 178(8), 591–595, (2008). [DOI: 10.1016/j.cpc.2007.11.011](https://doi.org/10.1016/j.cpc.2007.11.011)
* **Over-etched Tracks**:
  > D. Nikezic and K. N. Yu, *"Three-dimensional analytical determination of the track parameters: over-etched tracks"*, **Radiation Measurements**, 37(1), 39–45, (2003). [DOI: 10.1016/S1350-4487(02)00129-4](https://doi.org/10.1016/S1350-4487(02)00129-4)
* **Geometrical Parameters**:
  > D. Nikezić, *"Three dimensional analytical determination of the track parameters"*, **Radiation Measurements**, 32(4), 277–282, (2000). [DOI: 10.1016/S1350-4487(00)00034-2](https://doi.org/10.1016/S1350-4487(00)00034-2)

---

## 🚀 Key Improvements in TrackLab

* **Fully Vectorized Architecture**: Leverages NumPy arrays to compute entire particle trajectories simultaneously, replacing slow loop-based legacy execution.
* **Z-Slice Parametric Engine**: Eliminates legacy mesh artifacts and spikes, generating physically accurate 3D track surfaces even for extreme overetching or shallow angles.
* **Expanded Multi-Ion Models**: Out-of-the-box routing for:
  - **Protons**: Analytical Nikezic/Dorschel model.
  - **Alpha particles (He)**: Selection of 7 world-class models (Brun, Green, Yu, Hermsdorf, etc.).
  - **Heavy Ions (Li, C, O)**: Broken Power Law (BPL) fitted to experimental datasets.
* **3D Snell's Vector Optics**: Simulates microscope transmission lighting with condenser cone ray tracing and objective numerical aperture filtering, replicating actual microscope contrast and Fresnel losses.
* **User-Friendly GUI**: Interactive PyQt6 dashboard for single-track diagnostics, batch Monte Carlo processing, look-up table generation, and Blender-compatible exports.

---

## 🛠 Features & Analysis Modes

| Mode | Name | Capability |
| :--- | :--- | :--- |
| **01** | **V(y) Explorer** | Analyze etch-rate ratios with multi-model overlays and experimental data fitting. |
| **02** | **Single Track** | 4-panel diagnostic view (3D Rendering, XY Top-view, Longitudinal YZ/XZ Profiles). |
| **03** | **Reference LUT** | Generate massive Look-Up Tables with sub-µm geometric precision. |
| **04** | **FLUKA Processor** | Batch process high-energy physics phase-space files into detector responses. |
| **05** | **Ultra-3D High** | Premium visualization with Ambient Occlusion, Catmull-Clark subdivision, and Blender export. |
| **06** | **Fast Interpolation** | Bypass physics/optics using precomputed LUTs for high-speed statistics. |

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

- `tracklab/`: Core library package (installable via `setup.py`).
  - `data/`: Tabulated SRIM range-energy datasets for CR-39 and calibration fits.
  - `gui/`: Tab implementation and layout configuration for the PyQt6 dashboard.
  - `lut_engine.py`: Numerical integration solver and Look-Up Table (LUT) manager.
  - `vt_multiion.py` / `track_optics_p_optimized.py`: Core physical and optical vector solvers.
- `docs/`: In-depth documentation files (`PHYSICS_MODEL.md`, `USER_GUIDE.md`, etc.).
- `examples/`: Code scripts demonstrating standalone use and batch simulations.
- `tests/`: Automated pytest unit and verification suite.
