@echo off
:: ============================================================
::  Spectr PDF — Direct Launcher
::  Double-click this. No building, no compiling, no waiting.
::  On first run: installs dependencies (~2 min).
::  Every run after: opens instantly.
:: ============================================================
title Spectr PDF
setlocal EnableDelayedExpansion

:: Resolve to the folder this .bat lives in
set "DIR=%~dp0"
if "%DIR:~-1%"=="\" set "DIR=%DIR:~0,-1%"
cd /d "%DIR%"

:: ── Python check ─────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Python not found.
    echo  Install from https://python.org — check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

:: ── Check if deps are already installed (fast path) ─────────────────────────
python -c "import PyQt6, pymupdf, pikepdf" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  First run: installing dependencies...
    echo  This takes about 2 minutes and only happens once.
    echo.
    python -m pip install --upgrade --no-cache-dir ^
        PyQt6 pymupdf pikepdf pillow ^
        opencv-python-headless pyhanko cryptography ^
        pytesseract python-docx xsdata aiohttp PyKCS11
    if errorlevel 1 (
        echo.
        echo  [WARN] Some packages failed. The app may still work.
        echo         PyKCS11 requires C++ Build Tools for CAC signing.
        echo.
    )
    echo.
    echo  Done. Launching Spectr PDF...
    echo.
)

:: ── Launch ────────────────────────────────────────────────────────────────────
:: pythonw.exe runs without a console window (like a native GUI app)
where pythonw >nul 2>&1
if not errorlevel 1 (
    start "" pythonw "%DIR%\main.py"
) else (
    :: Fall back to python if pythonw isn't available
    start "" python "%DIR%\main.py"
)
