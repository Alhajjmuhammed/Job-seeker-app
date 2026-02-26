@echo off
REM Worker Connect - Local Development Setup Script for Windows
REM This script sets up the project for local development without Docker

echo 🚀 Setting up Worker Connect for Local Development...

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not available in PATH.
    echo.
    echo Please install Python 3.11+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    echo Alternative: You can also use py command if you have Python Launcher:
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ Python Launcher is available. Using 'py' command.
        set PYTHON_CMD=py
    ) else (
        echo After installing Python, run this script again.
        pause
        exit /b 1
    )
) else (
    echo ✅ Python is available
    set PYTHON_CMD=python
)

REM Create virtual environment
echo 📦 Creating virtual environment...
%PYTHON_CMD% -m venv venv

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️ Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip

REM Install requirements
echo 📚 Installing Python dependencies...
pip install -r requirements-local.txt

REM Optional: Install full requirements if needed
echo.
set /p full_install="Install full requirements including optional packages? (y/N): "
if /i "%full_install%"=="y" (
    echo 📦 Installing full requirements...
    pip install -r requirements.txt
)

REM Create .env if it doesn't exist (it should exist now)
if not exist .env (
    echo 📝 Copying environment configuration...
    copy .env.example .env
)

REM Run migrations
echo 🗄️ Setting up database...
%PYTHON_CMD% manage.py migrate

REM Create superuser (optional)
echo 👤 Create superuser account? (optional)
set /p create_superuser="Create superuser? (y/N): "
if /i "%create_superuser%"=="y" (
    %PYTHON_CMD% manage.py createsuperuser
)

REM Collect static files
echo 📁 Collecting static files...
%PYTHON_CMD% manage.py collectstatic --noinput

echo.
echo 🎉 Setup complete!
echo.
echo To start the development server:
echo   1. Run: start-local.bat
echo   2. Or manually: venv\Scripts\activate && python manage.py runserver
echo.
echo The API will be available at: http://localhost:8000
pause