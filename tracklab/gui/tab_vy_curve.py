"""
tab_vy_curve.py — Mode 1: V(y) Curve Explorer
================================================
Plot the etch-rate ratio V(y) for any ion, with experimental data overlay.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QFrame, QMessageBox,
)
from PyQt6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from .styles import get_plot_colors

ALPHA_MODEL_NAMES = [
    "Durrani & Bull (1987)",
    "Brun et al. (1999)",
    "Yu et al. (2005)",
    "Al-Jubbori (2020)",
    "Hermsdorf (2009)",
    "Green et al. (1982)",
    "Yu et al. (2005a,b)"
]


class VyCurveTab(QWidget):
    """Mode 1: V(y) Curve Explorer."""

    def __init__(self, param_panel):
        super().__init__()
        self.param_panel = param_panel
        self._init_ui()
        self.param_panel.theme_changed.connect(self._on_theme_changed)

    def _colors(self):
        return get_plot_colors(self.param_panel.theme)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QLabel("Mode 1 — V(y) Etch-Rate Curve")
        f = QFont(); f.setBold(True); f.setPointSize(12)
        header.setFont(f)
        header.setStyleSheet("color: #89b4fa;")
        layout.addWidget(header)

        desc = QLabel(
            "Plot the dimensionless etch-rate ratio V(y) = VT(y)/VB as a function "
            "of residual range y. For protons the Nikezic analytical model is used; "
            "for other ions the Broken Power Law (BPL) fitted to experimental data.")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 11px; margin-bottom: 8px;")
        layout.addWidget(desc)

        # Controls
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("y max (µm):"))
        self.ymax_spin = QDoubleSpinBox()
        self.ymax_spin.setValue(50.0)
        self.ymax_spin.setRange(1, 10000)
        ctrl.addWidget(self.ymax_spin)

        ctrl.addWidget(QLabel("Points:"))
        self.npts_spin = QDoubleSpinBox()
        self.npts_spin.setValue(500)
        self.npts_spin.setRange(50, 5000)
        self.npts_spin.setDecimals(0)
        ctrl.addWidget(self.npts_spin)

        plot_btn = QPushButton("Plot V(y)")
        plot_btn.setProperty("type", "primary")
        plot_btn.clicked.connect(self._plot)
        ctrl.addWidget(plot_btn)

        compare_btn = QPushButton("Compare All Ions")
        compare_btn.clicked.connect(self._plot_all)
        ctrl.addWidget(compare_btn)

        ctrl.addStretch()
        layout.addLayout(ctrl)

        # Plot canvas
        c = self._colors()
        self.fig = Figure(figsize=(10, 6), dpi=100)
        self.fig.patch.set_facecolor(c['bg'])
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas, 1)

        # Info label
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("font-size: 10px;")
        layout.addWidget(self.info_label)

    def _on_theme_changed(self, theme):
        c = self._colors()
        self.fig.patch.set_facecolor(c['bg'])
        for ax in self.fig.axes:
            ax.set_facecolor(c['axes_bg'])
            ax.tick_params(colors=c['muted'])
            ax.xaxis.label.set_color(c['text'])
            ax.yaxis.label.set_color(c['text'])
            ax.title.set_color(c['text'])
            for spine in ax.spines.values():
                spine.set_color(c['border'])
        self.canvas.draw()

    def _style_ax(self, ax):
        c = self._colors()
        ax.set_facecolor(c['axes_bg'])
        ax.tick_params(colors=c['muted'])
        for spine in ax.spines.values():
            spine.set_color(c['border'])

    def _plot(self):
        """Plot V(y) for the currently selected ion."""
        try:
            from tracklab.vt_multiion import get_model
            from tracklab.vt_utils import vt_function

            c = self._colors()
            ion = self.param_panel.ion
            energy = self.param_panel.energy
            vb = self.param_panel.vb
            ymax = self.ymax_spin.value()
            npts = int(self.npts_spin.value())

            model = get_model()
            y = np.linspace(0.01, ymax, npts)

            self.fig.clear()
            self.fig.patch.set_facecolor(c['bg'])
            ax = self.fig.add_subplot(111)
            self._style_ax(ax)

            if ion == 'protons':
                v = vt_function(y)
                ax.plot(y, v, '-', color=c['accent'], lw=2.5,
                        label=f'Protons (Analytical)')
                ax.set_title("Model: Hermsdorf / Nikezic (Analytical)", 
                             color=c['muted'], fontsize=10)
            elif ion == 'alpha':
                v = model.V(y, ion=ion, energy=energy, vb=vb)
                ax.plot(y, v, '-', color=c['accent5'], lw=2.5,
                        label=f'Alpha (Analytical)')
                
                from tracklab.config import ALPHA_VT_MODEL
                m_name = ALPHA_MODEL_NAMES[ALPHA_VT_MODEL-1] if 1 <= ALPHA_VT_MODEL <= 7 else "Custom"
                ax.set_title(f"Model: {m_name} (Analytical)", 
                             color=c['muted'], fontsize=10)
            else:
                v = model.V(y, ion=ion, energy=energy, vb=vb)
                ax.plot(y, v, '-', color=c['accent2'], lw=2.5,
                        label=f'{ion} @ {energy:.1f} MeV (BPL)')

                params = model.get_parameters(ion, energy)
                ax.set_title(
                    f"BPL: A={params['A']:.3f}, y₀={params['y0']:.3f}, "
                    f"α={params['alpha']:.3f}, β={params['beta']:.3f}",
                    color=c['muted'], fontsize=10)

            ax.axhline(1.0, color=c['grid'], ls='--', lw=1, alpha=0.7,
                       label='V = 1 (bulk)')
            ax.set_xlabel('Residual range y (µm)', color=c['text'], fontsize=11)
            ax.set_ylabel('V(y) = VT(y) / VB', color=c['text'], fontsize=11)
            ax.set_title(f'V(y) for {ion}', color=c['text'], fontsize=13,
                         fontweight='bold')
            ax.legend(facecolor=c['legend_bg'], edgecolor=c['legend_edge'],
                      labelcolor=c['text'])
            ax.grid(True, alpha=0.2, color=c['grid'])

            self.fig.tight_layout()
            self.canvas.draw()

            vmax = float(np.max(v))
            y_peak = float(y[np.argmax(v)])
            self.info_label.setText(
                f"V_max = {vmax:.4f} at y = {y_peak:.2f} µm  |  "
                f"VB = {vb:.2f} µm/h")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _plot_all(self):
        """Plot V(y) for all ions on the same axes."""
        try:
            from tracklab.vt_multiion import get_model
            from tracklab.vt_utils import vt_function

            c = self._colors()
            model = get_model()
            ymax = self.ymax_spin.value()
            y = np.linspace(0.01, ymax, int(self.npts_spin.value()))

            self.fig.clear()
            self.fig.patch.set_facecolor(c['bg'])
            ax = self.fig.add_subplot(111)
            self._style_ax(ax)

            colors = {
                'protons': c['accent'],
                'Li': c['accent3'],
                'C': c['accent2'],
                'O': c['accent4'],
                'alpha': c['accent5'],
            }
            test_energies = {
                'protons': 1.0, 'Li': 6.75, 'C': 14.8,
                'O': 22.0, 'alpha': 5.0,
            }

            for ion, color in colors.items():
                energy = test_energies.get(ion, 1.0)
                if ion == 'protons':
                    v = vt_function(y)
                    label = 'Protons'
                else:
                    v = model.V(y, ion=ion, energy=energy, vb=1.73)
                    label = f'{ion} @ {energy} MeV'
                ax.plot(y, v, '-', color=color, lw=2, label=label)

            ax.axhline(1.0, color=c['grid'], ls='--', lw=1, alpha=0.7)
            ax.set_xlabel('Residual range y (µm)', color=c['text'], fontsize=11)
            ax.set_ylabel('V(y)', color=c['text'], fontsize=11)
            ax.set_title('V(y) Comparison — All Ions', color=c['text'],
                         fontsize=13, fontweight='bold')
            ax.legend(facecolor=c['legend_bg'], edgecolor=c['legend_edge'],
                      labelcolor=c['text'])
            ax.grid(True, alpha=0.2, color=c['grid'])

            self.fig.tight_layout()
            self.canvas.draw()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
