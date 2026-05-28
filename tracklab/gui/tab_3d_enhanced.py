"""
tab_3d_enhanced.py — Mode 5: 3D Enhanced Visualization
========================================================
Enhanced track rendering with mesh subdivision, AO, OBJ/STL/Blender export.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QMessageBox, QFileDialog,
)
from PyQt6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import cm
import numpy as np
import os

from .workers import TrackWorker
from .styles import get_plot_colors


def _plot_4panel(fig, ion, energy, angle, X, Y, Z, B, colors=None):
    """Shared 4-panel plotting helper."""
    if colors is None:
        colors = get_plot_colors('dark')
    c = colors
    fig.clear()
    fig.patch.set_facecolor(c['bg'])
    pad   = (X.max() - X.min()) * 0.2
    lim_x = (X.min() - pad, X.max() + pad)
    lim_y = (Y.min() - pad, Y.max() + pad)
    lim_z = (Z.min() * 1.1, 0)

    ax1 = fig.add_subplot(2, 2, 1, projection='3d')
    xx, yy = np.meshgrid(np.linspace(*lim_x, 2), np.linspace(*lim_y, 2))
    ax1.plot_surface(xx, yy, np.zeros_like(xx), color='blue', alpha=0.08)
    if B is not None:
        ax1.plot_surface(X, Y, Z, facecolors=cm.gray(B),
                         linewidth=0, antialiased=False, shade=False)
    ax1.set_xlim(lim_x); ax1.set_ylim(lim_y); ax1.set_zlim(lim_z)
    ax1.set_title(f"3D: {ion} {energy:.2f} MeV, {angle:.1f}°",
                  fontweight='bold', color=c['text'])
    ax1.set_xlabel("X (µm)"); ax1.set_ylabel("Y (µm)"); ax1.set_zlabel("Z (µm)")
    ax1.view_init(elev=20, azim=-55)

    ax2 = fig.add_subplot(2, 2, 2)
    ax2.set_facecolor('#DCDCDC')
    if B is not None:
        ax2.pcolormesh(X, Y, B, cmap='gray', shading='flat',
                       vmin=0, vmax=1, rasterized=True)
    ax2.plot(X[0, :], Y[0, :], 'r-', lw=1.5, label='Opening')
    ax2.set_xlim(lim_x); ax2.set_ylim(lim_y); ax2.set_aspect('equal')
    ax2.set_title("XY Microscope View", fontweight='bold', color=c['text'])
    ax2.set_xlabel("X (µm)"); ax2.set_ylabel("Y (µm)")
    ax2.legend(fontsize=8, loc='upper right')

    for ax, coord, lim, xlbl in [
        (fig.add_subplot(2, 2, 3), (Y, Z), (lim_y, lim_z),
         ("Y (µm)", "Z (µm)", "YZ Profile")),
        (fig.add_subplot(2, 2, 4), (X, Z), (lim_x, lim_z),
         ("X (µm)", "Z (µm)", "XZ Profile")),
    ]:
        c1, c2 = coord
        lim1, lim2 = lim
        xlabel, ylabel, title = xlbl
        ax.set_facecolor(c['axes_bg'])
        ax.plot(c1, c2, color='black', alpha=0.05)
        b_row = c1[-1, :]; b_z = c2[-1, :]
        bc = np.append(b_row, b_row[0]); bz = np.append(b_z, b_z[0])
        ax.fill(bc, bz, color=c['accent'], alpha=0.15)
        ax.plot(bc, bz, c['accent'], lw=2)
        ax.axhline(0, color=c['grid'], ls='--', lw=1, alpha=0.5)
        ax.set_xlim(lim1); ax.set_ylim(lim2); ax.set_aspect('equal')
        ax.set_title(title, fontweight='bold', color=c['text'])
        ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
        ax.tick_params(colors=c['muted'])
        ax.grid(True, alpha=0.2, color=c['grid'])

    fig.tight_layout()


class Enhanced3DTab(QWidget):
    """Mode 5: 3D Enhanced Visualization with export."""

    def __init__(self, param_panel):
        super().__init__()
        self.param_panel = param_panel
        self.result = None
        self.worker = None
        self._init_ui()
        self.param_panel.theme_changed.connect(self._on_theme_changed)

    def _colors(self):
        return get_plot_colors(self.param_panel.theme)

    def _on_theme_changed(self, theme):
        c = self._colors()
        self.fig.patch.set_facecolor(c['bg'])
        self.canvas.draw()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QLabel("Mode 5 — 3D Enhanced Visualization")
        f = QFont(); f.setBold(True); f.setPointSize(12)
        header.setFont(f)
        header.setStyleSheet("color: #89b4fa;")
        layout.addWidget(header)

        # Options
        opts_row = QHBoxLayout()
        self.subdiv_check  = QCheckBox("Mesh subdivision")
        self.subdiv_check.setChecked(True)
        self.ao_check      = QCheckBox("Ambient occlusion")
        self.ao_check.setChecked(True)
        self.export_check  = QCheckBox("Export OBJ/STL")
        self.blender_check = QCheckBox("Blender script")
        for w in (self.subdiv_check, self.ao_check,
                  self.export_check, self.blender_check):
            opts_row.addWidget(w)
        opts_row.addStretch()
        layout.addLayout(opts_row)

        # Buttons
        btn_row = QHBoxLayout()
        self.render_btn = QPushButton("Render Track")
        self.render_btn.setProperty("type", "primary")
        self.render_btn.clicked.connect(self._render)
        btn_row.addWidget(self.render_btn)

        self.png_btn = QPushButton("Export PNG")
        self.png_btn.setEnabled(False)
        self.png_btn.clicked.connect(self._export_png)
        btn_row.addWidget(self.png_btn)

        self.status = QLabel("Ready")
        self.status.setStyleSheet("color: #a6adc8; font-size: 10px;")
        btn_row.addWidget(self.status)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Canvas
        c = self._colors()
        self.fig = Figure(figsize=(12, 9), dpi=100)
        self.fig.patch.set_facecolor(c['bg'])
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas, 1)

    def _render(self):
        self.render_btn.setEnabled(False)
        self.status.setText("Computing…")

        params = self.param_panel.get_params()
        self.worker = TrackWorker(params)
        self.worker.result_ready.connect(self._on_result)
        self.worker.error.connect(self._on_error)
        self.worker.status_update.connect(self.status.setText)
        self.worker.start()

    def _on_result(self, res):
        self.render_btn.setEnabled(True)
        if res.get('indicator', -1) != 1:
            self.status.setText(f"❌ {res.get('status')}")
            return

        self.result = res
        X, Y, Z, B = res['X_surf'], res['Y_surf'], res['Z_surf'], res['B_faces']

        if self.subdiv_check.isChecked() or self.ao_check.isChecked():
            X, Y, Z, B = self._advanced(X, Y, Z, B)

        _plot_4panel(self.fig, self.param_panel.ion,
                     self.param_panel.energy, self.param_panel.angle,
                     X, Y, Z, B, colors=self._colors())
        self.canvas.draw()
        self.png_btn.setEnabled(True)

        if self.export_check.isChecked() or self.blender_check.isChecked():
            self._export_3d(X, Y, Z, B)

        self.status.setText("✅ Rendered")

    def _on_error(self, msg):
        self.render_btn.setEnabled(True)
        self.status.setText(f"❌ {msg}")

    def _advanced(self, X, Y, Z, B):
        try:
            from tracklab.mode4_enhanced import (
                subdivide_mesh, calculate_ambient_occlusion)
            from tracklab.track_optics_p_optimized import (
                track_optics_p_optimized)
            from tracklab.config import CONDENSER_NA, N_CONE_RAYS

            if self.subdiv_check.isChecked():
                X, Y, Z = subdivide_mesh(X, Y, Z, subdivisions=1)
                bp, ts, ps, _v, _n, brt = track_optics_p_optimized(
                    X, Y, Z, condenser_na=CONDENSER_NA,
                    n_cone_rays=N_CONE_RAYS)
                Nr, Nc = X.shape
                Nq = (Nr - 1) * (Nc - 1)
                nv = len(brt)
                bq = (0.5 * (brt[:Nq] + brt[Nq:2*Nq]) if nv >= 2 * Nq
                      else (brt[:Nq] if nv >= Nq else np.zeros(Nq)))
                B = bq.reshape(Nr - 1, Nc - 1)

            if self.ao_check.isChecked() and B is not None:
                ao = calculate_ambient_occlusion(X, Y, Z, radius=2.0)
                ao_f = (ao[:-1, :-1] + ao[1:, :-1] +
                        ao[:-1, 1:] + ao[1:, 1:]) / 4
                B = B * (0.3 + 0.7 * ao_f)
        except Exception as e:
            self.status.setText(f"⚠ Advanced failed: {e}")
        return X, Y, Z, B

    def _export_3d(self, X, Y, Z, B):
        outdir = QFileDialog.getExistingDirectory(
            self, "Select export directory")
        if not outdir:
            return
        try:
            from tracklab.mode4_enhanced import (
                export_to_obj, export_to_stl, create_blender_script)
            e = self.param_panel.energy
            a = self.param_panel.angle
            ion = self.param_panel.ion
            base = os.path.join(outdir,
                f"track_{ion}_{e:.1f}MeV_{a:.0f}deg")
            if self.export_check.isChecked():
                export_to_obj(X, Y, Z, base + ".obj", B)
                export_to_stl(X, Y, Z, base + ".stl")
            if self.blender_check.isChecked():
                obj_path = base + ".obj"
                if not os.path.exists(obj_path):
                    export_to_obj(X, Y, Z, obj_path, B)
                create_blender_script(obj_path, outdir)
            QMessageBox.information(self, "Export Complete",
                                    f"Files saved to:\n{outdir}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _export_png(self):
        if not self.result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PNG", "", "PNG (*.png);;All Files (*)")
        if path:
            try:
                c = self._colors()
                self.fig.savefig(path, dpi=150, bbox_inches='tight',
                                facecolor=c['bg'])
                QMessageBox.information(self, "Saved", path)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
