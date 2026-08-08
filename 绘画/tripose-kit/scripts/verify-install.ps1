# Verify TriPose kit install against a local ComfyUI tree.
param(
    [string]$ComfyRoot = "E:\AIGC\ComfyUI-aki-v3\ComfyUI",
    [string]$ComfyUrl = "http://127.0.0.1:8188",
    [switch]$SkipApi
)

$ErrorActionPreference = "Continue"
$fail = 0

function Check-Path([string]$rel, [int]$MinBytes = 0) {
    $p = Join-Path $ComfyRoot $rel
    if (-not (Test-Path -LiteralPath $p)) {
        Write-Host "MISS  $rel"
        $script:fail++
        return
    }
    if ($MinBytes -gt 0) {
        $len = (Get-Item -LiteralPath $p).Length
        if ($len -lt $MinBytes) {
            Write-Host "SMALL $rel ($len < $MinBytes)"
            $script:fail++
            return
        }
    }
    Write-Host "OK    $rel"
}

Write-Host "=== ComfyRoot: $ComfyRoot ==="
Write-Host "--- shared nodes / lexicons / workflows ---"
@(
    "custom_nodes\ComfyUI-Impact-Pack",
    "custom_nodes\ComfyUI-Impact-Subpack",
    "custom_nodes\rgthree-comfy",
    "custom_nodes\ComfyUI-TriPose-Utils",
    "custom_nodes\ComfyUI-TriPose-Utils\nodes_tagmap.py",
    "custom_nodes\ComfyUI-TriPose-Utils\maps\danbooru_zh.sqlite",
    "custom_nodes\ComfyUI-TriPose-Utils\maps\danbooru_zh_nsfw.sqlite",
    "custom_nodes\ComfyUI-TriPose-Utils\maps\tripose_aliases.json",
    "user\default\workflows\CF-TriPose-SDXL-template.json",
    "user\default\workflows\CF-TriPose-SDXL-single.json",
    "user\default\workflows\CF-TriPose-Anima-single.json",
    "user\default\workflows\CF-TriPose-Krea2-single.json",
    "user\default\workflows\CF-Wan22-I2V-single-frame.json"
) | ForEach-Object { Check-Path $_ }

Write-Host "--- shared YOLO (still WFs) ---"
Check-Path "models\ultralytics\bbox\face_yolov8m.pt" 1000000

Write-Host "--- optional engine models (report only; missing does not fail exit) ---"
$modelChecks = @(
    @{ Rel = "models\diffusion_models\miaomiao3DHarem_animaLH3D10.safetensors"; Tag = "Anima UNET" },
    @{ Rel = "models\text_encoders\qwen_3_06b_base.safetensors"; Tag = "Anima CLIP" },
    @{ Rel = "models\vae\qwen_image_vae.safetensors"; Tag = "Qwen VAE (Anima/Krea2)" },
    @{ Rel = "models\diffusion_models\moodyKrea2Mix_cutieXEDITION.safetensors"; Tag = "Krea2 UNET" },
    @{ Rel = "models\text_encoders\qwen3vl_4b_fp8_scaled.safetensors"; Tag = "Krea2 CLIP" },
    @{ Rel = "models\diffusion_models\DasiwaWAN22I2V14BLightspeed_snatchkissHighV11.safetensors"; Tag = "Wan Hi" },
    @{ Rel = "models\diffusion_models\DasiwaWAN22I2V14BLightspeed_snatchkissLowV11.safetensors"; Tag = "Wan Lo" },
    @{ Rel = "models\text_encoders\umt5_xxl_fp8_e4m3fn_scaled.safetensors"; Tag = "Wan UMT5" },
    @{ Rel = "models\vae\wan_2.1_vae.safetensors"; Tag = "Wan VAE" }
)
foreach ($m in $modelChecks) {
    $p = Join-Path $ComfyRoot $m.Rel
    if (Test-Path -LiteralPath $p) {
        $mb = [math]::Round((Get-Item -LiteralPath $p).Length / 1MB, 1)
        Write-Host ("HAVE  [{0}] {1} ({2} MB)" -f $m.Tag, $m.Rel, $mb)
    } else {
        Write-Host ("NEED  [{0}] {1}" -f $m.Tag, $m.Rel)
    }
}

# any full checkpoint?
$ckptDir = Join-Path $ComfyRoot "models\checkpoints"
$ckpts = @()
if (Test-Path -LiteralPath $ckptDir) {
    $ckpts = Get-ChildItem -LiteralPath $ckptDir -Filter "*.safetensors" -File -ErrorAction SilentlyContinue
}
if ($ckpts.Count -gt 0) {
    Write-Host ("HAVE  [SDXL ckpt] {0} file(s) under models\checkpoints" -f $ckpts.Count)
} else {
    Write-Host "NEED  [SDXL ckpt] models\checkpoints\*.safetensors"
}

if (-not $SkipApi) {
    Write-Host "--- object_info nodes ---"
    try {
        $py = Join-Path (Split-Path (Split-Path $ComfyRoot -Parent) -Parent) "python\python.exe"
        if (-not (Test-Path $py)) {
            $py = "python"
        }
        # Prefer Comfy aki python next to Comfy root
        $akiPy = Join-Path (Split-Path $ComfyRoot -Parent) "python\python.exe"
        if (Test-Path $akiPy) { $py = $akiPy }
        $code = @"
import json, urllib.request, sys
url = sys.argv[1].rstrip('/') + '/object_info'
oi = json.loads(urllib.request.urlopen(url, timeout=90).read())
keys = [
  'UltralyticsDetectorProvider','FaceDetailer','Seed (rgthree)',
  'Power Lora Loader (rgthree)','TriPoseZhTagMap','TriPoseLaneEnable',
  'WanImageToVideo','CreateVideo','SaveVideo'
]
required = {
  'UltralyticsDetectorProvider','FaceDetailer','Seed (rgthree)',
  'Power Lora Loader (rgthree)','TriPoseZhTagMap','TriPoseLaneEnable'
}
fail = 0
for k in keys:
    has = k in oi
    print(('OK' if has else 'MISS') + '    node ' + k)
    if (not has) and k in required:
        fail += 1
sys.exit(fail)
"@
        $tmpPy = Join-Path $env:TEMP "tripose_verify_oi.py"
        Set-Content -LiteralPath $tmpPy -Value $code -Encoding UTF8
        & $py $tmpPy $ComfyUrl
        if ($LASTEXITCODE -gt 0) { $script:fail += [int]$LASTEXITCODE }
    } catch {
        Write-Host "WARN  object_info failed: $($_.Exception.Message) (is Comfy running?)"
        $script:fail++
    }
}

Write-Host "=== result: $fail required check(s) failed ==="
if ($fail -gt 0) { exit 1 } else { exit 0 }
