# -*- coding: utf-8 -*-
"""TriPose 三态立绘 v1.2: LatentUpscaleBy 1.5 + refine KSampler before VAE/FaceDetailer."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / "workflows" / "CF-TriPose-SDXL-template.json"

NOTE = (
    "TriPose 三态立绘 SDXL 模板 v1.2\n"
    "• 左列中文短标签 → 中列词典映射 → CLIP\n"
    "• 每条：KSampler → 潜空间1.5x → 精炼(denoise0.4) → VAE → FaceDetailer → Save\n"
    "• Seed 随机同步；YOLO FaceDetailer\n"
    "• 需安装 ComfyUI-TriPose-Utils 并重启"
)


def find(nodes, nid):
    for n in nodes:
        if n["id"] == nid:
            return n
    raise KeyError(nid)


def main():
    data = json.loads(WF.read_text(encoding="utf-8"))
    nodes = data["nodes"]
    links = data["links"]

    # Note node — find type Note
    for n in nodes:
        if n["type"] == "Note":
            n["widgets_values"] = [NOTE]
            break

    # Chains: sampler 14/15/16 → vae 17/18/19 via links 28/30/32
    # Insert upscale 112/114/116 + refine 113/115/117
    # New links 200+
    drop = {28, 30, 32}
    new_links = [L for L in links if L[0] not in drop]
    new_links = [L for L in new_links if L[0] < 200 or L[0] > 230]

    chains = [
        # (sampler, vae, up_id, ref_id, y, title_suffix)
        # y pitch ~1060 so FaceDetailer (~980) never overlaps next lane
        (14, 17, 112, 113, 40, "图1"),
        (15, 18, 114, 115, 1100, "图2"),
        (16, 19, 116, 117, 2160, "图3"),
    ]

    link_by_id = {L[0]: L for L in links}

    # Align latents / samplers / saves with new lane ys
    latent_ids = [8, 9, 10]
    save_ids = [24, 25, 26]
    fd_ids = [21, 22, 23]

    next_link = 200
    for idx, (sampler_id, vae_id, up_id, ref_id, y, label) in enumerate(chains):
        samp = find(nodes, sampler_id)
        vae = find(nodes, vae_id)

        model_link = next(i["link"] for i in samp["inputs"] if i["name"] == "model")
        pos_link = next(i["link"] for i in samp["inputs"] if i["name"] == "positive")
        neg_link = next(i["link"] for i in samp["inputs"] if i["name"] == "negative")
        seed_link = next(i["link"] for i in samp["inputs"] if i["name"] == "seed")
        ml, pl, nl, sl = (
            link_by_id[model_link],
            link_by_id[pos_link],
            link_by_id[neg_link],
            link_by_id[seed_link],
        )
        model_src, model_slot = ml[1], ml[2]
        pos_src, pos_slot = pl[1], pl[2]
        neg_src, neg_slot = nl[1], nl[2]
        seed_src, seed_slot = sl[1], sl[2]

        find(nodes, latent_ids[idx])["pos"] = [1400, y + 40]
        find(nodes, latent_ids[idx])["size"] = [240, 100]
        samp["pos"] = [1680, y]
        samp["size"] = [300, 280]

        if not any(n["id"] == up_id for n in nodes):
            nodes.append(
                {
                    "id": up_id,
                    "type": "LatentUpscaleBy",
                    "pos": [2020, y],
                    "size": [220, 90],
                    "flags": {},
                    "order": up_id,
                    "mode": 0,
                    "inputs": [{"name": "samples", "type": "LATENT", "link": None}],
                    "outputs": [
                        {"name": "LATENT", "type": "LATENT", "links": None, "slot_index": 0}
                    ],
                    "properties": {"Node name for S&R": "LatentUpscaleBy"},
                    "widgets_values": ["bislerp", 1.5],
                    "title": f"潜空间放大 1.5x {label}",
                }
            )
        else:
            u = find(nodes, up_id)
            u["pos"] = [2020, y]
            u["widgets_values"] = ["bislerp", 1.5]
            u["title"] = f"潜空间放大 1.5x {label}"

        if not any(n["id"] == ref_id for n in nodes):
            nodes.append(
                {
                    "id": ref_id,
                    "type": "KSampler",
                    "pos": [2020, y + 100],
                    "size": [280, 220],
                    "flags": {},
                    "order": ref_id,
                    "mode": 0,
                    "inputs": [
                        {"name": "model", "type": "MODEL", "link": None},
                        {"name": "positive", "type": "CONDITIONING", "link": None},
                        {"name": "negative", "type": "CONDITIONING", "link": None},
                        {"name": "latent_image", "type": "LATENT", "link": None},
                        {"name": "seed", "type": "INT", "link": None},
                    ],
                    "outputs": [
                        {"name": "LATENT", "type": "LATENT", "links": None, "slot_index": 0}
                    ],
                    "properties": {"Node name for S&R": "KSampler"},
                    "widgets_values": [0, "fixed", 18, 5.0, "dpmpp_2m", "karras", 0.4],
                    "title": f"精炼 Sampler {label} (denoise0.4)",
                }
            )
        else:
            r = find(nodes, ref_id)
            r["pos"] = [2020, y + 100]
            r["size"] = [280, 220]
            r["widgets_values"] = [0, "fixed", 18, 5.0, "dpmpp_2m", "karras", 0.4]
            r["title"] = f"精炼 Sampler {label} (denoise0.4)"

        vae["pos"] = [2320, y + 40]
        find(nodes, fd_ids[idx])["pos"] = [2560, y]
        find(nodes, fd_ids[idx])["size"] = [360, 980]
        find(nodes, save_ids[idx])["pos"] = [3000, y]
        find(nodes, save_ids[idx])["size"] = [420, 600]
        find(nodes, save_ids[idx])["title"] = f"Save {label} (审阅放大)"
        l_samp_up = next_link
        next_link += 1
        l_up_ref = next_link
        next_link += 1
        l_ref_vae = next_link
        next_link += 1
        l_model = next_link
        next_link += 1
        l_pos = next_link
        next_link += 1
        l_neg = next_link
        next_link += 1
        l_seed = next_link
        next_link += 1

        find(nodes, up_id)["inputs"][0]["link"] = l_samp_up
        ref = find(nodes, ref_id)
        for inp in ref["inputs"]:
            if inp["name"] == "model":
                inp["link"] = l_model
            elif inp["name"] == "positive":
                inp["link"] = l_pos
            elif inp["name"] == "negative":
                inp["link"] = l_neg
            elif inp["name"] == "latent_image":
                inp["link"] = l_up_ref
            elif inp["name"] == "seed":
                inp["link"] = l_seed
        for inp in vae["inputs"]:
            if inp["name"] == "samples":
                inp["link"] = l_ref_vae

        new_links.extend(
            [
                [l_samp_up, sampler_id, 0, up_id, 0, "LATENT"],
                [l_up_ref, up_id, 0, ref_id, 3, "LATENT"],
                [l_ref_vae, ref_id, 0, vae_id, 0, "LATENT"],
                [l_model, model_src, model_slot, ref_id, 0, "MODEL"],
                [l_pos, pos_src, pos_slot, ref_id, 1, "CONDITIONING"],
                [l_neg, neg_src, neg_slot, ref_id, 2, "CONDITIONING"],
                [l_seed, seed_src, seed_slot, ref_id, 4, "INT"],
            ]
        )

    data["links"] = new_links
    data["last_node_id"] = max(n["id"] for n in nodes)
    data["last_link_id"] = max(L[0] for L in new_links)
    data["id"] = "cf-tripose-sdxl-v1.2"
    if "extra" not in data:
        data["extra"] = {}
    if "info" not in data["extra"]:
        data["extra"]["info"] = {}
    data["extra"]["info"]["version"] = "1.2.0"
    data["extra"]["info"]["description"] = (
        "TriPose 三态立绘 v1.2：每条潜空间1.5x精炼 + YOLO FaceDetailer"
    )

    outs = defaultdict(list)
    for L in data["links"]:
        outs[(L[1], L[2])].append(L[0])
    for n in data["nodes"]:
        for i, o in enumerate(n.get("outputs") or []):
            o["links"] = outs.get((n["id"], i)) or None

    ids = {n["id"] for n in nodes}
    for L in data["links"]:
        assert L[1] in ids and L[3] in ids, L

    # overlap check among new nodes vs neighbors
    items = []
    for n in data["nodes"]:
        x, y = n["pos"]
        w, h = n.get("size") or [240, 80]
        if isinstance(w, dict):
            w, h = 240, 80
        items.append((n["id"], x, y, w, h, n.get("title") or n["type"]))

    def ov(a, b):
        return not (
            a[1] + a[3] <= b[1]
            or b[1] + b[3] <= a[1]
            or a[2] + a[4] <= b[2]
            or b[2] + b[4] <= a[2]
        )

    bad = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if ov(items[i], items[j]):
                bad.append((items[i][0], items[j][0], items[i][5][:20], items[j][5][:20]))
    if bad:
        print("WARN overlaps:", bad[:20])

    WF.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"TriPose patched {WF} nodes={len(nodes)} links={len(data['links'])} ver=1.2.0")


if __name__ == "__main__":
    main()
