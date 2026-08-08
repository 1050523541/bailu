# Danbooru zh lexicon + NSFW large pack + TriPose aliases

| File | Role | Scale |
|------|------|-------|
| `danbooru_zh.sqlite` | Official `cn_name` → English (ffdkj) | ~31MB / 25万+ |
| `danbooru_zh_nsfw.sqlite` | NSFW/口语大词库（默认启用） | ~12MB / **11万+** |
| `tripose_aliases.json` | TriPose 模板口语覆盖 | 小 |
| `danbooru_zh_nsfw.json` | 仅指针，不是词库本体 | — |

## 默认词典 `danbooru_zh+nsfw`

1. 全库 sqlite  
2. NSFW 大词库 sqlite（覆盖冲突键，含社区口语译名）  
3. `tripose_aliases.json`  
4. optional `custom_path`  
5. Google 整段兜底（跑图；预览不开）

NSFW 包来源：本机全库宽抽成人向 + BooruTagCart `danbooru_all.csv` + Yellow-Rush 中文对照 + 口语同义词。

重建：

```text
python packages/tripose-kit/scripts/build-nsfw-lexicon.py
```

（需已下载 `maps/_download/*.csv`）
