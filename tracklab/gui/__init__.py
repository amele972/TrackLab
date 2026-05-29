"""GUI sub-package for TrackLab v1.0."""


def launch():
    """Launch the TrackLab GUI."""
    import sys

    from PyQt6.QtWidgets import QApplication

    from .main_window import TrackLabMainWindow

    app = QApplication(sys.argv)
    window = TrackLabMainWindow()
    window.show()
    sys.exit(app.exec())
