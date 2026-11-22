# Open a deck in Microsoft PowerPoint and export every slide as PNG (and the deck as PDF).
#   powershell -ExecutionPolicy Bypass -File documentation\build\render_pptx.ps1 -Pptx <path> -OutDir <dir>
param([Parameter(Mandatory = $true)][string]$Pptx, [Parameter(Mandatory = $true)][string]$OutDir)
$ErrorActionPreference = "Stop"
$Pptx = (Resolve-Path $Pptx).Path
New-Item -ItemType Directory -Force $OutDir | Out-Null
Get-ChildItem $OutDir -Filter "slide-*.png" | Remove-Item
$app = New-Object -ComObject PowerPoint.Application
try {
    # ReadOnly, Untitled=false, WithWindow=false
    $deck = $app.Presentations.Open($Pptx, -1, 0, 0)
    $i = 0
    foreach ($slide in $deck.Slides) {
        $i++
        $slide.Export((Join-Path $OutDir ("slide-{0:D2}.png" -f $i)), "PNG", 1600, 900)
    }
    $deck.SaveAs([IO.Path]::ChangeExtension($Pptx, ".pdf"), 32)   # 32 = ppSaveAsPDF
    Write-Output "slides=$i"
    $deck.Close()
}
finally {
    $app.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
