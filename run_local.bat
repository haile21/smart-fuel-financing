@echo off
REM Quick start script for Windows
echo ========================================
echo Smart Fuel Financing Backend
echo Local Development Server
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if .env exists
if not exist ".env" (
    echo.
    echo WARNING: .env file not found!
    echo Please copy .env.example to .env and configure it.
    echo.
    pause
)

REM Start server
echo.
echo Starting FastAPI server...
echo API Docs will be available at: http://localhost:8000/docs
echo Press Ctrl+C to stop the server
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause

