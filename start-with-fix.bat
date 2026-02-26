@echo off
REM Start Django with HTTPS fix enabled
echo.
echo ============================================================================
echo    STARTING DJANGO SERVER WITH HTTPS FIX
echo ============================================================================
echo.
echo Changes made:
echo   ✓ DEBUG=True in .env file
echo   ✓ Added middleware to handle HTTPS requests gracefully
echo   ✓ All security settings disabled for development
echo.
echo Starting server on port 8080...
echo.
timeout /t 2 /nobreak >nul

REM Start Django
python manage.py runserver 8080

echo.
echo Server stopped.
pause
