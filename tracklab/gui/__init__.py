"""GUI sub-package for TrackLab v1.0."""


def launch():
    """Launch the TrackLab GUI."""
    import sys

    from PyQt6.QtWidgets import QApplication

    from .config_summary import ConfigSummaryDialog, should_show_summary
    from .main_window import TrackLabMainWindow

    app = QApplication(sys.argv)

    # Show the configuration summary popup unless the user has opted out.
    if should_show_summary():
        dlg = ConfigSummaryDialog(theme="dark")
        result = dlg.exec()
        # If the user closes the dialog via the window 'X', we still continue.
        # (reject == 0 means cancelled — we don't block launch on that.)

    window = TrackLabMainWindow()
    window.show()
    sys.exit(app.exec())
