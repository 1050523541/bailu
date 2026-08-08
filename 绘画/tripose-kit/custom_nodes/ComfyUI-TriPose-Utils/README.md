# TriPose Utils

ComfyUI 自定义节点包：中文短标签映射 + OC 设定图辅助。

## 节点

| 节点 | 用途 |
|------|------|
| `TriPoseZhTagMap` | 中文短标签 → Danbooru 英文（词典优先） |
| `TriPoseOptionalLoadImage` | 可选参考图；`(none)` = 无图 |
| `TriPoseRefSemanticDecompose` | 参考图语义拆解（WD14）；无图跳过 |
| `TriPoseIdentityMerge` | 手写 Identity ∪ 参考构成（默认手写优先） |
| `TriPoseOptionalIPAdapter` | 有有效参考图才加载并应用 IPAdapter，否则 MODEL 直通 |
| `TriPoseImageStack` | 2–3 张图拼成一张总图（row / column / grid2） |

## 安装

将本目录复制到 `ComfyUI/custom_nodes/ComfyUI-TriPose-Utils/`，并把套件 `maps/` 复制到本目录下的 `maps/`（或使用 sync 脚本）。

重启 ComfyUI 后搜索「TriPose」。

语义拆解权重放到：`ComfyUI/models/tripose_tagger/wd-swinv2-tagger-v3.onnx` + `.csv`（首次有图时可自动下载）。

## 词表

| 文件 | 说明 |
|------|------|
| `maps/danbooru_zh.sqlite` | 官方中文全库（约 25 万） |
| `maps/danbooru_zh_nsfw.sqlite` | NSFW / 口语大词库（约 11 万+） |
| `maps/tripose_aliases.json` | 模板口语覆盖（优先于 sqlite） |

工作流默认 dictionary：`danbooru_zh+nsfw`。  
旧名 `zh_danbooru*.json` 已废弃，请勿再依赖。
