@echo off
:: ============================================================
:: Bulk PDF Generator — Windows Build Script
:: ============================================================
:: Prerequisites:
::   - Python 3 installed with all packages from requirements.txt
::   - PyInstaller: pip install pyinstaller
::
:: Usage:
::   Double-click this file, or run it from a terminal.
::   Output: dist\Bulk PDF Generator.exe
:: ============================================================

cd /d "%~dp0"

echo.
echo ============================================================
echo  Bulk PDF Generator - Build Script
echo ============================================================
echo.

:: Find Python — prefer venv if present, fall back to py launcher
if exist "venv\Scripts\python.exe" (
    set PYTHON="%~dp0venv\Scripts\python.exe"
    echo Using virtual environment: .\venv\
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set PYTHON=py -3
        echo Using py launcher
    ) else (
        set PYTHON=python
        echo Using system python
    )
)

:: Install / upgrade PyInstaller
echo [1/3] Installing PyInstaller...
%PYTHON% -m pip install --upgrade pyinstaller --quiet
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install PyInstaller.
    pause
    exit /b 1
)

:: Clean previous build artifacts
echo [2/3] Cleaning previous build...
if exist "build\" rmdir /s /q "build"
if exist "dist\Bulk PDF Generator.exe" del /f /q "dist\Bulk PDF Generator.exe"

:: Run PyInstaller
echo [3/3] Building executable (this takes 1-3 minutes)...
echo.
%PYTHON% -m PyInstaller BulkPDFGenerator.spec --clean
echo.

:: Result
if exist "dist\Bulk PDF Generator.exe" (
    echo ============================================================
    echo  BUILD SUCCESSFUL
    echo  Output: %~dp0dist\Bulk PDF Generator.exe
    echo ============================================================
    echo.
    echo You can now copy "dist\Bulk PDF Generator.exe" to any
    echo Windows machine and run it — no Python install required.
    echo.
    echo NOTE: Windows Defender may flag the exe on first run.
    echo This is a known false positive with PyInstaller executables.
    echo Right-click the file and choose "Run anyway" if prompted.
) else (
    echo ============================================================
    echo  BUILD FAILED
    echo  Check the output above for errors.
    echo ============================================================
)

echo.
pause
