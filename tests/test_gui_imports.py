"""Pytest gui imports check for TrackLab."""

def test_gui_imports():
    """Verify that all components of the GUI sub-package import successfully."""
    from tracklab.gui.styles import STYLESHEET
    assert STYLESHEET is not None

    from tracklab.gui.param_panel import ParamPanel
    assert ParamPanel is not None

    from tracklab.gui.workers import TrackWorker, BatchWorker, FlukaWorker
    assert TrackWorker is not None
    assert BatchWorker is not None
    assert FlukaWorker is not None

    from tracklab.gui.tab_vy_curve import VyCurveTab
    assert VyCurveTab is not None

    from tracklab.gui.tab_single_track import SingleTrackTab
    assert SingleTrackTab is not None

    from tracklab.gui.tab_reference import ReferenceTab
    assert ReferenceTab is not None

    from tracklab.gui.tab_fluka import FlukaTab
    assert FlukaTab is not None

    from tracklab.gui.tab_3d_enhanced import Enhanced3DTab
    assert Enhanced3DTab is not None

    from tracklab.gui.tab_lut import LUTTab
    assert LUTTab is not None

    from tracklab.gui.tab_config import ConfigTab
    assert ConfigTab is not None

    from tracklab.gui.main_window import TrackLabMainWindow
    assert TrackLabMainWindow is not None
