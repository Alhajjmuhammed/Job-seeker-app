@echo off
REM Quick fix: Open app in private browser mode to bypass HTTPS redirect
echo.
echo ============================================================================
echo   OPENING APP IN PRIVATE MODE
echo ============================================================================
echo.
echo Trying to open: http://127.0.0.1:8000/
echo.

REM Try Edge InPrivate
start msedge -inprivate "http://127.0.0.1:8000/"

echo.
echo ✅ Opening in Microsoft Edge (InPrivate mode)
echo.
echo If Edge didn't open, try these alternatives:
echo.
echo 1. Chrome Incognito: Press CTRL+SHIFT+N and type: http://127.0.0.1:8000/
echo 2. Firefox Private:  Press CTRL+SHIFT+P and type: http://127.0.0.1:8000/
echo 3. Manual: Copy this URL: http://127.0.0.1:8000/
echo.
echo Make sure to include "http://" (not https://)
echo.
echo ============================================================================
echo.
echo 🔐 LOGIN CREDENTIALS:
echo    Admin:  admin@test.com  / test1234
echo    Client: client@test.com / test1234
echo    Worker: worker@test.com / test1234
echo.
echo ============================================================================
pause
