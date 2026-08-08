# TriPose-SDXL-Anima-Krea2-Wan22 I2V图+视频工作流

同一套 **TriPose 中文短标签映射 + Seed 同步**，覆盖静图与 I2V：

| 工作流 | 用途 |
|--------|------|
| `CF-TriPose-SDXL-template` | SDXL **三态立绘**（正常 / 赤裸 / 事后） |
| `CF-TriPose-SDXL-single` | SDXL **单图**（定稿布局） |
| `CF-TriPose-Anima-single` | Anima **单图** |
| `CF-TriPose-Krea2-single` | Krea2 **单图** |
| `CF-Wan22-I2V-single-frame` | Wan2.2 **I2V**（单图起步） |

- 包显示名：**TriPose-SDXL-Anima-Krea2-Wan22 I2V图+视频工作流**
- 包目录：`packages/tripose-kit`（安装路径不变）
- 版本：**v1.6.1**

SDXL 三态仍是：一次 Queue 出三张同角色立绘，共用随机种子 · Identity/Variant 锁角色 · YOLO FaceDetailer · **不绑定**单一底模（任意 SDXL / Illustrious / NoobAI **全量 checkpoint**）。Anima / Krea2 / Wan 的模型与验收见 [`依赖与安装.md`](依赖与安装.md)。

## 本版 (v1.6.1)

- **五工作流布局**与本机用户定稿对齐（以套件 `workflows/CF-*.json` 为准）
- **人工 + Agent 安装**按工作流分节补齐；新增 `scripts/verify-install.ps1`
- **词库默认 `danbooru_zh+nsfw`**：`danbooru_zh.sqlite` + `danbooru_zh_nsfw.sqlite` + `tripose_aliases.json`
- **Google 整段兜底**：跑图默认开；实时预览仍不走谷歌
- **质量 / 背景独立输入**（SDXL 系）；**Power Lora**；三态 **三路开关**
- Agent：**≥100MB 权重须用户批准后再下**

## 目录说明

| 路径 | 内容 |
|------|------|
| `README.md` | 本说明 |
| `依赖与安装.md` | 中文安装：共用 + 五工作流模型/验收 |
| `AGENT_执行方案.md` | Agent 逐步执行清单 |
| `DEPENDENCIES.md` | 文档与脚本索引 |
| `manifest.json` | 机器可读依赖 |
| `workflows/CF-TriPose-SDXL-template.json` | SDXL 三态立绘 |
| `workflows/CF-TriPose-SDXL-single.json` | SDXL 单图（定稿布局） |
| `workflows/CF-TriPose-Anima-single.json` | Anima 单图 |
| `workflows/CF-TriPose-Krea2-single.json` | Krea2 单图 |
| `workflows/CF-Wan22-I2V-single-frame.json` | Wan2.2 I2V 单图框架 |
| `workflows/archive/CF-TriPose-SDXL-single-v1.0.0.json` | 单图布局存档 v1.0.0 |
| `maps/danbooru_zh.sqlite` | Danbooru 中文全库（约 25 万条） |
| `maps/danbooru_zh_nsfw.sqlite` | NSFW/口语大词库（约 11 万条，默认启用） |
| `maps/tripose_aliases.json` | 模板口语覆盖 |
| `custom_nodes/ComfyUI-TriPose-Utils/` | TagMap / LaneEnable 等 |
| `scripts/sync-to-comfy.ps1` | 同步工作流 + Utils |
| `scripts/verify-install.ps1` | 安装自检 |
| `scripts/pack-release.ps1` | 打 release zip |
| `dist/` | 版本发布包 |

## 管线结构

```text
Checkpoint → Power Lora → 三路开关(TriPoseLaneEnable)
中文短标签 → TriPoseZhTagMap（全库+NSFW大词库；无词条可 Google 兜底）→ CLIP
Identity + Variant + 质量 + 背景 ──► Concat ► KSampler ► Upscale1.5
  ► 精炼 ► VAE ► FaceDetailer ► Save
Seed(rgthree) 同步开启的各路
```

| 槽位 | 含义 | 提示词注意 |
|------|------|------------|
| 质量 | 三路共用 | 杰作/画质/光影；单独改 |
| Identity | 角色共用 | 外貌/气质；不含质量与背景 |
| 背景 | 三路共用 | 默认白底；单独改 |
| Variant1 | 正常服装 | 只写服装差分 |
| Variant2 | 赤裸 | 用「赤裸/全裸」等词；禁内衣 |
| Variant3 | 性爱事后 | **全裸 + 事后**；勿写半脱内衣 |

映射节点默认 `danbooru_zh+nsfw`：全库 + NSFW 口语大词库；`google_fallback=开` 时剩余中文整段走 Google。

## 五分钟上手

1. 按 [`依赖与安装.md`](依赖与安装.md) 安装共用节点与 YOLO，运行 `scripts/sync-to-comfy.ps1`。  
2. 跑 `scripts/verify-install.ps1` 看缺什么模型。  
3. 加载要用的 `CF-*` 工作流；按第四节补齐该引擎模型。  
4. SDXL 三态：只开「开·图1正常」校准 Identity，再三路全开。  

## 验收

- `verify-install.ps1` 共用项全 OK  
- 三态：只开图1 → 只出 `CF_TriPose_01_normal`；三路全开 → 同 seed 三张  
- 单图 / Anima / Krea2 / Wan：各自前缀出图或出视频，无缺模红错  
- 映射默认 `danbooru_zh+nsfw`  

## 打包发布

```powershell
powershell -ExecutionPolicy Bypass -File packages/tripose-kit/scripts/pack-release.ps1
```

产物（同内容两份）：

- `packages/tripose-kit/dist/TriPose-SDXL-Anima-Krea2-Wan22-I2V图+视频工作流-v1.6.1.zip`
- `packages/tripose-kit/dist/tripose-kit-v1.6.1.zip`（稳定别名）

## Agent

见 [`AGENT_执行方案.md`](AGENT_执行方案.md)。
