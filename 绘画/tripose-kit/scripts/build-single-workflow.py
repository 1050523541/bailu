# -*- coding: utf-8 -*-
"""Build CF-TriPose-SDXL-single.json from TriPose layout: keep positions, drop lanes 2/3."""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Prefer user-tuned layout
SRC_CANDIDATES = [
    Path(r"E:\AIGC\ComfyUI-aki-v3\ComfyUI\user\default\workflows\CF-TriPose-SDXL-template1.json"),
    Path(r"E:\AIGC\ComfyUI-aki-v3\ComfyUI\user\default\workflows\CF-TriPose-SDXL-template.json"),
    ROOT / "workflows" / "CF-TriPose-SDXL-template.json",
]
OUT = ROOT / "workflows" / "CF-TriPose-SDXL-single.json"
COMFY_USER = Path(r"E:\AIGC\ComfyUI-aki-v3\ComfyUI\user\default\workflows")

# Keep lane-1 / shared only (same coordinates as TriPose).
KEEP = {
    1,  # Checkpoint
    2,  # CLIP Identity
    3,  # CLIP Variant1
    6,  # CLIP Neg
    7,  # CLIP Face
    8,  # Latent 图1
    11,  # Concat ID+V1
    14,  # Sampler 图1
    17,  # VAEDecode 图1
    20,  # YOLO
    21,  # FaceDetailer 图1
    24,  # Save 图1
    27,  # Seed
    28,  # Note
    100,
    101,  # Identity zh + map
    102,
    103,  # Variant1 zh + map
    108,
    109,  # Neg
    110,
    111,  # Face
    112,
    113,  # Upscale + refine 图1
    120,  # Power Lora
    121,  # Lane enable (single)
    124,
    125,
    126,  # BG
    127,  # Concat +bg 图1
    130,
    131,
    132,  # Quality
    133,  # Concat +quality 图1
}

NOTE = (
    "TriPose 单图 SDXL 模板 v1.0\n"
    "• 架构同三态立绘，只保留一路采样/精炼/FaceDetailer/Save\n"
    "• 操作栏：Checkpoint → Power Lora → 开·采样 · Seed\n"
    "• 提示词：质量 · Identity · 背景 · Variant · Neg · Face\n"
    "• 词库默认 danbooru_zh+nsfw；Power Lora 可空\n"
    "• 布局先沿用三态坐标，请自行拖拽定稿"
)

EMPTY_LORA = [
    {},
    {"type": "PowerLoraLoaderHeaderWidget"},
    {},
    "",
]


def main() -> None:
    src = next(p for p in SRC_CANDIDATES if p.is_file())
    wf = json.loads(src.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in wf["nodes"]}

    # Drop lanes 2/3
    wf["nodes"] = [copy.deepcopy(nodes[i]) for i in sorted(KEEP) if i in nodes]
    nodes = {n["id"]: n for n in wf["nodes"]}

    # Filter links: both ends must exist
    keep_ids = set(nodes)
    new_links = []
    for L in wf.get("links") or []:
        # [id, from, from_slot, to, to_slot, type]
        if L[1] in keep_ids and L[3] in keep_ids:
            new_links.append(L)
    wf["links"] = new_links
    link_ids = {L[0] for L in new_links}

    # Repair node input/output link refs
    for n in wf["nodes"]:
        for inp in n.get("inputs") or []:
            lid = inp.get("link")
            if lid is not None and lid not in link_ids:
                inp["link"] = None
        for out in n.get("outputs") or []:
            links = out.get("links")
            if isinstance(links, list):
                out["links"] = [x for x in links if x in link_ids]

    # Titles / save name for single mode
    renames = {
        3: "Variant 服装/状态",
        8: "Latent",
        11: "Concat Identity+Variant",
        14: "Sampler",
        17: "VAEDecode",
        21: "FaceDetailer",
        24: "Save (审阅放大)",
        27: "Seed 同步器",
        102: "中文 Variant",
        103: "映射 Variant",
        112: "潜空间放大 1.5x",
        113: "精炼 Sampler (denoise0.4)",
        121: "开·采样",
        127: "Concat +背景",
        133: "Concat +质量",
    }
    for nid, title in renames.items():
        if nid in nodes:
            nodes[nid]["title"] = title

    if 24 in nodes:
        nodes[24]["widgets_values"] = ["CF_TriPose_single"]

    if 120 in nodes:
        nodes[120]["widgets_values"] = copy.deepcopy(EMPTY_LORA)
        nodes[120]["title"] = "多 LoRA (Power Lora·可空)"

    if 28 in nodes and isinstance(nodes[28].get("widgets_values"), list):
        nodes[28]["widgets_values"] = [NOTE]

    # Groups: keep bounding boxes (user will retune), update titles
    groups = []
    for g in wf.get("groups") or []:
        g = copy.deepcopy(g)
        title = g.get("title") or ""
        if "操作栏" in title:
            g["title"] = "操作栏 · Checkpoint / 多LoRA / Seed / 开·采样"
        elif "提示词" in title:
            g["title"] = "提示词 · 质量 / Identity / 背景 / Variant / Neg / Face"
        elif "采样" in title:
            g["title"] = "单路采样 · 放大 / 精炼"
        elif "FaceDetailer" in title or "Save" in title:
            g["title"] = "YOLO FaceDetailer → Save"
        groups.append(g)
    wf["groups"] = groups

    wf["id"] = "cf-tripose-sdxl-single-v1.0"
    wf["last_node_id"] = max(nodes)
    wf["last_link_id"] = max((L[0] for L in new_links), default=0)
    extra = wf.setdefault("extra", {})
    info = extra.setdefault("info", {})
    info["name"] = "CF-TriPose-SDXL-single"
    info["version"] = "1.0.0"
    info["description"] = "TriPose 单图：同架构一路采样；布局沿用三态，可自行定稿"
    info["author"] = "cursor-agent"

    OUT.write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if COMFY_USER.is_dir():
        dest = COMFY_USER / OUT.name
        dest.write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")
        print("synced", dest)

    print(f"source={src}")
    print(f"wrote {OUT}")
    print(f"nodes={len(wf['nodes'])} links={len(wf['links'])} groups={len(wf['groups'])}")
    missing = KEEP - set(nodes)
    if missing:
        print("WARN missing keep ids", sorted(missing))


if __name__ == "__main__":
    main()
