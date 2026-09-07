"""
config_summary.py — TrackLab Startup Configuration Summary
============================================================
Shown at every launch as a read-only reminder of the active physics
settings.  Users can dismiss it permanently with "Don't show again".

Re-open any time via:  Help → Show Configuration Summary
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# ── Persistent flag location ──────────────────────────────────────────────────
_CONFIG_FILE = Path.home() / ".tracklab_config.json"

# ── Jupyter notebook path (relative to package root) ─────────────────────────
_PKG_ROOT = Path(__file__).resolve().parent.parent.parent
_NOTEBOOK = _PKG_ROOT / "TrackLab_User_Guide.ipynb"


def _load_prefs() -> dict:
    """Load user preferences from ~/.tracklab_config.json."""
    try:
        if _CONFIG_FILE.exists():
            return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_prefs(prefs: dict) -> None:
    """Write preferences back to ~/.tracklab_config.json."""
    try:
        _CONFIG_FILE.write_text(
            json.dumps(prefs, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def should_show_summary() -> bool:
    """Return True if the startup summary should be shown."""
    return not _load_prefs().get("skip_summary", False)


def set_skip_summary(skip: bool) -> None:
    """Persist the user's 'don't show again' preference."""
    prefs = _load_prefs()
    prefs["skip_summary"] = skip
    _save_prefs(prefs)


# ── Dialog ────────────────────────────────────────────────────────────────────

class ConfigSummaryDialog(QDialog):
    """
    Read-only startup popup summarising the active TrackLab physics settings.

    Parameters
    ----------
    theme : str
        'dark' or 'light' — controls colours to match the main window.
    parent : QWidget, optional
    """

    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setWindowTitle("TrackLab — Configuration Summary")
        self.setMinimumWidth(580)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self._build_ui()
        self._apply_theme()

    # ── Colour helpers ────────────────────────────────────────────────────────

    @property
    def _is_dark(self) -> bool:
        return self._theme != "light"

    def _c(self, key: str) -> str:
        """Return a theme colour by semantic key."""
        DARK = {
            "bg": "#1e1e2e",
            "card": "#313244",
            "border": "#585b70",
            "text": "#cdd6f4",
            "muted": "#a6adc8",
            "accent": "#89b4fa",
            "accent2": "#fab387",
            "accent5": "#cba6f7",
            "warn_bg": "#2a1f14",
            "warn_border": "#fab387",
            "btn_primary": "#89b4fa",
            "btn_primary_text": "#1e1e2e",
            "btn_secondary": "#45475a",
            "btn_secondary_text": "#cdd6f4",
            "green": "#a6e3a1",
        }
        LIGHT = {
            "bg": "#f8fafc",
            "card": "#ffffff",
            "border": "#e2e8f0",
            "text": "#0f172a",
            "muted": "#475569",
            "accent": "#2563eb",
            "accent2": "#ea580c",
            "accent5": "#9333ea",
            "warn_bg": "#fff7ed",
            "warn_border": "#ea580c",
            "btn_primary": "#2563eb",
            "btn_primary_text": "#ffffff",
            "btn_secondary": "#e2e8f0",
            "btn_secondary_text": "#0f172a",
            "green": "#16a34a",
        }
        palette = DARK if self._is_dark else LIGHT
        return palette.get(key, "#888888")

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        from tracklab.config import (
            ALPHA_MODELS_INFO,
            ALPHA_VT_MODEL,
            PROTON_MODELS_INFO,
            PROTON_VT_MODEL,
            TIME_ETCHING,
            VB_BY_ION,
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(12)

        # ── Header ────────────────────────────────────────────────────────────
        header = QLabel("⚙  Active Configuration Summary")
        hf = QFont()
        hf.setBold(True)
        hf.setPointSize(13)
        header.setFont(hf)
        root.addWidget(header)

        # ── Warning banner ────────────────────────────────────────────────────
        warn = QFrame()
        warn.setProperty("role", "warn")
        wl = QHBoxLayout(warn)
        wl.setContentsMargins(10, 8, 10, 8)
        wl.setSpacing(8)
        wl.addWidget(QLabel("⚠"))
        txt = QLabel(
            "<b>Please confirm your physics settings before running any simulation.</b><br>"
            "To change them, open the <b>Configuration tab (Mode 7)</b> in the main window."
        )
        txt.setWordWrap(True)
        txt.setProperty("role", "warn_text")
        wl.addWidget(txt, 1)
        root.addWidget(warn)

        # ── Scrollable content ─────────────────────────────────────────────
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(8)
        scroll_area.setWidget(content)
        root.addWidget(scroll_area, 1)

        # Helper: section card
        def _card(title: str, rows: list[tuple[str, str, str]]) -> QFrame:
            """Build a card with (label, value, colour) rows."""
            card = QFrame()
            card.setProperty("role", "card")
            cvl = QVBoxLayout(card)
            cvl.setContentsMargins(12, 10, 12, 10)
            cvl.setSpacing(4)

            sec_lbl = QLabel(title)
            sf = QFont()
            sf.setBold(True)
            sf.setPointSize(10)
            sec_lbl.setFont(sf)
            sec_lbl.setProperty("role", "section_title")
            cvl.addWidget(sec_lbl)

            for label, value, colour_key in rows:
                row = QHBoxLayout()
                row.setSpacing(6)
                lbl = QLabel(label)
                lbl.setProperty("role", "row_label")
                val = QLabel(value)
                val.setWordWrap(True)
                val.setProperty("colour_key", colour_key)
                row.addWidget(lbl)
                row.addWidget(val, 1)
                cvl.addLayout(row)

            return card

        # — Proton V(y) model card —
        p_info = PROTON_MODELS_INFO.get(PROTON_VT_MODEL, {})
        p_name = p_info.get("name", "Unknown")
        p_formula = p_info.get("formula", "")
        is_p_default = PROTON_VT_MODEL == 1
        p_tag = "  ★ Recommended default" if is_p_default else ""
        cl.addWidget(_card(
            "Proton  V(y) Model",
            [
                ("Model:", f"Model {PROTON_VT_MODEL} — {p_name}{p_tag}", "accent"),
                ("Formula:", p_formula, "muted"),
            ],
        ))

        # — Alpha V(y) model card —
        a_info = ALPHA_MODELS_INFO.get(ALPHA_VT_MODEL, {})
        a_name = a_info.get("name", "Unknown")
        a_formula = a_info.get("formula", "")
        is_a_default = ALPHA_VT_MODEL == 5
        a_tag = "  ★ Recommended default" if is_a_default else ""
        cl.addWidget(_card(
            "Alpha  V(y) Model",
            [
                ("Model:", f"Model {ALPHA_VT_MODEL} — {a_name}{a_tag}", "accent5"),
                ("Formula:", a_formula, "muted"),
            ],
        ))

        # — Li / C / O —
        cl.addWidget(_card(
            "Heavy Ions  (Li, C, O)",
            [
                (
                    "Method:",
                    "Broken Power Law (BPL) — fitted to experimental data.  No selection needed.",
                    "green",
                ),
            ],
        ))

        # — Etching parameters —
        vb_proton = VB_BY_ION.get("protons", 4.7)
        cl.addWidget(_card(
            "Etching Parameters",
            [
                ("VB (protons):", f"{vb_proton:.3f}  µm/h  (CR-39 standard)", "accent2"),
                ("Etching time:", f"{TIME_ETCHING:.3f}  h", "accent2"),
            ],
        ))

        cl.addStretch()

        # ── Bottom bar ────────────────────────────────────────────────────────
        bottom = QHBoxLayout()
        bottom.setSpacing(10)

        self._skip_cb = QCheckBox("Don't show this again")
        self._skip_cb.setChecked(False)
        bottom.addWidget(self._skip_cb)
        bottom.addStretch()

        # "Getting Started" button — only shown if the notebook exists
        if _NOTEBOOK.exists():
            gs_btn = QPushButton("📓  Getting Started")
            gs_btn.setProperty("role", "secondary")
            gs_btn.setToolTip(f"Open {_NOTEBOOK.name} in Jupyter")
            gs_btn.clicked.connect(self._open_notebook)
            bottom.addWidget(gs_btn)

        launch_btn = QPushButton("✔  Got it, Launch TrackLab!")
        launch_btn.setProperty("role", "primary")
        launch_btn.setDefault(True)
        launch_btn.clicked.connect(self._on_launch)
        bottom.addWidget(launch_btn)

        root.addLayout(bottom)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_launch(self):
        if self._skip_cb.isChecked():
            set_skip_summary(True)
        self.accept()

    def _open_notebook(self):
        """Try to launch the Jupyter notebook in the system browser."""
        try:
            if sys.platform == "win32":
                os.startfile(str(_NOTEBOOK))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(_NOTEBOOK)])
            else:
                subprocess.Popen(["xdg-open", str(_NOTEBOOK)])
        except Exception as exc:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Cannot open notebook",
                f"Could not open the notebook automatically.\n\n"
                f"Path: {_NOTEBOOK}\n\nError: {exc}",
            )

    # ── Theming ───────────────────────────────────────────────────────────────

    def _apply_theme(self):
        c = self._c
        self.setStyleSheet(f"""
            ConfigSummaryDialog {{
                background-color: {c('bg')};
            }}

            /* ── Overall dialog background ── */
            QDialog {{
                background-color: {c('bg')};
            }}

            /* ── Warning banner ── */
            QFrame[role="warn"] {{
                background-color: {c('warn_bg')};
                border: 1px solid {c('warn_border')};
                border-radius: 6px;
            }}
            QLabel[role="warn_text"] {{
                color: {c('text')};
                font-size: 11px;
            }}

            /* ── Info cards ── */
            QFrame[role="card"] {{
                background-color: {c('card')};
                border: 1px solid {c('border')};
                border-radius: 8px;
            }}
            QLabel[role="section_title"] {{
                color: {c('accent')};
                margin-bottom: 4px;
            }}
            QLabel[role="row_label"] {{
                color: {c('muted')};
                font-size: 11px;
                min-width: 90px;
            }}

            /* Generic label colour fallback */
            QLabel {{
                color: {c('text')};
                background: transparent;
            }}

            QCheckBox {{
                color: {c('muted')};
                font-size: 11px;
            }}
            QCheckBox::indicator {{
                border: 1px solid {c('border')};
                border-radius: 3px;
                width: 14px;
                height: 14px;
                background: {c('card')};
            }}
            QCheckBox::indicator:checked {{
                background: {c('accent')};
                border-color: {c('accent')};
            }}

            /* ── Buttons ── */
            QPushButton[role="primary"] {{
                background-color: {c('btn_primary')};
                color: {c('btn_primary_text')};
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton[role="primary"]:hover {{
                opacity: 0.9;
            }}
            QPushButton[role="secondary"] {{
                background-color: {c('btn_secondary')};
                color: {c('btn_secondary_text')};
                border: 1px solid {c('border')};
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 11px;
            }}

            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QWidget {{
                background: transparent;
            }}
            /* keep cards opaque */
            QFrame[role="card"] {{
                background-color: {c('card')};
            }}
            QFrame[role="warn"] {{
                background-color: {c('warn_bg')};
            }}
        """)
