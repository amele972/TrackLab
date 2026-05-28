"""
tab_config.py — Mode 7: System Configuration
===============================================
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QTabWidget, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame,
    QComboBox,
)
from PyQt6.QtGui import QFont

from tracklab.config import (
    VB_BY_ION, N_PLASTIC, MICROSCOPE_NA, CONDENSER_NA,
    TIME_ETCHING, SUPPORTED_IONS, OPTICS_MODEL,
    ALPHA_VT_MODEL, ALPHA_MODELS_INFO
)


class ConfigTab(QWidget):
    """Mode 7: System Configuration."""

    def __init__(self, param_panel):
        super().__init__()
        self.param_panel = param_panel
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # ── Settings panel ───
        settings = QFrame(); settings.setProperty("type", "card")
        sl = QVBoxLayout(settings)
        sl.setContentsMargins(16, 16, 16, 16)

        title = QLabel("System Configuration")
        f = QFont(); f.setBold(True); f.setPointSize(12)
        title.setFont(f)
        title.setStyleSheet("color: #89b4fa;")
        sl.addWidget(title)

        tabs = QTabWidget()

        # Ion VB tab
        vb_tab = QWidget()
        vl = QVBoxLayout(vb_tab)
        vl.addWidget(QLabel("Ion-Specific Bulk Etch Rates"))
        self.vb_table = QTableWidget(len(SUPPORTED_IONS), 2)
        self.vb_table.setHorizontalHeaderLabels(["Ion", "VB (µm/h)"])
        self.vb_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        for i, ion in enumerate(SUPPORTED_IONS):
            self.vb_table.setItem(i, 0, QTableWidgetItem(ion))
            item = QTableWidgetItem(f"{VB_BY_ION.get(ion, 4.7):.3f}")
            self.vb_table.setItem(i, 1, item)
        vl.addWidget(self.vb_table)
        tabs.addTab(vb_tab, "Ion VB")

        # Optical tab
        opt_tab = QWidget()
        ol = QVBoxLayout(opt_tab)
        ol.addWidget(QLabel("Optical Model Parameters"))
        self._opt_spins = {}
        for label, key, val in [
            ("CR-39 refractive index:", "n", N_PLASTIC),
            ("Objective NA:", "na", MICROSCOPE_NA),
            ("Condenser NA:", "cond", CONDENSER_NA),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            s = QDoubleSpinBox(); s.setValue(val); s.setDecimals(4)
            s.setRange(0.001, 5.0)
            self._opt_spins[key] = s
            row.addWidget(s)
            ol.addLayout(row)
        
        # New Optics Engine selection
        fid_row = QHBoxLayout()
        fid_row.addWidget(QLabel("Model Fidelity (Ray-Trace):"))
        self.optics_combo = QComboBox()
        self.optics_combo.addItems(["Optimized (v2.0)", "Full Trace (v3.0)"])
        # Set current index based on config
        self.optics_combo.setCurrentIndex(1 if OPTICS_MODEL == "full_trace" else 0)
        fid_row.addWidget(self.optics_combo)
        ol.addLayout(fid_row)
        
        ol.addStretch()
        tabs.addTab(opt_tab, "Optical")

        # Etching tab
        etch_tab = QWidget()
        el = QVBoxLayout(etch_tab)
        el.addWidget(QLabel("Default Etching Parameters"))
        self._etch_spins = {}
        for label, key, val in [
            ("Default VB (µm/h):", "vb", VB_BY_ION.get('protons', 4.7)),
            ("Default Time (h):", "t", TIME_ETCHING),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            s = QDoubleSpinBox(); s.setValue(val); s.setDecimals(3)
            self._etch_spins[key] = s
            row.addWidget(s)
            el.addLayout(row)
        el.addStretch()
        tabs.addTab(etch_tab, "Etching")

        # Alpha Physics tab
        alpha_tab = QWidget()
        al = QVBoxLayout(alpha_tab)
        al.addWidget(QLabel("Alpha Particle V(y) Model Selection"))
        
        row = QHBoxLayout()
        row.addWidget(QLabel("Active Model:"))
        self.alpha_combo = QComboBox()
        for idx, info in ALPHA_MODELS_INFO.items():
            if idx in [2, 4, 5, 7]:
                self.alpha_combo.addItem(f"Model {idx}: {info['name']}", idx)
        
        # Set current
        idx_to_set = self.alpha_combo.findData(ALPHA_VT_MODEL)
        if idx_to_set >= 0:
            self.alpha_combo.setCurrentIndex(idx_to_set)
        
        row.addWidget(self.alpha_combo)
        al.addLayout(row)
        
        self.alpha_formula = QLabel("")
        self.alpha_formula.setStyleSheet("font-style: italic; color: #fab387; margin-top: 5px;")
        self.alpha_formula.setWordWrap(True)
        al.addWidget(self.alpha_formula)
        
        self.alpha_params_label = QLabel("")
        self.alpha_params_label.setStyleSheet("font-size: 10px; color: #a6adc8; margin-top: 5px;")
        al.addWidget(self.alpha_params_label)
        
        al.addStretch()
        tabs.addTab(alpha_tab, "Alpha Physics")

        sl.addWidget(tabs)
        
        # Connect changes to global config
        self.optics_combo.currentIndexChanged.connect(self._on_optics_changed)
        self.alpha_combo.currentIndexChanged.connect(self._on_alpha_changed)
        
        self._update_alpha_info()
        
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._on_save)
        sl.addWidget(save_btn)
        sl.addStretch()
        layout.addWidget(settings, 1)

        # Call info panel helper
        self._init_ui_info_panel(layout, f)

    def _on_optics_changed(self, index):
        import tracklab.config as cfg
        model = "full_trace" if index == 1 else "optimized"
        cfg.OPTICS_MODEL = model
        print(f"[Config] Optics model changed to: {model}")

    def _on_alpha_changed(self, index):
        import tracklab.config as cfg
        model_idx = self.alpha_combo.currentData()
        cfg.ALPHA_VT_MODEL = model_idx
        self._update_alpha_info()
        # Clear physics cache so re-calculation picks up the new model
        from tracklab.vt_utils import clear_vrint_cache
        clear_vrint_cache()
        print(f"[Config] Alpha VT Model changed to: {model_idx}")

    def _update_alpha_info(self):
        idx = self.alpha_combo.currentData()
        info = ALPHA_MODELS_INFO.get(idx)
        if info:
            self.alpha_formula.setText(f"Formula: {info['formula']}")
            p_str = " | ".join([f"{k}={v}" for k, v in info['p'].items()])
            self.alpha_params_label.setText(f"Parameters: {p_str}")

    def _on_save(self):
        QMessageBox.information(
            self, "Settings",
            "Settings updated. Physics engine now using " + 
            ("Full Trace (v3.0)" if self.optics_combo.currentIndex() == 1 else "Optimized (v2.0)"))

    def _init_ui_info_panel(self, layout, f):
        # ── Info panel ───
        info = QFrame(); info.setProperty("type", "card")
        il = QVBoxLayout(info)
        il.setContentsMargins(16, 16, 16, 16)

        info_title = QLabel("System Information")
        info_title.setFont(f)
        info_title.setStyleSheet("color: #89b4fa;")
        il.addWidget(info_title)

        info_text = QLabel(
            "<b>TrackLab v1.0</b> — Unified Multi-Ion Package<br><br>"
            "<b>Supported Ions:</b> protons, Li, C, O, alpha<br><br>"
            "<b>Mode 1</b> — V(y) Curve Explorer<br>"
            "<b>Mode 2</b> — Single Track Calculation<br>"
            "<b>Mode 3</b> — Reference Dataset Generation<br>"
            "<b>Mode 4</b> — FLUKA Phase-Space Processing<br>"
            "<b>Mode 5</b> — 3D Enhanced + Blender Export<br>"
            "<b>Mode 6</b> — LUT Fast Simulation:<br>"
            "&nbsp;&nbsp;• 6a Single lookup (&lt;1 ms)<br>"
            "&nbsp;&nbsp;• 6b FLUKA batch (1M particles/min)<br>"
            "&nbsp;&nbsp;• 6c Inverse: axes → (E, θ)<br>"
            "<b>Mode 7</b> — Configuration<br><br>"
            "<b>V(y) Models:</b><br>"
            "&nbsp;&nbsp;• protons: Dorschel analytical (5 params)<br>"
            "&nbsp;&nbsp;• Li, C, O: Broken Power Law (BPL)<br><br>"
            "<b>Data files:</b><br>"
            "&nbsp;&nbsp;• Rang_CR_all_ions_SRIM.dat<br>"
            "&nbsp;&nbsp;• Data_ions.xlsx<br>"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #cdd6f4;")
        il.addWidget(info_text)
        il.addStretch()
        layout.addWidget(info, 1)
