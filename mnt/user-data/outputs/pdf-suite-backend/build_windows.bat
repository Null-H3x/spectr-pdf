@echo off
:: ============================================================
::  Spectr PDF — Backend Build Script  (verbose)
::  Builds the FastAPI backend .exe (Android companion).
::  Run from the backend\ directory.
:: ============================================================
title Spectr PDF Backend — Build
color 0B
setlocal EnableDelayedExpansion

echo.
echo  ================================================================
echo   Spectr PDF  ^|  Backend Build  (Android companion)
echo  ================================================================
echo.

if not exist "main.py" (
    echo  [ERROR] Run this script from the backend\ directory.
    pause & exit /b 1
)

echo  Checking Python...
python --version
if errorlevel 1 (
    echo  [ERROR] Python not found on PATH.
    pause & exit /b 1
)
echo.

:: ── Step 1 — Install packages ────────────────────────────────────────────────
echo  [1/5] Installing Python packages (one at a time)...
echo.

set PIP=python -m pip install --upgrade --no-cache-dir

echo  --- fastapi ---
%PIP% "fastapi>=0.100.0"
if errorlevel 1 ( echo  [FAIL] fastapi & pause & exit /b 1 )

echo  --- uvicorn ---
%PIP% "uvicorn[standard]>=0.23.0"
if errorlevel 1 ( echo  [FAIL] uvicorn & pause & exit /b 1 )

echo  --- python-multipart ---
%PIP% python-multipart
if errorlevel 1 ( echo  [FAIL] python-multipart & pause & exit /b 1 )

echo  --- pydantic ---
%PIP% pydantic
if errorlevel 1 ( echo  [FAIL] pydantic & pause & exit /b 1 )

echo  --- pymupdf ---
%PIP% pymupdf
if errorlevel 1 ( echo  [FAIL] pymupdf & pause & exit /b 1 )

echo  --- pikepdf ---
%PIP% pikepdf
if errorlevel 1 ( echo  [FAIL] pikepdf & pause & exit /b 1 )

echo  --- pillow ---
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

echo  --- pytesseract ---
%PIP% pytesseract
if errorlevel 1 ( echo  [FAIL] pytesseract & pause & exit /b 1 )

echo  --- python-docx ---
%PIP% python-docx
if errorlevel 1 ( echo  [FAIL] python-docx & pause & exit /b 1 )

echo  --- pystray ---
%PIP% pystray
if errorlevel 1 ( echo  [FAIL] pystray & pause & exit /b 1 )

echo  --- PyInstaller ---
%PIP% pyinstaller
if errorlevel 1 ( echo  [FAIL] pyinstaller & pause & exit /b 1 )

echo.
echo  [1/5] All packages installed OK.
echo.

:: ── Step 2 — Assets ──────────────────────────────────────────────────────────
echo  [2/5] Generating icons and installer graphics...
python icon_gen.py
if errorlevel 1 ( echo  [ERROR] icon_gen.py failed. & pause & exit /b 1 )
echo  [2/5] Assets OK.
echo.

:: ── Step 3 — Clean ───────────────────────────────────────────────────────────
echo  [3/5] Cleaning previous build...
if exist build\           rmdir /s /q build
if exist dist\Spectr-PDF\ rmdir /s /q dist\Spectr-PDF
echo  [3/5] Clean OK.
echo.

:: ── Step 4 — PyInstaller ─────────────────────────────────────────────────────
echo  [4/5] Running PyInstaller...
echo         First build: 10-20 min.  Output streams live below.
echo.

python -m PyInstaller spectr_pdf.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo  [ERROR] PyInstaller failed — see output above.
    pause & exit /b 1
)

if not exist "dist\Spectr-PDF\Spectr-PDF.exe" (
    echo  [ERROR] .exe not found after build.
    pause & exit /b 1
)

for %%F in ("dist\Spectr-PDF\Spectr-PDF.exe") do set SZ=%%~zF
set /a MB=%SZ% / 1048576
echo.
echo  [4/5] PyInstaller OK.  (~%MB% MB)
echo.

:: ── Step 5 — Inno Setup ──────────────────────────────────────────────────────
echo  [5/5] Building installer...

set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
    echo         Inno Setup not found — skipping.
    goto :summary
)

if not exist installer\ mkdir installer
"%ISCC%" SpectrPDF_Installer.iss
if errorlevel 1 ( echo  [WARNING] Inno Setup failed. & goto :summary )
echo  [5/5] Installer OK.

:summary
echo.
echo  ================================================================
echo   BUILD COMPLETE
echo   dist\Spectr-PDF\Spectr-PDF.exe
echo   installer\Spectr-PDF-Setup-1.0.0.exe
echo  ================================================================
echo.
pause
