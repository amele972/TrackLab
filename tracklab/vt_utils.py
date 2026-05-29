"""
vt_utils.py  —  TrackLab
====================================
Track etch-rate ratio  V(y) = VT(y) / VB  for protons in CR-39.

Physical background
-------------------
VB (bulk etch rate, µm/h) is CONSTANT for a given etching session.
VT(y) is the track etch rate, enhanced along the radiation damage trail.
The dimensionless ratio V(y) = VT(y) / VB >= 1 governs all track geometry.

Proton VT model
------------------------------------------
V(y) = 1 + (a1·exp(-a2·y) + a3·exp(-a4·y)) · (1 - exp(-a5·y))

where y = R - x  (µm) is the residual range.

Parameters:
    a1 = 0.4306
    a2 = 7.3736e-3  µm⁻¹
    a3 = 1.0559
    a4 = 0.1072     µm⁻¹
    a5 = 1.4120     µm⁻¹

These can be modified via vt_params for parameter sweeps.

Public API
----------
  vt_function(y)                          V(y) using current vt_params
  build_vrint_interpolator(...)           precompute cumulative ∫ 1/V(u) du
  fast_dint3(R, el, d, F_interp)          evaluate integral on a sub-interval
  clear_vrint_cache()                     reset interpolator cache
"""

import numpy as np
from scipy.integrate import cumulative_trapezoid
from scipy.interpolate import PchipInterpolator

# ============================================================================
from .config import PROTON_VT_PARAMS

# ============================================================================
# VT function  (Hermsdorf parametrization — protons only)
# ============================================================================


def vt_function(y):
    """
    Compute  V(y) = VT(y) / VB  for protons.

    VB is constant; only VT varies along the track (reflecting the local
    radiation damage density, which peaks near the Bragg peak at y -> 0).

    Parameters
    ----------
    y : float or array-like
        Residual range  R - x  (µm), where R is the total projected range
        and x is the distance etched along the track from the surface.

    Returns
    -------
    float or np.ndarray  —  V = VT/VB  >= 1
    """
    from .config import PROTON_VT_MODEL

    y = np.asarray(y, dtype=float)

    if PROTON_VT_MODEL == 2:
        # Hermsdorf (2009) model for protons
        # V_fit = 1 + a1/((R' + a2)**b1) * ln(R' + a3) * (1 - exp(-R'/a4)) + R'/a5
        a1 = 3.4
        a2 = 1.0
        a3 = 1.0
        a4 = 0.4
        a5 = 1500.0
        b1 = 1.0

        y_safe = np.maximum(y, 1e-9)
        term2 = (
            a1
            / ((y_safe + a2) ** b1)
            * np.log(y_safe + a3)
            * (1.0 - np.exp(-y_safe / a4))
        )
        term3 = y_safe / a5
        v = 1.0 + term2 + term3
    elif PROTON_VT_MODEL == 3:
        # Fromm (Fitted) for protons
        # V_emp = 1 + 2 * a1 * R' * (V_max - 1) / (a1**2 + R'**2)
        a1 = 3.2
        v_max = 2.20
        y_safe = np.maximum(y, 0.0)
        v = 1.0 + 2.0 * a1 * y_safe * (v_max - 1.0) / (a1**2 + y_safe**2)
    elif PROTON_VT_MODEL == 4:
        # Fromm (Theoretical) for protons
        a1 = 1.5
        v_max = 2.20
        y_safe = np.maximum(y, 0.0)
        v = 1.0 + 2.0 * a1 * y_safe * (v_max - 1.0) / (a1**2 + y_safe**2)
    elif PROTON_VT_MODEL == 5:
        # Optimized Double-Exponential
        a1 = 0.3268327
        a2 = 0.009232814
        a3 = 1.290755
        a4 = 0.1373331
        a5 = 1.116459
        v = 1.0 + (a1 * np.exp(-a2 * y) + a3 * np.exp(-a4 * y)) * (
            1.0 - np.exp(-a5 * y)
        )
    else:
        # Model 1: Double-Exponential (Original Nikezic)
        p = PROTON_VT_PARAMS
        v = 1.0 + (p["a1"] * np.exp(-p["a2"] * y) + p["a3"] * np.exp(-p["a4"] * y)) * (
            1.0 - np.exp(-p["a5"] * y)
        )

    return np.maximum(v, 1.0)


# ============================================================================
# Alpha-specific VT models (Multiple Models allowed)
# ============================================================================


def alpha_vt_function(y, model_index=None):
    """
    Compute V(y) for Alpha particles using one of the 7 allowed models.
    """
    from .config import ALPHA_MODELS_INFO, ALPHA_VT_MODEL

    if model_index is None:
        model_index = ALPHA_VT_MODEL

    y = np.asarray(y, dtype=float)
    y_safe = np.maximum(y, 1e-9)

    if model_index not in ALPHA_MODELS_INFO:
        # Fallback to proton model
        return vt_function(y)

    m_info = ALPHA_MODELS_INFO[model_index]
    p = m_info["p"]

    if model_index == 1:
        # 1: Durrani & Bull (1987) - Optimized form
        v = 1.0 + (p["a1"] * np.exp(-p["a2"] * y) + p["a3"] * np.exp(-p["a4"] * y)) * (
            1.0 - np.exp(-p["a5"] * y)
        )

    elif model_index == 2:
        # 2: Brun et al. (1999)
        v = (
            1.0
            + np.exp(-p["a1"] * y + p["a4"])
            - np.exp(-p["a2"] * y + p["a3"])
            + np.exp(p["a3"])
            - np.exp(p["a4"])
        )

    elif model_index == 3:
        # 3: Yu et al. (2005)
        v = 1.0 + np.exp(-p["a1"] * y + p["a2"]) - np.exp(-p["a3"] * y + p["a4"])

    elif model_index == 4:
        # 4: Al-Jubbori (2020)
        v = 1.0 + np.exp(
            -p["a1"] * y_safe
            + p["a2"]
            - p["a3"] / y_safe
            + p["a4"] / (y_safe ** p["a5"])
        )

    elif model_index == 5:
        # 5: Hermsdorf (2009)
        v = 1.0 + (p["a1"] / (p["a2"] + y) ** p["b1"]) * (
            1.0 - np.exp(-y / p["a4"])
        ) * (np.log(y + p["a3"]) + y / p["a5"])

    elif model_index == 6:
        # 6: Green et al. (1982)
        v = 1.0 + (p["a1"] * np.exp(-p["a2"] * y) + p["a3"] * np.exp(-p["a4"] * y)) * (
            1.0 - np.exp(-p["a5"] * y)
        )

    elif model_index == 7:
        # 7: Yu et al. (2005a,b)
        v = 1.0 + np.exp(-p["a1"] * y + p["a3"]) - np.exp(-p["a2"] * y + p["a3"])

    else:
        return vt_function(y)

    return np.maximum(v, 1.0)


