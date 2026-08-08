# Sync TriPose kit (5x CF-*.json + TriPose-Utils + sqlite maps) into local ComfyUI.
param(
    [string]$ComfyRoot = "E:\AIGC\ComfyUI-aki-v3\ComfyUI",
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [switch]$SkipApi,
    [switch]$SkipNodes
)

$ErrorActionPreference = "Stop"
$KitRoot = Split-Path -Parent $PSScriptRoot
$WorkflowDir = Join-Path $KitRoot "workflows"
$DestDir = Join-Path $ComfyRoot "user\default\workflows"
$NodeSrc = Join-Path $KitRoot "custom_nodes\ComfyUI-TriPose-Utils"
$MapsSrc = Join-Path $KitRoot "maps"
$NodeDest = Join-Path $ComfyRoot "custom_nodes\ComfyUI-TriPose-Utils"

if (-not (Test-Path $WorkflowDir)) {
    throw "Workflows folder not found: $WorkflowDir"
}
New-Item -ItemType Directory -Force -Path $DestDir | Out-Null

# --- workflows (canonical CF-*.json only; skip bak / archive) ---
$workflowFiles = Get-ChildItem $WorkflowDir -Filter "CF-*.json" -File
if (-not $workflowFiles) { throw "No CF-*.json under $WorkflowDir" }
foreach ($wf in $workflowFiles) {
    $dest = Join-Path $DestDir $wf.Name
    Copy-Item $wf.FullName $dest -Force
    Write-Host "copied $($wf.Name) -> $dest"

    if (-not $SkipApi) {
        try {
            $bytes = [System.IO.File]::ReadAllBytes($wf.FullName)
            $url = $ComfyUrl.TrimEnd('/') + "/api/userdata/" + [uri]::EscapeDataString("workflows/" + $wf.Name)
            Invoke-RestMethod -Uri $url -Method Post -ContentType "application/json" -Body $bytes -TimeoutSec 30 | Out-Null
            Write-Host "synced API $($wf.Name)"
        }
        catch {
            Write-Warning "API sync failed for $($wf.Name): $($_.Exception.Message) (file copy still ok)"
        }
    }
}

# --- custom node + maps ---
if (-not $SkipNodes) {
    if (-not (Test-Path $NodeSrc)) {
        throw "TriPose utils missing: $NodeSrc"
    }
    New-Item -ItemType Directory -Force -Path $NodeDest | Out-Null
    Copy-Item (Join-Path $NodeSrc "*") $NodeDest -Recurse -Force
    $mapsDest = Join-Path $NodeDest "maps"
    New-Item -ItemType Directory -Force -Path $mapsDest | Out-Null
    foreach ($mapName in @(
            "danbooru_zh.sqlite",
            "danbooru_zh_nsfw.sqlite",
            "danbooru_zh_nsfw.json",
            "tripose_aliases.json",
            "README_lexicon.md"
        )) {
        $srcMap = Join-Path $MapsSrc $mapName
        if (Test-Path -LiteralPath $srcMap) {
            Copy-Item -LiteralPath $srcMap (Join-Path $mapsDest $mapName) -Force
        }
    }
    Write-Host "installed ComfyUI-TriPose-Utils + maps -> $NodeDest"
    Write-Host "Restart ComfyUI if TriPoseZhTagMap is not in the node list yet."
}

Write-Host "Done. Reload workflows in ComfyUI."
