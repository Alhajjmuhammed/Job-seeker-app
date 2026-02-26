@echo off
REM Ultimate fix for HTTPS redirect issue
echo.
echo ============================================================================
echo    FIXING LOCALHOST HTTPS REDIRECT - PERMANENT SOLUTION
echo ============================================================================
echo.

echo Step 1: Killing all browser processes...
taskkill /F /IM chrome.exe /T >nul 2>&1
taskkill /F /IM msedge.exe /T >nul 2>&1
taskkill /F /IM firefox.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul
echo Done!
echo.

echo Step 2: Clearing Chrome HSTS cache...
if exist "%LOCALAPPDATA%\Google\Chrome\User Data\Default\TransportSecurity" (
    del /F /Q "%LOCALAPPDATA%\Google\Chrome\User Data\Default\TransportSecurity" >nul 2>&1
    echo Chrome HSTS cache cleared!
) else (
    echo Chrome cache not found (may not be installed)
)
echo.

echo Step 3: Clearing Edge HSTS cache...
if exist "%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\TransportSecurity" (
    del /F /Q "%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\TransportSecurity" >nul 2>&1
    echo Edge HSTS cache cleared!
) else (
    echo Edge cache not found (may not be installed)
)
echo.

echo ============================================================================
echo    STARTING DJANGO ON PORT 8080 (Avoids HSTS issues)
echo ============================================================================
echo.
echo Server will start in 3 seconds...
timeout /t 3 /nobreak >nul
echo.

REM Start Django on port 8080 in this window
echo Starting Django server at http://127.0.0.1:8080/
echo.
echo Opening browser in 5 seconds...
timeout /t 5 /nobreak >nul

REM Open in regular Edge (cache is cleared so should work)
start msedge "http://127.0.0.1:8080/"

echo.
echo ============================================================================
echo    SERVER RUNNING!
echo ============================================================================
echo.
echo Backend:     http://127.0.0.1:8080/
echo Admin:       http://127.0.0.1:8080/admin/
echo API Docs:    http://127.0.0.1:8080/api/docs/
echo.
echo LOGIN:
echo   Admin:  admin@test.com  / test1234
echo   Client: client@test.com / test1234
echo   Worker: worker@test.com / test1234
echo.
echo If browser still redirects to HTTPS:
echo   1. Close browser completely
echo   2. Re-run this script
echo   3. Or manually type: http://127.0.0.1:8080/
echo.
echo Press CTRL+C to stop the server
echo ============================================================================
echo.

python manage.py runserver 8080
