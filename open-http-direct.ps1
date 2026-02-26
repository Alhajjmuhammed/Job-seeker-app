# Direct HTTP Opener - Bypasses Browser HSTS Cache
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Worker Connect - HTTP Direct Access" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test if server is responding
Write-Host "Testing server..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8080/" -UseBasicParsing -MaximumRedirection 0 -ErrorAction Stop
    Write-Host "SUCCESS: Server is responding on HTTP port 8080" -ForegroundColor Green
    Write-Host "   Status Code: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Server not responding on port 8080" -ForegroundColor Red
    Write-Host "   Please start the server with: python manage.py runserver 8080" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Opening browser with direct HTTP URL..." -ForegroundColor Yellow

# Method 1: Try Chrome in Incognito mode (bypasses cache completely)
$chromeLocations = @(
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe"
)

$chromeFound = $false
foreach ($chromePath in $chromeLocations) {
    if (Test-Path $chromePath) {
        Write-Host "Opening Chrome in Incognito mode (bypasses HSTS cache)..." -ForegroundColor Green
        Start-Process $chromePath -ArgumentList "--incognito", "http://127.0.0.1:8080/", "--disable-hsts"
        $chromeFound = $true
        break
    }
}

if (-not $chromeFound) {
    # Method 2: Try Edge in InPrivate mode
    $edgePath = "$env:ProgramFiles(x86)\Microsoft\Edge\Application\msedge.exe"
    if (Test-Path $edgePath) {
        Write-Host "Opening Edge in InPrivate mode..." -ForegroundColor Green
        Start-Process $edgePath -ArgumentList "-inprivate", "http://127.0.0.1:8080/"
    } else {
        # Method 3: Default browser
        Write-Host "WARNING: Opening default browser..." -ForegroundColor Yellow
        Start-Process "http://127.0.0.1:8080/"
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Browser Opened Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "URL: http://127.0.0.1:8080/" -ForegroundColor White
Write-Host ""
Write-Host "Test Credentials:" -ForegroundColor Yellow
Write-Host "  Admin: admin@test.com / test1234" -ForegroundColor White
Write-Host "  Client: client@test.com / test1234" -ForegroundColor White
Write-Host "  Worker: worker@test.com / test1234" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANT: If you still see HTTPS error:" -ForegroundColor Red
Write-Host "  1. Look at the URL bar - it might show 'https://' " -ForegroundColor Yellow
Write-Host "  2. Manually change it to 'http://' (not https)" -ForegroundColor Yellow
Write-Host "  3. Or type: http://127.0.0.1:8080/ directly" -ForegroundColor Yellow
Write-Host ""
Write-Host "TIP: Bookmark the HTTP URL to avoid future issues" -ForegroundColor Cyan
Write-Host ""
