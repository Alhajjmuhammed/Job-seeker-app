@echo off
echo Adding Windows Firewall rule for Django on port 8080...
echo.
echo This script needs Administrator privileges.
echo.

netsh advfirewall firewall delete rule name="Django Development Server 8080" >nul 2>&1
netsh advfirewall firewall add rule name="Django Development Server 8080" dir=in action=allow protocol=TCP localport=8080

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS! Port 8080 is now allowed through Windows Firewall.
    echo Your mobile device can now connect to http://192.168.0.238:8080
    echo.
) else (
    echo.
    echo FAILED! Please right-click this file and select "Run as administrator"
    echo.
)

pause
