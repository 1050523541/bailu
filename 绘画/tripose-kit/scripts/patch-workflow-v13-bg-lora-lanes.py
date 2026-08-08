# -*- coding: utf-8 -*-
"""TriPose v1.3: background input, Power Lora, per-lane enable switches, layout."""
from __future__ import annotations

import copy
import json
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / "workflows" / "CF-TriPose-SDXL-template.json"
BAK = ROOT / "workflows" / "CF-TriPose-SDXL-template.json.bak-v12-before-v13"

NOTE = (
    "TriPose 三态立绘 SDXL 模板 v1.3\n"
    "• 操作栏：Checkpoint → Power Lora → 三路开关 · Seed\n"
    "• 提示词：Identity · 背景(独立) · V1/V2/V3 · Neg · Face\n"
    "• 分路开关关=跳过该路采样/精炼/FD/Save（可只开正常校准角色）\n"
    "• 每条：KSampler → 潜空间1.5x → 精炼 → VAE → FaceDetailer → Save"
)

BG_DEFAULT = "白底, 纯白背景, 简洁背景"

GRID = 64
TITLE = 56


def snap(v: float) -> int:
    return int(round(v / GRID) * GRID)


def find(nodes, nid):
    for n in nodes:
        if n["id"] == nid:
            return n
    raise KeyError(nid)


def set_pos(n, x, y, w=None, h=None):
    n["pos"] = [float(snap(x)), float(snap(y))]
    if w is not None:
        n["size"] = [float(w), float(h if h is not None else n["size"][1])]


def set_link(n, name, lid):
    for inp in n.get("inputs") or []:
        if inp["name"] == name:
            inp["link"] = lid
            return
    raise KeyError(f"{n['id']} missing input {name}")


def repair_outputs(nodes, links):
    outs = defaultdict(list)
    for L in links:
        outs[(L[1], L[2])].append(L[0])
    for n in nodes:
        for i, o in enumerate(n.get("outputs") or []):
            o["links"] = outs.get((n["id"], i)) or None
            o["slot_index"] = i


