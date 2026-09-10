#!/usr/bin/env python3
"""
run_gui.py — TrackLab v1.0 GUI Launcher
=============================================
Usage:
    python run_gui.py
"""

import os
import sys

# Ensure the package root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tracklab.gui import launch

if __name__ == "__main__":
    launch()
