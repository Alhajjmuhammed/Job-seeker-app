@echo off
cls
echo.
echo =========================================================================
echo   BROWSER HSTS CACHE CLEANER - ULTIMATE FIX
echo =========================================================================
echo.
echo This will permanently fix the HTTPS redirect issue by:
echo   1. Killing all browser processes
echo   2. Deleting HSTS cache files
echo   3. Opening HTTP URL in fresh browser
echo.
pause
echo.

echo [1/4] Closing all browsers...
taskkill /F /IM chrome.exe /T >nul 2>&1
taskkill /F /IM msedge.exe /T >nul 2>&1
taskkill /F /IM firefox.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul
echo Done!

echo.
echo [2/4] Deleting Chrome HSTS cache...
del /F /Q "%LOCALAPPDATA%\Google\Chrome\User Data\Default\TransportSecurity" 2>nul
del /F /Q "%LOCALAPPDATA%\Google\Chrome\User Data\Profile 1\TransportSecurity" 2>nul
del /F /Q "%LOCALAPPDATA%\Google\Chrome\User Data\Profile 2\TransportSecurity" 2>nul
echo Done!

echo.
echo [3/4] Deleting Edge HSTS cache...
del /F /Q "%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\TransportSecurity" 2>nul
del /F /Q "%LOCALAPPDATA%\Microsoft\Edge\User Data\Profile 1\TransportSecurity" 2>nul
del /F /Q "%LOCALAPPDATA%\Microsoft\Edge\User Data\Profile 2\TransportSecurity" 2>nul
echo Done!

echo.
echo [4/4] Opening browser with HTTP URL...
timeout /t 2 /nobreak >nul

REM Try to open in Edge with specific flags to force HTTP
start msedge --new-window --disable-features=AutomaticHttpsUpgrades "http://127.0.0.1:8080/"

echo.
echo =========================================================================
echo   COMPLETE! Browser opened with clean cache
echo =========================================================================
echo.
echo If you STILL see HTTPS redirect, do this:
echo.
echo   1. In the browser address bar, DELETE everything
echo   2. Type EXACTLY: http://127.0.0.1:8080/
echo   3. Press ENTER
echo.
echo   (Make sure "http://" is at the beginning, not "https://")
echo.
echo =========================================================================
echo.
echo Login credentials:
echo   Admin:  admin@test.com / test1234
echo   Client: client@test.com / test1234
echo   Worker: worker@test.com / test1234
echo.
echo =========================================================================
pause
