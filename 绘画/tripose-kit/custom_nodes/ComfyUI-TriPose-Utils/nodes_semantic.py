# -*- coding: utf-8 -*-
"""Reference-image semantic decompose + Identity merge for OC Design."""
from __future__ import annotations

import csv
import os
import re
import urllib.request
from typing import Dict, List, Optional, Sequence, Set, Tuple

import folder_paths
import numpy as np
import torch
from PIL import Image

from .nodes_oc import _has_valid_image

# ---------------------------------------------------------------------------
# Model paths / download
# ---------------------------------------------------------------------------

_MODEL_REPO = "SmilingWolf/wd-swinv2-tagger-v3"
_MODEL_FILES = {
    "onnx": "model.onnx",
    "csv": "selected_tags.csv",
}
_DEFAULT_MODEL_KEY = "wd-swinv2-tagger-v3"

_session_cache = {}
_tags_cache = {}


def _models_dir() -> str:
    base = os.path.join(folder_paths.models_dir, "tripose_tagger")
    os.makedirs(base, exist_ok=True)
    return base


def _model_paths(model_key: str = _DEFAULT_MODEL_KEY) -> Tuple[str, str]:
    d = _models_dir()
    return (
        os.path.join(d, f"{model_key}.onnx"),
        os.path.join(d, f"{model_key}.csv"),
    )


