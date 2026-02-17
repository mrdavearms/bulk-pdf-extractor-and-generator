@echo off
:: VCAA PDF Generator Launcher for Windows
cd /d "%~dp0"

:: Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo Virtual environment not found in %CD%\venv
    echo Please follow the setup instructions in README.md
    pause
    exit /b
)

:: Run the application
python vcaa_pdf_generator_v2.py

:: Keep window open if there's an error
if %ERRORLEVEL% neq 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%
    pause
)
