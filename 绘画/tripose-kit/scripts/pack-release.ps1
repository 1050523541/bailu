# Pack TriPose kit into a versioned release zip.
param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$KitRoot = Split-Path -Parent $PSScriptRoot
$Manifest = Join-Path $KitRoot "manifest.json"
if (-not (Test-Path $Manifest)) { throw "manifest missing: $Manifest" }

$man = Get-Content $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $Version) { $Version = [string]$man.version }
if (-not $Version) { throw "version empty" }

$Dist = Join-Path $KitRoot "dist"
New-Item -ItemType Directory -Force -Path $Dist | Out-Null
# Release zip uses the product display name; inner folder stays tripose-kit for install paths.
$DisplayName = [string]$man.display_name
if (-not $DisplayName) { $DisplayName = "tripose-kit" }
$SafeDisplay = ($DisplayName -replace '[\\/:*?"<>|]', '-' -replace '\s+', '-')
$ZipName = "$SafeDisplay-v$Version.zip"
$ZipPath = Join-Path $Dist $ZipName
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
# Also keep a stable slug alias for scripts that expect tripose-kit-v*.zip
$AliasZipName = "tripose-kit-v$Version.zip"
$AliasZipPath = Join-Path $Dist $AliasZipName
if (Test-Path $AliasZipPath) { Remove-Item $AliasZipPath -Force }

$Stage = Join-Path $env:TEMP ("tripose-kit-pack-" + [guid]::NewGuid().ToString("N"))
$StageRoot = Join-Path $Stage "tripose-kit"
New-Item -ItemType Directory -Force -Path $StageRoot | Out-Null

$excludeDirNames = @(
    "_download", "dist", "__pycache__", ".git", ".venv", "node_modules"
)
$excludeNamePatterns = @(
    "*.bak*", "*.pyc", "*.pyo", ".DS_Store", "Thumbs.db"
)

function ShouldSkip([System.IO.FileSystemInfo]$item, [string]$rel) {
    $parts = $rel -split "[\\/]"
    foreach ($p in $parts) {
        if ($excludeDirNames -contains $p) { return $true }
    }
    foreach ($pat in $excludeNamePatterns) {
        if ($item.Name -like $pat) { return $true }
    }
    return $false
}

Get-ChildItem $KitRoot -Force | ForEach-Object {
    $name = $_.Name
    if ($name -in @("dist", "_download")) { return }
    $dest = Join-Path $StageRoot $name
    if ($_.PSIsContainer) {
        robocopy $_.FullName $dest /E /NFL /NDL /NJH /NJS /nc /ns /np `
            /XD _download dist __pycache__ .git .venv node_modules `
            /XF *.bak* *.pyc *.pyo .DS_Store Thumbs.db | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "robocopy failed for $($_.FullName) code=$LASTEXITCODE" }
    } else {
        if (ShouldSkip $_ $name) { return }
        Copy-Item $_.FullName $dest -Force
    }
}

# Ensure critical lexicons are present
$must = @(
    "maps\danbooru_zh.sqlite",
    "maps\danbooru_zh_nsfw.sqlite",
    "maps\tripose_aliases.json",
    "workflows\CF-TriPose-SDXL-template.json",
    "workflows\CF-TriPose-SDXL-single.json",
    "workflows\CF-TriPose-Anima-single.json",
    "workflows\CF-TriPose-Krea2-single.json",
    "workflows\CF-Wan22-I2V-single-frame.json",
    "custom_nodes\ComfyUI-TriPose-Utils\nodes_tagmap.py",
    "scripts\sync-to-comfy.ps1",
    "scripts\verify-install.ps1",
    "manifest.json",
    "README.md",
    "DEPENDENCIES.md"
)
foreach ($m in $must) {
    $p = Join-Path $StageRoot $m
    if (-not (Test-Path $p)) { throw "missing in stage: $m" }
}
# Chinese-named docs (avoid embedding non-ASCII paths in this .ps1 for Windows PowerShell 5)
$rootMd = @(Get-ChildItem -LiteralPath $StageRoot -File -Filter "*.md")
if ($rootMd.Count -lt 4) {
    throw "expected >=4 root markdown docs (README/DEPENDENCIES/install/agent), got $($rootMd.Count)"
}
$hasVerify = Test-Path (Join-Path $StageRoot "scripts\verify-install.ps1")
if (-not $hasVerify) { throw "missing verify-install.ps1" }

Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $ZipPath -CompressionLevel Optimal
Copy-Item $ZipPath $AliasZipPath -Force
Remove-Item $Stage -Recurse -Force

$zi = Get-Item $ZipPath
Write-Host "Display: $DisplayName"
Write-Host "Packed: $($zi.FullName)"
Write-Host "Alias:  $AliasZipPath"
Write-Host ("Size: {0:N2} MB" -f ($zi.Length / 1MB))
Write-Host "Version: $Version"
