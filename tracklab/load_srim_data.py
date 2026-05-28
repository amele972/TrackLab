"""
load_srim_data.py  —  TrackLab v1.0
=========================================
Unified SRIM range-energy data loader for all ions.

Reads the unified ``Rang_CR_all_ions_SRIM.dat`` file which has columns:
    Ion   Ion_Energy_MeV   Projected_Range_um

Supports: protons, Li, C, O, alpha

Public API
----------
  load_srim_data(filename)          → dict of PchipInterpolators per ion
  interpolate_range(energy, ion, interpolators) → float (range in µm)
"""

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import curve_fit
import os


def load_srim_data(filename=None, target_max_mev=30.0):
    """
    Load SRIM range data and create separate interpolators per ion.

    Parameters
    ----------
    filename       : str or None
        Path to unified SRIM data file. Defaults to config.SRIM_FILENAME.
    target_max_mev : float
        Extend data to this energy via Bragg-Kleeman power law if needed.

    Returns
    -------
    interpolators : dict
        {'protons': PchipInterpolator, 'Li': ..., 'C': ..., 'O': ..., 'alpha': ...}
    data_dict : dict
        {'protons': (energies, ranges), ...}
    """
    if filename is None:
        try:
            from .config import SRIM_FILENAME
            filename = SRIM_FILENAME
        except ImportError:
            filename = os.path.join(os.path.dirname(__file__), 'data',
                                    'Rang_CR_all_ions_SRIM.dat')

    # Supported ions
    supported_ions = {'protons', 'Li', 'C', 'O', 'alpha'}
    ion_data = {ion: {'enes': [], 'rans': []} for ion in supported_ions}

    if not os.path.exists(filename):
        # Try local fallback
        local = os.path.basename(filename)
        if os.path.exists(local):
            filename = local
        else:
            raise FileNotFoundError(f"SRIM file not found: '{filename}'")

    with open(filename, 'r') as fh:
        for line in fh:
            parts = line.strip().split()
            if len(parts) < 3:
                # Try 2-column format (legacy proton-only file)
                if len(parts) == 2:
                    try:
                        energy = float(parts[0])
                        range_val = float(parts[1])
                        ion_data['protons']['enes'].append(energy)
                        ion_data['protons']['rans'].append(range_val)
                    except ValueError:
                        continue
                continue

            try:
                ion_name = parts[0]
                energy = float(parts[1])
                range_val = float(parts[2])

                if ion_name in ion_data:
                    ion_data[ion_name]['enes'].append(energy)
                    ion_data[ion_name]['rans'].append(range_val)
            except (ValueError, IndexError):
                continue

    # Build interpolators for each ion
    interpolators = {}
    data_dict = {}

    for ion in ['protons', 'Li', 'C', 'O', 'alpha']:
        enes_list = ion_data[ion]['enes']
        rans_list = ion_data[ion]['rans']

        if len(enes_list) < 5:
            if len(enes_list) > 0:
                print(f"  Warning: {ion} has only {len(enes_list)} points, skipping")
            continue

        enes = np.array(enes_list)
        rans = np.array(rans_list)

        # Sort ascending
        idx = np.argsort(enes)
        enes = enes[idx]
        rans = rans[idx]

        # Remove duplicates
        _, unique_idx = np.unique(enes, return_index=True)
        enes = enes[unique_idx]
        rans = rans[unique_idx]

        # Bragg-Kleeman extrapolation if needed
        cur_max = enes.max()
        if cur_max < target_max_mev:
            mask = enes > cur_max * 0.5

            def power_law(e, a, p):
                return a * e ** p

            try:
                popt, _ = curve_fit(power_law, enes[mask], rans[mask],
                                    p0=[1, 1.77])
            except Exception:
                popt = [rans[-1] / enes[-1] ** 1.77, 1.77]

            e_ext = np.linspace(cur_max, target_max_mev, 50)[1:]
            enes = np.concatenate([enes, e_ext])
            rans = np.concatenate([rans, power_law(e_ext, *popt)])

        interp = PchipInterpolator(enes, rans, extrapolate=False)
        interpolators[ion] = interp
        data_dict[ion] = (enes, rans)

        print(f"  [OK] {ion:8s}: {len(enes_list):3d} points, "
              f"{enes[0]:.3f}–{enes[-1]:.3f} MeV, "
              f"{rans[0]:.3f}–{rans[-1]:.3f} µm")

    return interpolators, data_dict


def interpolate_range(energy, ion_or_interpolator, interpolators=None):
    """
    Get range for a specific (ion, energy).

    Can be called two ways:
      1. interpolate_range(energy, interpolator)       — single interpolator
      2. interpolate_range(energy, 'protons', interps) — ion name + dict

    Parameters
    ----------
    energy : float
        Kinetic energy (MeV).
    ion_or_interpolator : str or PchipInterpolator
        Ion name (str) or a PchipInterpolator directly.
    interpolators : dict, optional
        Required if ion_or_interpolator is a string.

    Returns
    -------
    float — Projected range (µm).
    """
    if isinstance(ion_or_interpolator, str):
        ion = ion_or_interpolator
        if interpolators is None:
            raise ValueError("interpolators dict required when passing ion name")
        if ion not in interpolators:
            raise ValueError(
                f"Ion '{ion}' not in loaded data. "
                f"Available: {list(interpolators.keys())}")
        return float(interpolators[ion](energy))
    else:
        # Direct interpolator passed
        return float(ion_or_interpolator(energy))


# ============================================================================
# Self-test
# ============================================================================

if __name__ == '__main__':
    print("\nUnified SRIM Data Loader — Self Test")
    print("=" * 70)

    interps, data = load_srim_data()

    if interps is None:
        print("Failed to load SRIM data")
    else:
        print(f"\n[OK] Loaded {len(interps)} ions\n")

        test_cases = [
            ('protons', 1.0),
            ('protons', 10.0),
            ('C', 14.8),
            ('O', 5.0),
            ('Li', 3.0),
            ('alpha', 5.0),
        ]

        print(f"{'Ion':<10} {'Energy (MeV)':<15} {'Range (µm)':<15}")
        print("-" * 40)
        for ion, energy in test_cases:
            if ion in interps:
                r = interpolate_range(energy, ion, interps)
                print(f"{ion:<10} {energy:<15.2f} {r:<15.4f}")
