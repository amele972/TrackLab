"""
test_fluka.py — Tests for FLUKA Phase-Space Processing Engine in TrackLab.
========================================================================
Validates format detection, multi-ion species mapping, effective etching
time computation, and end-to-end track simulation from FLUKA event data.
"""

import os
import tempfile

import numpy as np
import pytest

from tracklab.fluka_engine import (
    detect_fluka_format,
    map_particle_species,
    parse_beam_energy_from_filename,
    process_fluka_file,
)


def test_beam_energy_filename_parsing():
    """Verify nominal beam energy extraction from filenames."""
    assert parse_beam_energy_from_filename("protons_1.5MeV.txt") == pytest.approx(1.5)
    assert parse_beam_energy_from_filename("AmBe_2,5MeV_test.dat") == pytest.approx(2.5)
    assert parse_beam_energy_from_filename("neutrons_14.8MeV.txt") == pytest.approx(
        14.8
    )
    assert parse_beam_energy_from_filename("sample.txt") is None


def test_fluka_format_detection():
    """Verify auto-detection of extended MGDRAW vs standard BXDRAW vs tabular formats."""
    mgdraw_sample = [
        "# Header comment",
        "NCASE EVENT_TYPE PART_NAME Z A EKIN_GEV Z_POS CZ_DIR COMMENT",
        "1001 2 PROTON 1 1 2.770e-03 -0.550 0.9676 ENTER_TRK",
        "1002 2 TRITON 1 3 2.730e-03 -0.550 0.8500 ENTER_TRK",
    ]
    fmt, header_cnt = detect_fluka_format(mgdraw_sample)
    assert fmt == "mgdraw_extended"
    assert header_cnt == 2

    bxdraw_sample = [
        "Particle Energy x y z cosx cosy cosz",
        "1 2.770e-03 -2.156 2.918 -0.550 0.099 -0.231 0.9676",
        "1 3.864e-03 -2.185 2.724 -0.550 -0.119 -0.147 0.9818",
    ]
    fmt, header_cnt = detect_fluka_format(bxdraw_sample)
    assert fmt == "bxdraw_standard"
    assert header_cnt == 1

    table_sample = [
        "1.5 75.0 protons",
        "2.73 90.0 tritons",
    ]
    fmt, header_cnt = detect_fluka_format(table_sample)
    assert fmt == "simple_table"
    assert header_cnt == 0


def test_particle_species_mapping():
    """Verify multi-ion mapping for protons, tritons, alphas, Li, C, O."""
    # Z and A based mapping
    assert map_particle_species(z_val=1, a_val=1) == "protons"
    assert map_particle_species(z_val=1, a_val=3) == "tritons"
    assert map_particle_species(z_val=2, a_val=4) == "alpha"
    assert map_particle_species(z_val=3, a_val=7) == "Li"
    assert map_particle_species(z_val=6, a_val=12) == "C"
    assert map_particle_species(z_val=8, a_val=16) == "O"

    # Name-based mapping
    assert map_particle_species(part_name="TRITON") == "tritons"
    assert map_particle_species(part_name="PROTON") == "protons"
    assert map_particle_species(part_name="4-HELIUM") == "alpha"
    assert map_particle_species(part_name="12-CARBON") == "C"
    assert map_particle_species(part_name="16-OXYGEN") == "O"

    # FLUKA particle code fallback
    assert map_particle_species(pid=1) == "protons"


def test_end_to_end_fluka_multiion_processing():
    """Verify complete processing of a multi-ion FLUKA file."""
    # Create synthetic multi-ion MGDRAW file containing p, t, alpha, C
    test_content = """# FLUKA Advanced MGDRAW Phase-Space Sample
NCASE EVENT_TYPE PART_NAME Z A EKIN_GEV Z_POS CZ_DIR COMMENT
1001 2 PROTON 1 1 1.500e-03 -0.550 0.9659 ENTER_TRK
1002 2 TRITON 1 3 2.730e-03 -0.550 1.0000 ENTER_TRK
1003 2 4-HELIUM 2 4 4.000e-03 -0.550 0.8660 ENTER_TRK
1004 2 12-CARBON 6 12 1.480e-02 -0.550 1.0000 ENTER_TRK
1005 4 PROTON 1 1 0.050e-03 -0.580 0.5000 STOPPING_TRK
"""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix="_test_fluka.txt") as f:
        f.write(test_content)
        tmp_path = f.name

    out_csv = tmp_path.replace(".txt", "_out.csv")

    try:
        res = process_fluka_file(
            file_path=tmp_path,
            time_etching=2.83,
            output_csv=out_csv,
        )

        assert res["total"] == 5
        assert res["processed"] == 4  # 4 entrance tracks processed, 1 stopping skipped
        assert res["skipped"] == 1  # stopping track skipped
        assert res["format"] == "mgdraw_extended"

        # Check ion breakdown
        counts = res["ion_counts"]
        assert counts["protons"]["total"] == 1
        assert counts["tritons"]["total"] == 1
        assert counts["alpha"]["total"] == 1
        assert counts["C"]["total"] == 1

        # Check results list content
        assert len(res["results"]) == 4
        ions_found = [r["ion"] for r in res["results"]]
        assert "protons" in ions_found
        assert "tritons" in ions_found
        assert "alpha" in ions_found
        assert "C" in ions_found

        # Verify CSV export
        assert os.path.exists(out_csv)
        with open(out_csv, "r") as csvf:
            lines = csvf.readlines()
            assert len(lines) == 5  # header + 4 rows

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        if os.path.exists(out_csv):
            os.remove(out_csv)
