# TagToolbox 前端设计锁定

## 设计源

| 代号 | 含义 |
|---|---|
| A | 词库组合 V1：左浏览 / 右组合 |
| B | 双模式壳：modebar + iframe |
| C | 分类编辑能力 |
| D | 单顶栏 + 无操作不重读 |
| E | 提示词预设管理（角色/场景/服装/动作/表情） |

## 单顶栏

- 只留外壳 modebar（安静条）
- 词库嵌入时隐藏 `app-header`；编辑器嵌入时隐藏整段 `topbar`
- 编辑操作经 `editor-chrome` / `editor-command` 上移到 modebar
- 双 iframe 缓存；编辑改库后才重建词库帧

## 提示词预设管理

入口：词库组合右侧「提示词预设管理」。

类型：`character` / `scene` / `outfit` / `action` / `expression` / `free`  
能力：另存、覆盖升版、载入、删除、导入配图（最多 4 张，本地压缩）。  
存储：`localStorage` 键 `tag-toolbox-v3:kits`，schema `tag-toolbox-preset-v1`。
