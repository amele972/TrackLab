"""
tab_fluka.py — Mode 4: FLUKA Phase-Space Processing
=====================================================
Process FLUKA output files and calculate track parameters for any ion.
"""

import csv
import os
import re

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .workers import FlukaWorker


class FlukaTab(QWidget):
    """Mode 4: FLUKA Phase-Space Processing."""

    def __init__(self, param_panel):
        super().__init__()
        self.param_panel = param_panel
        self.worker = None
        self.results = []
        self.input_file = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QLabel("Mode 4 — FLUKA Phase-Space Processing")
        f = QFont()
        f.setBold(True)
        f.setPointSize(12)
        header.setFont(f)
        header.setStyleSheet("color: #89b4fa;")
        layout.addWidget(header)

        desc = QLabel(
            "Load a FLUKA phase-space file and compute track parameters "
            "for each particle using the selected ion type."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        layout.addWidget(desc)

        # File selection
        file_row = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #6c7086;")
        file_row.addWidget(self.file_label, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        # Options
        opts_row = QHBoxLayout()
        opts_row.addWidget(QLabel("Skip header:"))
        self.skip_header = QSpinBox()
        self.skip_header.setValue(1)
        self.skip_header.setRange(0, 100)
        opts_row.addWidget(self.skip_header)
        opts_row.addStretch()
        layout.addLayout(opts_row)

        # Buttons
        btn_row = QHBoxLayout()
        self.process_btn = QPushButton("Process File")
        self.process_btn.setProperty("type", "primary")
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self._start)
        btn_row.addWidget(self.process_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Progress
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        self.status_text = QLabel("Ready")
        self.status_text.setStyleSheet("color: #a6adc8; font-size: 10px;")
        layout.addWidget(self.status_text)

        # Stats
        stats_row = QHBoxLayout()
        self.val_processed = self._stat_card("Processed", stats_row)
        self.val_developed = self._stat_card("Developed", stats_row)
        self.val_skipped = self._stat_card("Skipped", stats_row)
        layout.addLayout(stats_row)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["E (MeV)", "Angle (°)", "Depth", "Major", "Minor", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table, 1)

        # Export
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self._export)
        layout.addWidget(export_btn)

    def _stat_card(self, label_text, parent_layout):
        card = QFrame()
        card.setProperty("type", "panel")
        card.setFixedHeight(55)
        v = QVBoxLayout(card)
        v.setContentsMargins(10, 6, 10, 6)
        v.addWidget(QLabel(label_text))
        val_lbl = QLabel("0")
        val_lbl.setStyleSheet("font-weight: bold; color: #89b4fa;")
        v.addWidget(val_lbl)
        parent_layout.addWidget(card)
        return val_lbl

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select FLUKA File", "", "Text Files (*.txt);;All (*)"
        )
        if path:
            # Reset state for the new file
            self.input_file = os.path.abspath(path)
            self.results = []
            self.val_processed.setText("0")
            self.val_developed.setText("0")
            self.val_skipped.setText("0")
            self.table.setRowCount(0)

            self.file_label.setText(os.path.basename(path))
            self.file_label.setStyleSheet("color: #cdd6f4; font-weight: bold;")
            self.process_btn.setEnabled(True)
            # Try to auto-detect beam energy from filename (e.g. '1MeV.txt' -> 1.0)
            self._beam_energy = self._parse_beam_energy(os.path.basename(path))
            if self._beam_energy:
                self.status_text.setText(
                    f"Loaded: {os.path.basename(path)}  |  Beam energy: {self._beam_energy} MeV (auto-detected)"
                )
            else:
                self.status_text.setText(
                    f"Loaded: {os.path.basename(path)}  |  ⚠ Beam energy not detected from filename"
                )

    def _parse_beam_energy(self, filename):
        """Extract nominal beam energy in MeV from a filename like '1MeV.txt' or '2,5MeV.txt'."""
        # Match patterns like '1MeV', '2,5MeV', '14,8MeV', '0,5642MeV'
        m = re.search(r"([\d,\.]+)\s*MeV", filename, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except ValueError:
                pass
        return None

    def _start(self):
        if not self.input_file:
            return

        # Ensure latest parameters and clear UI
        self.process_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.table.setRowCount(0)
        self.results = []

        params = {
            "ion": self.param_panel.ion,
            "vb": self.param_panel.vb,
            "time": self.param_panel.time,
            "file": self.input_file,
            "skip_header": self.skip_header.value(),
            "beam_energy_MeV": getattr(self, "_beam_energy", None),
        }

        print(f"\n[FlukaTab] Starting process for: {self.input_file}")
        self.worker = FlukaWorker(params)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status_update.connect(self.status_text.setText)
        self.worker.result_ready.connect(self._on_done)
        self.worker.error.connect(
            lambda e: (QMessageBox.critical(self, "Error", e), self._reset())
        )
        self.worker.start()

    def _cancel(self):
        if self.worker:
            self.worker.running = False
            self.worker.wait()
        self._reset()

    def _on_done(self, data):
        self.results = data["results"]
        self.val_processed.setText(str(data["processed"]))
        self.val_developed.setText(str(data["developed"]))
        self.val_skipped.setText(str(data["skipped"]))

        self.table.setRowCount(min(100, len(self.results)))
        for i, r in enumerate(self.results[:100]):
            self.table.setItem(i, 0, QTableWidgetItem(f"{r['energy_MeV']:.2f}"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{r['angle_deg']:.1f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{r['depth_um']:.3f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{r['major_axis_um']:.3f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{r['minor_axis_um']:.3f}"))
            self.table.setItem(i, 5, QTableWidgetItem(r["status"]))
        self._reset()

    def _reset(self):
        self.process_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def _export(self):
        if not self.results:
            QMessageBox.warning(self, "No Data", "Process a file first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                writer.writeheader()
                writer.writerows(self.results)
            QMessageBox.information(self, "Saved", f"Saved to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
