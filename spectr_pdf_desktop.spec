# -*- mode: python ; coding: utf-8 -*-
#
# Spectr PDF — Windows Desktop App PyInstaller Spec
# Single standalone .exe — no server, no browser, no localhost.
#
# Usage (from windows_app\ directory):
#   pyinstaller spectr_pdf_desktop.spec --clean --noconfirm
#
# Output: dist\Spectr-PDF\Spectr-PDF.exe

import sys
import os
from PyInstaller.utils.hooks import collect_all

# ── CRITICAL: resolve app directory at spec-process time ─────────────────────
# SPEC is a PyInstaller built-in that holds the absolute path to this .spec
# file. We use it to find the app root so that engine/, viewer/, panels/ etc
# are discoverable during import analysis regardless of CWD.
APP_DIR = os.path.dirname(os.path.abspath(SPEC))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# ── Safe collect wrapper ───────────────────────────────────────────────────────
def safe_collect(name):
    """collect_all with fallback so missing optional packages don't abort build."""
    try:
        return collect_all(name)
    except Exception as e:
        print(f"  [WARN] collect_all({name!r}) skipped: {e}")
        return [], [], []

# ── Collect third-party packages ─────────────────────────────────────────────
pyqt6_d,     pyqt6_b,     pyqt6_h     = safe_collect("PyQt6")
pymupdf_d,   pymupdf_b,   pymupdf_h   = safe_collect("pymupdf")
pikepdf_d,   pikepdf_b,   pikepdf_h   = safe_collect("pikepdf")
pillow_d,    pillow_b,    pillow_h    = safe_collect("PIL")
pyhanko_d,   pyhanko_b,   pyhanko_h   = safe_collect("pyhanko")
certval_d,   certval_b,   certval_h   = safe_collect("pyhanko_certvalidator")
cv2_d,       cv2_b,       cv2_h       = safe_collect("cv2")
crypto_d,    crypto_b,    crypto_h    = safe_collect("cryptography")
docx_d,      docx_b,      docx_h      = safe_collect("docx")
tess_d,      tess_b,      tess_h      = safe_collect("pytesseract")
pykcs_d,     pykcs_b,     pykcs_h     = safe_collect("PyKCS11")
xsdata_d,    xsdata_b,    xsdata_h    = safe_collect("xsdata")
aiohttp_d,   aiohttp_b,   aiohttp_h   = safe_collect("aiohttp")

# ── App assets — only non-Python files go here ───────────────────────────────
# .py source files are bundled automatically via import analysis.
# Only icons and bitmaps belong in datas.
app_datas = []
for asset in ["spectr_pdf.png", "spectr_pdf.ico",
              "installer_sidebar.bmp", "installer_header.bmp"]:
    src = os.path.join(APP_DIR, "assets", asset)
    if os.path.exists(src):
        app_datas.append((src, "assets"))

all_datas = (
    app_datas + pyqt6_d + pymupdf_d + pikepdf_d + pillow_d
    + pyhanko_d + certval_d + cv2_d + crypto_d + docx_d + tess_d + pykcs_d
    + xsdata_d + aiohttp_d
)

all_binaries = (
    pyqt6_b + pymupdf_b + pikepdf_b + pillow_b
    + pyhanko_b + certval_b + cv2_b + crypto_b + docx_b + tess_b + pykcs_b
    + xsdata_b + aiohttp_b
)

all_hiddenimports = (
    pyqt6_h + pymupdf_h + pikepdf_h + pillow_h
    + pyhanko_h + certval_h + cv2_h + crypto_h + docx_h + tess_h + pykcs_h
    + xsdata_h + aiohttp_h
    + [
        # PyQt6
        "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets",
        "PyQt6.QtPrintSupport", "PyQt6.sip",
        # pyHanko signing chain
        "pyhanko.sign.signers",
        "pyhanko.sign.signers.pdf_signer",
        "pyhanko.sign.fields",
        "pyhanko.sign.validation",
        "pyhanko.pdf_utils.reader",
        "pyhanko.pdf_utils.incremental_writer",
        "pyhanko_certvalidator",
        # cryptography
        "cryptography.x509",
        "cryptography.hazmat.primitives.asymmetric.rsa",
        "cryptography.hazmat.primitives.hashes",
        "cryptography.hazmat.primitives.serialization.pkcs12",
        "cryptography.hazmat.backends",
        # opencv / numpy
        "cv2", "numpy",
        # OCR
        "pytesseract", "PIL.Image",
        # docx
        "docx", "docx.oxml",
        # CAC
        "PyKCS11", "PyKCS11.LowLevel",
        # ── App modules — explicit to guarantee inclusion ─────────────────────
        # PyInstaller must be able to FIND these files on sys.path (APP_DIR).
        # We add APP_DIR to sys.path above so this always works.
        "engine", "engine.pdf_engine", "engine.cac_engine",
        "viewer", "viewer.pdf_viewer", "viewer.thumbnail_panel",
        "panels", "panels.tool_panels", "panels.cac_panel",
        "utils", "utils.range_parser",
        "theme", "window",
        # stdlib
        "difflib", "zipfile", "json", "base64", "io",
        "threading", "multiprocessing", "multiprocessing.freeze_support",
        "pathlib", "shutil", "subprocess", "tempfile", "datetime",
        "asyncio", "ctypes",
    ]
)

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(APP_DIR, "main.py")],    # absolute path to entry point
    # pathex: directories added to sys.path during analysis.
    # APP_DIR is absolute so this works regardless of where pyinstaller
    # is invoked from.
    pathex=[APP_DIR],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    # runtime_hooks: scripts that run BEFORE main.py in the frozen exe.
    # spectr_rthook.py inserts sys._MEIPASS into sys.path so the local
    # packages (engine/, viewer/, panels/, utils/) are always importable.
    runtime_hooks=[os.path.join(APP_DIR, "spectr_rthook.py")],
    excludes=[
        "tkinter", "matplotlib", "scipy", "pandas",
        "IPython", "jupyter", "notebook", "pytest",
        "test", "tests", "unittest", "doctest",
        "fastapi", "uvicorn", "starlette", "pystray",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Spectr-PDF",
    debug=False,
    strip=False,
    upx=True,
    console=False,                                    # GUI app, no console
    icon=os.path.join(APP_DIR, "assets", "spectr_pdf.ico"),
    version=os.path.join(APP_DIR, "version_info.txt"),
    uac_admin=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="Spectr-PDF",
)
