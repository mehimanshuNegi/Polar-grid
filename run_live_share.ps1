# Polar Grid - Single-Command Live Share Launcher
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  POLAR GRID - LIVE SHARING LAUNCHER     " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Check Python dependencies & models
Write-Host "`n[1/3] Starting Polar Grid FastAPI Backend (Port 8000)..." -ForegroundColor Yellow
$backendProcess = Start-Process -FilePath "python" -ArgumentList "backend/main.py" -PassThru -NoNewWindow
Start-Sleep -Seconds 3

# 2. Start Cloudflare HTTPS Tunnel
Write-Host "[2/3] Launching Secure HTTPS Tunnel..." -ForegroundColor Yellow
$tunnelProcess = Start-Process -FilePath ".\scratch\cloudflared.exe" -ArgumentList "tunnel --protocol http2 --url http://127.0.0.1:8000" -PassThru -NoNewWindow -RedirectStandardError "scratch\tunnel_output.log"

Start-Sleep -Seconds 5

# 3. Retrieve Live URL
Write-Host "[3/3] Retrieving Shareable Link..." -ForegroundColor Yellow
$tunnelLog = Get-Content "scratch\tunnel_output.log" -Raw
if ($tunnelLog -match "https://[a-zA-Z0-9-]+\.trycloudflare\.com") {
    $liveUrl = $matches[0]
    Write-Host "`n=========================================" -ForegroundColor Green
    Write-Host "  PUBLIC LIVE LINK: $liveUrl" -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host "Send this link to your teammates to view the live dashboard!`n"
} else {
    Write-Host "Tunnel is initializing. Check scratch\tunnel_output.log for the live link." -ForegroundColor Yellow
}

Write-Host "Press Ctrl+C to stop sharing."
Wait-Process -Id $tunnelProcess.Id