# ============================================================================
# VT integral interpolator cache
# ============================================================================

_VRINT_CACHE: dict = {}


def build_vrint_interpolator(
    vt_model=None, ion=None, energy=None, vb=None, R_max: float = 6600.0, N: int = 10000
):
    """
    Build (and cache) the precomputed cumulative integral:
        F(r) = integral_0^r  1/V(u) du

    where V(u) = VT(u) / VB_user.

    Parameters
    ----------
    vt_model : VTMultiIonModel, optional
        Multi-ion model.  If None, uses legacy proton vt_function.
    ion : str, optional
        Ion symbol ('protons', 'Li', 'C', 'O').  Default 'protons'.
    energy : float, optional
        Kinetic energy (MeV).  Required when vt_model is not None.
    vb : float, optional
        User bulk etch rate (µm/h).  If None, uses the model's calibration VB.
    R_max : float
        Upper integration limit (µm).
    N : int
        Number of quadrature nodes.

    Returns
    -------
    PchipInterpolator  F(r)
    """
    # Resolve R_max automatically if not provided and energy is available
    if R_max == 6600.0 and energy is not None:
        if ion == "protons":
            # Estimation for protons: Range(um) approx 18 * E^1.78
            # We take a safe margin.
            R_max = float(20.0 * (energy**1.8) + 50.0)
        elif ion == "alpha":
            # Estimation for alphas: Range(um) approx 1.6 * E^1.5
            R_max = float(5.0 * (energy**2.0) + 50.0)
        # Cap at 6600.0 for safety
        R_max = min(R_max, 6600.0)

    # Default routing logic when no vt_model is provided (legacy or convenient path)
    if vt_model is None:
        from . import vt_multiion as vtm
        from .config import ALPHA_VT_MODEL

        # Build cache key including ion and alpha model index if applicable
        alpha_idx = ALPHA_VT_MODEL if ion == "alpha" else 0
        cache_key = (ion, alpha_idx, vb, R_max, N)

        if cache_key in _VRINT_CACHE:
            return _VRINT_CACHE[cache_key]

        u = np.linspace(0.0, R_max, N)

        # Route V(u) based on ion
        # Note: vtm.V() handles routing to alpha_vt_function and vt_function(protons) internally
        def v_func(y):
            return vtm.V(y, ion=ion, energy=energy or 1.0, vb=vb)

        f = 1.0 / np.maximum(v_func(u), 1.0)
        F = cumulative_trapezoid(f, u, initial=0.0)
        interp = PchipInterpolator(u, F, extrapolate=True)
        _VRINT_CACHE[cache_key] = interp
        return interp

    # Multi-ion support
    if ion is None:
        ion = "protons"
    if energy is None:
        raise ValueError("energy is required when using multi-ion model (vt_model)")

    cache_key = (ion, energy, vb, R_max, N)
    if cache_key in _VRINT_CACHE:
        return _VRINT_CACHE[cache_key]

    # Build V(u) = VT(u) / vb  (vb=None → uses model's calibration VB)
    def v_func(y):
        return vt_model.V(y, ion=ion, energy=energy, vb=vb)

    u = np.linspace(0.0, R_max, N)
    f = 1.0 / np.maximum(v_func(u), 1.0)  # guard V < 1
    F = cumulative_trapezoid(f, u, initial=0.0)
    interp = PchipInterpolator(u, F, extrapolate=True)
    _VRINT_CACHE[cache_key] = interp
    return interp


def clear_vrint_cache():
    """Clear the VT-integral interpolator cache."""
    _VRINT_CACHE.clear()


# ============================================================================
# fast_dint3
# ============================================================================


def fast_dint3(R: float, el: float, d: float, F_interp) -> float:
    """
    Compute  integral_el^d  1/VT(R-x) dx  via the precomputed integral.

    Parameters
    ----------
    R        : float  total projected range (µm)
    el       : float  lower integration limit (µm)
    d        : float  upper integration limit (µm)
    F_interp : PchipInterpolator  from build_vrint_interpolator()

    Returns
    -------
    float
    """
    return float(F_interp(R - el) - F_interp(R - d))


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    print("Proton VT function spot-checks  (V = VT/VB, VB is constant):")
    for y_test in [100, 50, 10, 5, 1, 0.1]:
        v = vt_function(y_test)
        print(f"  y = {y_test:6.1f} µm   V = {float(v):.4f}")

    print("\nIntegral check:")
    F = build_vrint_interpolator(R_max=200.0)
    val = fast_dint3(100.0, 0.0, 50.0, F)
    print(f"  integral_0^50  1/V(100-x) dx  =  {val:.4f}  (should be > 0)")
