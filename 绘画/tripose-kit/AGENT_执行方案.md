# Agent 执行方案（可逐步照做）

本文给 Cursor / 其它 Agent 使用：按步骤顺序执行，每步先验证再进入下一步。  
**不要修改本套件以外的用户个人工作流，除非用户明确要求。**  
**不要编辑任何 `.plan.md` 计划文件。**  
**不要擅自重排用户已定稿的节点坐标**（套件 JSON 已与用户布局对齐）。

## 目标

在用户本机 ComfyUI 上装好本套件**共用依赖**，同步 **5 个** `CF-*.json` 工作流，并按用户要用的引擎核对模型；最后给出可 Queue 状态。

包显示名：`TriPose-SDXL-Anima-Krea2-Wan22 I2V图+视频工作流`（v1.6.1）

## 默认路径（可被用户参数覆盖）

```text
WORKSPACE = <工作区根，含 packages/tripose-kit>
COMFY_ROOT = E:\AIGC\ComfyUI-aki-v3\ComfyUI
COMFY_URL  = http://127.0.0.1:8188
PYTHON     = E:\AIGC\ComfyUI-aki-v3\python\python.exe
KIT        = {WORKSPACE}/packages/tripose-kit
```

若路径不同：先询问用户或扫描常见秋叶/官方安装位置，再继续。

## 大模型下载策略（强制）

- YOLO（`face_yolov8m.pt`，约几十 MB）与缺失的**小文件**可自动下载。  
- Anima / Krea2 / Wan 的 UNET、UMT5、完整 TE（数百 MB～十余 GB）：**先检查是否存在并汇报缺失清单 + 直链**；**未经用户明确批准不得开始下载**。  
- 禁止用 Anima 的 `qwen_3_06b_base` 顶替 Krea2 的 `qwen3vl_4b_fp8_scaled`。

---

## 步骤 0 — 只读探活

1. 确认套件内存在全部工作流：

```text
{KIT}/workflows/CF-TriPose-SDXL-template.json
{KIT}/workflows/CF-TriPose-SDXL-single.json
{KIT}/workflows/CF-TriPose-Anima-single.json
{KIT}/workflows/CF-TriPose-Krea2-single.json
{KIT}/workflows/CF-Wan22-I2V-single-frame.json
```

2. `GET {COMFY_URL}/system_stats`：若失败，提示用户先启动 ComfyUI；**不要强杀/重启进程，除非用户批准**。  
3. `GET {COMFY_URL}/object_info`，记录是否已有：

| 节点 | 用途 |
|------|------|
| `UltralyticsDetectorProvider` | 静图 Face YOLO |
| `FaceDetailer` | 静图修脸 |
| `Seed (rgthree)` | 全工作流 |
| `Power Lora Loader (rgthree)` | 全工作流 |
| `TriPoseZhTagMap` | 全工作流 |
| `TriPoseLaneEnable` | 静图开关 |
| `UNETLoader` / `CLIPLoader` / `VAELoader` | Anima/Krea2/Wan |
| `WanImageToVideo` / `CreateVideo` / `SaveVideo` | Wan I2V |

4. 可选：读设置确认 `Comfy.VueNodes.Enabled` 为 `false`（rgthree 控件兼容）；若为 true，告知用户关闭并刷新。

---

## 步骤 1 — 安装自定义节点

对下列三项，若 `{COMFY_ROOT}/custom_nodes/<名>` 不存在则 `git clone --depth 1`：

| 目录名 | URL |
|--------|-----|
| ComfyUI-Impact-Pack | https://github.com/ltdrdata/ComfyUI-Impact-Pack.git |
| ComfyUI-Impact-Subpack | https://github.com/ltdrdata/ComfyUI-Impact-Subpack.git |
| rgthree-comfy | https://github.com/rgthree/rgthree-comfy.git |

然后：

```text
{PYTHON} -m pip install -r {COMFY_ROOT}/custom_nodes/ComfyUI-Impact-Subpack/requirements.txt
```

失败且报 `cv2` 占用：说明需关闭占用进程后重试；可尝试仅 `pip install ultralytics`。

