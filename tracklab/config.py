# config.py  —  TrackLab v1.0 (Unified Multi-Ion)
"""
Central configuration for TrackLab.

Edit ONLY this file to change paths, physical constants, or mode parameters.
Every other module imports from here — change once, applies everywhere.

Supported ions: protons, Li, C, O, alpha
"""

import os

# ============================================================================
# PHYSICAL PARAMETERS — ION-SPECIFIC BULK ETCH RATES
# ============================================================================

# Bulk etch rates VARY BY ION.
# VB is the etching rate in the bulk (undamaged) detector material.
VB_BY_ION = {
    "protons": 4.7,  # Proton: ~4.7 µm/h in CR-39
    "C": 1.73,  # Carbon: ~1.73 µm/h
    "O": 1.73,  # Oxygen: ~1.73 µm/h
    "Li": 1.73,  # Lithium: ~1.73 µm/h
    "alpha": 1.73,  # Alpha (He-4): ~1.73 µm/h
}

# Default/fallback value (proton)
VB = VB_BY_ION["protons"]

# ============================================================================
# PROTON VT MODELS
# ============================================================================

# Selection for the V(y) model to be used for Protons (Default = 2)
# Available models:
# 1: Double-Exponential (Original/Nominal Nikezic)
# 2: Hermsdorf (2009)
# 3: Fromm (Fitted)
# 4: Fromm (Theoretical)
# 5: Optimized Double-Exponential
PROTON_VT_MODEL = 1

# ============================================================================
# ALPHA PARTICLE VT MODELS
# ============================================================================

# Selection for the V(y) model to be used for Alpha particles (Default = 6)
# Available models:
# 1: Durrani & Bull (1987) - 1 + (A1*exp(-B1*y) + A2*exp(-B2*y)) * (1 - exp(-B3*y))
# 2: Brun et al. (1999) - 1 + exp(-a1*y + a4) - exp(-a2*y + a3) + exp(a3) - exp(a4)
# 3: Yu et al. (2005) - 1 + exp(-0.06082*y + 1.119) - exp(-0.08055*y + 1.111)
# 4: Al-Jubbori (2020) - 1 + exp(-a1*y + a2 - a3/y + a4/y**a5)
# 5: Hermsdorf (2009) - 1 + (a1/(a2+y)**b1) * (1-exp(-y/a4)) * (ln(y+a3) + y/a5)
# 6: Green et al. (1982) - 1 + (11.45*exp(-0.339y) + 4*exp(-0.44y)) * (1 - exp(-0.58y))
# 7: Yu et al. (2005a,b) - 1 + exp(-a1*y + a3) - exp(-a2*y + a3)
ALPHA_VT_MODEL = 2

# Detailed configuration for Alpha VT models (Standard Parameters)
ALPHA_MODELS_INFO = {
    1: {
        "name": "Durrani & Bull (1987) - Optimized",
        "formula": "1 + (a1*exp(-a2*y) + a3*exp(-a4*y)) * (1 - exp(-a5*y))",
        "p": {"a1": 0.4526, "a2": 0.0526, "a3": 1.0342, "a4": 0.1014, "a5": 0.8460},
    },
    2: {
        "name": "Brun et al. (1999) - Universal Aligned",
        "formula": "1 + exp(-a1*y + a4) - exp(-a2*y + a3) + exp(a3) - exp(a4)",
        "p": {"a1": 0.47194, "a2": 8.19748, "a3": 4.80204, "a4": 4.79230},
    },
    3: {
        "name": "Yu et al. (2005)",
        "formula": "1 + exp(-a1*y + a2) - exp(-a3*y + a4)",
        "p": {"a1": 0.06082, "a2": 1.119, "a3": 0.08055, "a4": 1.111},
    },
    4: {
        "name": "Al-Jubbori (2020)",
        "formula": "1 + exp(-a1*y + a2 - a3/y + a4/y**a5)",
        "p": {"a1": 0.1, "a2": 1.84, "a3": 37.78, "a4": 36.98, "a5": 0.98},
    },
    5: {
        "name": "Hermsdorf (2009)",
        "formula": "1 + (a1/(a2+y)**b1) * (1-exp(-y/a4)) * (ln(y+a3) + y/a5)",
        "p": {"a1": 390.0, "a2": 2.0, "a3": 1.0, "a4": 5.0, "a5": 80.0, "b1": 2.35},
    },
    6: {
        "name": "Green et al. (1982)",
        "formula": "1 + (a1*exp(-a2*y) + a3*exp(-a4*y)) * (1 - exp(-a5*y))",
        "p": {"a1": 11.45, "a2": 0.339, "a3": 4.0, "a4": 0.44, "a5": 0.58},
    },
    7: {
        "name": "Yu et al. (2005a,b)",
        "formula": "1 + exp(-a1*y + a3) - exp(-a2*y + a3)",
        "p": {"a1": 0.068, "a2": 0.6513, "a3": 1.1784},
    },
}

