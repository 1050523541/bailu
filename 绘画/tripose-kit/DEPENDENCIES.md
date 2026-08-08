# 依赖文档索引

| 文档 | 用途 |
|------|------|
| **[依赖与安装.md](依赖与安装.md)** | 人工安装：共用节点/词库 + **五个工作流各自模型与验收** |
| **[AGENT_执行方案.md](AGENT_执行方案.md)** | Agent 逐步安装、大模型下载策略、分引擎核对 |
| **[manifest.json](manifest.json)** | 机器可读：工作流 / 节点 / 模型 / 词库 |
| **[README.md](README.md)** | 套件总览与打包 |

脚本：

| 脚本 | 用途 |
|------|------|
| `scripts/sync-to-comfy.ps1` | 同步 `CF-*.json` + TriPose-Utils + maps |
| `scripts/verify-install.ps1` | 安装自检（共用必检 + 各引擎模型汇报） |
| `scripts/pack-release.ps1` | 打 release zip |

词库现行为 `maps/danbooru_zh.sqlite` + `danbooru_zh_nsfw.sqlite` + `tripose_aliases.json`（旧 `zh_danbooru*.json` 已废弃）。