**安装 TriPose Utils + 同步五工作流 + sqlite 词库：**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "{KIT}/scripts/sync-to-comfy.ps1" -ComfyRoot "{COMFY_ROOT}" -ComfyUrl "{COMFY_URL}"
```

或手动：

- `{KIT}/custom_nodes/ComfyUI-TriPose-Utils` → `{COMFY_ROOT}/custom_nodes/ComfyUI-TriPose-Utils`
- `{KIT}/maps/*` → `{COMFY_ROOT}/custom_nodes/ComfyUI-TriPose-Utils/maps/`
- `{KIT}/workflows/CF-*.json` → `{COMFY_ROOT}/user/default/workflows/`

**若本步新装了 Subpack 或 TriPose-Utils，而步骤 0 时对应节点缺失：请求用户批准后重启 ComfyUI，再重新探活。**

---

## 步骤 2 — 下载检测模型（静图共用）

目标：`{COMFY_ROOT}/models/ultralytics/bbox/face_yolov8m.pt`

- 若不存在或体积 < 1MB：下载  
  `https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8m.pt`  
- 可选：`hand_yolov8s.pt`、`person_yolov8m-seg.pt`（见 `依赖与安装.md`）

---

## 步骤 3 — 同步工作流（若步骤 1 未跑 sync）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "{KIT}/scripts/sync-to-comfy.ps1" `
  -ComfyRoot "{COMFY_ROOT}" -ComfyUrl "{COMFY_URL}"
```

验证五个文件均在 `{COMFY_ROOT}/user/default/workflows/`，且：

- `{COMFY_ROOT}/custom_nodes/ComfyUI-TriPose-Utils/nodes_tagmap.py` 存在  
- `{COMFY_ROOT}/custom_nodes/ComfyUI-TriPose-Utils/maps/danbooru_zh.sqlite` 存在  
- `{COMFY_ROOT}/custom_nodes/ComfyUI-TriPose-Utils/maps/danbooru_zh_nsfw.sqlite` 存在  
- `{COMFY_ROOT}/custom_nodes/ComfyUI-TriPose-Utils/maps/tripose_aliases.json` 存在  

**禁止**再要求 `zh_danbooru.json`（已废弃）。

---

## 步骤 4 — 按工作流核对模型（只检查 / 经批准再下）

对用户声明要跑的工作流执行下表。默认「仅检查」：缺失则列出路径 + 链接，等待批准。

### 4A · SDXL 三态 / 单图

| 检查项 | 路径模式 |
|--------|----------|
| 至少一个全量 checkpoint | `models/checkpoints/*.safetensors`（体积合理，非 UNET-only） |
| YOLO | `models/ultralytics/bbox/face_yolov8m.pt` |

不要把 Anima/Krea2 UNET 写进 `CheckpointLoaderSimple`。

### 4B · Anima 单图

| 文件 | 路径 |
|------|------|
| `miaomiao3DHarem_animaLH3D10.safetensors`（或用户指定 Anima UNET） | `models/diffusion_models/` |
| `qwen_3_06b_base.safetensors` | `models/text_encoders/` |
| `qwen_image_vae.safetensors` | `models/vae/` |
| 可选 LoRA | `models/loras/` |

### 4C · Krea2 单图

| 文件 | 路径 | 备注 |
|------|------|------|
| `moodyKrea2Mix_cutieXEDITION.safetensors`（或用户指定） | `models/diffusion_models/` | |
| `qwen3vl_4b_fp8_scaled.safetensors` | `models/text_encoders/` | **必完整个**；直链见安装文档 |
| `qwen_image_vae.safetensors` | `models/vae/` | 可与 Anima 共用 |
| 可选 Krea2 LoRA | `models/loras/` | |

HF：`https://huggingface.co/Comfy-Org/Krea-2/resolve/main/text_encoders/qwen3vl_4b_fp8_scaled.safetensors`  
镜像：`https://hf-mirror.com/Comfy-Org/Krea-2/resolve/main/text_encoders/qwen3vl_4b_fp8_scaled.safetensors`

### 4D · Wan2.2 I2V

| 文件 | 路径 | 备注 |
|------|------|------|
| `DasiwaWAN22I2V14BLightspeed_snatchkissHighV11.safetensors` | `models/diffusion_models/` | |
| `DasiwaWAN22I2V14BLightspeed_snatchkissLowV11.safetensors` | `models/diffusion_models/` | Low≈13.5GB：https://civitai.com/api/download/models/2953485 |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `models/text_encoders/` | CLIP type=`wan` |
| `wan_2.1_vae.safetensors` | `models/vae/` | Comfy-Org Wan repackaged |

确认 **不要** 再叠 lightx2v LoRA（Lightspeed 已烘焙）。

---

## 步骤 5 — 机器自检

优先跑：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "{KIT}/scripts/verify-install.ps1" `
  -ComfyRoot "{COMFY_ROOT}" -ComfyUrl "{COMFY_URL}"
```

或按文末「一键自检命令」手工跑。

清单：

- [ ] 共用节点齐全（步骤 0 表）  
- [ ] `face_yolov8m.pt` 正常（跑静图时）  
- [ ] sqlite 词库两份 + aliases 已安装  
- [ ] 五个 `CF-*.json` 已同步  
- [ ] 用户目标引擎的模型文件存在（步骤 4）  

任一失败：回到对应步骤；**不要代用户 Queue**，除非用户要求。

---

## 步骤 6 — 换模与提示词（仅在用户要求时）

1. 打开用户指定的 `CF-*` 工作流（布局已定稿，勿重置坐标）。  
2. SDXL：Checkpoint 设为全量 `.safetensors`；中文框改 质量 / Identity / 背景 / Variant（见 `profiles/soft-gothic.zh.example.md`）。  
3. Anima/Krea2：只换 UNET（及对应 CLIP/VAE）；Power Lora 可空。  
4. Wan：换「起始图像」+ 运动中文提示；确认 Hi/Lo 成对。  
5. Seed 保持 `-1`；保持 KSampler / FaceDetailer 的 seed 槽位与 `Seed (rgthree)` 连线。  
6. **默认不要替用户点 Queue**；用户明确要求时再提交 `/prompt`。

---

## 步骤 7 — 向用户汇报

用中文简短汇报：

- 节点安装结果（新建 / 已存在）  
- 检测模型是否就绪  
- 五个工作流同步路径  
- **按引擎**列出模型 OK / 缺失（附链接）  
- 还需用户手动：选模、改提示词、Queue；大文件是否批准下载  

---

## 禁止事项

- 不把 UNET-only（Anima/Krea2/Wan）写进 SDXL `CheckpointLoaderSimple`  
- 不用错误 CLIP 顶替 Krea2 `qwen3vl_4b_fp8_scaled`  
- 不删除 seed 控件槽位导致 FaceDetailer 参数错位  
- 不在未批准时强制结束用户正在运行的 Comfy 进程  
- 不在未批准时下载 ≥100MB 的模型权重  
- 不提交含密钥的 `.env`；本套件无密钥需求  
- 不重排用户定稿布局  

---

## 一键自检命令（Agent 可跑）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "{KIT}/scripts/verify-install.ps1"
```

等价手写检查（词库已改为 sqlite）：

```powershell
$py = "E:\AIGC\ComfyUI-aki-v3\python\python.exe"
$root = "E:\AIGC\ComfyUI-aki-v3\ComfyUI"
@(
  "custom_nodes\ComfyUI-Impact-Pack",
  "custom_nodes\ComfyUI-Impact-Subpack",
  "custom_nodes\rgthree-comfy",
  "custom_nodes\ComfyUI-TriPose-Utils",
  "custom_nodes\ComfyUI-TriPose-Utils\maps\danbooru_zh.sqlite",
  "custom_nodes\ComfyUI-TriPose-Utils\maps\danbooru_zh_nsfw.sqlite",
  "custom_nodes\ComfyUI-TriPose-Utils\maps\tripose_aliases.json",
  "models\ultralytics\bbox\face_yolov8m.pt",
  "user\default\workflows\CF-TriPose-SDXL-template.json",
  "user\default\workflows\CF-TriPose-SDXL-single.json",
  "user\default\workflows\CF-TriPose-Anima-single.json",
  "user\default\workflows\CF-TriPose-Krea2-single.json",
  "user\default\workflows\CF-Wan22-I2V-single-frame.json"
) | ForEach-Object {
  $p = Join-Path $root $_
  "{0}  {1}" -f ($(if (Test-Path $p) {"OK"} else {"MISS"}), $p)
}
& $py -c "import urllib.request,json; oi=json.loads(urllib.request.urlopen('http://127.0.0.1:8188/object_info',timeout=60).read());
keys=['UltralyticsDetectorProvider','FaceDetailer','Seed (rgthree)','Power Lora Loader (rgthree)','TriPoseZhTagMap','TriPoseLaneEnable','WanImageToVideo','CreateVideo','SaveVideo'];
[print(k, k in oi) for k in keys]"
```
