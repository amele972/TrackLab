"""
TrackLab v1.0 — Unified Multi-Ion Nuclear Track Detector Simulation
=========================================================================
Supports: protons, Li, C, O, alpha particles in CR-39.

This package provides:
  - V(y) etch-rate models (Dorschel for protons, BPL for heavy ions)
  - SRIM range-energy interpolation for all supported ions
  - Track geometry calculation (depth, axes, surface, optical properties)
  - LUT-based fast simulation
  - GUI with 7 modes for interactive analysis
"""

__version__ = "1.0"
__author__ = "TrackLab Team"

# ── Core physics ─────────────────────────────────────────────────────
from .calculate_track_parameter import calculate_track_parameters
from .config import (
    SRIM_FILENAME,
    SUPPORTED_IONS,
    TIME_ETCHING,
    VB,
    VB_BY_ION,
    get_vb_for_ion,
)
from .load_srim_data import (
    interpolate_range,
    load_srim_data,
)
from .track_optics_p_optimized import track_optics_p_optimized
from .vt_multiion import (
    V as V_multiion,
)
from .vt_multiion import (
    VTMultiIonModel,
    vt_bpl,
)
from .vt_multiion import (
    get_model as get_vt_model,
)
from .vt_multiion import (
    reset_model as reset_vt_model,
)
from .vt_utils import (
    build_vrint_interpolator,
    clear_vrint_cache,
    fast_dint3,
    vt_function,
    vt_params,
)

# ── Optional modules (may not be needed for basic usage) ─────────────
try:
    from .lut_engine import LUTEngine
except ImportError:
    LUTEngine = None

try:
    from .mode4_enhanced import (
        calculate_ambient_occlusion,
        create_blender_script,
        export_to_obj,
        export_to_stl,
        subdivide_mesh,
    )
except ImportError:
    pass
