"""
tab_single_track.py — Mode 2: Single Track Calculation
========================================================
4-panel track visualization for any ion.
"""

import numpy as np
from matplotlib import cm
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .styles import get_plot_colors
from .workers import TrackWorker


class SingleTrackTab(QWidget):
    """Mode 2: Single track with 4-panel visualization."""

    def __init__(self, param_panel):
        super().__init__()
        self.param_panel = param_panel
        self.result = None
        self.worker = None
        self._init_ui()
        self.param_panel.theme_changed.connect(self._on_theme_changed)

    def _colors(self):
        return get_plot_colors(self.param_panel.theme)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header
        header = QLabel("Mode 2 — Single Track Calculation")
        f = QFont()
        f.setBold(True)
        f.setPointSize(12)
        header.setFont(f)
        header.setStyleSheet("color: #89b4fa;")
        layout.addWidget(header)

        # Results row
        results_row = QHBoxLayout()
        self.result_labels = {}
        for key, label in [
            ("depth", "Depth (µm)"),
            ("major", "Major (µm)"),
            ("minor", "Minor (µm)"),
            ("total_length", "Proj. Diam (µm)"),
            ("black", "Black (%)"),
            ("surface", "Surface (µm²)"),
        ]:
            card = QFrame()
            card.setProperty("type", "panel")
            card.setMinimumWidth(80)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 6, 10, 6)
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 10px;")
            cl.addWidget(lbl)
            val = QLabel("—")
            val.setStyleSheet("font-weight: bold; font-size: 14px;")
            cl.addWidget(val)
            self.result_labels[key] = val
            results_row.addWidget(card)
        layout.addLayout(results_row)

        # Buttons
        btn_row = QHBoxLayout()
        self.calc_btn = QPushButton("Calculate Track")
        self.calc_btn.setProperty("type", "primary")
        self.calc_btn.clicked.connect(self._calculate)
        btn_row.addWidget(self.calc_btn)

        self.export_btn = QPushButton("Export PNG")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export)
        btn_row.addWidget(self.export_btn)

        self.status = QLabel("Ready")
        self.status.setStyleSheet("font-size: 10px;")
        btn_row.addWidget(self.status)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Plot canvas
        c = self._colors()
        self.fig = Figure(figsize=(12, 9), dpi=100)
        self.fig.patch.set_facecolor(c["bg"])
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas, 1)

    def _on_theme_changed(self, theme):
        c = self._colors()
        self.fig.patch.set_facecolor(c["bg"])
        # Re-plot if we have data
        if self.result and self.result.get("indicator", -1) == 1:
            self._plot_4panel(self.result)
        else:
            self.canvas.draw()

    def _calculate(self):
        self.calc_btn.setEnabled(False)
        self.status.setText("Computing…")

        params = self.param_panel.get_params()
        self.worker = TrackWorker(params)
        self.worker.result_ready.connect(self._on_result)
        self.worker.error.connect(self._on_error)
        self.worker.status_update.connect(self.status.setText)
        self.worker.start()

    def _on_result(self, res):
        self.result = res
        self.calc_btn.setEnabled(True)

        if res.get("indicator", -1) != 1:
            self.status.setText(f"❌ {res.get('status', 'Not developed')}")
            for v in self.result_labels.values():
                v.setText("—")
            return

        self.result_labels["depth"].setText(f"{res['depth_um']:.3f}")
        self.result_labels["major"].setText(f"{res['major_axis_um']:.3f}")
        self.result_labels["minor"].setText(f"{res['minor_axis_um']:.3f}")
        self.result_labels["total_length"].setText(f"{res['total_length_um']:.3f}")
        self.result_labels["black"].setText(f"{res['black_part'] * 100:.1f}")
        self.result_labels["surface"].setText(f"{res['total_surface']:.1f}")
        self.status.setText(
            f"✅ {self.param_panel.ion} @ {self.param_panel.energy:.2f} MeV, "
            f"{self.param_panel.angle:.1f}°"
        )
        self._plot_4panel(res)
        self.export_btn.setEnabled(True)

    def _on_error(self, msg):
        self.calc_btn.setEnabled(True)
        self.status.setText(f"❌ {msg}")
        QMessageBox.critical(self, "Error", msg)

    def _plot_4panel(self, res):
        X, Y, Z, B = (res["X_surf"], res["Y_surf"], res["Z_surf"], res["B_faces"])
        if X is None or np.isnan(X).all():
            return

        c = self._colors()
        self.fig.clear()
        self.fig.patch.set_facecolor(c["bg"])

        depth = res["depth_um"]

        pad = (X.max() - X.min()) * 0.2
        lim_x = (X.min() - pad, X.max() + pad)
        lim_y = (Y.min() - pad, Y.max() + pad)
        lim_z = (Z.min() * 1.1, 0)

        ion = self.param_panel.ion
        energy = self.param_panel.energy
        angle = self.param_panel.angle

        # 3D surface
        ax1 = self.fig.add_subplot(2, 2, 1, projection="3d")
        ax1.set_facecolor(c["axes_bg"])
        if B is not None:
            ax1.plot_surface(
                X,
                Y,
                Z,
                facecolors=cm.gray(B),
                linewidth=0,
                antialiased=True,
                shade=True,
                rstride=1,
                cstride=1,
            )
        ax1.set_xlim(lim_x)
        ax1.set_ylim(lim_y)
        ax1.set_zlim(lim_z)
        ax1.set_title(
            f"3D — {ion} {energy:.2f} MeV, {angle:.1f}°",
            color=c["text"],
            fontweight="bold",
            pad=15,
        )
        ax1.set_xlabel("X (µm)")
        ax1.set_ylabel("Y (µm)")
        ax1.set_zlabel("Z (µm)")
        ax1.view_init(elev=25, azim=-50)

        # XY microscope view
        ax2 = self.fig.add_subplot(2, 2, 2)
        ax2.set_facecolor("#DCDCDC")
        if B is not None:
            ax2.pcolormesh(
                X, Y, B, cmap="gray", shading="flat", vmin=0, vmax=1, rasterized=True
            )
        ax2.plot(X[0, :], Y[0, :], "k-", lw=1)

        # Vibrant scientific colors for indicators
        c_maj, c_min, c_dep = "#007bff", "#ff7200", "#00c853"

        # Major Axis Arrow
        x_min_op, x_max_op = X[0, :].min(), X[0, :].max()
        ax2.annotate(
            "",
            xy=(x_min_op, 0),
            xytext=(x_max_op, 0),
            arrowprops=dict(arrowstyle="<->", color=c_maj, lw=1.5),
        )

        # Minor Axis Arrow (at widest point)
        y_max_op = Y[0, :].max()
        idx_max_y = np.argmax(Y[0, :])
        x_at_max_y = X[0, idx_max_y]
        ax2.annotate(
            "",
            xy=(x_at_max_y, -y_max_op),
            xytext=(x_at_max_y, y_max_op),
            arrowprops=dict(arrowstyle="<->", color=c_min, lw=1.5, alpha=1.0),
        )

        # Legend with colored markers for axes
        from matplotlib.lines import Line2D

        custom_lines = [
            Line2D([0], [0], color="k", lw=1),
            Line2D([0], [0], color=c_maj, lw=1.5),
            Line2D([0], [0], color=c_min, lw=1.5),
        ]
        ax2.legend(
            custom_lines,
            ["Opening", "Major Axis", "Minor Axis"],
            fontsize=8,
            loc="upper right",
            framealpha=0.8,
        )

        ax2.set_xlim(lim_x)
        ax2.set_ylim(lim_y)
        ax2.set_aspect("equal")
        ax2.set_title("XY Microscope View", color=c["text"], fontweight="bold")
        ax2.set_xlabel("X (µm)")
        ax2.set_ylabel("Y (µm)")

        # YZ cross-section
        ax3 = self.fig.add_subplot(2, 2, 3)
        ax3.set_facecolor(c["axes_bg"])
        ax3.plot(Y, Z, color="black", alpha=0.05)
        y_b, z_b = Y[-1, :], Z[-1, :]
        y_c = np.append(y_b, y_b[0])
        z_c = np.append(z_b, z_b[0])
        ax3.fill(y_c, z_c, color=c["accent"], alpha=0.15)
        ax3.plot(y_c, z_c, color=c["accent"], lw=2)
        ax3.axhline(0, color=c["grid"], ls="--", lw=1, alpha=0.5)

        # Depth indicator in YZ (Left side)
        ax3.axhline(-depth, color=c_dep, ls=":", lw=1.5, alpha=0.6)
        y_pos_arrow = Y.min() + (Y.max() - Y.min()) * 0.02
        ax3.annotate(
            "",
            xy=(y_pos_arrow, -depth),
            xytext=(y_pos_arrow, 0),
            arrowprops=dict(arrowstyle="<->", color=c_dep, lw=1.5),
        )

        # YZ Legend (Bottom)
        prof_lines = [Line2D([0], [0], color=c_dep, lw=1.5)]
        ax3.legend(prof_lines, ["Depth"], fontsize=8, loc="lower right", framealpha=0.8)

        ax3.set_xlim(lim_y)
        ax3.set_ylim(lim_z)
        ax3.set_aspect("equal")
        ax3.set_title("YZ Profile", color=c["text"], fontweight="bold")
        ax3.set_xlabel("Y (µm)")
        ax3.set_ylabel("Z (µm)")
        ax3.tick_params(colors=c["muted"])
        ax3.grid(True, alpha=0.2, color=c["grid"])

        # XZ cross-section
        ax4 = self.fig.add_subplot(2, 2, 4)
        ax4.set_facecolor(c["axes_bg"])
        ax4.plot(X, Z, color="black", alpha=0.05)
        x_b, z_b4 = X[-1, :], Z[-1, :]
        x_c = np.append(x_b, x_b[0])
        z_c4 = np.append(z_b4, z_b4[0])
        ax4.fill(x_c, z_c4, color=c["accent"], alpha=0.15)
        ax4.plot(x_c, z_c4, color=c["accent"], lw=2)
        ax4.axhline(0, color=c["grid"], ls="--", lw=1, alpha=0.5)

        # Depth indicator in XZ (Left side)
        ax4.axhline(-depth, color=c_dep, ls=":", lw=1.5, alpha=0.6)
        x_pos_arrow = X.min() + (X.max() - X.min()) * 0.02
        ax4.annotate(
            "",
            xy=(x_pos_arrow, -depth),
            xytext=(x_pos_arrow, 0),
            arrowprops=dict(arrowstyle="<->", color=c_dep, lw=1.5),
        )

        # XZ Legend (Bottom)
        ax4.legend(prof_lines, ["Depth"], fontsize=8, loc="lower right", framealpha=0.8)

        ax4.set_xlim(lim_x)
        ax4.set_ylim(lim_z)
        ax4.set_aspect("equal")
        ax4.set_title("XZ Profile", color=c["text"], fontweight="bold")
        ax4.set_xlabel("X (µm)")
        ax4.set_ylabel("Z (µm)")
        ax4.tick_params(colors=c["muted"])
        ax4.grid(True, alpha=0.2, color=c["grid"])
        self.fig.tight_layout(pad=2.0)
        self.canvas.draw()

    def _export(self):
        if not self.result:
            return
        c = self._colors()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PNG", "", "PNG (*.png);;All Files (*)"
        )
        if path:
            try:
                self.fig.savefig(path, dpi=600, bbox_inches="tight", facecolor=c["bg"])
                QMessageBox.information(self, "Saved", f"Saved to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
