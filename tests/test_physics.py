"""Quick test of the unified TrackLab package."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracklab.load_srim_data import load_srim_data
from tracklab.vt_utils import build_vrint_interpolator
from tracklab.vt_multiion import get_model
from tracklab.calculate_track_parameter import calculate_track_parameters

interps, _ = load_srim_data()
vt_model = get_model()

# Test proton
F = build_vrint_interpolator(vt_model=vt_model, ion='protons', energy=1.5, vb=4.7)
res = calculate_track_parameters(
    energy=1.5, angle_deg=75.0, vb=4.7, time_etching=2.83,
    range_interpolator=interps['protons'], F_interp=F,
    ion='protons', vt_model=vt_model)

print()
print("=== Proton Track: 1.5 MeV, 75 deg ===")
print("Status:", res['status'])
print("Depth: ", "{:.4f}".format(res['depth_um']), "um")
print("Major: ", "{:.4f}".format(res['major_axis_um']), "um")
print("Minor: ", "{:.4f}".format(res['minor_axis_um']), "um")
print("Black: ", "{:.4f}".format(res['black_part']))

# Test Carbon
F = build_vrint_interpolator(vt_model=vt_model, ion='C', energy=14.8, vb=1.73)
res = calculate_track_parameters(
    energy=14.8, angle_deg=90.0, vb=1.73, time_etching=5.0,
    range_interpolator=interps['C'], F_interp=F,
    ion='C', vt_model=vt_model)

print()
print("=== Carbon Track: 14.8 MeV, 90 deg ===")
print("Status:", res['status'])
print("Depth: ", "{:.4f}".format(res['depth_um']), "um")
print("Major: ", "{:.4f}".format(res['major_axis_um']), "um")
print("Minor: ", "{:.4f}".format(res['minor_axis_um']), "um")

print()
print("All tests passed!")
