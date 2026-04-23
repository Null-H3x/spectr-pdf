"""
Spectr PDF — Windows Desktop Application
Entry point. Run directly or via PyInstaller .exe.

Usage:
    python main.py [file.pdf]
    Spectr-PDF.exe [file.pdf]
"""

import sys
import os
import multiprocessing

# ── Required for PyInstaller on Windows ───────────────────────────────────────
multiprocessing.freeze_support()

# ── Path setup (PyInstaller bundle) ──────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure all app subpackages are importable
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ── Qt application ────────────────────────────────────────────────────────────
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore    import Qt
from PyQt6.QtGui     import QIcon

import theme
from window import MainWindow


def main():
    # High-DPI support — guarded for PyQt6 version differences
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except AttributeError:
        pass  # Not available in all PyQt6 builds

    app = QApplication(sys.argv)
    app.setApplicationName("Spectr PDF")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Null-H3x")
    app.setOrganizationDomain("bartunek.tech")

    # Apply SPECTR dark theme
    theme.apply(app)

    # Set window icon (if available)
    icon_path = os.path.join(BASE_DIR, "assets", "spectr_pdf.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Launch main window
    window = MainWindow()
    window.setAcceptDrops(True)
    window.show()

    # Open file passed as command-line argument
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isfile(path) and path.lower().endswith(".pdf"):
            window.open_file(path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
