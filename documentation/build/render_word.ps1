# Open the report in Microsoft Word, refresh all fields (TOC, lists, page numbers),
# save it, export a PDF and optionally page images for review.
#   powershell -ExecutionPolicy Bypass -File documentation\build\render_word.ps1 -Docx <path> [-PageDir <dir>]
param([Parameter(Mandatory = $true)][string]$Docx, [string]$PageDir = "")

$ErrorActionPreference = "Stop"
$Docx = (Resolve-Path $Docx).Path
$pdf = [IO.Path]::ChangeExtension($Docx, ".pdf")
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($Docx, $false, $false)
    # Two passes: the first fills the lists (changing page count), the second fixes page numbers.
    for ($i = 0; $i -lt 2; $i++) {
        $doc.Fields.Update() | Out-Null
        foreach ($toc in $doc.TablesOfContents) { $toc.Update() | Out-Null }
        $doc.Repaginate()
    }
    $doc.Save()
    $doc.ExportAsFixedFormat($pdf, 17)   # 17 = wdExportFormatPDF
    $pages = $doc.ComputeStatistics(2)   # 2 = wdStatisticPages
    Write-Output "pages=$pages pdf=$pdf"

    if ($PageDir) {
        Add-Type -AssemblyName System.Drawing
        New-Item -ItemType Directory -Force $PageDir | Out-Null
        $word.ActiveWindow.View.Type = 3   # print layout
        $n = 0
        foreach ($pane in $word.ActiveWindow.Panes) {
            foreach ($page in $pane.Pages) {
                $n++
                $bits = $page.EnhMetaFileBits
                $ms = New-Object IO.MemoryStream(, $bits)
                $img = [System.Drawing.Image]::FromStream($ms)
                $scale = 1100 / $img.Width
                $bmp = New-Object System.Drawing.Bitmap([int]($img.Width * $scale), [int]($img.Height * $scale))
                $g = [System.Drawing.Graphics]::FromImage($bmp)
                $g.Clear([System.Drawing.Color]::White)
                $g.SmoothingMode = "HighQuality"; $g.InterpolationMode = "HighQualityBicubic"
                $g.DrawImage($img, 0, 0, $bmp.Width, $bmp.Height)
                $bmp.Save((Join-Path $PageDir ("page-{0:D2}.png" -f $n)), [System.Drawing.Imaging.ImageFormat]::Png)
                $g.Dispose(); $bmp.Dispose(); $img.Dispose(); $ms.Dispose()
            }
        }
        Write-Output "page images=$n"
    }
    $doc.Close($false)
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
