"""
param_panel.py — TrackLab v1.0 Shared Parameter Panel
==========================================================
Left-side panel with shared ion/energy/angle/VB/time controls.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QFrame, QGroupBox,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import pyqtSignal
    
from tracklab.config import SUPPORTED_IONS, VB_BY_ION, TIME_ETCHING


class ParamPanel(QWidget):
    """Shared parameter panel for all modes."""

    ion_changed    = pyqtSignal(str)
    params_changed = pyqtSignal()
    theme_changed  = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self._theme = 'light'
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Title
        title = QLabel("⚛  TrackLab v1.0")
        f = QFont(); f.setBold(True); f.setPointSize(13)
        title.setFont(f)
        title.setStyleSheet("color: #89b4fa; margin-bottom: 8px;")
        layout.addWidget(title)

        subtitle = QLabel("Unified Multi-Ion Track Detector")
        subtitle.setStyleSheet("color: #a6adc8; font-size: 11px; "
                               "margin-bottom: 12px;")
        layout.addWidget(subtitle)

        # ─── Ion Selection ───
        ion_group = QGroupBox("Ion Selection")
        ig_layout = QVBoxLayout(ion_group)

        row = QHBoxLayout()
        row.addWidget(QLabel("Ion:"))
        self.ion_combo = QComboBox()
        self.ion_combo.addItems(SUPPORTED_IONS)
        self.ion_combo.setCurrentText('protons')
        self.ion_combo.currentTextChanged.connect(self._on_ion_changed)
        row.addWidget(self.ion_combo)
        ig_layout.addLayout(row)

        layout.addWidget(ion_group)

        # ─── Physical Parameters ───
        phys_group = QGroupBox("Physical Parameters")
        pg_layout = QVBoxLayout(phys_group)

        self._spins = {}
        for label, key, default, lo, hi, decimals in [
            ("Energy (MeV):", "energy", 1.5,  0.01, 1000, 3),
            ("Angle (°):",    "angle",  75.0, 0.0,  90.0, 1),
            ("VB (µm/h):",    "vb",     4.7,  0.01, 20.0, 3),
            ("Time (h):",     "time",   TIME_ETCHING, 0.01, 100.0, 3),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setMinimumWidth(90)
            row.addWidget(lbl)
            spin = QDoubleSpinBox()
            spin.setValue(default)
            spin.setRange(lo, hi)
            spin.setDecimals(decimals)
            spin.setSingleStep(0.1)
            spin.valueChanged.connect(self._on_param_changed)
            self._spins[key] = spin
            row.addWidget(spin)
            pg_layout.addLayout(row)

        layout.addWidget(phys_group)

        # ─── VB Info ───
        self.vb_info = QLabel("")
        self.vb_info.setStyleSheet("color: #a6adc8; font-size: 10px;")
        self.vb_info.setWordWrap(True)
        layout.addWidget(self.vb_info)
        self._update_vb_info()

        layout.addStretch()

        # ─── Status ───
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(
            "color: #a6adc8; font-size: 10px; padding: 4px;")
        layout.addWidget(self.status_label)

    def _on_ion_changed(self, ion_name):
        """Update VB to ion-specific default."""
        vb = VB_BY_ION.get(ion_name, 1.73)
        self._spins['vb'].setValue(vb)
        self._update_vb_info()
        self.ion_changed.emit(ion_name)

    def _on_param_changed(self):
        self.params_changed.emit()

    def _update_vb_info(self):
        ion = self.ion_combo.currentText()
        vb = VB_BY_ION.get(ion, 4.7)
        self.vb_info.setText(
            f"Default VB for {ion}: {vb:.2f} µm/h")

    # ─── Public API ───
    @property
    def ion(self):
        return self.ion_combo.currentText()

    @property
    def energy(self):
        return self._spins['energy'].value()

    @property
    def angle(self):
        return self._spins['angle'].value()

    @property
    def vb(self):
        return self._spins['vb'].value()

    @property
    def time(self):
        return self._spins['time'].value()

    def get_params(self):
        """Return dict of all current parameters."""
        return {
            'ion':    self.ion,
            'energy': self.energy,
            'angle':  self.angle,
            'vb':     self.vb,
            'time':   self.time,
        }

    def set_status(self, text):
        self.status_label.setText(text)

    @property
    def theme(self):
        return self._theme

    def set_theme(self, theme):
        self._theme = theme
        self.theme_changed.emit(theme)
