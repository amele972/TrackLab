"""
fluka_engine.py — TrackLab v1.0
================================
Unified FLUKA Monte Carlo phase-space processor supporting all ion species
(protons, tritons, alpha particles, lithium, carbon, oxygen).

Automatically detects the phase-space format:
  1. Extended MGDRAW (e.g. remlayer_events.dat):
     Columns: NCASE EVENT_TYPE PART_NAME Z A EKIN_GEV Z_POS CZ_DIR COMMENT
  2. Standard BXDRAW boundary crossing:
     Columns: Particle Energy_GeV x y z cosx cosy cosz
  3. Simple tabular:
     Columns: [Energy_MeV, Angle_deg] or [Ion, Energy_MeV, Angle_deg]

Physical processing:
  - Particle identification via Z and A or particle code
  - Kinetic energy conversion (GeV -> MeV)
  - Surface incidence angle calculation: theta = 90 - arccos(|cosz|)
  - Effective etching time calculation taking particle origin depth into account
  - Forward vs reverse (bottom) detector surface entry handling
  - Species-specific track formation using respective V(y) models and SRIM tables
"""

import csv
import os
import re
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from .calculate_track_parameter import calculate_track_parameters
from .config import SUPPORTED_IONS, TIME_ETCHING, Z_REF, get_vb_for_ion
from .load_srim_data import load_srim_data
from .utils import compute_etching_time
from .vt_multiion import get_model
from .vt_utils import build_vrint_interpolator

# Mapping from nuclear charge Z (and mass A) to TrackLab ion name
Z_TO_ION = {
    1: "protons",  # default for Z=1; A=3 overridden to 'tritons'
    2: "alpha",
    3: "Li",
    6: "C",
    8: "O",
}

# Standard FLUKA particle IDs (where applicable)
FLUKA_PID_TO_ION = {
    1: "protons",  # PROTON
    -3: "alpha",  # 4-HELIUM (in some scoring setups)
    -4: "tritons",  # 3-H (in some scoring setups)
    -6: "alpha",  # 4-He
}