# List of all supported ions (for GUI dropdowns, etc.)
SUPPORTED_IONS = ["protons", "Li", "C", "O", "alpha"]

# Reference etching time (hours)
TIME_ETCHING = 2.83

# Backward-compatible alias
T_REF = TIME_ETCHING

# Reference detector-surface depth for etching-time scaling (cm, FLUKA units).
Z_REF = -0.55

# ============================================================================
# SRIM DATA  (unified range table with ALL ions)
# ============================================================================

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_HERE, "data")
_PROJECT_ROOT = os.path.dirname(_HERE)

SRIM_FILENAME = os.path.join(_DATA_DIR, "Rang_CR_all_ions_SRIM.dat")
SRIM_MAX_ENERGY = 30.0  # MeV — extend table via Bragg-Kleeman power law

# Experimental V(y) data for BPL fitting (multi-ion)
VY_DATA_FILENAME = os.path.join(_DATA_DIR, "Data_ions.xlsx")

# ============================================================================
# OPTICAL PARAMETERS  (v2.0 ray-tracing model)
# ============================================================================

N_PLASTIC = 1.504  # CR-39 refractive index (~550 nm)
N_AIR = 1.0  # Air refractive index
MICROSCOPE_NA = 0.45  # Objective numerical aperture
CONDENSER_NA = 0.25  # Condenser NA (illumination cone half-angle)
N_CONE_RAYS = 32

# Brightness threshold below which a face is counted as "black"
BRIGHTNESS_THRESHOLD = 0.01

# Optics model to use for simulations
# Options: "optimized" (v2.0), "full_trace" (v3.0)
OPTICS_MODEL = "optimized"

# ============================================================================
# MESH GENERATION
# ============================================================================

MESH_AZIMUTHAL_POINTS = 180
MESH_RESAMPLE_POINTS = 300
TIP_CLUSTERING_EXPONENT = 3.0

# ============================================================================
# OUTPUT CONFIGURATION
# ============================================================================

RESULTS_BASE_DIR = os.path.join(_PROJECT_ROOT, "results")

MODE_DIRECTORIES = {
    "mode3": os.path.join(RESULTS_BASE_DIR, "reference_dataset"),
    "mode4": os.path.join(RESULTS_BASE_DIR, "fluka_processing"),
    "mode2": os.path.join(RESULTS_BASE_DIR, "single_track"),
    "mode5": os.path.join(RESULTS_BASE_DIR, "enhanced_3d"),
}

OUTPUT_FILENAMES = {
    "mode3": "reference_dataset.csv",
    "mode4": "fluka_results.csv",
    "mode2": "track_{energy}MeV_{angle}deg.csv",
}

CHECKPOINT_INTERVAL = 100

# ============================================================================
# MODE 3: REFERENCE DATASET
# ============================================================================

MODE3_ENERGIES = (0.1, 10.0, 100)  # (start, stop, num_points) MeV
MODE3_ANGLES = (0.0, 90.0, 45)  # (start, stop, num_points) degrees
MODE3_VB = VB
MODE3_TIME_ETCHING = TIME_ETCHING

# ============================================================================
# MODE 4: FLUKA PROCESSING
# ============================================================================

MODE4_DEFAULT_INPUT = "phase_space_data.txt"
MODE4_MAX_LINES = None
MODE4_SKIP_HEADER_LINES = 1

# FLUKA column indices (0-based)
FLUKA_COL_PARTICLE_ID = 0
FLUKA_COL_ENERGY_GEV = 1
FLUKA_COL_X = 2
FLUKA_COL_Y = 3
FLUKA_COL_Z = 4
FLUKA_COL_COSX = 5
FLUKA_COL_COSY = 6
FLUKA_COL_COSZ = 7

# ============================================================================
# MODE 5: VISUALIZATION
# ============================================================================