def _download_file(url: str, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    mirrors = [url]
    if url.startswith("https://huggingface.co/"):
        mirrors.append(url.replace("https://huggingface.co/", "https://hf-mirror.com/", 1))
    last_err = None
    for u in mirrors:
        try:
            urllib.request.urlretrieve(u, tmp)
            os.replace(tmp, dest)
            return
        except Exception as e:
            last_err = e
            if os.path.isfile(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
    raise RuntimeError(f"download failed: {url} ({last_err})")


def ensure_tagger_model(model_key: str = _DEFAULT_MODEL_KEY) -> Tuple[str, str]:
    onnx_path, csv_path = _model_paths(model_key)
    base = f"https://huggingface.co/{_MODEL_REPO}/resolve/main"
    if not os.path.isfile(onnx_path):
        _download_file(f"{base}/{_MODEL_FILES['onnx']}", onnx_path)
    if not os.path.isfile(csv_path):
        _download_file(f"{base}/{_MODEL_FILES['csv']}", csv_path)
    return onnx_path, csv_path


def _get_session(onnx_path: str):
    if onnx_path in _session_cache:
        return _session_cache[onnx_path]
    import onnxruntime as ort

    # CPU is enough for one-shot tagging and avoids CUDA EP DLL mismatches
    sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    _session_cache[onnx_path] = sess
    return sess


def _load_tag_rows(csv_path: str) -> List[Tuple[str, int]]:
    if csv_path in _tags_cache:
        return _tags_cache[csv_path]
    rows: List[Tuple[str, int]] = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for row in reader:
            if len(row) < 3:
                continue
            name = row[1]
            try:
                category = int(row[2])
            except ValueError:
                category = 0
            rows.append((name, category))
    _tags_cache[csv_path] = rows
    return rows


# ---------------------------------------------------------------------------
# Slot taxonomy / filtering
# ---------------------------------------------------------------------------

# Exact deny (pose / camera / bg / meta / quality clutter)
_DENY_EXACT = {
    "solo",
    "1girl",
    "1boy",
    "2girls",
    "multiple girls",
    "looking at viewer",
    "looking away",
    "looking to the side",
    "from above",
    "from below",
    "from behind",
    "from side",
    "side view",
    "back view",
    "front view",
    "cowboy shot",
    "upper body",
    "lower body",
    "close-up",
    "portrait",
    "full body",
    "standing",
    "sitting",
    "kneeling",
    "lying",
    "walking",
    "running",
    "arms up",
    "arms behind back",
    "hand up",
    "hand on hip",
    "hands on hips",
    "outdoors",
    "indoors",
    "sky",
    "cloud",
    "clouds",
    "tree",
    "trees",
    "grass",
    "water",
    "ocean",
    "beach",
    "city",
    "building",
    "window",
    "bed",
    "chair",
    "table",
    "simple background",
    "white background",
    "grey background",
    "gray background",
    "blue background",
    "gradient background",
    "blurry background",
    "detailed background",
    "scenery",
    "sky",
    "cloud",
    "clouds",
    "day",
    "night",
    "sunset",
    "blue sky",
    "flat color",
    "cel shading",
    "monochrome",
    "greyscale",
    "grayscale",
    "depth of field",
    "bokeh",
    "lens flare",
    "cinematic lighting",
    "dramatic lighting",
    "shadow",
    "facing viewer",
    "dutch angle",
    "foreshortening",
    "artist name",
    "signature",
    "watermark",
    "username",
    "patreon logo",
    "commission",
    "english text",
    "speech bubble",
    "comic",
    "manga",
    "panel",
    "border",
    "framed",
    "photo",
    "realistic",
    "photorealistic",
    "3d",
    "rating:safe",
    "rating:questionable",
    "rating:explicit",
    "general",
    "sensitive",
    "questionable",
    "explicit",
}

_DENY_CONTAINS = (
    "background",
    "viewpoint",
    "angle",
    "perspective",
    "camera",
    "blurry",
    "motion blur",
    "depth of field",
    "cowboy shot",
    "looking ",
    "arms ",
    "hand ",
    "hands ",
    "sitting",
    "standing",
    "kneeling",
    "lying",
    "outdoors",
    "indoors",
    "scenery",
    " sky",
    "sky ",
    "cloud",
    "flat color",
    "monochrome",
)

# Prefer keeping composition-related tags (hair / eyes / clothes / species / accessories)
_KEEP_KEYWORDS = (
    "hair",
    "bangs",
    "ahoge",
    "twintail",
    "ponytail",
    "braid",
    "eye",
    "eyes",
    "pupil",
    "eyelashes",
    "eyebrow",
    "mole",
    "freckle",
    "fang",
    "teeth",
    "lip",
    "skin",
    "pale",
    "tan",
    "dark skin",
    "horn",
    "horns",
    "wing",
    "wings",
    "tail",
    "ears",
    "animal ear",
    "fox ear",
    "cat ear",
    "elf",
    "demon",
    "angel",
    "halo",
    "dress",
    "skirt",
    "shirt",
    "blouse",
    "jacket",
    "coat",
    "hoodie",
    "uniform",
    "armor",
    "kimono",
    "lingerie",
    "pantyhose",
    "thighhigh",
    "boots",
    "shoes",
    "gloves",
    "ribbon",
    "bow",
    "choker",
    "necklace",
    "earring",
    "jewelry",
    "bracelet",
    "brooch",
    "flower",
    "rose",
    "butterfly",
    "gem",
    "jewel",
    "frill",
    "lace",
    "corset",
    "cape",
    "cloak",
    "veil",
    "hat",
    "crown",
    "tiara",
    "mask",
    "tattoo",
    "scar",
    "nail",
    "makeup",
    "lipstick",
    "clothing",
    "clothes",
    "outfit",
    "sleeves",
    "collar",
    "belt",
    "zipper",
    "button",
    "pattern",
    "stripe",
    "plaid",
    "checkered",
    "color",
    "coloured",
    "colored",
    "white",
    "black",
    "blue",
    "red",
    "pink",
    "purple",
    "violet",
    "green",
    "yellow",
    "silver",
    "gold",
    "blonde",
    "brunette",
    "aqua",
    "teal",
    "lavender",
    "multicolored",
    "gradient",
)

# Mutex groups: if user already has any tag in group, drop ref tags in same group
_MUTEX_GROUPS: Dict[str, Tuple[str, ...]] = {
    "hair_color": (
        "white hair",
        "black hair",
        "blonde hair",
        "brown hair",
        "red hair",
        "pink hair",
        "blue hair",
        "purple hair",
        "green hair",
        "grey hair",
        "gray hair",
        "silver hair",
        "orange hair",
        "aqua hair",
        "multicolored hair",
        "gradient hair",
    ),
    "eye_color": (
        "blue eyes",
        "red eyes",
        "green eyes",
        "brown eyes",
        "purple eyes",
        "pink eyes",
        "yellow eyes",
        "orange eyes",
        "grey eyes",
        "gray eyes",
        "heterochromia",
        "aqua eyes",
        "violet eyes",
    ),
    "hair_length": (
        "very long hair",
        "long hair",
        "medium hair",
        "short hair",
        "very short hair",
        "bald",
    ),
}


def _norm_tag(t: str) -> str:
    t = t.strip().lower().replace("_", " ")
    t = re.sub(r"\s+", " ", t)
    return t


def _split_tags(text: str) -> List[str]:
    parts = re.split(r"[,，、\n]+", text or "")
    out = []
    seen = set()
    for p in parts:
        n = _norm_tag(p)
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


def _is_denied(tag: str) -> bool:
    if tag in _DENY_EXACT:
        return True
    if tag.endswith(" sky") or tag == "sky" or "cloud" in tag:
        return True
    for frag in _DENY_CONTAINS:
        if frag in tag:
            return True
    # ratings
    if tag.startswith("rating:"):
        return True
    return False


def _is_composition(tag: str) -> bool:
    if _is_denied(tag):
        return False
    # character category often useful as-is but skip if looks like series name only — keep general composition
    for kw in _KEEP_KEYWORDS:
        if kw in tag:
            return True
    # short color+noun patterns already covered; allow bare accessory-ish tokens
    return False


def _tensor_to_pil(image: torch.Tensor) -> Image.Image:
    arr = (image[0].detach().cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def _run_wd14(
    pil: Image.Image,
    threshold: float = 0.35,
    character_threshold: float = 0.85,
    model_key: str = _DEFAULT_MODEL_KEY,
) -> List[Tuple[str, float, int]]:
    onnx_path, csv_path = ensure_tagger_model(model_key)
    sess = _get_session(onnx_path)
    rows = _load_tag_rows(csv_path)

    inp = sess.get_inputs()[0]
    # shape often [1, size, size, 3]
    height = int(inp.shape[1] if isinstance(inp.shape[1], int) else inp.shape[2])
    if not isinstance(height, int) or height <= 0:
        height = 448

    ratio = float(height) / max(pil.size)
    new_size = (max(1, int(pil.size[0] * ratio)), max(1, int(pil.size[1] * ratio)))
    resized = pil.resize(new_size, Image.Resampling.LANCZOS)
    square = Image.new("RGB", (height, height), (255, 255, 255))
    square.paste(resized, ((height - new_size[0]) // 2, (height - new_size[1]) // 2))

    arr = np.asarray(square).astype(np.float32)[:, :, ::-1]  # RGB->BGR
    arr = np.expand_dims(arr, 0)

    out_name = sess.get_outputs()[0].name
    probs = sess.run([out_name], {inp.name: arr})[0][0]

    scored: List[Tuple[str, float, int]] = []
    for (name, category), p in zip(rows, probs):
        tag = _norm_tag(name)
        thr = character_threshold if category == 4 else threshold
        if float(p) >= thr:
            scored.append((tag, float(p), int(category)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def decompose_tags(
    scored: Sequence[Tuple[str, float, int]],
    max_tags: int = 48,
) -> Tuple[str, Dict[str, List[str]]]:
    slots: Dict[str, List[str]] = {
        "hair": [],
        "eyes_face": [],
        "species": [],
        "outfit": [],
        "accessories": [],
        "other": [],
    }
    kept: List[str] = []
    for tag, _p, cat in scored:
        # skip character names by default (category 4) — they fight OC inventiveness
        if cat == 4:
            continue
        # skip rating categories (usually first few)
        if cat == 9:
            continue
        if not _is_composition(tag):
            continue
        if tag in kept:
            continue
        kept.append(tag)
        if any(k in tag for k in ("hair", "bangs", "ahoge", "twintail", "ponytail", "braid")):
            slots["hair"].append(tag)
        elif any(k in tag for k in ("eye", "pupil", "eyelash", "eyebrow", "mole", "fang", "lip", "makeup")):
            slots["eyes_face"].append(tag)
        elif any(k in tag for k in ("horn", "wing", "tail", "ear", "elf", "demon", "angel", "halo", "animal")):
            slots["species"].append(tag)
        elif any(
            k in tag
            for k in (
                "dress",
                "skirt",
                "shirt",
                "jacket",
                "coat",
                "hoodie",
                "uniform",
                "armor",
                "kimono",
                "clothes",
                "clothing",
                "sleeve",
                "pantyhose",
                "thighhigh",
                "boot",
                "shoe",
                "glove",
                "cape",
                "cloak",
                "frill",
                "lace",
                "corset",
            )
        ):
            slots["outfit"].append(tag)
        elif any(
            k in tag
            for k in (
                "ribbon",
                "bow",
                "choker",
                "necklace",
                "earring",
                "jewelry",
                "bracelet",
                "flower",
                "rose",
                "butterfly",
                "gem",
                "hat",
                "crown",
                "tiara",
                "brooch",
            )
        ):
            slots["accessories"].append(tag)
        else:
            slots["other"].append(tag)
        if len(kept) >= max_tags:
            break

    # ordered dump by slot priority
    ordered: List[str] = []
    for key in ("hair", "eyes_face", "species", "outfit", "accessories", "other"):
        for t in slots[key]:
            if t not in ordered:
                ordered.append(t)
    return ", ".join(ordered), slots


def merge_identity(
    quality_text: str,
    character_text: str,
    ref_text: str,
    has_image: bool,
    mode: str = "auto_split",
) -> Tuple[str, str]:
    """Split Identity: quality always; character only when no ref; ref replaces character when present.

    mode:
      - auto_split (recommended): no image → quality+character; has image → quality+ref ONLY
      - auto_ref_main: legacy soft merge (quality+ref+character overrides)
      - user_priority / ref_priority / user_only / ref_only
    """
    quality = _split_tags(quality_text)
    character = _split_tags(character_text)
    # also accept legacy single-blob in character_text that includes quality
    user = _split_tags((quality_text + ", " + character_text).strip(", "))

    ref = (
        [t for t in _split_tags(ref_text) if _is_composition(t)]
        if has_image
        else []
    )

    _QUALITY = {
        "masterpiece",
        "best quality",
        "highres",
        "absurdres",
        "ultra detailed",
        "highly detailed",
        "detailed",
        "sharp focus",
        "soft lighting",
        "official art",
        "newest",
        "very aesthetic",
        "aesthetic",
    }

    def split_quality(tags: List[str]) -> Tuple[List[str], List[str]]:
        q, rest = [], []
        for t in tags:
            if t in _QUALITY or "quality" in t or t.endswith("res"):
                q.append(t)
            else:
                rest.append(t)
        return q, rest

    def uniq(seq: List[str]) -> List[str]:
        out, seen = [], set()
        for t in seq:
            if t in seen:
                continue
            seen.add(t)
            out.append(t)
        return out

    if mode == "user_only":
        return ", ".join(uniq(quality + character)), "applied: user_only"

    if not has_image or not ref:
        # text-only path
        q_extra, char_from_blob = split_quality(character)
        merged = uniq(quality + q_extra + char_from_blob)
        return ", ".join(merged), "bypass: text-only Identity (character enabled)"

    # has reference image
    if mode == "auto_split":
        # STRICT: drop handwritten character entirely
        q_from_char, _ = split_quality(character)
        merged = uniq(quality + q_from_char + ref)
        return (
            ", ".join(merged),
            f"applied: auto_split (ref={len(ref)}, character IGNORED)",
        )

    if mode in ("ref_only", "auto_ref_main"):
        q, user_rest = split_quality(user)
        if mode == "ref_only" or mode == "auto_split":
            user_rest = []
        if mode == "auto_ref_main":
            # soft: allow overrides
            pass
        else:
            user_rest = []

        user_set = set(user_rest)
        blocked_groups: Set[str] = set()
        for g, members in _MUTEX_GROUPS.items():
            if any(m in user_set for m in members):
                blocked_groups.add(g)

        def ref_blocked(tag: str) -> bool:
            if tag in user_set:
                return True
            for g in blocked_groups:
                if tag in _MUTEX_GROUPS[g]:
                    return True
            return False

        ref_kept = [t for t in ref if not ref_blocked(t)]
        if mode == "ref_only":
            merged = uniq(q + ref_kept)
            return ", ".join(merged), f"applied: ref_only (ref={len(ref_kept)})"

        # auto_ref_main soft
        merged = uniq(q + ref_kept + user_rest)
        return (
            ", ".join(merged),
            f"applied: auto_ref_main (ref={len(ref_kept)}, override={len(user_rest)})",
        )

    user_set = set(user)
    blocked_groups = set()
    for g, members in _MUTEX_GROUPS.items():
        if any(m in user_set for m in members):
            blocked_groups.add(g)

    def ref_blocked(tag: str) -> bool:
        if tag in user_set:
            return True
        for g in blocked_groups:
            if tag in _MUTEX_GROUPS[g]:
                return True
        return False

    ref_kept = [t for t in ref if not ref_blocked(t)]

    if mode == "ref_priority":
        return (
            ", ".join(uniq(ref_kept + user)),
            f"applied: ref_priority (+{len(ref_kept)} ref tags)",
        )

    # user_priority
    return (
        ", ".join(uniq(user + [t for t in ref_kept if t not in user_set])),
        f"applied: user_priority (+{len(ref_kept)} ref tags)",
    )


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


class TriPoseRefSemanticDecompose:
    """WD14-based character composition extract. No-op when has_image is false."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "threshold": ("FLOAT", {"default": 0.35, "min": 0.05, "max": 0.9, "step": 0.05}),
                "character_threshold": ("FLOAT", {"default": 0.85, "min": 0.05, "max": 1.0, "step": 0.05}),
                "max_tags": ("INT", {"default": 40, "min": 5, "max": 80, "step": 1}),
                "min_side": ("INT", {"default": 16, "min": 1, "max": 512, "step": 1}),
            },
            "optional": {
                "image": ("IMAGE",),
                "has_image": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("ref_tags", "slots_text", "status")
    FUNCTION = "decompose"
    CATEGORY = "TriPose"
    DESCRIPTION = (
        "Decompose reference image into OC composition tags (hair/eyes/outfit/species/accessories). "
        "Drops pose/background/camera. When no image, returns empty and does not load the tagger."
    )

    def decompose(
        self,
        threshold,
        character_threshold,
        max_tags,
        min_side,
        image=None,
        has_image=True,
    ):
        if has_image is False or not _has_valid_image(image, min_side=min_side):
            return ("", "", "bypass: no reference image")

        try:
            pil = _tensor_to_pil(image)
            scored = _run_wd14(
                pil,
                threshold=float(threshold),
                character_threshold=float(character_threshold),
            )
            tags, slots = decompose_tags(scored, max_tags=int(max_tags))
            slot_lines = []
            for k, vals in slots.items():
                if vals:
                    slot_lines.append(f"{k}: {', '.join(vals)}")
            slots_text = "\n".join(slot_lines)
            return (tags, slots_text, f"ok: {len(tags.split(', ')) if tags else 0} composition tags")
        except Exception as e:
            return ("", "", f"bypass: tagger failed ({e})")


class TriPoseIdentityMerge:
    """Quality + character Identity, with optional reference-tag sharing switch."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "quality_text": (
                    "STRING",
                    {
                        "forceInput": True,
                        "multiline": True,
                        "default": "",
                        "tooltip": "Always used (masterpiece / best quality ...)",
                    },
                ),
                "character_text": (
                    "STRING",
                    {
                        "forceInput": True,
                        "multiline": True,
                        "default": "",
                        "tooltip": "Handwritten OC tags (used only when 参考图共享 is OFF)",
                    },
                ),
                "share_with_ref": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "label_on": "只用参考图ON",
                        "label_off": "只用手写角色词OFF",
                        "tooltip": (
                            "ON + 有参考图：Identity 角色描述只用参考语义，完全跳过手写角色词。"
                            "OFF：只用手写角色词，不读参考图。"
                            "画质底词始终保留。"
                        ),
                    },
                ),
                "mode": (
                    ["ref_only", "user_priority", "ref_priority", "auto_split", "auto_ref_main", "user_only"],
                    {
                        "default": "ref_only",
                        "tooltip": "Advanced merge mode. Ignored when switch is OFF. "
                        "When switch is ON, default ref_only skips handwritten character tags.",
                    },
                ),
            },
            "optional": {
                "ref_tags": ("STRING", {"forceInput": True, "multiline": True, "default": ""}),
                "has_image": ("BOOLEAN", {"default": True, "forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("merged_text", "status")
    FUNCTION = "merge"
    CATEGORY = "TriPose"
    DESCRIPTION = (
        "参考图开关 ON（有图）：只用参考语义作角色描述，跳过手写角色词。"
        "OFF：只用手写角色词。画质底词始终生效。"
    )

    def merge(
        self,
        quality_text,
        character_text,
        share_with_ref,
        mode,
        ref_tags="",
        has_image=True,
    ):
        has_img = bool(has_image)
        want_ref = bool(share_with_ref)

        if has_img and want_ref:
            # User contract: ON = reference only for character, skip handwritten OC tags
            effective_mode = mode if mode in ("ref_only", "auto_split") else "ref_only"
            use_ref = True
        else:
            # OFF, or no image → handwritten character only
            effective_mode = "user_only"
            use_ref = False

        merged, status = merge_identity(
            quality_text,
            character_text,
            ref_tags or "",
            use_ref,
            mode=effective_mode,
        )
        switch = "shareON→ref_only" if use_ref else "shareOFF→handwrite"
        return (merged, f"[{switch}] {status}")



NODE_CLASS_MAPPINGS = {
    "TriPoseRefSemanticDecompose": TriPoseRefSemanticDecompose,
    "TriPoseIdentityMerge": TriPoseIdentityMerge,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TriPoseRefSemanticDecompose": "TriPose 参考图语义拆解",
    "TriPoseIdentityMerge": "TriPose Identity 合并",
}