def main():
    shutil.copy2(WF, BAK)
    data = json.loads(WF.read_text(encoding="utf-8"))
    nodes = data["nodes"]
    links = list(data["links"])

    for n in nodes:
        if n["type"] == "Note":
            n["widgets_values"] = [NOTE]
            break

    # --- ids ---
    N_LORA = 120
    N_SW = (121, 122, 123)  # lane enables
    N_BG_PRIM, N_BG_MAP, N_BG_CLIP = 124, 125, 126
    N_BG_CAT = (127, 128, 129)  # concat +bg per lane

    # Drop links we will rebuild (ckpt MODEL/CLIP fanout to samplers/FD/CLIPEncode)
    # Keep structure of text maps etc.
    drop_link_ids = set()
    # model links from ckpt(1) to samplers/refine/FD
    for L in links:
        # ckpt model → anything that should come from lora/switches
        if L[1] == 1 and L[2] == 0:
            drop_link_ids.add(L[0])
        # ckpt clip → CLIP encodes / FD
        if L[1] == 1 and L[2] == 1:
            drop_link_ids.add(L[0])
        # positive from Concat 11/12/13 to samplers/refine — rewire via BG concat
        if L[1] in (11, 12, 13) and L[5] == "CONDITIONING":
            drop_link_ids.add(L[0])

    links = [L for L in links if L[0] not in drop_link_ids]

    used = {L[0] for L in links}

    def new_lid():
        i = max(used | {220}) + 1
        while i in used:
            i += 1
        used.add(i)
        return i

    # templates
    t_prim = find(nodes, 100)
    t_map = find(nodes, 101)
    t_clip = find(nodes, 2)
    t_cat = find(nodes, 11)

    # --- Power Lora Loader ---
    lora = {
        "id": N_LORA,
        "type": "Power Lora Loader (rgthree)",
        "pos": [400.0, 80.0],
        "size": [360.0, 160.0],
        "flags": {},
        "order": 1,
        "mode": 0,
        "inputs": [
            {"name": "model", "type": "MODEL", "link": None},
            {"name": "clip", "type": "CLIP", "link": None},
        ],
        "outputs": [
            {"name": "MODEL", "type": "MODEL", "links": [], "slot_index": 0},
            {"name": "CLIP", "type": "CLIP", "links": [], "slot_index": 1},
        ],
        "title": "多 LoRA (Power Lora·可空)",
        "properties": {"Node name for S&R": "Power Lora Loader (rgthree)"},
        "widgets_values": [],
    }
    lid_ckpt_m, lid_ckpt_c = new_lid(), new_lid()
    set_link(lora, "model", lid_ckpt_m)
    set_link(lora, "clip", lid_ckpt_c)
    links.append([lid_ckpt_m, 1, 0, N_LORA, 0, "MODEL"])
    links.append([lid_ckpt_c, 1, 1, N_LORA, 1, "CLIP"])
    nodes.append(lora)

    # --- Lane enables ---
    sw_titles = ["开·图1正常", "开·图2赤裸", "开·图3事后"]
    for i, sid in enumerate(N_SW):
        sw = {
            "id": sid,
            "type": "TriPoseLaneEnable",
            "pos": [800.0 + i * 280, 80.0],
            "size": [240.0, 80.0],
            "flags": {},
            "order": 2,
            "mode": 0,
            "inputs": [
                {"name": "model", "type": "MODEL", "link": None},
                {
                    "name": "enabled",
                    "type": "BOOLEAN",
                    "widget": {"name": "enabled"},
                    "link": None,
                },
            ],
            "outputs": [
                {"name": "MODEL", "type": "MODEL", "links": [], "slot_index": 0}
            ],
            "title": sw_titles[i],
            "properties": {"Node name for S&R": "TriPoseLaneEnable"},
            "widgets_values": [True],
        }
        lid = new_lid()
        set_link(sw, "model", lid)
        links.append([lid, N_LORA, 0, sid, 0, "MODEL"])
        nodes.append(sw)

    # Sampler / refine model from switches
    # 14/113 ← 121, 15/115 ← 122, 16/117 ← 123
    lane_samp = [(121, 14, 113), (122, 15, 115), (123, 16, 117)]
    for sw_id, samp_id, ref_id in lane_samp:
        for tgt, slot_hint in ((samp_id, 0), (ref_id, 0)):
            lid = new_lid()
            links.append([lid, sw_id, 0, tgt, 0, "MODEL"])
            set_link(find(nodes, tgt), "model", lid)

    # FaceDetailer model from Power Lora (shared); skip via image blocker when lane off
    for fid in (21, 22, 23):
        lid = new_lid()
        links.append([lid, N_LORA, 0, fid, 1, "MODEL"])  # slot may not be 1 — use set_link
        set_link(find(nodes, fid), "model", lid)

    # CLIP from Power Lora to all CLIPTextEncode + FD
    clip_targets = []
    for n in nodes:
        if n["type"] == "CLIPTextEncode":
            clip_targets.append(n["id"])
        if n["type"] == "FaceDetailer":
            clip_targets.append(n["id"])
    # also upcoming BG CLIP 126 — added below

    # --- Background chain ---
    bg_prim = copy.deepcopy(t_prim)
    bg_map = copy.deepcopy(t_map)
    bg_clip = copy.deepcopy(t_clip)
    bg_prim["id"], bg_map["id"], bg_clip["id"] = N_BG_PRIM, N_BG_MAP, N_BG_CLIP
    bg_prim["title"] = "中文 背景 (独立输入)"
    bg_prim["widgets_values"] = [BG_DEFAULT]
    bg_map["title"] = "映射 背景"
    # keep dictionary zh_danbooru from template map node
    bg_clip["title"] = "CLIP 背景"
    bg_clip["widgets_values"] = [""]
    for inp in bg_clip["inputs"]:
        if inp["name"] == "text":
            inp["link"] = None
        if inp["name"] == "clip":
            inp["link"] = None
    bg_prim["outputs"][0]["links"] = []
    bg_map["outputs"][0]["links"] = []
    bg_clip["outputs"][0]["links"] = []
    nodes.extend([bg_prim, bg_map, bg_clip])

    lid_s, lid_m, lid_c = new_lid(), new_lid(), new_lid()
    set_link(bg_map, "text", lid_s)
    links.append([lid_s, N_BG_PRIM, 0, N_BG_MAP, 0, "STRING"])
    # map → clip text
    # find mapped_text output index 0
    set_link(bg_clip, "text", lid_m)
    links.append([lid_m, N_BG_MAP, 0, N_BG_CLIP, 1, "STRING"])  # text often slot 1
    # fix: CLIPTextEncode inputs order is clip=0, text=1 in some versions — use names
    for inp in bg_clip["inputs"]:
        if inp["name"] == "text":
            inp["link"] = lid_m
        if inp["name"] == "clip":
            inp["link"] = lid_c
    # rewrite link target slots correctly by name index
    links = [L for L in links if L[0] != lid_m]
    text_slot = next(i for i, inp in enumerate(bg_clip["inputs"]) if inp["name"] == "text")
    clip_slot = next(i for i, inp in enumerate(bg_clip["inputs"]) if inp["name"] == "clip")
    links.append([lid_m, N_BG_MAP, 0, N_BG_CLIP, text_slot, "STRING"])
    links.append([lid_c, N_LORA, 1, N_BG_CLIP, clip_slot, "CLIP"])

    # Concat +BG per lane
    base_cats = (11, 12, 13)
    samp_pos = [(14, 113), (15, 115), (16, 117)]
    for i, cat_id in enumerate(N_BG_CAT):
        cat = copy.deepcopy(t_cat)
        cat["id"] = cat_id
        cat["title"] = f"Concat +背景 图{i+1}"
        cat["inputs"] = [
            {"name": "conditioning_to", "type": "CONDITIONING", "link": None},
            {"name": "conditioning_from", "type": "CONDITIONING", "link": None},
        ]
        cat["outputs"] = [
            {"name": "CONDITIONING", "type": "CONDITIONING", "links": [], "slot_index": 0}
        ]
        lid_to, lid_from = new_lid(), new_lid()
        set_link(cat, "conditioning_to", lid_to)
        set_link(cat, "conditioning_from", lid_from)
        links.append([lid_to, base_cats[i], 0, cat_id, 0, "CONDITIONING"])
        links.append([lid_from, N_BG_CLIP, 0, cat_id, 1, "CONDITIONING"])
        nodes.append(cat)
        # positives to main+refine
        for tgt in samp_pos[i]:
            lid = new_lid()
            links.append([lid, cat_id, 0, tgt, 1, "CONDITIONING"])
            set_link(find(nodes, tgt), "positive", lid)

    # Rewire remaining CLIP encodes + FD clip from Power Lora
    for n in nodes:
        if n["id"] == N_BG_CLIP:
            continue
        if n["type"] == "CLIPTextEncode":
            lid = new_lid()
            clip_slot = next(i for i, inp in enumerate(n["inputs"]) if inp["name"] == "clip")
            set_link(n, "clip", lid)
            links.append([lid, N_LORA, 1, n["id"], clip_slot, "CLIP"])
        if n["type"] == "FaceDetailer":
            lid = new_lid()
            clip_slot = next(i for i, inp in enumerate(n["inputs"]) if inp["name"] == "clip")
            set_link(n, "clip", lid)
            links.append([lid, N_LORA, 1, n["id"], clip_slot, "CLIP"])

    # --- Layout ---
    oy = 16 + TITLE
    set_pos(find(nodes, 1), 64, oy, 320, 110)
    set_pos(find(nodes, N_LORA), 416, oy, 360, 160)
    set_pos(find(nodes, 27), 816, oy, 256, 120)  # Seed
    for i, sid in enumerate(N_SW):
        set_pos(find(nodes, sid), 1120 + i * 256, oy, 240, 90)

    py = 240 + TITLE
    # Identity row
    set_pos(find(nodes, 100), 64, py, 352, 150)
    set_pos(find(nodes, 101), 448, py, 300, 150)
    set_pos(find(nodes, 2), 768, py, 256, 100)
    # Background
    set_pos(find(nodes, N_BG_PRIM), 64, py + 192, 352, 110)
    set_pos(find(nodes, N_BG_MAP), 448, py + 192, 300, 150)
    set_pos(find(nodes, N_BG_CLIP), 768, py + 192, 256, 100)
    # Variants
    y = py + 384
    for prim, mp, clip in ((102, 103, 3), (104, 105, 4), (106, 107, 5)):
        set_pos(find(nodes, prim), 64, y, 352, 120)
        set_pos(find(nodes, mp), 448, y, 300, 150)
        set_pos(find(nodes, clip), 768, y, 256, 100)
        y += 176
    # Neg + Face
    set_pos(find(nodes, 108), 64, y, 352, 130)
    set_pos(find(nodes, 109), 448, y, 300, 150)
    set_pos(find(nodes, 6), 768, y, 256, 100)
    y += 176
    set_pos(find(nodes, 110), 64, y, 352, 120)
    set_pos(find(nodes, 111), 448, y, 300, 150)
    set_pos(find(nodes, 7), 768, y, 256, 100)
    # Note under prompts
    for n in nodes:
        if n["type"] == "Note":
            set_pos(n, 64, y + 176, 1000, 160)
            break

    # Concat column
    set_pos(find(nodes, 11), 1056, py + 384, 220, 70)
    set_pos(find(nodes, 12), 1056, py + 560, 220, 70)
    set_pos(find(nodes, 13), 1056, py + 736, 220, 70)
    set_pos(find(nodes, N_BG_CAT[0]), 1280, py + 384, 220, 70)
    set_pos(find(nodes, N_BG_CAT[1]), 1280, py + 560, 220, 70)
    set_pos(find(nodes, N_BG_CAT[2]), 1280, py + 736, 220, 70)

    # Sample lanes
    sx = 1568
    lanes = [
        (8, 14, 112, 113, 17, 0),
        (9, 15, 114, 115, 18, 480),
        (10, 16, 116, 117, 19, 960),
    ]
    for lat, samp, up, ref, vae, dy in lanes:
        ly = 240 + TITLE + dy
        set_pos(find(nodes, lat), sx, ly, 224, 100)
        set_pos(find(nodes, samp), sx + 256, ly, 288, 280)
        set_pos(find(nodes, up), sx + 576, ly, 192, 80)
        set_pos(find(nodes, ref), sx + 576, ly + 96, 256, 240)
        set_pos(find(nodes, vae), sx + 864, ly + 64, 192, 64)

    # FD + Save
    fx = 2688
    fy = 240 + TITLE
    for i, (fd, sav) in enumerate(((21, 24), (22, 25), (23, 26))):
        set_pos(find(nodes, fd), fx, fy + i * 1000, 360, 960)
        set_pos(find(nodes, sav), fx + 400, fy + i * 1000, 480, 640)

    # YOLO
    set_pos(find(nodes, 20), 1120, oy + 160, 288, 80) if any(
        n["id"] == 20 for n in nodes
    ) else None
    # find YOLO
    for n in nodes:
        if n["type"] == "UltralyticsDetectorProvider":
            set_pos(n, 1900, oy, 288, 80)
            break

    data["groups"] = [
        {
            "id": 10,
            "title": "操作栏 · Checkpoint / 多LoRA / Seed / 三路开关",
            "bounding": [32, 16, 2400, 220],
            "color": "#2a8a6a",
            "font_size": 20,
            "flags": {},
        },
        {
            "id": 1,
            "title": "提示词 · Identity / 背景 / Variant / Neg / Face",
            "bounding": [32, 240, 1504, 1200],
            "color": "#3f789e",
            "font_size": 20,
            "flags": {},
        },
        {
            "id": 2,
            "title": "三路采样 · 开关控制是否执行",
            "bounding": [1536, 240, 1120, 1400],
            "color": "#b58b2a",
            "font_size": 20,
            "flags": {},
        },
        {
            "id": 3,
            "title": "YOLO FaceDetailer → Save",
            "bounding": [2656, 240, 1200, 3100],
            "color": "#a1309b",
            "font_size": 20,
            "flags": {},
        },
    ]

    repair_outputs(nodes, links)
    data["nodes"] = nodes
    data["links"] = links
    data["last_node_id"] = max(n["id"] for n in nodes)
    data["last_link_id"] = max(L[0] for L in links)
    data["id"] = "cf-tripose-sdxl-v1.3"
    data.setdefault("extra", {}).setdefault("info", {})
    data["extra"]["info"].update(
        {
            "name": "CF-TriPose-SDXL-template",
            "version": "1.3.0",
            "description": "TriPose v1.3：背景独立 + Power Lora + 三路开关 + 布局整理",
        }
    )

    # sanity
    errs = []
    lb = {L[0]: L for L in links}
    ids = {n["id"] for n in nodes}
    for n in nodes:
        for inp in n.get("inputs") or []:
            lid = inp.get("link")
            if lid is None:
                continue
            if lid not in lb:
                errs.append(f"node {n['id']} {inp['name']} missing {lid}")
            elif lb[lid][1] not in ids:
                errs.append(f"link {lid} src missing")
    if errs:
        raise SystemExit("link errors:\n" + "\n".join(errs[:30]))

    WF.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", WF, "nodes", len(nodes), "links", len(links))
    print("backup", BAK.name)


if __name__ == "__main__":
    main()
