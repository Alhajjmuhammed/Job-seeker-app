@echo off
REM Worker Connect - Start Local Development Server

echo 🚀 Starting Worker Connect Development Server...

REM Check if virtual environment exists
if not exist venv\ (
    echo ❌ Virtual environment not found!
    echo Please run setup-local.bat first to set up the project.
    pause
    exit /b 1
)

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if Python is working
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found in virtual environment
    echo Please run setup-local.bat again
    pause
    exit /b 1
)

REM Run any pending migrations
echo 🗄️ Checking for database migrations...
python manage.py migrate --check >nul 2>&1
if %errorlevel% neq 0 (
    echo 📊 Running pending migrations...
    python manage.py migrate
)

echo.
echo 🌐 Starting Django development server...
echo.
echo 📱 API Server: http://localhost:8000
echo 🔧 Admin Panel: http://localhost:8000/admin/
echo 📚 API Docs: http://localhost:8000/api/docs/
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the Django development server
python manage.py runserver 0.0.0.0:8000