"""
reference_dataset_interpolation.py  —  TrackLab Proton v2.0
================================================================
Fast track parameter calculation using pre-computed reference dataset
via interpolation. Suitable for bulk processing of FLUKA phase space data
or large parameter sweeps.

This module loads a reference CSV dataset (pre-calculated with Track_p.exe),
builds interpolators, and provides rapid lookups without 3D mesh generation.

Key functions:
- load_reference_dataset()      → Load CSV file
- create_interpolators()        → Build scipy interpolators
- calculate_from_reference()    → Get parameters via interpolation
"""

import numpy as np
import pandas as pd
from scipy.interpolate import griddata


def load_reference_dataset(filepath):
    """
    Load a reference dataset CSV file.

    Expected columns:
    - energy_MeV : Proton energy in MeV
    - angle_deg : Track angle in degrees
    - range_um : Range in µm
    - vb : Bulk etch rate in µm/h
    - time_etching_h : Etching time in hours
    - removed_um : Removed material in µm
    - major_axis_um : Major axis in µm
    - minor_axis_um : Minor axis in µm
    - depth_um : Track depth in µm
    - black_part : Black portion (0-1)
    - total_surface : Total surface area in µm²
    - status : Track status (e.g., 'Developed')

    Parameters
    ----------
    filepath : str
        Path to reference dataset CSV file

    Returns
    -------
    pd.DataFrame
        Reference dataset with all columns properly typed
    """
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        raise FileNotFoundError(f"Reference dataset not found: {filepath}")
    except Exception as e:
        raise RuntimeError(f"Error loading reference dataset: {e}")

    # Check required columns for interpolation
    required_cols = [
        "energy_MeV",
        "angle_deg",
        "major_axis_um",
        "minor_axis_um",
        "depth_um",
        "black_part",
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in reference dataset: {missing_cols}")

    # Fill NaN values
    df.fillna(0, inplace=True)

    # Ensure numeric columns
    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Ensure optional surface fields exist using geometric fallback
    if "projected_surface" not in df.columns:
        df["projected_surface"] = (
            np.pi * df["major_axis_um"] * df["minor_axis_um"] / 4.0
        )
    else:
        df["projected_surface"] = pd.to_numeric(
            df["projected_surface"], errors="coerce"
        ).fillna(0)

    if "total_surface" not in df.columns:
        df["total_surface"] = df["projected_surface"]
    else:
        df["total_surface"] = pd.to_numeric(
            df["total_surface"], errors="coerce"
        ).fillna(0)

    return df


def create_interpolators(reference_df):
    """
    Create interpolator functions from reference dataset.

    Uses scipy.interpolate.griddata with cubic interpolation for smooth results.

    Parameters
    ----------
    reference_df : pd.DataFrame
        Reference dataset from load_reference_dataset()

    Returns
    -------
    dict
        Dictionary with keys: 'major_axis', 'minor_axis', 'depth', 'black_part'
        Each value is a callable interpolator function
    """
    # Get XY points (energy, angle)
    xy_points = reference_df[["energy_MeV", "angle_deg"]].values

    # Build interpolators for each parameter
    interpolators = {}

    for param, col in [
        ("major_axis", "major_axis_um"),
        ("minor_axis", "minor_axis_um"),
        ("depth", "depth_um"),
        ("black_part", "black_part"),
        ("projected_surface", "projected_surface"),
        ("total_surface", "total_surface"),
    ]:
        if col not in reference_df.columns:
            continue

        z_values = reference_df[col].values

        def make_interp(xy, z):
            """Factory to create interpolator closure"""

            def interp(energy, angle):
                """
                Interpolate parameter at given energy and angle.

                Parameters
                ----------
                energy : float or array-like
                    Proton energy in MeV
                angle : float or array-like
                    Track angle in degrees

                Returns
                -------
                float or array
                    Interpolated parameter value(s)
                """
                # Convert to arrays
                energy = np.atleast_1d(energy)
                angle = np.atleast_1d(angle)

                # Stack into points for interpolation
                xi = np.column_stack((energy, angle))

                # Cubic interpolation with rescaling
                result = griddata(
                    xy, z, xi, method="cubic", fill_value=np.nan, rescale=True
                )

                # Clip negative values to zero (non-physical)
                result = np.clip(result, 0, None)

                # Return scalar if input was scalar
                if len(energy) == 1:
                    return float(result[0]) if not np.isnan(result[0]) else 0.0
                return result

            return interp

        interpolators[param] = make_interp(xy_points, z_values)

    return interpolators


def calculate_from_reference(
    energy_mev, angle_deg, interpolators, etching_time_hr=2.83, bulk_etch_rate_um_hr=4.7
):
    """
    Calculate track parameters using reference dataset interpolation.

    This is a fast lookup method suitable for:
    - Processing FLUKA phase space data
    - Parameter sweeps and sensitivity analysis
    - Rapid visualization and analysis

    Does NOT include:
    - 3D mesh generation
    - Optical brightness calculation
    - Full numerical optics simulation

    Parameters
    ----------
    energy_mev : float or array-like
        Proton energy in MeV
    angle_deg : float or array-like
        Track angle in degrees (0=parallel, 90=perpendicular to surface)
    interpolators : dict
        Interpolator dictionary from create_interpolators()
    etching_time_hr : float, optional
        Etching time in hours (default 2.83)
    bulk_etch_rate_um_hr : float, optional
        Bulk etch rate in µm/hr (default 4.7)

    Returns
    -------
    dict or list of dict
        Single dict if scalar input, list if array input
        Keys: 'energy_mev', 'angle_deg', 'major_axis_um', 'minor_axis_um',
              'depth_um', 'black_part', 'etching_time_hr', 'bulk_etch_rate'
    """
    # Convert to numpy arrays
    energy = np.atleast_1d(energy_mev)
    angle = np.atleast_1d(angle_deg)

    # Check shapes match
    if energy.shape != angle.shape:
        # Broadcast if one is scalar
        energy = np.broadcast_to(energy, max(energy.shape, angle.shape))
        angle = np.broadcast_to(angle, max(energy.shape, angle.shape))

    # Interpolate parameters
    major = interpolators["major_axis"](energy, angle)
    minor = interpolators["minor_axis"](energy, angle)
    depth = interpolators["depth"](energy, angle)
    black = interpolators["black_part"](energy, angle)

    if "total_surface" in interpolators:
        total_surface = interpolators["total_surface"](energy, angle)
    else:
        total_surface = np.pi * major * minor / 4.0

    if "projected_surface" in interpolators:
        projected_surface = interpolators["projected_surface"](energy, angle)
    else:
        projected_surface = np.pi * major * minor / 4.0

    # Ensure they're arrays
    major = np.atleast_1d(major)
    minor = np.atleast_1d(minor)
    depth = np.atleast_1d(depth)
    black = np.atleast_1d(black)
    total_surface = np.atleast_1d(total_surface)
    projected_surface = np.atleast_1d(projected_surface)

    # Build result
    is_scalar = np.isscalar(energy_mev) and np.isscalar(angle_deg)

    if is_scalar:
        return {
            "energy_mev": float(energy[0]),
            "angle_deg": float(angle[0]),
            "major_axis_um": float(major[0]),
            "minor_axis_um": float(minor[0]),
            "depth_um": float(depth[0]),
            "black_part": float(black[0]),
            "total_surface": float(total_surface[0]),
            "projected_surface": float(projected_surface[0]),
            "etching_time_hr": etching_time_hr,
            "bulk_etch_rate": bulk_etch_rate_um_hr,
        }
    else:
        results = []
        for e, a, maj, min_, dep, blk in zip(energy, angle, major, minor, depth, black):
            results.append(
                {
                    "energy_mev": float(e),
                    "angle_deg": float(a),
                    "major_axis_um": float(maj),
                    "minor_axis_um": float(min_),
                    "depth_um": float(dep),
                    "black_part": float(blk),
                    "etching_time_hr": etching_time_hr,
                    "bulk_etch_rate": bulk_etch_rate_um_hr,
                }
            )
        return results


def process_fluka_phase_space(
    fluka_data_df, interpolators, etching_time_hr=2.83, bulk_etch_rate_um_hr=4.7
):
    """
    Process FLUKA phase space data using reference interpolation.

    Assumes FLUKA DataFrame has columns:
    - energy_MeV : Proton energy
    - angle_deg : Track angle

    Parameters
    ----------
    fluka_data_df : pd.DataFrame
        FLUKA phase space data
    interpolators : dict
        From create_interpolators()
    etching_time_hr : float
        Etching time in hours
    bulk_etch_rate_um_hr : float
        Bulk etch rate in µm/hr

    Returns
    -------
    pd.DataFrame
        Input DataFrame with added columns:
        - major_axis_um
        - minor_axis_um
        - depth_um
        - black_part
    """
    df = fluka_data_df.copy()

    # Get arrays
    energies = df["energy_MeV"].values
    angles = df["angle_deg"].values

    # Interpolate all at once
    major = interpolators["major_axis"](energies, angles)
    minor = interpolators["minor_axis"](energies, angles)
    depth = interpolators["depth"](energies, angles)
    black = interpolators["black_part"](energies, angles)

    # Add columns
    df["major_axis_um"] = major
    df["minor_axis_um"] = minor
    df["depth_um"] = depth
    df["black_part"] = black
    df["total_surface"] = (
        interpolators["total_surface"](energies, angles)
        if "total_surface" in interpolators
        else np.pi * major * minor / 4.0
    )
    df["projected_surface"] = (
        interpolators["projected_surface"](energies, angles)
        if "projected_surface" in interpolators
        else np.pi * major * minor / 4.0
    )

    return df


def validate_interpolation_range(reference_df):
    """
    Check and report the valid range for interpolation.

    Parameters
    ----------
    reference_df : pd.DataFrame
        Reference dataset

    Returns
    -------
    dict
        Ranges for energy and angle
    """
    energy_range = {
        "min": reference_df["energy_MeV"].min(),
        "max": reference_df["energy_MeV"].max(),
    }
    angle_range = {
        "min": reference_df["angle_deg"].min(),
        "max": reference_df["angle_deg"].max(),
    }

    return {
        "energy_mev": energy_range,
        "angle_deg": angle_range,
        "n_points": len(reference_df),
    }


# Example usage
if __name__ == "__main__":
    # Load reference dataset
    ref_path = "reference_dataset.csv"  # Update path as needed
    try:
        ref_df = load_reference_dataset(ref_path)
        print(f"✅ Loaded reference dataset: {len(ref_df)} points")

        # Create interpolators
        interp = create_interpolators(ref_df)
        print("✅ Created interpolators")

        # Show valid range
        valid_range = validate_interpolation_range(ref_df)
        print("\nValid interpolation range:")
        print(
            f"  Energy: {valid_range['energy_mev']['min']:.2f} - "
            f"{valid_range['energy_mev']['max']:.2f} MeV"
        )
        print(
            f"  Angle:  {valid_range['angle_deg']['min']:.1f} - "
            f"{valid_range['angle_deg']['max']:.1f}°"
        )

        # Example: Single point lookup
        result = calculate_from_reference(1.0, 55.0, interp)
        print("\nExample lookup (1.0 MeV, 55°):")
        for k, v in result.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.3f}")
            else:
                print(f"  {k}: {v}")

    except FileNotFoundError as e:
        print(f"⚠️  {e}")
        print("To use this module, provide a reference_dataset.csv file")