MODE5_3D_FIGSIZE = (14, 10)
MODE5_2D_FIGSIZE = (10, 10)
MODE5_4PANEL_FIGSIZE = (16, 12)
MODE5_DPI = 150
MODE4_DPI = 150
MODE5_DEFAULT_ENERGY = 1.5
MODE5_DEFAULT_ANGLE = 75.0

MODE5_ENABLE_SUBDIVISION = True
MODE5_SUBDIVISION_LEVELS = 1
MODE5_ENABLE_AO = True
MODE5_AO_SAMPLES = 16
MODE5_AO_RADIUS = 2.0
MODE5_ENABLE_EXPORT = True
MODE5_GENERATE_BLENDER_SCRIPT = True
MODE5_EXPORT_OBJ = True
MODE5_EXPORT_STL = True
MODE5_EXPORT_PLY = False

# ============================================================================
# ADVANCED
# ============================================================================

ENABLE_PROGRESS_BARS = True
N_WORKERS = None  # None = single-threaded


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_vb_for_ion(ion):
    """Get bulk etch rate (VB) for a specific ion."""
    return VB_BY_ION.get(ion, VB)


def validate_config():
    """Validate configuration parameters; raise ValueError on errors."""
    errors = []
    if not VB_BY_ION or not all(v > 0 for v in VB_BY_ION.values()):
        errors.append("VB_BY_ION must have positive values for all ions")
    if VB <= 0:
        errors.append("VB (fallback) must be positive")
    if TIME_ETCHING <= 0:
        errors.append("TIME_ETCHING must be positive")
    if not os.path.exists(SRIM_FILENAME):
        errors.append(f"SRIM file not found: {SRIM_FILENAME}")
    if N_PLASTIC <= N_AIR:
        errors.append("N_PLASTIC must be > N_AIR")
    if not (0 < MICROSCOPE_NA < 1):
        errors.append("MICROSCOPE_NA must be in (0, 1)")
    if not (0.0 <= CONDENSER_NA < 1.0):
        errors.append("CONDENSER_NA must be in [0, 1)")
    if N_CONE_RAYS < 1:
        errors.append("N_CONE_RAYS must be >= 1")
    if errors:
        raise ValueError(
            "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
        )
    return True


def get_output_path(mode, filename=None):
    """Return (and create) the output path for a given mode."""
    mode_dir = MODE_DIRECTORIES.get(mode)
    if mode_dir is None:
        raise ValueError(f"Unknown mode: {mode}")
    os.makedirs(mode_dir, exist_ok=True)
    if filename is None:
        filename = OUTPUT_FILENAMES.get(mode, "")
    return os.path.join(mode_dir, filename)


def print_config_summary():
    """Print a human-readable configuration summary."""
    print("=" * 70)
    print("  TrackLab v1.0 — UNIFIED MULTI-ION CONFIGURATION")
    print("=" * 70)
    print("\n  Bulk etch rates by ion (µm/h):")
    for ion, vb in VB_BY_ION.items():
        print(f"    {ion:8s}: {vb:6.2f} µm/h")
    print("\n  Reference values:")
    print(f"    TIME_ETCHING : {TIME_ETCHING} h")
    print(f"    Z_REF        : {Z_REF} cm")
    srim_ok = "found" if os.path.exists(SRIM_FILENAME) else "NOT FOUND"
    print(f"\n  SRIM file : {os.path.basename(SRIM_FILENAME)}  [{srim_ok}]")
    print(f"  Max energy: {SRIM_MAX_ENERGY} MeV")
    vy_ok = "found" if os.path.exists(VY_DATA_FILENAME) else "NOT FOUND"
    print(f"  V(y) data : {os.path.basename(VY_DATA_FILENAME)}  [{vy_ok}]")
    print("\n  Optical model (v2.0 ray-tracing):")
    print(f"    n_plastic     : {N_PLASTIC}")
    print(f"    Objective NA  : {MICROSCOPE_NA}")
    print(f"    Condenser NA  : {CONDENSER_NA}")
    print(f"    Cone rays/face: {N_CONE_RAYS}")
    print(f"\n  Output base : {RESULTS_BASE_DIR}/")
    print("=" * 70)


if __name__ == "__main__":
    try:
        validate_config()
        print_config_summary()
        print("\nConfiguration is valid.")
    except ValueError as e:
        print(f"\nConfiguration error:\n{e}")
