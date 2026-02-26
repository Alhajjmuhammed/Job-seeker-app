# Clear browser HSTS cache for localhost
# This fixes the automatic HTTPS redirect issue

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "   FIXING HTTPS REDIRECT ISSUE FOR LOCALHOST" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Detected Issue: Browser automatically redirecting HTTP to HTTPS" -ForegroundColor Yellow
Write-Host ""

# Function to kill browser processes
function Stop-Browsers {
    Write-Host "Closing all browser instances..." -ForegroundColor Yellow
    Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-Process msedge -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-Process firefox -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2
    Write-Host "✓ Browsers closed" -ForegroundColor Green
}

# Chrome HSTS cache location
$chromePath = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\TransportSecurity"
$edgePath = "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\TransportSecurity"

Write-Host "SOLUTION 1: Clear Browser HSTS Cache" -ForegroundColor Cyan
Write-Host "-------------------------------------" -ForegroundColor Cyan
Write-Host ""

$clearCache = Read-Host "Do you want to clear browser HSTS cache? (Y/n)"

if ($clearCache -ne 'n' -and $clearCache -ne 'N') {
    Stop-Browsers
    
    # Clear Chrome HSTS
    if (Test-Path $chromePath) {
        Remove-Item $chromePath -Force
        Write-Host "✓ Chrome HSTS cache cleared" -ForegroundColor Green
    } else {
        Write-Host "ℹ Chrome HSTS cache not found (Chrome not installed or different profile)" -ForegroundColor Gray
    }
    
    # Clear Edge HSTS
    if (Test-Path $edgePath) {
        Remove-Item $edgePath -Force
        Write-Host "✓ Edge HSTS cache cleared" -ForegroundColor Green
    } else {
        Write-Host "ℹ Edge HSTS cache not found (Edge not installed or different profile)" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "✓ HSTS cache cleared successfully!" -ForegroundColor Green
    Write-Host ""
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "   STARTING DJANGO SERVER ON PORT 8080" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Using port 8080 to avoid HSTS issues with port 8000" -ForegroundColor Yellow
Write-Host ""

# Start Django on port 8080
Write-Host "Starting Django server..." -ForegroundColor Yellow
Start-Sleep -Seconds 1

# Open browser
Write-Host ""
Write-Host "Opening browser in 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Try Edge first
Start-Process msedge "http://127.0.0.1:8080/"

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Green
Write-Host "   SERVER STARTED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "✓ Backend URL:  http://127.0.0.1:8080/" -ForegroundColor Green
Write-Host "✓ Admin Panel:  http://127.0.0.1:8080/admin/" -ForegroundColor Green
Write-Host "✓ API Docs:     http://127.0.0.1:8080/api/docs/" -ForegroundColor Green
Write-Host ""
Write-Host "🔐 LOGIN CREDENTIALS:" -ForegroundColor Cyan
Write-Host "   Admin:  admin@test.com  / test1234" -ForegroundColor White
Write-Host "   Client: client@test.com / test1234" -ForegroundColor White
Write-Host "   Worker: worker@test.com / test1234" -ForegroundColor White
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Green
Write-Host ""

# Run Django
python manage.py runserver 8080
