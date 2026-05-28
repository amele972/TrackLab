"""
tab_reference.py — Mode 3: Reference Dataset Generation
=========================================================
Energy × Angle sweep with 3D surfaces, for any ion.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QSpinBox, QProgressBar, QTableWidget,
    QTableWidgetItem, QFrame, QHeaderView, QMessageBox,
    QFileDialog, QTabWidget, QComboBox,
)
from PyQt6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import csv

from .workers import BatchWorker
from .styles import get_plot_colors


class ReferenceTab(QWidget):
    """Mode 3: Reference Dataset with 3D Surfaces."""

    def __init__(self, param_panel):
        super().__init__()
        self.param_panel = param_panel
        self.worker  = None
        self.results = []
        self.energies = []
        self.angles   = []
        self._init_ui()
        self.param_panel.theme_changed.connect(self._on_theme_changed)

    def _colors(self):
        return get_plot_colors(self.param_panel.theme)

    def _on_theme_changed(self, theme):
        c = self._colors()
        self.plot3d_fig.patch.set_facecolor(c['bg'])
        self.analysis_fig.patch.set_facecolor(c['bg'])
        if self.results:
            self._plot_3d_surfaces()
            self._plot_analysis()
        else:
            self.plot3d.draw()
            self.analysis_canvas.draw()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QLabel("Mode 3 — Reference Dataset Generation")
        f = QFont(); f.setBold(True); f.setPointSize(12)
        header.setFont(f)
        header.setStyleSheet("color: #89b4fa;")
        layout.addWidget(header)

        # ── Ion and VB selector row ───────────────────────────────────────────
        ion_row = QHBoxLayout()

        ion_row.addWidget(QLabel("Ion:"))
        self.ion_combo = QComboBox()
        self.ion_combo.addItems(['protons', 'alpha', 'Li', 'C', 'O'])
        self.ion_combo.setCurrentText(
            self.param_panel.ion if hasattr(self.param_panel, 'ion') else 'protons')
        self.ion_combo.setToolTip(
            "Ion species for this reference dataset. Independent of Mode 2 settings.")
        self.ion_combo.currentTextChanged.connect(self._on_ion_changed)
        ion_row.addWidget(self.ion_combo)

        ion_row.addWidget(QLabel("  VB (µm/h):"))
        self.vb_local = QDoubleSpinBox()
        self.vb_local.setRange(0.01, 20.0)
        self.vb_local.setDecimals(3)
        self.vb_local.setSingleStep(0.05)
        self.vb_local.setValue(
            self.param_panel.vb if hasattr(self.param_panel, 'vb') else 1.73)
        self.vb_local.setToolTip(
            "Bulk etch rate for this dataset. Typical: 1.73 µm/h (CR-39 NTD), "
            "4.7 µm/h (proton standard).")
        ion_row.addWidget(self.vb_local)

        ion_row.addWidget(QLabel("  Etching time (h):"))
        self.time_local = QDoubleSpinBox()
        self.time_local.setRange(0.01, 100.0)
        self.time_local.setDecimals(2)
        self.time_local.setSingleStep(0.5)
        self.time_local.setValue(
            self.param_panel.time if hasattr(self.param_panel, 'time') else 2.83)
        self.time_local.setToolTip("Total etching time for track development.")
        ion_row.addWidget(self.time_local)

        ion_row.addStretch()
        layout.addLayout(ion_row)

        # Grid controls
        grid_row = QHBoxLayout()
        for label, attr, lo_val, hi_val, steps_val in [
            ("Energy", "e", 0.1, 10.0, 20),
            ("Angle", "a", 0.0, 90.0, 15),
        ]:
            grid_row.addWidget(QLabel(f"{label} min:"))
            s_min = QDoubleSpinBox()
            s_min.setValue(lo_val); s_min.setRange(0.0, 1000)
            setattr(self, f'{attr}_min', s_min)
            grid_row.addWidget(s_min)

            grid_row.addWidget(QLabel("max:"))
            s_max = QDoubleSpinBox()
            s_max.setValue(hi_val); s_max.setRange(0.0, 1000)
            setattr(self, f'{attr}_max', s_max)
            grid_row.addWidget(s_max)

            grid_row.addWidget(QLabel("pts:"))
            s_pts = QSpinBox()
            s_pts.setValue(steps_val); s_pts.setRange(2, 200)
            setattr(self, f'{attr}_steps', s_pts)
            grid_row.addWidget(s_pts)

        self.gen_btn = QPushButton("Generate")
        self.gen_btn.setProperty("type", "primary")
        self.gen_btn.clicked.connect(self._start)
        grid_row.addWidget(self.gen_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        grid_row.addWidget(self.cancel_btn)
        grid_row.addStretch()
        layout.addLayout(grid_row)

        # Progress
        prog_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        prog_row.addWidget(self.progress_bar, 1)
        self.progress_text = QLabel("Ready")
        self.progress_text.setStyleSheet("color: #a6adc8; font-size: 10px;")
        prog_row.addWidget(self.progress_text)
        layout.addLayout(prog_row)

        # Stats
        stats_row = QHBoxLayout()
        self.val_developed = self._stat_card("Developed", stats_row)
        self.val_total     = self._stat_card("Total", stats_row)
        layout.addLayout(stats_row)

        # Result tabs
        self.tabs = QTabWidget()

        # Data table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Ion", "E (MeV)", "A (°)", "Depth", "Major", "Minor", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.table, "Data Table")

        # 3D surfaces
        c = self._colors()
        self.plot3d_fig = Figure(figsize=(10, 5), dpi=100)
        self.plot3d_fig.patch.set_facecolor(c['bg'])
        self.plot3d = FigureCanvasQTAgg(self.plot3d_fig)
        self.tabs.addTab(self.plot3d, "3D Surfaces")

        # Analysis plot
        analysis_widget = QWidget()
        al = QVBoxLayout(analysis_widget)
        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(QLabel("Slice at angle (°):"))
        self.analysis_angle = QDoubleSpinBox()
        self.analysis_angle.setValue(90.0); self.analysis_angle.setRange(0, 90)
        ctrl_row.addWidget(self.analysis_angle)
        ctrl_row.addStretch()
        al.addLayout(ctrl_row)
        self.analysis_fig = Figure(figsize=(10, 5), dpi=100)
        self.analysis_fig.patch.set_facecolor(c['bg'])
        self.analysis_canvas = FigureCanvasQTAgg(self.analysis_fig)
        al.addWidget(self.analysis_canvas)
        self.tabs.addTab(analysis_widget, "Analysis")

        layout.addWidget(self.tabs, 1)

        # Export
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self._export)
        layout.addWidget(export_btn)

    def _stat_card(self, label_text, parent_layout):
        card = QFrame(); card.setProperty("type", "panel")
        card.setFixedHeight(55)
        v = QVBoxLayout(card); v.setContentsMargins(10, 6, 10, 6)
        v.addWidget(QLabel(label_text))
        val_lbl = QLabel("0")
        val_lbl.setStyleSheet("font-weight: bold; color: #89b4fa;")
        v.addWidget(val_lbl)
        parent_layout.addWidget(card)
        return val_lbl

    def _on_ion_changed(self, ion_name):
        """Auto-fill sensible VB default when the ion changes."""
        defaults = {
            'protons': 1.73,
            'alpha':   1.73,
            'Li':      1.73,
            'C':       1.73,
            'O':       1.73,
        }
        self.vb_local.setValue(defaults.get(ion_name, 1.73))

    def _start(self):
        self.gen_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        params = {
            'ion':     self.ion_combo.currentText(),
            'e_min':   self.e_min.value(),
            'e_max':   self.e_max.value(),
            'e_steps': self.e_steps.value(),
            'a_min':   self.a_min.value(),
            'a_max':   self.a_max.value(),
            'a_steps': self.a_steps.value(),
            'vb':      self.vb_local.value(),
            'time':    self.time_local.value(),
        }
        self.worker = BatchWorker(params)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status_update.connect(self.progress_text.setText)
        self.worker.result_ready.connect(self._on_done)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _cancel(self):
        if self.worker:
            self.worker.running = False
            self.worker.wait()
        self._reset()

    def _on_done(self, data):
        self.results  = data['results']
        self.energies = np.array(data['energies'])
        self.angles   = np.array(data['angles'])

        self.val_developed.setText(str(data['developed']))
        self.val_total.setText(str(data['total']))

        # Fill table
        self.table.setRowCount(min(100, len(self.results)))
        for i, r in enumerate(self.results[:100]):
            self.table.setItem(i, 0, QTableWidgetItem(r.get('ion', '')))
            self.table.setItem(i, 1, QTableWidgetItem(f"{r['energy_MeV']:.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{r['angle_deg']:.1f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{r['depth_um']:.3f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{r['major_axis_um']:.3f}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{r['minor_axis_um']:.3f}"))
            self.table.setItem(i, 6, QTableWidgetItem(r['status']))

        self._plot_3d_surfaces()
        self.analysis_angle.valueChanged.connect(self._plot_analysis)
        self._plot_analysis()
        self._reset()

    def _on_error(self, msg):
        QMessageBox.critical(self, "Error", msg)
        self._reset()

    def _reset(self):
        self.gen_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def _plot_3d_surfaces(self):
        if not self.results:
            return
        n_e, n_a = len(self.energies), len(self.angles)
        minor_grid = np.zeros((n_a, n_e))
        major_grid = np.zeros((n_a, n_e))

        for r in self.results:
            e_idx = np.argmin(np.abs(self.energies - r['energy_MeV']))
            a_idx = np.argmin(np.abs(self.angles - r['angle_deg']))
            minor_grid[a_idx, e_idx] = r['minor_axis_um']
            major_grid[a_idx, e_idx] = r['major_axis_um']

        self.plot3d_fig.clear()
        c = self._colors()
        self.plot3d_fig.patch.set_facecolor(c['bg'])
        E, A = np.meshgrid(self.energies, self.angles)
        for idx, (grid, label) in enumerate([
            (minor_grid, 'Minor Axis (µm)'),
            (major_grid, 'Major Axis (µm)'),
        ]):
            ax = self.plot3d_fig.add_subplot(1, 2, idx + 1, projection='3d')
            ax.plot_surface(E, A, grid, cmap='plasma', alpha=0.85)
            ax.set_xlabel('E (MeV)'); ax.set_ylabel('Angle (°)')
            ax.set_title(label, color=c['text'])
        self.plot3d_fig.tight_layout()
        self.plot3d.draw()

    def _plot_analysis(self):
        if len(self.angles) == 0:
            return
        target = self.analysis_angle.value()
        a_idx = np.argmin(np.abs(self.angles - target))
        actual = self.angles[a_idx]

        pairs = [(r['energy_MeV'], r['major_axis_um'], r['minor_axis_um'])
                 for r in self.results if abs(r['angle_deg'] - actual) < 0.5]
        if not pairs:
            return
        pairs.sort()

        c = self._colors()
        self.analysis_fig.clear()
        self.analysis_fig.patch.set_facecolor(c['bg'])
        ax = self.analysis_fig.add_subplot(111)
        ax.set_facecolor(c['axes_bg'])
        ax.plot([p[0] for p in pairs], [p[1] for p in pairs],
                'o-', color=c['accent'], lw=2, ms=5, label='Major Axis')
        ax.plot([p[0] for p in pairs], [p[2] for p in pairs],
                's-', color=c['accent2'], lw=2, ms=5, label='Minor Axis')
        ax.set_xlabel('Energy (MeV)', color=c['text'])
        ax.set_ylabel('Axis Length (µm)', color=c['text'])
        ax.set_title(f'Axes vs Energy at {actual:.1f}°',
                     color=c['text'], fontweight='bold')
        ax.tick_params(colors=c['muted'])
        ax.legend(facecolor=c['legend_bg'], edgecolor=c['legend_edge'],
                  labelcolor=c['text'])
        ax.grid(True, alpha=0.2, color=c['grid'])
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def _export(self):
        if not self.results:
            QMessageBox.warning(self, "No Data", "Generate first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", "", "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                writer.writeheader()
                writer.writerows(self.results)
            QMessageBox.information(self, "Saved", f"Saved to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


# Alias for import
FigureCanvasQTAgg = FigureCanvas
