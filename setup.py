"""
TrackLab v1.0 — Unified Multi-Ion Package
"""

from setuptools import setup, find_packages

setup(
    name="track-vision",
    version="1.0.0",
    author="TrackLab Team",
    description="Nuclear track detector analysis for multiple ions in CR-39",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "tracklab": ["data/*.dat", "data/*.xlsx"],
    },
    install_requires=[
        "numpy>=1.22",
        "scipy>=1.9",
        "matplotlib>=3.5",
        "pandas>=1.4",
        "PyQt6>=6.4",
        "openpyxl>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "track-vision=tracklab.main:main",
        ],
        "gui_scripts": [
            "track-vision-gui=tracklab.gui:launch",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering :: Physics",
    ],
)
