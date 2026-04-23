@echo off
:: ============================================================
::  Spectr PDF — Windows Desktop Build Script
::  Self-contained: everything needed is in THIS folder.
::  Run from anywhere — script resolves its own location.
:: ============================================================
title Spectr PDF — Build
color 0B
setlocal EnableDelayedExpansion

:: Resolve the directory this .bat lives in (works from any CWD)
set "SCRIPT_DIR=%~dp0"
:: Remove trailing backslash
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo.
echo  ================================================================
echo   Spectr PDF  ^|  Windows Desktop Build
echo   Script dir : %SCRIPT_DIR%
echo  ================================================================
echo.

:: ── Verify we're in the right place ──────────────────────────────────────────
if not exist "%SCRIPT_DIR%\main.py" (
    echo  [ERROR] main.py not found in:
    echo          %SCRIPT_DIR%
    echo.
    echo  Make sure all files from the spectr-pdf-desktop output are in
    echo  the same folder as this build_windows.bat.
    pause & exit /b 1
)

if not exist "%SCRIPT_DIR%\icon_gen.py" (
    echo  [ERROR] icon_gen.py not found in:
    echo          %SCRIPT_DIR%
    echo.
    echo  Download icon_gen.py from the spectr-pdf-desktop output and
    echo  place it in the same folder as build_windows.bat.
    pause & exit /b 1
)

:: ── Change to script directory so relative paths work ────────────────────────
cd /d "%SCRIPT_DIR%"
echo  Working directory: %CD%
echo.

:: ── Python ───────────────────────────────────────────────────────────────────
echo  Checking Python...
python --version
if errorlevel 1 (
    echo  [ERROR] Python not found on PATH.
    echo          Install from https://python.org and check "Add to PATH".
    pause & exit /b 1
)
echo.


:: ── Python version check ──────────────────────────────────────────────────────
echo  Checking Python version compatibility...
for /f "tokens=2 delims=." %%M in ('python -c "import sys; print(sys.version)"') do set PYMINOR=%%M
for /f "tokens=1 delims=." %%M in ('python -c "import sys; print(sys.version_info.major)"') do set PYMAJOR=%%M
for /f "tokens=2 delims=." %%M in ('python -c "import sys; print(sys.version_info.minor)"') do set PYMINOR=%%M

if %PYMAJOR% EQU 3 if %PYMINOR% GEQ 14 (
    echo.
    echo  [WARN] Python 3.14 detected. PyInstaller 6.x may not fully support it.
    echo         If the build fails, install Python 3.12 from python.org and retry.
    echo         Python 3.12 is the recommended build target.
    echo.
)
if %PYMAJOR% EQU 3 if %PYMINOR% LSS 10 (
    echo  [ERROR] Python 3.10 or higher is required.
    pause ^& exit /b 1
)
echo  Version check OK.
echo.

:: ── Step 1 — Packages ────────────────────────────────────────────────────────
echo  [1/5] Installing Python packages...
echo         Installs one at a time so you can see progress.
echo         Large packages (PyQt6, OpenCV) may take 1-3 min each.
echo.

set "PIP=python -m pip install --upgrade --no-cache-dir"

echo  --- PyQt6 (GUI, ~120 MB) ---
%PIP% PyQt6
if errorlevel 1 ( echo  [FAIL] PyQt6 & pause & exit /b 1 )

echo  --- PyMuPDF ---
%PIP% pymupdf
if errorlevel 1 ( echo  [FAIL] pymupdf & pause & exit /b 1 )

echo  --- pikepdf ---
%PIP% pikepdf
if errorlevel 1 ( echo  [FAIL] pikepdf & pause & exit /b 1 )

echo  --- Pillow ---
%PIP% pillow
if errorlevel 1 ( echo  [FAIL] pillow & pause & exit /b 1 )

echo  --- opencv-python-headless (~35 MB) ---
%PIP% opencv-python-headless
if errorlevel 1 ( echo  [FAIL] opencv-python-headless & pause & exit /b 1 )

echo  --- pyhanko ---
%PIP% pyhanko
if errorlevel 1 ( echo  [FAIL] pyhanko & pause & exit /b 1 )

echo  --- cryptography ---
%PIP% cryptography
if errorlevel 1 ( echo  [FAIL] cryptography & pause & exit /b 1 )

echo  --- PyKCS11 (CAC / smart card — optional) ---
%PIP% PyKCS11
if errorlevel 1 (
    echo  [WARN] PyKCS11 failed — CAC signing will be unavailable.
    echo         To fix later: install C++ Build Tools from
    echo         https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo         then re-run this script.
    echo         Continuing without CAC support...
    echo.
)

echo  --- pytesseract ---
%PIP% pytesseract
if errorlevel 1 ( echo  [FAIL] pytesseract & pause & exit /b 1 )

echo  --- python-docx ---
%PIP% python-docx
if errorlevel 1 ( echo  [FAIL] python-docx & pause & exit /b 1 )

