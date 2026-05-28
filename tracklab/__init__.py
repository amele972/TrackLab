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
__author__  = "TrackLab Team"

# ── Core physics ─────────────────────────────────────────────────────
from .config import (
    VB, VB_BY_ION, TIME_ETCHING, SUPPORTED_IONS,
    get_vb_for_ion, SRIM_FILENAME,
)

from .load_srim_data import (
    load_srim_data,
    interpolate_range,
)

from .vt_utils import (
    vt_function,
    vt_params,
    build_vrint_interpolator,
    fast_dint3,
    clear_vrint_cache,
)

from .vt_multiion import (
    VTMultiIonModel,
    vt_bpl,
    get_model       as get_vt_model,
    reset_model     as reset_vt_model,
    V               as V_multiion,
)

from .calculate_track_parameter import calculate_track_parameters

from .track_optics_p_optimized import track_optics_p_optimized

# ── Optional modules (may not be needed for basic usage) ─────────────
try:
    from .lut_engine import LUTEngine
except ImportError:
    LUTEngine = None

try:
    from .mode4_enhanced import (
        subdivide_mesh,
        calculate_ambient_occlusion,
        export_to_obj,
        export_to_stl,
        create_blender_script,
    )
except ImportError:
    pass