def parse_beam_energy_from_filename(filename: str) -> Optional[float]:
    """Extract nominal beam energy in MeV from filename (e.g. '1.5MeV.txt', '2,5MeV.txt')."""
    m = re.search(r"([\d,\.]+)\s*MeV", filename, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            pass
    return None


def detect_fluka_format(lines: List[str]) -> Tuple[str, int]:
    """
    Auto-detect the format of a FLUKA phase-space file and determine header rows.

    Returns:
        (format_name, header_lines_count)
        format_name is one of: 'mgdraw_extended', 'bxdraw_standard', 'simple_table'
    """
    header_count = 0
    first_data_line = None

    for i, line in enumerate(lines):
        line_str = line.strip()
        if not line_str:
            continue
        if line_str.startswith("#"):
            header_count = i + 1
            continue

        lower = line_str.lower()
        # Check if line is a text header
        if any(
            h in lower for h in ["particle", "energy", "ncase", "part_name", "ekin"]
        ):
            header_count = i + 1
            continue

        parts = line_str.split()
        if len(parts) >= 2:
            first_data_line = parts
            break

    if not first_data_line:
        return "bxdraw_standard", header_count

    n_cols = len(first_data_line)

    # 9 or more columns with string comment or integer Z, A
    if n_cols >= 9:
        try:
            # Check if columns 3 and 4 look like Z and A integers
            int(first_data_line[3])
            int(first_data_line[4])
            float(first_data_line[5])
            return "mgdraw_extended", header_count
        except ValueError:
            pass

    # Standard BXDRAW has 8 columns: Particle, Energy, x, y, z, cosx, cosy, cosz
    if n_cols == 8:
        try:
            float(first_data_line[1])
            float(first_data_line[4])
            float(first_data_line[7])
            return "bxdraw_standard", header_count
        except ValueError:
            pass

    return "simple_table", header_count


def map_particle_species(
    z_val: Optional[int] = None,
    a_val: Optional[int] = None,
    part_name: Optional[str] = None,
    pid: Optional[int] = None,
    default_ion: str = "protons",
) -> Optional[str]:
    """
    Resolve ion name in TrackLab convention from physical Z, A, name, or FLUKA PID.
    """
    # 1. Physical Z and A have highest precedence
    if z_val is not None:
        if z_val == 1:
            if a_val == 3:
                return "tritons"
            return "protons"
        if z_val in Z_TO_ION:
            return Z_TO_ION[z_val]

    # 2. Text name matching
    if part_name:
        pn = part_name.upper().strip()
        if "TRIT" in pn or pn == "3-H":
            return "tritons"
        if "PROT" in pn or pn == "1-H":
            return "protons"
        if "ALPHA" in pn or "HELI" in pn or pn == "4-HE":
            return "alpha"
        if "CARB" in pn or "12-C" in pn:
            return "C"
        if "OXY" in pn or "16-O" in pn:
            return "O"
        if "LITH" in pn or "7-LI" in pn:
            return "Li"

    # 3. Particle ID fallback
    if pid is not None and pid in FLUKA_PID_TO_ION:
        return FLUKA_PID_TO_ION[pid]

    return default_ion


def process_fluka_file(
    file_path: str,
    time_etching: Optional[float] = None,
    vb: Optional[float] = None,
    default_ion: str = "protons",
    skip_header: Optional[int] = None,
    output_csv: Optional[str] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    beam_energy_mev: Optional[float] = None,
) -> Dict:
    """
    Process a FLUKA phase-space file for all ions.

    Parameters:
        file_path: Path to the FLUKA file.
        time_etching: Bulk etching time (hours). If None, uses config.TIME_ETCHING.
        vb: Bulk etch rate (µm/h). If None, uses ion-specific rates from config.
        default_ion: Fallback ion species when species cannot be inferred.
        skip_header: Number of header rows to skip. If None, auto-detected.
        output_csv: Optional path to export CSV results.
        progress_callback: Optional callback func(pct: int, msg: str).
        cancel_check: Optional func() -> bool that returns True to cancel.
        beam_energy_mev: Nominal beam energy in MeV (auto-detected if None).

    Returns:
        Dictionary with keys:
          - 'results': List of dicts per particle
          - 'processed': Total particles processed
          - 'developed': Count of tracks that developed
          - 'skipped': Count of particles skipped (stopped, below critical angle, etc.)
          - 'total': Total valid candidate lines
          - 'ion_counts': Dict of particle counts per ion species
          - 'format': Detected file format string
    """
    if time_etching is None:
        time_etching = TIME_ETCHING

    if beam_energy_mev is None:
        beam_energy_mev = parse_beam_energy_from_filename(os.path.basename(file_path))

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"FLUKA file not found: {file_path}")

    # Read lines
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = [line.strip() for line in f if line.strip()]

    fmt, auto_skip = detect_fluka_format(lines)
    header_rows = skip_header if skip_header is not None else auto_skip
    data_lines = [
        line_item for line_item in lines[header_rows:] if not line_item.startswith("#")
    ]
    total = len(data_lines)

    if progress_callback:
        progress_callback(5, f"Detected format: {fmt}. Loading physics models…")

    interps, _ = load_srim_data()
    vt_model = get_model()

    results: List[Dict] = []
    processed = 0
    developed = 0
    skipped = 0
    ion_counts: Dict[str, Dict[str, int]] = {
        ion: {"total": 0, "developed": 0} for ion in SUPPORTED_IONS
    }

    if progress_callback:
        progress_callback(10, f"Simulating {total} particles across supported ions…")

    # Cache interpolators per (ion, energy, vb) to avoid recomputing cumulative integrals
    # For speed on large datasets
    f_interp_cache: Dict[Tuple[str, float, float], any] = {}

    for idx, line in enumerate(data_lines):
        if cancel_check and cancel_check():
            break

        try:
            parts = line.split()
            ncase = idx + 1
            ion_name = default_ion
            z_pos = Z_REF
            cosz = 1.0
            energy_mev = 0.0

            if fmt == "mgdraw_extended":
                # NCASE EVENT_TYPE PART_NAME Z A EKIN_GEV Z_POS CZ_DIR COMMENT
                if len(parts) < 8:
                    skipped += 1
                    continue

                event_type = int(parts[1]) if len(parts) > 1 else 0
                part_name = parts[2] if len(parts) > 2 else ""
                z_val = int(parts[3]) if len(parts) > 3 else 1
                a_val = int(parts[4]) if len(parts) > 4 else 1
                ekin_gev = float(parts[5])
                z_pos = float(parts[6])
                cosz = float(parts[7])
                comment = parts[8] if len(parts) > 8 else ""

                # Skip end-of-track / stopping events (only surface entries form etched pits)
                if event_type == 4 or comment == "STOPPING_TRK":
                    skipped += 1
                    continue

                ion_name = map_particle_species(
                    z_val=z_val,
                    a_val=a_val,
                    part_name=part_name,
                    default_ion=default_ion,
                )
                energy_mev = ekin_gev * 1000.0

            elif fmt == "bxdraw_standard":
                # Particle Energy_GeV x y z cosx cosy cosz
                if len(parts) < 8:
                    skipped += 1
                    continue
                try:
                    pid = int(parts[0])
                except ValueError:
                    pid = 1

                ekin_gev = float(parts[1])
                z_pos = float(parts[4])
                cosz = float(parts[7])
                ion_name = map_particle_species(pid=pid, default_ion=default_ion)
                energy_mev = ekin_gev * 1000.0

            else:
                # Simple tabular format: e.g. Energy_MeV Angle_deg [Ion]
                if len(parts) == 2:
                    energy_mev = float(parts[0])
                    angle_deg = float(parts[1])
                    cosz = np.cos(np.radians(90.0 - angle_deg))
                elif len(parts) >= 3:
                    try:
                        energy_mev = float(parts[0])
                        angle_deg = float(parts[1])
                        ion_name = parts[2]
                        cosz = np.cos(np.radians(90.0 - angle_deg))
                    except ValueError:
                        ion_name = parts[0]
                        energy_mev = float(parts[1])
                        angle_deg = float(parts[2])
                        cosz = np.cos(np.radians(90.0 - angle_deg))

            if not ion_name or ion_name not in interps:
                skipped += 1
                continue

            if energy_mev <= 0:
                skipped += 1
                continue

            cosz_clipped = float(np.clip(cosz, -1.0, 1.0))
            # TrackLab convention: angle relative to detector surface (90 deg = normal incidence)
            angle_deg = 90.0 - float(np.degrees(np.arccos(abs(cosz_clipped))))

            # Determine bulk etch rate for this specific ion
            ion_vb = vb if vb is not None else get_vb_for_ion(ion_name)

            # Effective etching time (subtracts delay to reach penetration depth z)
            t_eff = compute_etching_time(
                z_pos, vb=ion_vb, t_ref=time_etching, cosz=cosz_clipped
            )
            if t_eff <= 0:
                skipped += 1
                continue

            # Cache key rounded to 3 decimal places to accelerate large phase-spaces
            e_key = round(energy_mev, 3)
            cache_key = (ion_name, e_key, round(ion_vb, 3))
            F_interp = f_interp_cache.get(cache_key)
            if F_interp is None:
                F_interp = build_vrint_interpolator(
                    vt_model=vt_model, ion=ion_name, energy=energy_mev, vb=ion_vb
                )
                if len(f_interp_cache) < 2000:
                    f_interp_cache[cache_key] = F_interp

            range_interp = interps[ion_name]
            is_bottom = bool(cosz_clipped < 0)

            res = calculate_track_parameters(
                energy=energy_mev,
                angle_deg=angle_deg,
                vb=ion_vb,
                time_etching=t_eff,
                range_interpolator=range_interp,
                F_interp=F_interp,
                ion=ion_name,
                vt_model=vt_model,
                is_bottom_track=is_bottom,
            )

            is_dev = res.get("indicator", -1) == 1 or res.get("status") == "Developed"
            if is_dev:
                developed += 1
                if ion_name in ion_counts:
                    ion_counts[ion_name]["developed"] += 1

            if ion_name in ion_counts:
                ion_counts[ion_name]["total"] += 1

            results.append(
                {
                    "ncase": ncase,
                    "ion": ion_name,
                    "energy_MeV": energy_mev,
                    "beam_energy_MeV": beam_energy_mev
                    if beam_energy_mev is not None
                    else energy_mev,
                    "angle_deg": angle_deg,
                    "z_cm": z_pos,
                    "cosz": cosz_clipped,
                    "is_bottom": is_bottom,
                    "etching_time_h": t_eff,
                    "depth_um": res.get("depth_um", 0.0),
                    "major_axis_um": res.get("major_axis_um", 0.0),
                    "minor_axis_um": res.get("minor_axis_um", 0.0),
                    "total_length_um": res.get("total_length_um", 0.0),
                    "black_part": res.get("black_part", 0.0),
                    "total_surface": res.get("total_surface", 0.0),
                    "projected_surface": res.get("projected_surface", 0.0),
                    "status": res.get("status", "unknown"),
                }
            )
            processed += 1

        except Exception:
            skipped += 1

        if progress_callback and (idx + 1) % max(1, total // 20) == 0:
            pct = 10 + int(85 * (idx + 1) / total)
            progress_callback(pct, f"Processed {idx + 1}/{total} particles…")

    if output_csv and results:
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    if progress_callback:
        progress_callback(
            100,
            f"Completed: {processed} processed ({developed} developed, {skipped} skipped).",
        )

    return {
        "results": results,
        "processed": processed,
        "developed": developed,
        "skipped": skipped,
        "total": total,
        "ion_counts": ion_counts,
        "format": fmt,
    }
