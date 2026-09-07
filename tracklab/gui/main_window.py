"""
main_window.py — TrackLab Main Window
=================================================
Unified splitter layout: shared param panel (left) + 7-tab widget (right).
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
)

from .config_summary import ConfigSummaryDialog, set_skip_summary
from .param_panel import ParamPanel
from .styles import THEMES, get_stylesheet
from .tab_3d_enhanced import Enhanced3DTab
from .tab_config import ConfigTab
from .tab_fluka import FlukaTab
from .tab_lut import LUTTab
from .tab_reference import ReferenceTab
from .tab_single_track import SingleTrackTab
from .tab_vy_curve import VyCurveTab


class TrackLabMainWindow(QMainWindow):
    """Unified multi-ion Track Lab GUI."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TrackLab")
        self.setMinimumSize(1200, 800)
        self._current_theme = "light"
        self.setStyleSheet(get_stylesheet(self._current_theme))
        self._init_menu()
        self._init_ui()
        self._init_statusbar()

    def _init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu with theme toggle
        view_menu = menubar.addMenu("View")
        theme_menu = view_menu.addMenu("Theme")

        self._theme_actions = {}
        for theme in THEMES:
            action = QAction(theme.capitalize(), self)
            action.setCheckable(True)
            action.setChecked(theme == self._current_theme)
            action.triggered.connect(lambda checked, t=theme: self._set_theme(t))
            theme_menu.addAction(action)
            self._theme_actions[theme] = action

        help_menu = menubar.addMenu("Help")

        summary_action = QAction("Show Configuration Summary", self)
        summary_action.setShortcut("F1")
        summary_action.setToolTip(
            "Re-open the startup physics configuration summary"
        )
        summary_action.triggered.connect(self._show_config_summary)
        help_menu.addAction(summary_action)

        help_menu.addSeparator()

        about_action = QAction("About", self)
        about_action.triggered.connect(self._about)
        help_menu.addAction(about_action)

    def _init_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: shared parameter panel
        self.param_panel = ParamPanel()
        splitter.addWidget(self.param_panel)

        # Right: tab widget with 7 modes
        self.tabs = QTabWidget()

        self.tab1 = VyCurveTab(self.param_panel)
        self.tab2 = SingleTrackTab(self.param_panel)
        self.tab3 = ReferenceTab(self.param_panel)
        self.tab4 = FlukaTab(self.param_panel)
        self.tab5 = Enhanced3DTab(self.param_panel)
        self.tab6 = LUTTab(self.param_panel)
        self.tab7 = ConfigTab(self.param_panel)

        self.tabs.addTab(self.tab1, "1: V(y) Curve")
        self.tabs.addTab(self.tab2, "2: Single Track")
        self.tabs.addTab(self.tab3, "3: Reference Dataset")
        self.tabs.addTab(self.tab4, "4: FLUKA Process")
        self.tabs.addTab(self.tab5, "5: 3D Enhanced")
        self.tabs.addTab(self.tab6, "6: LUT Simulation")
        self.tabs.addTab(self.tab7, "7: Configuration")

        self.tabs.currentChanged.connect(self._on_tab_changed)

        splitter.addWidget(self.tabs)
        splitter.setSizes([280, 920])

        self.setCentralWidget(splitter)

    def _init_statusbar(self):
        self.statusBar().showMessage("TrackLab — Ready")

    def _on_tab_changed(self, index):
        mode_names = [
            "V(y) Curve Explorer",
            "Single Track Calculation",
            "Reference Dataset Generation",
            "FLUKA Phase-Space Processing",
            "3D Enhanced + Export",
            "LUT Fast Simulation",
            "System Configuration",
        ]
        if 0 <= index < len(mode_names):
            self.statusBar().showMessage(
                f"Mode {index + 1}: {mode_names[index]}  •  "
                f"Ion: {self.param_panel.ion}  •  "
                f"VB: {self.param_panel.vb:.2f} µm/h"
            )

    def _about(self):
        QMessageBox.about(
            self,
            "About TrackLab",
            "<b>TrackLab</b><br><br>"
            "Unified Multi-Ion Nuclear Track Detector Analysis<br><br>"
            "<b>Supported ions:</b> protons, Li, C, O, alpha<br>"
            "<b>V(y) models:</b><br>"
            "  • Dorschel (protons)<br>"
            "  • BPL fitting (Li, C, O)<br><br>"
            "<b>GUI:</b> 7 modes with shared parameter panel<br>"
            "<b>Framework:</b> PyQt6 + Matplotlib + NumPy/SciPy<br>",
        )

    def _show_config_summary(self):
        """Re-open the configuration summary dialog (Help → F1)."""
        # Reset the skip flag so the dialog re-enables itself for next launch
        set_skip_summary(False)
        dlg = ConfigSummaryDialog(theme=self._current_theme, parent=self)
        dlg.exec()

    def _set_theme(self, theme):
        """Switch the active theme."""
        self._current_theme = theme
        self.setStyleSheet(get_stylesheet(theme))
        self.param_panel.set_theme(theme)
        for t, action in self._theme_actions.items():
            action.setChecked(t == theme)
        self.statusBar().showMessage(f"Theme changed to {theme.capitalize()}")

    @property
    def current_theme(self):
        return self._current_theme
