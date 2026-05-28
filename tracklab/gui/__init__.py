"""GUI sub-package for TrackLab v1.0."""

def launch():
    """Launch the TrackLab GUI."""
    import sys
    from PyQt6.QtWidgets import QApplication
    from .main_window import TrackVisionMainWindow

    app = QApplication(sys.argv)
    window = TrackVisionMainWindow()
    window.show()
    sys.exit(app.exec())