echo  --- xsdata + aiohttp (pyhanko optional - silences build warnings) ---
%PIP% xsdata aiohttp
if errorlevel 1 (
    echo  [WARN] xsdata/aiohttp optional install failed - build will still work
)

echo  --- PyInstaller ---
%PIP% pyinstaller
if errorlevel 1 ( echo  [FAIL] pyinstaller & pause & exit /b 1 )

echo.
echo  [1/5] Packages OK.
echo.

:: ── Step 2 — Assets ──────────────────────────────────────────────────────────
echo  [2/5] Generating icons and graphics...
echo         Writing to: %SCRIPT_DIR%\assets\

python "%SCRIPT_DIR%\icon_gen.py"
if errorlevel 1 (
    echo  [ERROR] icon_gen.py failed.
    pause & exit /b 1
)

if not exist "%SCRIPT_DIR%\assets\spectr_pdf.ico" (
    echo  [ERROR] icon_gen.py ran but assets\spectr_pdf.ico was not created.
    echo          Check the output above for errors.
    pause & exit /b 1
)
echo  [2/5] Assets OK.
echo.

:: ── Step 3 — Clean ───────────────────────────────────────────────────────────
echo  [3/5] Cleaning previous build...
if exist "%SCRIPT_DIR%\build\"           ( rmdir /s /q "%SCRIPT_DIR%\build"           && echo         Cleared build\ )
if exist "%SCRIPT_DIR%\dist\Spectr-PDF\" ( rmdir /s /q "%SCRIPT_DIR%\dist\Spectr-PDF" && echo         Cleared dist\Spectr-PDF\ )
echo  [3/5] Clean OK.
echo.

:: ── Step 4 — PyInstaller ─────────────────────────────────────────────────────
echo  [4/5] Running PyInstaller...
echo         Bundling everything into a single folder.
echo         First build: 10-20 min.  Progress streams live below.
echo.

python -m PyInstaller "%SCRIPT_DIR%\spectr_pdf_desktop.spec" --clean --noconfirm
if errorlevel 1 (
    echo.
    echo  [ERROR] PyInstaller failed. Common causes:
    echo    "Permission denied"   — close File Explorer windows showing dist\
    echo    "ModuleNotFoundError" — a package above wasn't installed
    echo    "UPX not found"       — safe to ignore, UPX is optional
    pause & exit /b 1
)

if not exist "%SCRIPT_DIR%\dist\Spectr-PDF\Spectr-PDF.exe" (
    echo  [ERROR] Build finished but Spectr-PDF.exe is missing.
    echo          Check: %SCRIPT_DIR%\dist\Spectr-PDF\
    pause & exit /b 1
)

for %%F in ("%SCRIPT_DIR%\dist\Spectr-PDF\Spectr-PDF.exe") do set SZ=%%~zF
set /a MB=%SZ% / 1048576
echo.
echo  [4/5] PyInstaller OK — Spectr-PDF.exe  (~%MB% MB)
echo.

:: ── Step 5 — Inno Setup installer ────────────────────────────────────────────
echo  [5/5] Building installer (C:\Program Files target)...

set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if not defined ISCC (
    echo         Inno Setup 6 not found — skipping installer.
    echo         The portable app in dist\Spectr-PDF\ works without it.
    echo         Get Inno Setup: https://jrsoftware.org/isinfo.php
    goto :summary
)

:: Look for the .iss file — check windows_app\ first, then parent backend\
set "ISS_FILE="
if exist "%SCRIPT_DIR%\SpectrPDF_Installer.iss"           set "ISS_FILE=%SCRIPT_DIR%\SpectrPDF_Installer.iss"
if exist "%SCRIPT_DIR%\..\backend\SpectrPDF_Installer.iss" set "ISS_FILE=%SCRIPT_DIR%\..\backend\SpectrPDF_Installer.iss"

if not defined ISS_FILE (
    echo         SpectrPDF_Installer.iss not found — skipping installer.
    goto :summary
)

if not exist "%SCRIPT_DIR%\..\installer\" mkdir "%SCRIPT_DIR%\..\installer"

echo         Using: %ISS_FILE%
"%ISCC%" "%ISS_FILE%" "/DDistDir=%SCRIPT_DIR%\dist\Spectr-PDF" "/DOutputDir=%SCRIPT_DIR%\..\installer"
if errorlevel 1 (
    echo  [WARN] Inno Setup failed — portable app is still usable.
    goto :summary
)
echo  [5/5] Installer OK.

:summary
echo.
echo  ================================================================
echo   BUILD COMPLETE
echo.
echo   Portable : %SCRIPT_DIR%\dist\Spectr-PDF\Spectr-PDF.exe
echo   Installer: %SCRIPT_DIR%\..\installer\Spectr-PDF-Setup-1.0.0.exe
echo.
echo   The portable folder runs without installation.
echo   Just double-click Spectr-PDF.exe.
echo  ================================================================
echo.

set /p LAUNCH="Launch Spectr-PDF.exe now? [y/N]: "
if /i "!LAUNCH!"=="y" start "" "%SCRIPT_DIR%\dist\Spectr-PDF\Spectr-PDF.exe"

echo.
pause
