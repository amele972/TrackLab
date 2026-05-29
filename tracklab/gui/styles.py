"""
styles.py — TrackLab v1.0 GUI Stylesheet
===============================================
Dark and Light themes for PyQt6.

Usage:
    from .styles import get_stylesheet, THEMES
    app.setStyleSheet(get_stylesheet('dark'))   # or 'light'
"""

THEMES = ["dark", "light"]

# ── Matplotlib plot colors per theme ─────────────────────────────────
PLOT_COLORS = {
    "dark": {
        "bg": "#1e1e2e",
        "axes_bg": "#313244",
        "text": "#cdd6f4",
        "grid": "#585b70",
        "accent": "#89b4fa",
        "accent2": "#f38ba8",
        "accent3": "#a6e3a1",
        "accent4": "#fab387",
        "accent5": "#cba6f7",
        "muted": "#a6adc8",
        "border": "#585b70",
        "legend_bg": "#313244",
        "legend_edge": "#585b70",
    },
    "light": {
        "bg": "#ffffff",
        "axes_bg": "#f8f9fa",
        "text": "#0f172a",  # Darkened from #1e293b
        "grid": "#cbd5e1",
        "accent": "#2563eb",
        "accent2": "#dc2626",
        "accent3": "#16a34a",
        "accent4": "#ea580c",
        "accent5": "#9333ea",
        "muted": "#475569",  # Darkened from #64748b
        "border": "#e2e8f0",
        "legend_bg": "#ffffff",
        "legend_edge": "#e2e8f0",
    },
}


def get_plot_colors(theme="dark"):
    """Return matplotlib color palette for the given theme."""
    return PLOT_COLORS.get(theme, PLOT_COLORS["dark"])


def get_stylesheet(theme="dark"):
    """Return the QSS stylesheet for the given theme name."""
    if theme == "light":
        return STYLESHEET_LIGHT
    return STYLESHEET_DARK


# For backward compatibility
STYLESHEET = None  # set at bottom


# ═══════════════════════════════════════════════════════════════════════
# DARK THEME — Catppuccin Mocha
# ═══════════════════════════════════════════════════════════════════════

STYLESHEET_DARK = """
/* ═══════════════════════════════════════════════════════════════════
   TrackLab v1.0 — DARK THEME
   ═══════════════════════════════════════════════════════════════════ */

QMainWindow {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

/* ── Global defaults ─────────────────────────────────────────────── */
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QLabel {
    color: #cdd6f4;
    background: transparent;
}

/* ── Cards & Panels ──────────────────────────────────────────────── */
QFrame[type="card"] {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 10px;
}

QFrame[type="panel"] {
    background-color: #45475a;
    border: 1px solid #585b70;
    border-radius: 8px;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #585b70;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 500;
    min-height: 28px;
}
QPushButton:hover {
    background-color: #585b70;
    border-color: #89b4fa;
}
QPushButton:pressed {
    background-color: #313244;
}
QPushButton:disabled {
    background-color: #313244;
    color: #6c7086;
    border-color: #45475a;
}

QPushButton[type="primary"] {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    font-weight: 600;
}
QPushButton[type="primary"]:hover {
    background-color: #74c7ec;
}
QPushButton[type="primary"]:pressed {
    background-color: #89dceb;
}
QPushButton[type="primary"]:disabled {
    background-color: #45475a;
    color: #6c7086;
}

/* ── Inputs ──────────────────────────────────────────────────────── */
QDoubleSpinBox, QSpinBox, QLineEdit {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #585b70;
    border-radius: 5px;
    padding: 4px 8px;
    min-height: 24px;
}
QDoubleSpinBox:focus, QSpinBox:focus, QLineEdit:focus {
    border-color: #89b4fa;
}

QComboBox {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #585b70;
    border-radius: 5px;
    padding: 4px 10px;
    min-height: 24px;
}
QComboBox:hover {
    border-color: #89b4fa;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #585b70;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}

/* ── Tab Widget ──────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #45475a;
    border-radius: 8px;
    background-color: #1e1e2e;
    top: -1px;
}

QTabBar::tab {
    background-color: #313244;
    color: #a6adc8;
    border: 1px solid #45475a;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 16px;
    margin-right: 2px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #89b4fa;
    border-color: #89b4fa;
    border-bottom: 2px solid #89b4fa;
}
QTabBar::tab:hover:!selected {
    background-color: #45475a;
    color: #cdd6f4;
}

/* ── Table ───────────────────────────────────────────────────────── */
QTableWidget {
    background-color: #313244;
    alternate-background-color: #45475a;
    color: #cdd6f4;
    gridline-color: #45475a;
    border: 1px solid #45475a;
    border-radius: 6px;
}
QTableWidget::item:selected {
    background-color: #89b4fa;
    color: #1e1e2e;
}
QHeaderView::section {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #585b70;
    padding: 5px;
    font-weight: 600;
}

/* ── Progress Bar ────────────────────────────────────────────────── */
QProgressBar {
    background-color: #45475a;
    border: none;
    border-radius: 5px;
    min-height: 10px;
    max-height: 10px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #89b4fa, stop:1 #74c7ec);
    border-radius: 5px;
}

/* ── Scrollbar ───────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #1e1e2e;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #585b70;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #89b4fa;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── Text Edit ───────────────────────────────────────────────────── */
QTextEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px;
}

/* ── Check Box ───────────────────────────────────────────────────── */
QCheckBox {
    color: #cdd6f4;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #585b70;
    border-radius: 4px;
    background-color: #45475a;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

/* ── Group Box ───────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #89b4fa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #89b4fa;
}

/* ── Splitter ────────────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #45475a;
    width: 3px;
}
QSplitter::handle:hover {
    background-color: #89b4fa;
}

/* ── Status Bar ──────────────────────────────────────────────────── */
QStatusBar {
    background-color: #313244;
    color: #a6adc8;
    border-top: 1px solid #45475a;
}

/* ── Menu Bar ────────────────────────────────────────────────────── */
QMenuBar {
    background-color: #313244;
    color: #cdd6f4;
    border-bottom: 1px solid #45475a;
}
QMenuBar::item:selected {
    background-color: #45475a;
}
QMenu {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
}
QMenu::item:selected {
    background-color: #89b4fa;
    color: #1e1e2e;
}
"""


