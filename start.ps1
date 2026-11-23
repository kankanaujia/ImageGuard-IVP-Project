<#
.SYNOPSIS
  Start (or stop) ImageGuard: the FastAPI backend on port 8000 and the Next.js frontend on port 3000.
  Both run in the background; their output is written to the logs folder.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File start.ps1            # start both and open the browser
  powershell -ExecutionPolicy Bypass -File start.ps1 -NoBrowser
  powershell -ExecutionPolicy Bypass -File start.ps1 -Stop      # stop both servers
#>
param([switch]$NoBrowser, [switch]$Stop)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$python = Join-Path $root "backend\.venv\Scripts\python.exe"
$frontend = Join-Path $root "frontend"
$url = "http://localhost:3000"

function Test-Port([int]$port) {
    $client = New-Object Net.Sockets.TcpClient
    try { $client.Connect("127.0.0.1", $port); return $true } catch { return $false } finally { $client.Dispose() }
}

function Stop-Port([int]$port) {
    $owners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($id in $owners) {
        # npm/uvicorn start child processes; stop the whole tree so nothing keeps the port open
        & taskkill /PID $id /T /F | Out-Null
        Write-Host "  stopped process $id on port $port"
    }
    if (-not $owners) { Write-Host "  nothing listening on port $port" }
}

if ($Stop) {
    Write-Host "Stopping ImageGuard..."
    Stop-Port 8000; Stop-Port 3000
    return
}

# ---- prerequisites
if (-not (Test-Path $python)) {
    Write-Host "Backend environment not found. Set it up once (see README):" -ForegroundColor Yellow
    Write-Host "  py -3.12 -m venv backend\.venv; backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt"
    exit 1
}
$npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if (-not $npm -and (Test-Path "C:\Program Files\nodejs\npm.cmd")) { $npm = "C:\Program Files\nodejs\npm.cmd" }
if (-not $npm) { Write-Host "Node.js (npm) not found. Install Node.js 20 or newer." -ForegroundColor Yellow; exit 1 }
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Installing frontend packages (first run only)..."
    Push-Location $frontend; & $npm install --no-fund --no-audit; Pop-Location
}

# ---- start both servers in the background; their output goes to the logs folder
$logs = Join-Path $root "logs"
New-Item -ItemType Directory -Force $logs | Out-Null
if (Test-Port 8000) { Write-Host "Backend already running on port 8000" }
else {
    Write-Host "Starting backend on http://127.0.0.1:8000 ..."
    Start-Process -FilePath $python -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $root -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logs "backend.log") -RedirectStandardError (Join-Path $logs "backend.err.log")
}
if (Test-Port 3000) { Write-Host "Frontend already running on port 3000" }
else {
    Write-Host "Starting frontend on $url ..."
    $env:Path = (Split-Path $npm) + ";" + $env:Path      # npm needs node on the PATH
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", "`"$npm`" run dev") -WorkingDirectory $frontend -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logs "frontend.log") -RedirectStandardError (Join-Path $logs "frontend.err.log")
}

# ---- wait until both answer, then open the app
$deadline = (Get-Date).AddSeconds(120)
while (-not ((Test-Port 8000) -and (Test-Port 3000))) {
    if ((Get-Date) -gt $deadline) {
        Write-Host "Servers did not start within 2 minutes. Last lines of the logs:" -ForegroundColor Yellow
        foreach ($log in Get-ChildItem $logs -Filter *.log) { Write-Host "--- $($log.Name)"; Get-Content $log.FullName -Tail 15 }
        exit 1
    }
    Start-Sleep -Milliseconds 500
}
Write-Host "ImageGuard is running at $url" -ForegroundColor Green
Write-Host "Stop it with:  powershell -ExecutionPolicy Bypass -File start.ps1 -Stop"
if (-not $NoBrowser) { Start-Process $url }
