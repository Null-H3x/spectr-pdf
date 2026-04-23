"""
Spectr PDF — PyInstaller Runtime Hook
Runs before main.py in the frozen executable.
Ensures sys._MEIPASS is on sys.path so engine/, viewer/, panels/, utils/
are all importable as packages.
"""
import sys
import os

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    # sys._MEIPASS is where PyInstaller extracts the bundle.
    # It must be first in sys.path so our local packages shadow
    # anything else with the same name.
    meipass = sys._MEIPASS
    if meipass not in sys.path:
        sys.path.insert(0, meipass)

    # Also add the directory containing the .exe itself (for portable mode
    # where users place extra files next to the executable).
    exe_dir = os.path.dirname(sys.executable)
    if exe_dir and exe_dir not in sys.path:
        sys.path.append(exe_dir)
