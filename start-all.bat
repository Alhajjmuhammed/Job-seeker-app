@echo off
REM ============================================================================
REM WORKER CONNECT - START ALL SERVICES
REM ============================================================================
echo.
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ║           WORKER CONNECT - STARTING ALL SERVICES                     ║
echo ╚══════════════════════════════════════════════════════════════════════╝
echo.

REM Start Django Backend in new window
echo [1/2] Starting Django Backend Server...
start "Django Backend - Worker Connect" cmd /k "python manage.py runserver"
timeout /t 3 /nobreak >nul

echo ✅ Backend started at: http://127.0.0.1:8000/
echo.

REM Start React Native Mobile App in new window
echo [2/2] Starting React Native Mobile App...
start "React Native Mobile - Worker Connect" cmd /k "cd React-native-app\my-app && npm start"
timeout /t 2 /nobreak >nul

echo ✅ Mobile app starting (Expo Dev Server)
echo.
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ║                    ALL SERVICES STARTED!                             ║
echo ╚══════════════════════════════════════════════════════════════════════╝
echo.
echo 📱 BACKEND (Django):
echo    → http://127.0.0.1:8000/
echo    → Admin: http://127.0.0.1:8000/admin/
echo    → API Docs: http://127.0.0.1:8000/api/docs/
echo.
echo 📱 MOBILE APP (React Native):
echo    → Expo Dev Server: http://localhost:8081/
echo    → Scan QR code with Expo Go app
echo.
echo 🔐 TEST CREDENTIALS:
echo    ├─ Admin:  admin@test.com  / test1234
echo    ├─ Client: client@test.com / test1234
echo    └─ Worker: worker@test.com / test1234
echo.
echo ⚠️  To stop services: Close the terminal windows or press CTRL+C
echo.
pause
