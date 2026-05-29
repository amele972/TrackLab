Getting Started
===============

This guide helps you set up and run **TrackLab** on Windows.

Prerequisites
-------------

TrackLab requires:
* Python 3.9 or higher (Python 3.11 is recommended).
* A standard Windows shell (PowerShell or Command Prompt).

Installation
------------

To install TrackLab and its dependencies:

1. **Clone the repository**
   Open a terminal and clone the package:

   .. code-block:: powershell

      git clone https://github.com/amele972/TrackLab.git
      cd TrackLab

2. **Create a virtual environment**
   Create and activate a virtual environment to isolate dependencies:

   .. code-block:: powershell

      python -m venv .venv
      .venv\Scripts\Activate.ps1

3. **Install the package**
   Install the package in editable development mode with all optional development packages:

   .. code-block:: powershell

      python -m pip install --upgrade pip
      pip install -e ".[dev]"

Running the Applications
------------------------

TrackLab includes both a graphical user interface (GUI) dashboard and a command-line interface (CLI).

Launching the GUI Dashboard
~~~~~~~~~~~~~~~~~~~~~~~~~~~

To start the PyQt6-based dashboard, run the entry point command:

.. code-block:: bash

   tracklab-gui

Alternatively, you can run the GUI launcher script directly:

.. code-block:: bash

   python run_gui.py

Launching the CLI menu
~~~~~~~~~~~~~~~~~~~~~~

To use the text-based interactive menu, run the entry point command:

.. code-block:: bash

   tracklab

Or run the entry script directly:

.. code-block:: bash

   python -m tracklab.main
