@echo off
REM Worker Connect - Quick Start Script for Windows
REM This script helps you get the project running quickly

echo 🚀 Starting Worker Connect Development Environment...

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo ✅ Docker is running

REM Build and start services
echo 🔨 Building and starting services...
docker-compose up -d --build

REM Wait for database to be ready
echo ⏳ Waiting for database to be ready...
timeout /t 10 /nobreak

REM Run migrations
echo 📊 Running database migrations...
docker-compose exec web python manage.py migrate

REM Create superuser (optional)
echo 👤 Creating superuser (optional)...
echo You can create a superuser now or skip this step.
set /p create_superuser="Create superuser? (y/N): "
if /i "%create_superuser%"=="y" (
    docker-compose exec web python manage.py createsuperuser
)

echo.
echo 🎉 Worker Connect is now running!
echo.
echo 📱 API Server: http://localhost:8000
echo 🔧 Admin Panel: http://localhost:8000/admin/
echo 📚 API Docs: http://localhost:8000/api/docs/
echo.
echo Next steps:
echo 1. Navigate to React-native-app/my-app/
echo 2. Run 'npm install' to install dependencies
echo 3. Run 'npm start' to start the mobile app
echo.
echo To stop the services, run: docker-compose down
pause