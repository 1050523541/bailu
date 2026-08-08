# -*- coding: utf-8 -*-
"""TriPose v1.4: split quality prompts out of Identity into a dedicated chain."""
from __future__ import annotations

import copy
import json
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / "workflows" / "CF-TriPose-SDXL-template.json"
BAK = ROOT / "workflows" / "CF-TriPose-SDXL-template.json.bak-v13-before-v14"

NOTE = (
    "TriPose 三态立绘 SDXL 模板 v1.4\n"
    "• 操作栏：Checkpoint → Power Lora → 三路开关 · Seed\n"
    "• 提示词：质量(独立) · Identity · 背景(独立) · V1/V2/V3 · Neg · Face\n"
    "• 分路开关关=跳过该路采样/精炼/FD/Save（可只开正常校准角色）\n"
    "• 每条：KSampler → 潜空间1.5x → 精炼 → VAE → FaceDetailer → Save"
)

QUALITY_DEFAULT = "杰作, 最佳质量, 超高清, 高细节, 柔光, 空灵氛围"
IDENTITY_DEFAULT = (
    "单人, 成年女性, 全身立绘,\n"
    "白发, 凌乱长发, 刘海, 紫瞳, 细致眼睛, 美颜,\n"
    "角上黑玫瑰, 白色天使翅膀, 蓝宝石颈环,\n"
    "蓝蝴蝶, 粉黑玫瑰, 装饰锁链, 花瓣, 粉彩, 梦幻光"
)

GRID = 64


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

    # Update Identity text (strip quality line)
    id_prim = find(nodes, 100)
    id_prim["widgets_values"] = [IDENTITY_DEFAULT]
    id_map = find(nodes, 101)
    # TriPoseZhTagMap keeps a preview of mapped/source text in widgets[0]
    wv = list(id_map.get("widgets_values") or [])
    if wv:
        wv[0] = IDENTITY_DEFAULT
        id_map["widgets_values"] = wv

    N_Q_PRIM, N_Q_MAP, N_Q_CLIP = 130, 131, 132
    N_Q_CAT = (133, 134, 135)  # +质量 per lane
    N_BG_CAT = (127, 128, 129)
    N_ID_CAT = (11, 12, 13)

    # Drop ID-concat → BG-concat links; rebuild via quality concat
    drop = set()
    for L in links:
        if L[1] in N_ID_CAT and L[3] in N_BG_CAT:
            drop.add(L[0])
    links = [L for L in links if L[0] not in drop]

    used = {L[0] for L in links}

    def new_lid():
        i = max(used | {250}) + 1
        while i in used:
            i += 1
        used.add(i)
        return i

    t_prim = find(nodes, 100)
    t_map = find(nodes, 101)
    t_clip = find(nodes, 2)
    t_cat = find(nodes, 11)
    lora_id = 120

    # --- Quality chain (mirror BG) ---
    q_prim = copy.deepcopy(t_prim)
    q_prim.update(
        {
            "id": N_Q_PRIM,
            "title": "中文 质量 (独立输入)",
            "widgets_values": [QUALITY_DEFAULT],
        }
    )
    set_pos(q_prim, 64, 480, 352, 110)

    q_map = copy.deepcopy(t_map)
    q_map.update(
        {
            "id": N_Q_MAP,
            "title": "映射 质量",
            "widgets_values": [QUALITY_DEFAULT, "zh_danbooru+nsfw", "", "keep", True],
        }
    )
    set_pos(q_map, 448, 480, 300, 150)
    set_link(q_map, "text", new_lid())
    lid_q_text = q_map["inputs"][0]["link"]
    links.append([lid_q_text, N_Q_PRIM, 0, N_Q_MAP, 0, "STRING"])

    q_clip = copy.deepcopy(t_clip)
    q_clip.update(
        {
            "id": N_Q_CLIP,
            "title": "CLIP 质量",
        }
    )
    set_pos(q_clip, 768, 480, 256, 100)
    for inp in q_clip["inputs"]:
        if inp["name"] == "text":
            lid = new_lid()
            inp["link"] = lid
            links.append([lid, N_Q_MAP, 0, N_Q_CLIP, 0, "STRING"])
        elif inp["name"] == "clip":
            lid = new_lid()
            inp["link"] = lid
            links.append([lid, lora_id, 1, N_Q_CLIP, 1, "CLIP"])

    # Shift BG row down slightly for breathing room
    for nid, x in ((124, 64), (125, 448), (126, 768)):
        set_pos(find(nodes, nid), x, 608)

    # Per-lane Concat +质量 between ID-concat and BG-concat
    for i, (nid_q, nid_id, nid_bg, y) in enumerate(
        zip(N_Q_CAT, N_ID_CAT, N_BG_CAT, (704, 832, 1024))
    ):
        cat = copy.deepcopy(t_cat)
        cat.update(
            {
                "id": nid_q,
                "title": f"Concat +质量 图{i + 1}",
            }
        )
        set_pos(cat, 1152, y, 220, 70)
        # conditioning_to <- ID concat; conditioning_from <- quality CLIP
        lid_to = new_lid()
        lid_from = new_lid()
        set_link(cat, "conditioning_to", lid_to)
        set_link(cat, "conditioning_from", lid_from)
        links.append([lid_to, nid_id, 0, nid_q, 0, "CONDITIONING"])
        links.append([lid_from, N_Q_CLIP, 0, nid_q, 1, "CONDITIONING"])
        nodes.append(cat)

        # Rewire BG concat: conditioning_to from quality concat (was ID concat)
        bg = find(nodes, nid_bg)
        lid_bg_to = new_lid()
        set_link(bg, "conditioning_to", lid_bg_to)
        links.append([lid_bg_to, nid_q, 0, nid_bg, 0, "CONDITIONING"])
        set_pos(bg, 1408, y, 220, 70)

    nodes.extend([q_prim, q_map, q_clip])

    # Groups / meta
    for g in data.get("groups") or []:
        title = g.get("title") or ""
        if "提示词" in title:
            g["title"] = "提示词 · 质量 / Identity / 背景 / Variant / Neg / Face"
            # expand height a bit
            b = g.get("bounding") or g.get("bounding_rect")
            if b and len(b) >= 4:
                b[3] = max(float(b[3]), 1280.0)

    data["last_node_id"] = max(n["id"] for n in nodes)
    data["last_link_id"] = max(L[0] for L in links)
    data["links"] = links
    data["id"] = "cf-tripose-sdxl-v1.4"
    data.setdefault("extra", {})
    data["extra"]["info"] = {
        "name": "CF-TriPose-SDXL-template",
        "author": "cursor-agent",
        "version": "1.4.0",
        "description": "TriPose v1.4：质量独立 + 背景独立 + Power Lora + 三路开关",
    }

    repair_outputs(nodes, links)
    WF.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("patched", WF)
    print("backup", BAK)

    # verify wiring
    by_id = {n["id"]: n for n in nodes}
    for lid, frm, fslot, to, tslot, typ in links:
        if to in N_BG_CAT and tslot == 0:
            assert frm in N_Q_CAT, (lid, frm, to)
        if to in N_Q_CAT and tslot == 0:
            assert frm in N_ID_CAT, (lid, frm, to)
        if to in N_Q_CAT and tslot == 1:
            assert frm == N_Q_CLIP, (lid, frm, to)
    assert by_id[100]["widgets_values"][0].startswith("单人")
    assert "杰作" not in by_id[100]["widgets_values"][0]
    assert by_id[130]["widgets_values"][0].startswith("杰作")
    print("verify ok")


if __name__ == "__main__":
    main()
