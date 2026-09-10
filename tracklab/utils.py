"""
Utility functions for TrackLab Proton
"""

import os
import sys

# Import configuration
from .config import TIME_ETCHING, VB, Z_REF

# Add the current folder to sys.path to allow imports from other files in the folder
current_folder = os.path.dirname(os.path.abspath(__file__))
if current_folder not in sys.path:
    sys.path.append(current_folder)


def quadratic_interpolate(x0, y0, x1, y1, x2, y2, x):
    """
    Quadratic interpolation for intersection points with bounds checking

    Parameters:
        x0, y0: First point
        x1, y1: Second point
        x2, y2: Third point
        x: Target x value

    Returns:
        float: Interpolated y value
    """
    if (
        abs(x1 - x0) < 1e-10
        or abs(x2 - x1) < 1e-10
        or x < min(x0, x2)
        or x > max(x0, x2)
    ):
        return y1

    denom = (x0 - x1) * (x0 - x2) * (x1 - x2)
    if abs(denom) < 1e-10:
        return y1

    a = (x2 * (y1 - y0) + x1 * (y0 - y2) + x0 * (y2 - y1)) / denom
    b = (x2**2 * (y0 - y1) + x1**2 * (y2 - y0) + x0**2 * (y1 - y2)) / denom
    c = (
        x1 * x2 * (x1 - x2) * y0 + x2 * x0 * (x2 - x0) * y1 + x0 * x1 * (x0 - x1) * y2
    ) / denom

    return a * x**2 + b * x + c


def compute_etching_time(z_value, vb=None, z_ref=None, t_ref=None, cosz=1.0):
    """
    Compute remaining etching time by subtracting the delay to reach depth z.

    Parameters:
        z_value (float): Depth position (cm)
        vb (float, optional): Bulk etch rate (µm/h). Uses config.VB if None
        z_ref (float, optional): Top reference depth (cm). Uses config.Z_REF if None
        t_ref (float, optional): Total reference time (h). Uses config.TIME_ETCHING if None
        cosz (float, optional): Cosine of incident angle to determine surface

    Returns:
        float: Etching time (hours)
    """
    if vb is None:
        vb = VB
    if z_ref is None:
        z_ref = Z_REF
    if t_ref is None:
        t_ref = TIME_ETCHING

    # Determine surface Z based on particle direction (top or bottom)
    surface_z = z_ref if cosz >= 0 else abs(z_ref)

    # Distance from surface in cm, converted to µm
    distance_um = abs(z_value - surface_z) * 10000.0

    # Delay time to reach the particle depth
    delay_hours = distance_um / vb

    return max(t_ref - delay_hours, 0.0)


def format_energy(energy):
    """
    Format energy value for filenames

    Parameters:
        energy (float): Energy in MeV

    Returns:
        str: Formatted string (e.g., "1.50" for 1.5 MeV)
    """
    return f"{energy:.2f}"


def format_angle(angle):
    """
    Format angle value for filenames

    Parameters:
        angle (float): Angle in degrees

    Returns:
        str: Formatted string (e.g., "75.0" for 75 degrees)
    """
    return f"{angle:.1f}"


def ensure_directory(path):
    """
    Ensure directory exists, create if needed

    Parameters:
        path (str): Directory path

    Returns:
        str: Absolute path to directory
    """
    abs_path = os.path.abspath(path)
    os.makedirs(abs_path, exist_ok=True)
    return abs_path


def print_progress(current, total, prefix="Progress", suffix="Complete", length=50):
    """
    Print a progress bar

    Parameters:
        current (int): Current iteration
        total (int): Total iterations
        prefix (str): Prefix string
        suffix (str): Suffix string
        length (int): Bar length in characters
    """
    percent = 100 * (current / float(total))
    filled_length = int(length * current // total)
    bar = "█" * filled_length + "-" * (length - filled_length)
    print(f"\r{prefix} |{bar}| {percent:.1f}% {suffix}", end="")
    if current == total:
        print()
