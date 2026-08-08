# -*- coding: utf-8 -*-
"""TriPoseZhTagMap: Chinese short tags -> Danbooru English.

Lookup order (dictionary=danbooru_zh+nsfw, default):
1) danbooru_zh.sqlite (~25万+ official cn_name)
2) danbooru_zh_nsfw.sqlite (~11万 NSFW/口语大词库, ~12MB)
3) tripose_aliases.json (模板口语覆盖)
4) custom_path JSON
5) optional Google whole-segment fallback
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
from typing import Dict, List, Optional, Tuple

NODE_DIR = os.path.dirname(os.path.abspath(__file__))
MAPS_DIR = os.path.join(NODE_DIR, "maps")

KIT_MAPS_CANDIDATES = [
    MAPS_DIR,
    os.path.normpath(os.path.join(NODE_DIR, "..", "..", "maps")),
]

_SPLIT_RE = re.compile(r"[,，、\n]+")
_LATIN_TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-_'()/:+.]*$")

_LEXICON_LOCK = threading.Lock()
_LEXICON_CACHE: Optional[Dict[str, str]] = None
_LEXICON_META = {"path": "", "entries": 0}

_NSFW_LOCK = threading.Lock()
_NSFW_CACHE: Optional[Dict[str, str]] = None
_NSFW_META = {"path": "", "entries": 0}


def _find_maps_dir() -> str:
    # Prefer a maps dir that actually contains curated JSON / sqlite.
    for d in KIT_MAPS_CANDIDATES:
        if os.path.isfile(os.path.join(d, "danbooru_zh.sqlite")):
            return d
        if os.path.isfile(os.path.join(d, "zh_danbooru.json")):
            return d
    for d in KIT_MAPS_CANDIDATES:
        if os.path.isdir(d):
            return d
    return MAPS_DIR


def _find_lexicon_sqlite() -> str:
    for d in KIT_MAPS_CANDIDATES:
        if not os.path.isdir(d):
            continue
        for name in ("danbooru_zh.sqlite", "tag.sqlite"):
            path = os.path.join(d, name)
            if os.path.isfile(path) and os.path.getsize(path) > 1024 * 1024:
                return path
    return ""


def _find_nsfw_sqlite() -> str:
    for d in KIT_MAPS_CANDIDATES:
        path = os.path.join(d, "danbooru_zh_nsfw.sqlite")
        if os.path.isfile(path) and os.path.getsize(path) > 1024 * 1024:
            return path
    return ""


def _load_json(path: str) -> Dict[str, str]:
    if not path or not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"dictionary must be a JSON object: {path}")
    out = {}
    for k, v in data.items():
        if str(k).startswith("_"):
            continue
        if isinstance(v, str):
            out[str(k).strip()] = v.strip()
    return out


def _en_tag(name: str) -> str:
    # CLIP prompts usually use spaces; keep danbooru underscores as spaces.
    return str(name).replace("_", " ").strip()


def _load_danbooru_zh_lexicon() -> Dict[str, str]:
    """Build cn_name -> english tag map from ffdkj-style sqlite (cached)."""
    global _LEXICON_CACHE
    if _LEXICON_CACHE is not None:
        return _LEXICON_CACHE

    with _LEXICON_LOCK:
        if _LEXICON_CACHE is not None:
            return _LEXICON_CACHE

        path = _find_lexicon_sqlite()
        out: Dict[str, str] = {}
        best: Dict[str, Tuple[int, str]] = {}
        if not path:
            _LEXICON_CACHE = out
            _LEXICON_META.update({"path": "", "entries": 0})
            return out

        con = sqlite3.connect(path)
        try:
            cur = con.cursor()
            # name, category, cn_name, post_count
            for name, _cat, cn_name, post_count in cur.execute(
                "SELECT name, category, cn_name, post_count FROM tags "
                "WHERE cn_name IS NOT NULL AND cn_name != ''"
            ):
                if not name or not cn_name:
                    continue
                en = _en_tag(name)
                pc = int(post_count or 0)
                # cn_name may contain comma-separated aliases
                parts = [cn_name.strip()] + _split_tags(cn_name)
                for raw in parts:
                    key = raw.strip()
                    if not key:
                        continue
                    # Skip pure latin cn_name noise
                    if _LATIN_TAG_RE.match(key) and not any(
                        "\u4e00" <= ch <= "\u9fff" for ch in key
                    ):
                        continue
                    prev = best.get(key)
                    if prev is None or pc > prev[0]:
                        best[key] = (pc, en)
                    nk = _normalize_key(key)
                    if nk and nk != key:
                        prev_n = best.get(nk)
                        if prev_n is None or pc > prev_n[0]:
                            best[nk] = (pc, en)
        finally:
            con.close()

        out = {k: v[1] for k, v in best.items()}
        _LEXICON_CACHE = out
        _LEXICON_META.update({"path": path, "entries": len(out)})
        return out


def _load_nsfw_lexicon() -> Dict[str, str]:
    """Large NSFW/spoken zh→en pack (danbooru_zh_nsfw.sqlite, 10万+)."""
    global _NSFW_CACHE
    if _NSFW_CACHE is not None:
        return _NSFW_CACHE

    with _NSFW_LOCK:
        if _NSFW_CACHE is not None:
            return _NSFW_CACHE

        path = _find_nsfw_sqlite()
        out: Dict[str, str] = {}
        if not path:
            _NSFW_CACHE = out
            _NSFW_META.update({"path": "", "entries": 0})
            return out

        con = sqlite3.connect(path)
        try:
            for cn_name, name, _pc in con.execute(
                "SELECT cn_name, name, post_count FROM tags "
                "WHERE cn_name IS NOT NULL AND cn_name != '' AND name IS NOT NULL"
            ):
                key = str(cn_name).strip()
                en = _en_tag(name)
                if not key or not en:
                    continue
                out[key] = en
                nk = _normalize_key(key)
                if nk and nk != key:
                    out[nk] = en
        finally:
            con.close()

        _NSFW_CACHE = out
        _NSFW_META.update({"path": path, "entries": len(out)})
        return out


def lexicon_info() -> Dict[str, object]:
    _load_danbooru_zh_lexicon()
    _load_nsfw_lexicon()
    info = dict(_LEXICON_META)
    info["nsfw"] = dict(_NSFW_META)
    return info


def _dict_wants_nsfw(dictionary: str) -> bool:
    return dictionary in (
        "danbooru_zh+nsfw",
        "zh_danbooru+nsfw",
        "zh_danbooru+design+nsfw",
        "zh_danbooru.nsfw",
    )


def _kit_files_for(dictionary: str, maps: str) -> List[str]:
    """JSON overlays only (spoken aliases). NSFW bulk is danbooru_zh_nsfw.sqlite."""
    if dictionary == "custom":
        return []
    files: List[str] = []
    aliases = os.path.join(maps, "tripose_aliases.json")
    if os.path.isfile(aliases):
        files.append(aliases)
    return files


def _resolve_dictionaries(dictionary: str, custom_path: str) -> Dict[str, str]:
    """Full merged table (lexicon + overlays unless custom-only)."""
    return _resolve_dictionaries_ex(dictionary, custom_path, include_lexicon=True)


def _resolve_dictionaries_ex(
    dictionary: str,
    custom_path: str,
    include_lexicon: bool = True,
) -> Dict[str, str]:
    merged: Dict[str, str] = {}

    if dictionary == "custom":
        if custom_path.strip():
            merged.update(_load_json(custom_path.strip()))
        return merged

    if include_lexicon:
        merged.update(_load_danbooru_zh_lexicon())
    if _dict_wants_nsfw(dictionary):
        # NSFW/spoken large pack overwrites official cn_name on conflict.
        merged.update(_load_nsfw_lexicon())
    # Small TriPose spoken aliases last among kit files.
    merged.update(_load_kit_aliases(dictionary))

    if custom_path.strip():
        merged.update(_load_json(custom_path.strip()))

    return merged


def _normalize_key(s: str) -> str:
    return re.sub(r"\s+", "", s.strip())


def _split_tags(text: str) -> List[str]:
    parts = _SPLIT_RE.split(text or "")
    return [p.strip() for p in parts if p.strip()]


def _expand_value(val: str) -> List[str]:
    return [x.strip() for x in _SPLIT_RE.split(val) if x.strip()]


_GOOGLE_CACHE: Dict[str, str] = {}

# Tiny built-in aliases for compounds / quality words missing as exact lexicon keys.
# Full spoken pack lives in maps/tripose_aliases.json (loaded by _load_kit_aliases).
_BUILTIN_ALIASES: Dict[str, str] = {
    "杰作": "masterpiece",
    "最佳质量": "best quality",
    "超高清": "absurdres",
    "高细节": "highly detailed",
    "黑色双马尾": "black hair, twintails",
    "哥特洛丽塔短裙": "gothic lolita dress, short dress",
    "哥特洛丽塔": "gothic lolita",
}

_KIT_ALIAS_CACHE: Dict[str, Dict[str, str]] = {}


def _load_kit_aliases(dictionary: str = "danbooru_zh+nsfw") -> Dict[str, str]:
    if dictionary in _KIT_ALIAS_CACHE:
        return _KIT_ALIAS_CACHE[dictionary]
    maps = _find_maps_dir()
    out: Dict[str, str] = dict(_BUILTIN_ALIASES)
    for path in _kit_files_for(dictionary, maps):
        out.update(_load_json(path))
    _KIT_ALIAS_CACHE[dictionary] = out
    return out


def _google_translate_segment(seg: str) -> str:
    """Fallback: free-text zh→en via AlekPet GoogleTranslate / googletrans (cached)."""
    seg = (seg or "").strip()
    if not seg:
        return ""
    if seg in _GOOGLE_CACHE:
        return _GOOGLE_CACHE[seg]
    out_text = ""
    try:
        from GoogleTranslateNode.google_translate_node import translate as _gt

        out = _gt(seg, "zh-cn", "en")
        if out and str(out).strip():
            out_text = str(out).strip()
    except Exception:
        pass
    if not out_text:
        try:
            from googletrans import Translator

            out = Translator().translate(seg, src="zh-cn", dest="en")
            out_text = (getattr(out, "text", None) or str(out)).strip()
        except Exception:
            out_text = ""
    _GOOGLE_CACHE[seg] = out_text
    return out_text


def _forward_max_match(
    seg: str, lookup: Dict[str, str], min_len: int = 2, max_len: int = 16
) -> Tuple[List[str], List[str]]:
    """Greedy Chinese longest-match against lexicon keys."""
    s = seg.strip()
    n = len(s)
    i = 0
    hits: List[str] = []
    unknowns: List[str] = []

    def piece_hit(piece: str) -> Optional[str]:
        if piece in lookup:
            return lookup[piece]
        nk = _normalize_key(piece)
        if nk in lookup:
            return lookup[nk]
        return None

    while i < n:
        matched_val = None
        matched_len = 0
        upper = min(n, i + max_len)
        for j in range(upper, i, -1):
            piece = s[i:j]
            if len(piece) < min_len:
                continue
            val = piece_hit(piece)
            if val is not None:
                matched_val = val
                matched_len = j - i
                break
        if matched_val is not None:
            hits.extend(_expand_value(matched_val))
            i += matched_len
            continue

        start = i
        i += 1
        while i < n:
            # stop unknown span when a lexicon match can start here
            can = False
            upper = min(n, i + max_len)
            for j in range(upper, i, -1):
                piece = s[i:j]
                if len(piece) < min_len:
                    continue
                if piece_hit(piece) is not None:
                    can = True
                    break
            if can:
                break
            i += 1
        unknowns.append(s[start:i])

    return hits, unknowns


def map_tags(
    text: str,
    table: Dict[str, str],
    keep_unknown: str = "keep",
    passthrough_english: bool = True,
    google_fallback: bool = False,
) -> Tuple[str, str]:
    lookup: Dict[str, str] = {}
    for k, v in table.items():
        lookup[k] = v
        lookup[_normalize_key(k)] = v

    mapped: List[str] = []
    unmapped: List[str] = []
    seen = set()

    def add_tags(tags: List[str]):
        for t in tags:
            key = t.lower()
            if key in seen:
                continue
            seen.add(key)
            mapped.append(t)

    for seg in _split_tags(text):
        hit = None
        if seg in lookup:
            hit = lookup[seg]
        else:
            nk = _normalize_key(seg)
            if nk in lookup:
                hit = lookup[nk]

        if hit is not None:
            add_tags(_expand_value(hit))
            continue

        if passthrough_english and _LATIN_TAG_RE.match(seg):
            add_tags([seg])
            continue

        # Prefer whole-segment Google over greedy split (split leaves 角上/蓝/粉 scraps).
        if google_fallback:
            translated = _google_translate_segment(seg)
            if translated:
                add_tags(_expand_value(translated))
                continue
            unmapped.append(seg)
            if keep_unknown == "keep":
                add_tags([seg])
            continue

        # Offline only: optional longest-match for compounds, then keep leftovers.
        partial_hits, unknown_chunks = _forward_max_match(seg, lookup)
        add_tags(partial_hits)
        if not unknown_chunks and not partial_hits:
            unknown_chunks = [seg]
        for chunk in unknown_chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            unmapped.append(chunk)
            if keep_unknown == "keep":
                add_tags([chunk])

    return ", ".join(mapped), ", ".join(unmapped)


_VALID_DICTS = {
    "danbooru_zh+nsfw",
    "danbooru_zh",
    "custom",
    # legacy names
    "zh_danbooru+nsfw",
    "zh_danbooru+design",
    "zh_danbooru+design+nsfw",
    "zh_danbooru",
    "zh_danbooru.design",
    "zh_danbooru.nsfw",
}

_DEFAULT_DICT = "danbooru_zh+nsfw"


def _normalize_dictionary(dictionary: str) -> str:
    if dictionary == "custom":
        return "custom"
    if dictionary in ("danbooru_zh", "zh_danbooru", "zh_danbooru+design", "zh_danbooru.design"):
        return "danbooru_zh"
    # Anything NSFW / unknown kit name → default NSFW pack on
    return _DEFAULT_DICT


def _coerce_options(dictionary, custom_path, keep_unknown):
    if dictionary not in _VALID_DICTS:
        dictionary = _DEFAULT_DICT
    dictionary = _normalize_dictionary(dictionary)
    if keep_unknown not in ("keep", "drop"):
        if isinstance(custom_path, str) and custom_path in ("keep", "drop"):
            keep_unknown = custom_path
            custom_path = ""
        else:
            keep_unknown = "keep"
    if not isinstance(custom_path, str):
        custom_path = ""
    return dictionary, custom_path, keep_unknown


class TriPoseZhTagMap:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "forceInput": True,
                        "multiline": True,
                        "default": "",
                        "dynamicPrompts": False,
                        "tooltip": "Connect from a text Primitive. Edit Chinese only upstream.",
                    },
                ),
                "dictionary": (
                    ["danbooru_zh+nsfw", "danbooru_zh", "custom"],
                    {
                        "default": "danbooru_zh+nsfw",
                        "tooltip": "默认 danbooru_zh+nsfw=全库25万+NSFW口语大词库11万；danbooru_zh=仅全库+模板口语",
                    },
                ),
                "custom_path": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "可选：额外 JSON 覆盖；dictionary=custom 时仅用此文件",
                    },
                ),
                "keep_unknown": (["keep", "drop"], {"default": "keep"}),
                "passthrough_english": (
                    "BOOLEAN",
                    {"default": True, "label_on": "yes", "label_off": "no"},
                ),
            },
            "optional": {
                "google_fallback": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "label_on": "开",
                        "label_off": "关",
                        "tooltip": "词库/口语表未命中时整段 Google 译英（有缓存）。预览仍不走谷歌",
                    },
                ),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("mapped_text", "unmapped_text")
    FUNCTION = "map_text"
    CATEGORY = "TriPose"
    OUTPUT_NODE = True
    DESCRIPTION = (
        "Map Chinese tags: danbooru_zh.sqlite + danbooru_zh_nsfw.sqlite "
        "(default) + tripose_aliases.json, then optional Google fallback."
    )

    @classmethod
    def VALIDATE_INPUTS(cls, dictionary=None, keep_unknown=None, custom_path=None, **kwargs):
        # Tolerate widget-slot shift from older workflow JSON; coerce in map_text.
        return True

    def map_text(
        self,
        text,
        dictionary,
        custom_path,
        keep_unknown,
        passthrough_english,
        google_fallback=True,
        unique_id=None,
        extra_pnginfo=None,
    ):
        dictionary, custom_path, keep_unknown = _coerce_options(
            dictionary, custom_path, keep_unknown
        )
        table = _resolve_dictionaries(dictionary, custom_path)
        mapped, unmapped = map_tags(
            text,
            table,
            keep_unknown,
            passthrough_english,
            google_fallback=bool(google_fallback),
        )

        if extra_pnginfo and unique_id and isinstance(extra_pnginfo, dict):
            workflow = extra_pnginfo.get("workflow")
            if isinstance(workflow, dict):
                for node in workflow.get("nodes", []):
                    if str(node.get("id")) == str(unique_id):
                        vals = list(node.get("widgets_values") or [])
                        if len(vals) >= 2 and isinstance(vals[-1], str) and isinstance(
                            vals[-2], str
                        ):
                            vals[-2], vals[-1] = mapped, unmapped
                        else:
                            vals.extend([mapped, unmapped])
                        node["widgets_values"] = vals
                        break

        return {
            "ui": {
                "mapped_text": [mapped],
                "unmapped_text": [unmapped],
            },
            "result": (mapped, unmapped),
        }


NODE_CLASS_MAPPINGS = {
    "TriPoseZhTagMap": TriPoseZhTagMap,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TriPoseZhTagMap": "TriPose 中文短标签映射",
}
