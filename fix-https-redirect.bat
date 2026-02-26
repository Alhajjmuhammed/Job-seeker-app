@echo off
REM Fix HTTPS redirect issue for localhost
echo.
echo ============================================================================
echo   FIX HTTPS REDIRECT ISSUE FOR LOCALHOST
echo ============================================================================
echo.
echo Your browser is automatically redirecting HTTP to HTTPS.
echo This script will help you fix this issue.
echo.
echo SOLUTIONS:
echo.
echo 1. CLEAR CHROME HSTS (Recommended)
echo    - Open Chrome and go to: chrome://net-internals/#hsts
echo    - Under "Delete domain security policies"
echo    - Enter: localhost
echo    - Click "Delete"
echo    - Enter: 127.0.0.1
echo    - Click "Delete"
echo    - Restart Chrome
echo.
echo 2. USE EDGE IN INPRIVATE MODE
echo    Press 1 to open in Edge InPrivate mode
echo.
echo 3. USE CHROME INCOGNITO MODE
echo    Press 2 to open in Chrome Incognito mode
echo.
echo 4. USE FIREFOX PRIVATE WINDOW
echo    Press 3 to open in Firefox Private window
echo.
echo 5. MANUAL LINK (Copy and paste in any browser)
echo    http://127.0.0.1:8000/
echo.
set /p choice="Enter your choice (1-3) or press ENTER to see manual steps: "

if "%choice%"=="1" (
    echo.
    echo Opening in Microsoft Edge InPrivate mode...
    start msedge -inprivate "http://127.0.0.1:8000/"
    echo.
    echo If Edge didn't open, copy this URL manually:
    echo http://127.0.0.1:8000/
    echo.
    goto :end
)

if "%choice%"=="2" (
    echo.
    echo Opening in Chrome Incognito mode...
    start chrome --incognito "http://127.0.0.1:8000/"
    echo.
    echo If Chrome didn't open, copy this URL manually:
    echo http://127.0.0.1:8000/
    echo.
    goto :end
)

if "%choice%"=="3" (
    echo.
    echo Opening in Firefox Private window...
    start firefox -private-window "http://127.0.0.1:8000/"
    echo.
    echo If Firefox didn't open, copy this URL manually:
    echo http://127.0.0.1:8000/
    echo.
    goto :end
)

echo.
echo ============================================================================
echo   MANUAL FIX STEPS
echo ============================================================================
echo.
echo OPTION A: Clear Browser HSTS Cache
echo ----------------------------------
echo.
echo FOR CHROME:
echo 1. Open Chrome
echo 2. Type in address bar: chrome://net-internals/#hsts
echo 3. Scroll to "Delete domain security policies"
echo 4. Type: localhost
echo 5. Click "Delete"
echo 6. Type: 127.0.0.1
echo 7. Click "Delete"
echo 8. Restart Chrome
echo 9. Go to: http://127.0.0.1:8000/
echo.
echo FOR EDGE:
echo 1. Open Edge
echo 2. Type in address bar: edge://net-internals/#hsts
echo 3. Follow same steps as Chrome above
echo.
echo FOR FIREFOX:
echo 1. Close Firefox completely
echo 2. Delete file: %%APPDATA%%\Mozilla\Firefox\Profiles\*.default*\SiteSecurityServiceState.txt
echo 3. Restart Firefox
echo.
echo ============================================================================
echo.
echo OPTION B: Use Private/Incognito Mode
echo -------------------------------------
echo.
echo Chrome Incognito:  CTRL + SHIFT + N
echo Edge InPrivate:    CTRL + SHIFT + N
echo Firefox Private:   CTRL + SHIFT + P
echo.
echo Then type: http://127.0.0.1:8000/
echo (Make sure to include http:// at the start)
echo.
echo ============================================================================
echo.
echo OPTION C: Try Different Port
echo ----------------------------
echo.
set /p tryport="Would you like to run server on different port? (y/N): "
if /i "%tryport%"=="y" (
    echo.
    echo Starting Django on port 8080 instead...
    echo.
    echo Open this URL: http://127.0.0.1:8080/
    echo.
    python manage.py runserver 8080
)

:end
echo.
echo ============================================================================
echo If nothing works, copy and paste this URL in your browser:
echo http://127.0.0.1:8000/
echo.
echo Make sure to include "http://" at the beginning!
echo ============================================================================
echo.
pause
