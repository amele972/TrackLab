"""Test that all GUI module imports work."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing GUI imports...")

from tracklab.gui.styles import STYLESHEET
print("  styles.py OK")

from tracklab.gui.param_panel import ParamPanel
print("  param_panel.py OK")

from tracklab.gui.workers import TrackWorker, BatchWorker, FlukaWorker
print("  workers.py OK")

from tracklab.gui.tab_vy_curve import VyCurveTab
print("  tab_vy_curve.py OK")

from tracklab.gui.tab_single_track import SingleTrackTab
print("  tab_single_track.py OK")

from tracklab.gui.tab_reference import ReferenceTab
print("  tab_reference.py OK")

from tracklab.gui.tab_fluka import FlukaTab
print("  tab_fluka.py OK")

from tracklab.gui.tab_3d_enhanced import Enhanced3DTab
print("  tab_3d_enhanced.py OK")

from tracklab.gui.tab_lut import LUTTab
print("  tab_lut.py OK")

from tracklab.gui.tab_config import ConfigTab
print("  tab_config.py OK")

from tracklab.gui.main_window import TrackVisionMainWindow
print("  main_window.py OK")

print("\nAll GUI imports successful!")
