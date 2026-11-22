# Capture full-height screenshots of the running app with headless Microsoft Edge.
# Requires both servers running (backend :8000, frontend :3000).
#   powershell -ExecutionPolicy Bypass -File documentation\build\screenshots.ps1 -ImageId <id> -VideoId <id> [-VideoTime 5]
param([Parameter(Mandatory = $true)][string]$ImageId, [Parameter(Mandatory = $true)][string]$VideoId, [double]$VideoTime = 0)

$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$raw = Join-Path $PSScriptRoot "screenshots\raw"
New-Item -ItemType Directory -Force $raw | Out-Null
$profileDir = Join-Path $env:TEMP "imageguard-shot-profile"
$base = "http://localhost:3000"
$pages = [ordered]@{
    "overview"      = @("$base/", 1400, 1000)
    "investigation" = @("$base/investigation", 1400, 1000)
    "image"         = @("$base/image-analysis?id=$ImageId", 1400, 3400)
    "video"         = @("$base/video-analysis?id=$VideoId&t=$VideoTime", 1400, 3600)
    "reports"       = @("$base/reports?id=$ImageId", 1400, 2400)
}
foreach ($name in $pages.Keys) {
    $url, $w, $h = $pages[$name]
    $out = Join-Path $raw "$name.png"
    Remove-Item $out -ErrorAction SilentlyContinue
    & $edge --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 "--user-data-dir=$profileDir" `
        "--window-size=$w,$h" --virtual-time-budget=15000 "--screenshot=$out" $url 2>$null | Out-Null
    Start-Sleep -Milliseconds 300
    if (Test-Path $out) { "ok  $name" } else { "FAILED $name" }
}
