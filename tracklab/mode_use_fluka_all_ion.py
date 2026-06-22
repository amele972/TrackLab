"""
mode_use_fluka_all_ion.py — TrackLab v1.0
=========================================
Specific module to process unified FLUKA phase-space files
containing multiple ions (Protons, Alpha, Carbon, Oxygen).
"""

import csv
import numpy as np

from .calculate_track_parameter import calculate_track_parameters
from .config import TIME_ETCHING, get_vb_for_ion
from .load_srim_data import load_srim_data
from .vt_multiion import get_model
from .vt_utils import build_vrint_interpolator
from .utils import compute_etching_time

def run_mode_fluka_all_ion(
    input_file=None,
    time_etching=None,
    output_csv=None,
    skip_header=0,
):
    """Mode: Process FLUKA unified phase-space file for multiple ions."""
    if time_etching is None:
        time_etching = TIME_ETCHING
    if input_file is None:
        input_file = input("FLUKA file path: ").strip()
    if output_csv is None:
        output_csv = "fluka_results_all_ions.csv"

    print(f"\nMode: FLUKA Unified Processing (All Ions)")
    print(f"  File: {input_file}")

    # Load SRIM data for all supported ions
    interps, _ = load_srim_data()
    vt_model = get_model()

    # Z to Ion mapping
    z_to_ion = {
        1: "protons",
        2: "alpha",
        6: "C",
        8: "O"
    }

    # Read lines and skip comments/headers
    with open(input_file, "r") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    lines = lines[skip_header:]
    total = len(lines)
    print(f"  {total} particles found (excluding headers)")

    results = []
    developed = 0
    skipped = 0
    
    # Duplicate prevention
    # We store (NCASE, PART_NAME) to avoid counting the same track multiple times
    processed_events = set()

    for idx, line in enumerate(lines):
        try:
            parts = line.split()
            if len(parts) < 9:
                skipped += 1
                continue
            
            ncase = int(parts[0])
            event_type = int(parts[1])  # 1=BORN, 2=IN_FW, 3=IN_BW, 4=STOP
            part_name = parts[2]
            z_val_ion = int(parts[3])
            a_val_ion = int(parts[4])
            ekin_gev = float(parts[5])
            z_pos = float(parts[6])
            cz_dir = float(parts[7])
            comment = parts[8]

            # 1. Skip if it's a stopping event (we only care about track start)
            if event_type == 4 or comment == 'STOPPING_TRK':
                skipped += 1
                continue

            # 2. Map to supported ion
            ion_name = z_to_ion.get(z_val_ion)
            if not ion_name or ion_name not in interps:
                skipped += 1
                continue
                
            # 3. Prevent Double Counting
            # We track the NCASE and particle type to ensure we only get one track start per particle in a history
            event_key = (ncase, part_name)
            if event_key in processed_events:
                skipped += 1
                continue
            processed_events.add(event_key)

            # 4. Extract parameters
            energy_mev = ekin_gev * 1000.0
            if energy_mev <= 0:
                skipped += 1
                continue
            
            cosz = np.clip(cz_dir, -1.0, 1.0)
            # The angle should be relative to the surface
            angle_deg = 90.0 - np.degrees(np.arccos(abs(cosz)))

            vb = get_vb_for_ion(ion_name)
            range_interp = interps[ion_name]
            
            etching_time_particle = compute_etching_time(z_pos, vb=vb, t_ref=time_etching, cosz=cosz)
            if etching_time_particle <= 0:
                skipped += 1
                continue

            F_interp = build_vrint_interpolator(
                vt_model=vt_model, ion=ion_name, energy=energy_mev, vb=vb
            )
            
            res = calculate_track_parameters(
                energy=energy_mev,
                angle_deg=angle_deg,
                vb=vb,
                time_etching=etching_time_particle,
                range_interpolator=range_interp,
                F_interp=F_interp,
                ion=ion_name,
                vt_model=vt_model,
                is_bottom_track=(cosz < 0),
            )
            
            results.append(
                {
                    "ncase": ncase,
                    "ion": ion_name,
                    "energy_MeV": energy_mev,
                    "angle_deg": angle_deg,
                    "depth_um": res["depth_um"],
                    "major_axis_um": res["major_axis_um"],
                    "minor_axis_um": res["minor_axis_um"],
                    "total_length_um": res["total_length_um"],
                    "status": res["status"],
                }
            )
            if res.get("indicator", -1) == 1:
                developed += 1
                
        except Exception as e:
            skipped += 1

        if (idx + 1) % max(1, total // 10) == 0:
            print(f"  {idx + 1}/{total}")

    print(f"\n  Processed: {len(results)}  Developed: {developed}  Skipped: {skipped}")
    if results:
        with open(output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"  Saved to: {output_csv}")
    return results

if __name__ == "__main__":
    import sys
    # For quick testing from CLI
    if len(sys.argv) > 1:
        run_mode_fluka_all_ion(input_file=sys.argv[1])
    else:
        run_mode_fluka_all_ion()
