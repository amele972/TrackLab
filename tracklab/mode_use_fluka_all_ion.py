"""
mode_use_fluka_all_ion.py — TrackLab v1.0
=========================================
FLUKA multi-ion phase-space processor module.
Powered by tracklab.fluka_engine.
"""

from .fluka_engine import process_fluka_file


def run_mode_fluka_all_ion(
    input_file=None,
    time_etching=None,
    output_csv=None,
    skip_header=None,
    vb=None,
):
    """Process FLUKA unified phase-space file for multiple ions."""
    if input_file is None:
        input_file = input("FLUKA file path: ").strip()
    if output_csv is None:
        output_csv = "fluka_results_all_ions.csv"

    print("\nMode 4: FLUKA Multi-Ion Processing")
    print(f"  Input:  {input_file}")
    print(f"  Output: {output_csv}")

    res_dict = process_fluka_file(
        file_path=input_file,
        time_etching=time_etching,
        vb=vb,
        skip_header=skip_header,
        output_csv=output_csv,
        progress_callback=lambda pct, msg: print(f"  [{pct:3d}%] {msg}") if pct % 20 == 0 or pct == 100 else None,
    )

    print(
        f"\n  Done: {res_dict['processed']} processed "
        f"({res_dict['developed']} developed, {res_dict['skipped']} skipped)."
    )
    print("  Species breakdown:")
    for ion, cnt in res_dict.get("ion_counts", {}).items():
        if cnt["total"] > 0:
            print(f"    - {ion:8s}: {cnt['total']:6d} simulated, {cnt['developed']:6d} developed")
    print(f"  Results saved to: {output_csv}")
    return res_dict["results"]


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        run_mode_fluka_all_ion(input_file=sys.argv[1])
    else:
        run_mode_fluka_all_ion()
