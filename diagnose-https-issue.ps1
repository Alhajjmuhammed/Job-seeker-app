# Complete HTTPS Issue Diagnostic Tool
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  HTTPS Issue Diagnostic Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check if server is running
Write-Host "[1/8] Checking if Django server is running..." -ForegroundColor Yellow
$serverRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8080/" -UseBasicParsing -MaximumRedirection 0 -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ Server is responding on port 8080" -ForegroundColor Green
    Write-Host "      Status Code: $($response.StatusCode)" -ForegroundColor Gray
    $serverRunning = $true
} catch {
    Write-Host "   ❌ Server is NOT responding on port 8080" -ForegroundColor Red
}

# 2. Check Django settings
Write-Host ""
Write-Host "[2/8] Checking Django security settings..." -ForegroundColor Yellow
try {
    $settingsCheck = python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings'); from django.conf import settings; print(f'DEBUG={settings.DEBUG}'); print(f'SECURE_SSL_REDIRECT={settings.SECURE_SSL_REDIRECT}'); print(f'SECURE_HSTS_SECONDS={settings.SECURE_HSTS_SECONDS}')"
    Write-Host "   $settingsCheck" -ForegroundColor Gray
    if ($settingsCheck -match "SECURE_SSL_REDIRECT=False") {
        Write-Host "   ✅ SSL redirect is disabled" -ForegroundColor Green
    } else {
        Write-Host "   ❌ SSL redirect is enabled (should be False)" -ForegroundColor Red
    }
} catch {
    Write-Host "   ⚠️  Could not check Django settings" -ForegroundColor Yellow
}

# 3. Check .env file
Write-Host ""
Write-Host "[3/8] Checking .env configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    $envContent = Get-Content ".env" | Select-String "DEBUG|SECURE_SSL"
    Write-Host "   $envContent" -ForegroundColor Gray
    Write-Host "   ✅ .env file found" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  .env file not found" -ForegroundColor Yellow
}

# 4. Check middleware
Write-Host ""
Write-Host "[4/8] Checking HTTPS middleware..." -ForegroundColor Yellow
if (Test-Path "worker_connect\https_middleware.py") {
    Write-Host "   ✅ HTTPS middleware file exists" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  HTTPS middleware file not found" -ForegroundColor Yellow
}

# 5. Check browser HSTS cache files
Write-Host ""
Write-Host "[5/8] Checking browser HSTS cache..." -ForegroundColor Yellow
$hstsFiles = @(
    "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\TransportSecurity",
    "$env:LOCALAPPDATA\Google\Chrome\User Data\TransportSecurity",
    "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\TransportSecurity"
)
$hstsFound = $false
foreach ($file in $hstsFiles) {
    if (Test-Path $file) {
        $fileSize = (Get-Item $file).Length
        Write-Host "   ⚠️  Found HSTS cache: $file" -ForegroundColor Yellow
        Write-Host "      Size: $fileSize bytes" -ForegroundColor Gray
        $hstsFound = $true
    }
}
if (-not $hstsFound) {
    Write-Host "   ✅ No HSTS cache files found" -ForegroundColor Green
}

# 6. Test HTTP response headers
Write-Host ""
Write-Host "[6/8] Checking server response headers..." -ForegroundColor Yellow
if ($serverRunning) {
    try {
        $headers = Invoke-WebRequest -Uri "http://127.0.0.1:8080/" -UseBasicParsing -MaximumRedirection 0 -ErrorAction Stop
        $hstsHeader = $headers.Headers['Strict-Transport-Security']
        if ($hstsHeader) {
            Write-Host "   ⚠️  HSTS header is present: $hstsHeader" -ForegroundColor Yellow
        } else {
            Write-Host "   ✅ No HSTS header in response (good!)" -ForegroundColor Green
        }
        
        $location = $headers.Headers['Location']
        if ($location -and $location -match "https") {
            Write-Host "   ❌ Server is redirecting to HTTPS: $location" -ForegroundColor Red
        } else {
            Write-Host "   ✅ No HTTPS redirect in response" -ForegroundColor Green
        }
    } catch {
        Write-Host "   ⚠️  Could not check headers" -ForegroundColor Yellow
    }
}

# 7. Check for running Django processes
Write-Host ""
Write-Host "[7/8] Checking for Django processes..." -ForegroundColor Yellow
$djangoProcesses = Get-Process | Where-Object { $_.ProcessName -eq "python" }
if ($djangoProcesses) {
    Write-Host "   ✅ Found $($djangoProcesses.Count) Python process(es) running" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  No Python processes found" -ForegroundColor Yellow
}

# 8. Try direct curl test
Write-Host ""
Write-Host "[8/8] Testing with direct HTTP request..." -ForegroundColor Yellow
try {
    $testResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8080/api/health/" -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✅ Health check endpoint responds: $($testResponse.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Health check endpoint failed" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DIAGNOSIS SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($serverRunning) {
    Write-Host "✅ SERVER: Running and responding on HTTP" -ForegroundColor Green
} else {
    Write-Host "❌ SERVER: Not running or not responding" -ForegroundColor Red
    Write-Host "   Action: Start server with: python manage.py runserver 8080" -ForegroundColor Yellow
}

Write-Host ""
if ($hstsFound) {
    Write-Host "⚠️  BROWSER CACHE: HSTS cache files detected" -ForegroundColor Yellow
    Write-Host "   This is the likely cause of HTTPS redirect" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   SOLUTIONS:" -ForegroundColor Cyan
    Write-Host "   1. Use Incognito/Private browsing mode" -ForegroundColor White
    Write-Host "   2. Run: .\open-http-direct.ps1" -ForegroundColor White
    Write-Host "   3. Manually type: http://127.0.0.1:8080/ in address bar" -ForegroundColor White
    Write-Host "   4. Try a different browser" -ForegroundColor White
} else {
    Write-Host "✅ BROWSER CACHE: No obvious HSTS cache issues" -ForegroundColor Green
}

Write-Host ""
Write-Host "Press Enter to continue..."
Read-Host
