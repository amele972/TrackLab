"""
process_fluka_phase_space.py — FLUKA Monte Carlo Simulation Example
=====================================================================
Demonstrates loading a FLUKA phase-space file (e.g. AmBe neutron irradiation),
simulating etched track formation for all particles, and printing summary
statistics and track dimensions.
"""

import os
import sys

# Ensure package root is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tracklab.fluka_engine import process_fluka_file


def main():
    examples_dir = os.path.dirname(os.path.abspath(__file__))
    fluka_file = os.path.join(examples_dir, "AmBe_01001_Phase-space_BXDRAW.txt")

    if not os.path.exists(fluka_file):
        print(f"Error: Example FLUKA file not found at {fluka_file}")
        return

    print("=" * 70)
    print("  TrackLab — FLUKA Phase-Space Processing Example")
    print("=" * 70)
    print(f"Input file: {os.path.basename(fluka_file)}")

    # For a quick demonstration, we process the phase-space file
    output_csv = os.path.join(examples_dir, "fluka_processed_sample.csv")

    res = process_fluka_file(
        file_path=fluka_file,
        time_etching=2.83,
        output_csv=output_csv,
        progress_callback=lambda pct, msg: print(f"  [{pct:3d}%] {msg}")
        if pct % 25 == 0 or pct == 100
        else None,
    )

    print("\n--- Simulation Summary ---")
    print(f"Total particles in file:  {res['total']}")
    print(f"Successfully processed:   {res['processed']}")
    print(f"Developed etched tracks:  {res['developed']}")
    print(f"Skipped / non-developed:  {res['skipped']}")
    print(f"Detected file format:     {res['format']}")

    print("\n--- Breakdown by Species ---")
    for ion, stats in res.get("ion_counts", {}).items():
        if stats["total"] > 0:
            dev_pct = 100.0 * stats["developed"] / stats["total"]
            print(
                f"  {ion:8s}: {stats['total']:6d} incident | {stats['developed']:6d} developed ({dev_pct:.1f}%)"
            )

    # Display preview of first 5 tracks
    if res["results"]:
        print("\n--- First 5 Track Dimensions ---")
        print(
            f"{'Ion':<8} {'Energy (MeV)':>12} {'Angle (deg)':>12} {'Depth (um)':>12} {'Major (um)':>12} {'Status':<12}"
        )
        print("-" * 72)
        for r in res["results"][:5]:
            print(
                f"{r['ion']:<8} "
                f"{r['energy_MeV']:12.3f} "
                f"{r['angle_deg']:12.1f} "
                f"{r['depth_um']:12.3f} "
                f"{r['major_axis_um']:12.3f} "
                f"{r['status']:<12}"
            )

    print(f"\nFull output saved to: {output_csv}")


if __name__ == "__main__":
    main()
