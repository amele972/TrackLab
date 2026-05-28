"""
tab_lut.py — Mode 6: LUT-Based Fast Simulation
=================================================
Sub-ms lookups, inverse problem, and batch FLUKA processing from a
pre-computed reference CSV.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QTabWidget,
    QProgressBar, QTextEdit, QFrame,
)
from PyQt6.QtGui import QFont
import os
import pandas as pd

from .workers import GenericWorker


def _section_label(text, size=10):
    l = QLabel(text)
    f = QFont(); f.setBold(True); f.setPointSize(size); l.setFont(f)
    l.setStyleSheet("color: #89b4fa;")
    return l


# ── LUT Loader Mixin ────────────────────────────────────────────────

class _LUTLoaderMixin:
    """Mixin that adds a LUT load bar + shared lut property."""

    def _make_lut_bar(self, layout):
        row = QHBoxLayout()
        self.lut_label = QLabel("No LUT loaded")
        self.lut_label.setStyleSheet("color: #6c7086;")
        row.addWidget(self.lut_label, 1)
        btn = QPushButton("Load LUT CSV")
        btn.clicked.connect(self._load_lut)
        row.addWidget(btn)
        layout.addLayout(row)
        self._lut = None

    def _load_lut(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Mode-3 Reference CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            from tracklab.lut_engine import LUTEngine
            self._lut = LUTEngine(path)
            e = self._lut.energy_range
            a = self._lut.angle_range
            self.lut_label.setText(
                f"LUT: {os.path.basename(path)}  "
                f"n={self._lut.n_points}  "
                f"E=[{e[0]:.1f},{e[1]:.1f}] MeV  "
                f"θ=[{a[0]:.1f},{a[1]:.1f}]°")
            self.lut_label.setStyleSheet(
                "color: #a6e3a1; font-weight: bold;")
            self._on_lut_loaded()
        except Exception as ex:
            QMessageBox.critical(self, "Load error", str(ex))

    def _on_lut_loaded(self):
        pass


# ── Tab 6a: Single Lookup ───────────────────────────────────────────

class _Tab6a(QWidget, _LUTLoaderMixin):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.addWidget(_section_label("LUT File"))
        self._make_lut_bar(lay)
        lay.addWidget(QLabel(""))
        lay.addWidget(_section_label("Query"))

        grid = QHBoxLayout()
        for lbl, attr, val in [("Energy (MeV):", "e_spin", 1.5),
                                ("Angle (°):",    "a_spin", 75.0)]:
            grid.addWidget(QLabel(lbl))
            s = QDoubleSpinBox(); s.setValue(val); s.setRange(0.01, 1000)
            setattr(self, attr, s); grid.addWidget(s)
        btn = QPushButton("Lookup"); btn.setProperty("type", "primary")
        btn.clicked.connect(self._lookup); grid.addWidget(btn)
        grid.addStretch(); lay.addLayout(grid)

        lay.addWidget(QLabel(""))
        lay.addWidget(_section_label("Result"))
        self.result_table = QTableWidget(9, 2)
        self.result_table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.result_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.result_table.setMaximumHeight(250)
        params = ["Energy (MeV)", "Angle (°)", "Developed",
                  "Major axis (µm)", "Minor axis (µm)", "Depth (µm)",
                  "Total proj. length (µm)", "Black fraction", "Total surface (µm²)"]
        for i, p in enumerate(params):
            self.result_table.setItem(i, 0, QTableWidgetItem(p))
            self.result_table.setItem(i, 1, QTableWidgetItem("—"))
        lay.addWidget(self.result_table)
        lay.addStretch()

    def _lookup(self):
        if not self._lut:
            QMessageBox.warning(self, "No LUT", "Load a LUT CSV first.")
            return
        res = self._lut.query(self.e_spin.value(), self.a_spin.value())
        rows = [
            f"{res['energy_MeV']:.3f}",
            f"{res['angle_deg']:.2f}",
            "Yes ✓" if res['developed'] else "No ✗",
            f"{(res['major_axis_um']):.3f}" if res['developed'] else "—",
            f"{(res['minor_axis_um']):.3f}" if res['developed'] else "—",
            f"{(res['depth_um']):.3f}"      if res['developed'] else "—",
            f"{(res['total_length_um']):.3f}" if res['developed'] else "—",
            f"{(res['black_part']):.3f}"    if res['developed'] else "—",
            f"{(res['total_surface']):.2f}" if res['developed'] else "—",
        ]
        for i, v in enumerate(rows):
            self.result_table.setItem(i, 1, QTableWidgetItem(v))


# ── Tab 6b: FLUKA Batch ────────────────────────────────────────────

class _Tab6b(QWidget, _LUTLoaderMixin):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.addWidget(_section_label("LUT File"))
        self._make_lut_bar(lay)
        lay.addWidget(QLabel(""))

        file_row = QHBoxLayout()
        self.file_lbl = QLabel("No file selected")
        self.file_lbl.setStyleSheet("color: #6c7086;")
        file_row.addWidget(self.file_lbl, 1)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        file_row.addWidget(browse)
        lay.addLayout(file_row)
        self._fluka_path = None

        opts_row = QHBoxLayout()
        opts_row.addWidget(QLabel("Skip header:"))
        self.skip_spin = QSpinBox(); self.skip_spin.setValue(1)
        self.skip_spin.setRange(0, 100)
        opts_row.addWidget(self.skip_spin)
        opts_row.addWidget(QLabel("VB (µm/h):"))
        self.vb_spin = QDoubleSpinBox(); self.vb_spin.setValue(4.7)
        opts_row.addWidget(self.vb_spin)
        opts_row.addStretch()
        lay.addLayout(opts_row)

        self.run_btn = QPushButton("Process File")
        self.run_btn.setProperty("type", "primary")
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._run)
        lay.addWidget(self.run_btn)

        self.prog_bar = QProgressBar()
        lay.addWidget(self.prog_bar)
        self.log = QTextEdit(); self.log.setReadOnly(True)
        self.log.setMaximumHeight(200)
        lay.addWidget(self.log)

        self.export_btn = QPushButton("Export CSV")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export)
        lay.addWidget(self.export_btn)
        lay.addStretch()
        self._result_df = None

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "FLUKA file", "", "Text (*.txt);;All (*)")
        if path:
            self._fluka_path = path
            self.file_lbl.setText(os.path.basename(path))
            self.file_lbl.setStyleSheet("color: #cdd6f4; font-weight: bold;")
            if self._lut:
                self.run_btn.setEnabled(True)

    def _on_lut_loaded(self):
        if self._fluka_path:
            self.run_btn.setEnabled(True)

    def _run(self):
        if not self._lut or not self._fluka_path:
            return
        self.run_btn.setEnabled(False)
        self.prog_bar.setRange(0, 0)
        self.log.clear()

        def do_work():
            return self._lut.process_fluka_file(
                self._fluka_path,
                skip_header=self.skip_spin.value(),
                vb=self.vb_spin.value())

        self._worker = GenericWorker(do_work)
        self._worker.finished.connect(self._done)
        self._worker.error.connect(
            lambda e: (QMessageBox.critical(self, "Error", e),
                       self.run_btn.setEnabled(True)))
        self._worker.start()

    def _done(self, df):
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(100)
        self._result_df = df
        dev = df[df['developed']] if 'developed' in df.columns else df
        self.log.setPlainText(
            f"Particles processed: {len(df)}\n"
            f"Developed tracks: {len(dev)} ({len(dev)/max(len(df),1):.1%})")
        self.run_btn.setEnabled(True)
        self.export_btn.setEnabled(True)

    def _export(self):
        if self._result_df is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", "", "CSV (*.csv)")
        if path:
            self._result_df.to_csv(path, index=False)
            QMessageBox.information(self, "Saved", path)


# ── Tab 6c: Inverse Problem ────────────────────────────────────────

class _Tab6c(QWidget, _LUTLoaderMixin):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.addWidget(_section_label("LUT File"))
        self._make_lut_bar(lay)
        lay.addWidget(QLabel(""))
        lay.addWidget(_section_label(
            "Measured axes → estimate (E, θ)"))

        q_row = QHBoxLayout()
        for lbl, attr, val in [("Major axis (µm):", "maj_spin", 10.0),
                                ("Minor axis (µm):", "min_spin", 9.0),
                                ("# solutions:",     "n_spin",  5)]:
            q_row.addWidget(QLabel(lbl))
            if attr == "n_spin":
                s = QSpinBox(); s.setValue(val); s.setRange(1, 20)
            else:
                s = QDoubleSpinBox(); s.setValue(val); s.setRange(0.1, 500)
            setattr(self, attr, s); q_row.addWidget(s)
        btn = QPushButton("Find Solutions")
        btn.setProperty("type", "primary")
        btn.clicked.connect(self._solve)
        q_row.addWidget(btn)
        q_row.addStretch(); lay.addLayout(q_row)

        self.sol_table = QTableWidget(0, 6)
        self.sol_table.setHorizontalHeaderLabels(
            ["Rank", "E (MeV)", "θ (°)", "Major (µm)", "Residual", "Confidence"])
        self.sol_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.sol_table)
        lay.addStretch()
        self._sol_df = None

    def _solve(self):
        if not self._lut:
            QMessageBox.warning(self, "No LUT", "Load a LUT CSV first.")
            return
        try:
            sol = self._lut.inverse_lookup(
                self.maj_spin.value(), self.min_spin.value(),
                n_solutions=self.n_spin.value())
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        if sol.empty:
            QMessageBox.warning(self, "No Match", "No solutions found.")
            return
        self._sol_df = sol
        self.sol_table.setRowCount(len(sol))
        for i, row in sol.iterrows():
            for j, val in enumerate([
                str(i + 1),
                f"{row['energy_MeV']:.3f}",
                f"{row['angle_deg']:.2f}",
                f"{row['major_axis_um']:.3f}",
                f"{row['residual_um']:.4f}",
                f"{row['confidence']:.3f}",
            ]):
                self.sol_table.setItem(i, j, QTableWidgetItem(val))


# ── Mode 6 Widget ──────────────────────────────────────────────────

class LUTTab(QWidget):
    """Mode 6: LUT-Based Fast Simulation (3 sub-tabs)."""

    def __init__(self, param_panel):
        super().__init__()
        self.param_panel = param_panel
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QLabel("Mode 6 — LUT-Based Fast Simulation")
        f = QFont(); f.setBold(True); f.setPointSize(12)
        header.setFont(f)
        header.setStyleSheet("color: #89b4fa;")
        layout.addWidget(header)

        desc = QLabel(
            "Load a pre-computed Mode-3 reference CSV; "
            "then query at sub-millisecond speed.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        layout.addWidget(desc)

        tabs = QTabWidget()
        tabs.addTab(_Tab6a(), "6a: Single Lookup")
        tabs.addTab(_Tab6b(), "6b: FLUKA Batch")
        tabs.addTab(_Tab6c(), "6c: Inverse (axes→E,θ)")
        layout.addWidget(tabs)