# ═══════════════════════════════════════════════════════════════════════
# LIGHT THEME — Clean Professional
# ═══════════════════════════════════════════════════════════════════════

STYLESHEET_LIGHT = """
/* ═══════════════════════════════════════════════════════════════════
   TrackLab v1.0 — LIGHT THEME (HIGH CONTRAST)
   ═══════════════════════════════════════════════════════════════════ */

QMainWindow {
    background-color: #f8f9fa;
    color: #0f172a;
}

/* ── Global defaults ─────────────────────────────────────────────── */
QWidget {
    background-color: #f8f9fa;
    color: #0f172a; /* High contrast deep navy */
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QLabel {
    color: #0f172a;
    background: transparent;
}

/* ── Cards & Panels ──────────────────────────────────────────────── */
QFrame[type="card"] {
    background-color: #ffffff;
    border: 1px solid #cbd5e1; /* Darkened border for definition */
    border-radius: 10px;
}

QFrame[type="panel"] {
    background-color: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {
    background-color: #ffffff;
    color: #1e293b; /* Darker text */
    border: 1px solid #94a3b8; /* More visible border */
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 500;
    min-height: 28px;
}
QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #2563eb;
    color: #0f172a;
}

QPushButton[type="primary"] {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    font-weight: 600;
}

/* ── Inputs ──────────────────────────────────────────────────────── */
QDoubleSpinBox, QSpinBox, QLineEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #94a3b8;
    border-radius: 5px;
    padding: 4px 8px;
}

/* ── Tab Widget ──────────────────────────────────────────────────── */
QTabBar::tab {
    background-color: #e2e8f0; /* Darkened inactive tabs */
    color: #475569; /* Darkened from #64748b */
    border: 1px solid #cbd5e1;
    border-bottom: none;
    padding: 8px 16px;
}
QTabBar::tab:selected {
    background-color: #f8f9fa;
    color: #2563eb;
    border-color: #2563eb;
    font-weight: 600;
}

/* ── Table ───────────────────────────────────────────────────────── */
QTableWidget {
    background-color: #ffffff;
    color: #0f172a;
    gridline-color: #cbd5e1;
}
QHeaderView::section {
    background-color: #e2e8f0;
    color: #0f172a;
    font-weight: 700;
}

/* ── Status & Menu ───────────────────────────────────────────────── */
QStatusBar {
    background-color: #ffffff;
    color: #334155; /* Darkened text */
    border-top: 1px solid #cbd5e1;
}

QMenuBar {
    background-color: #ffffff;
    color: #0f172a;
    border-bottom: 1px solid #cbd5e1;
}

QMenu::item {
    color: #1e293b;
}
QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}
"""


# ── Default (backward compat) ───────────────────────────────────────
STYLESHEET = STYLESHEET_LIGHT
