# -*- coding: utf-8 -*-
"""Adapt TriPose single-image layout to Krea2 (Moody Cutie X) loaders.

Preserves node positions / groups / zh-tagmap / Power Lora / refine / FaceDetailer.
Replaces CheckpointLoader with UNET+CLIP(type=krea2)+VAE and inserts AuraFlow+CFGNorm.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "workflows" / "CF-TriPose-SDXL-single.json"
ARCH = (
    Path(__file__).resolve().parents[1]
    / "workflows"
    / "archive"
    / "CF-TriPose-SDXL-single-v1.0.0.json"
)
# Prefer live Anima single (same TriPose frame, already UNET-shaped) if present
ANIMA = Path(__file__).resolve().parents[1] / "workflows" / "CF-TriPose-Anima-single.json"
OUT_KIT = Path(__file__).resolve().parents[1] / "workflows" / "CF-TriPose-Krea2-single.json"
OUT_WS = Path(r"E:\OneDrive\ComfyUI work flow\Krea2-MoodyCutie-单图.json")
COMFY_DIRS = [
    Path(r"E:\AIGC\ComfyUI-aki-v3\ComfyUI\user\default\workflows"),
    Path(r"E:\AIGC\ComfyUI-aki-v3\ComfyUI\user\workflows"),
]

UNET_ID, CLIP_ID, VAE_ID = 1, 140, 141
AURA_ID, CFGN_ID = 142, 143

NOTE = (
    "Krea2 单图 · 布局沿用 TriPose 单图 v1.0\n"
    "• 加载：UNET(Moody Cutie X) + CLIPLoader type=krea2 + Qwen Image VAE\n"
    "• 必下文本编码器：text_encoders/qwen3vl_4b_fp8_scaled.safetensors\n"
    "  HF: https://huggingface.co/Comfy-Org/Krea-2/resolve/main/text_encoders/qwen3vl_4b_fp8_scaled.safetensors\n  镜像: https://hf-mirror.com/Comfy-Org/Krea-2/resolve/main/text_encoders/qwen3vl_4b_fp8_scaled.safetensors\n"
    "  （Anima 的 qwen_3_06b_base 不能当 krea2 CLIP 用）\n"
    "• 操作栏：UNET → Power Lora → AuraFlow(shift≈1.15) → CFGNorm → 开·采样 · Seed(-1)\n"
    "• 默认 LoRA：Niji Sweet Spot KREA2 (@NJSW33T) + Cornflower Daydream (@Cornflower)\n"
    "• 采样：8steps CFG1 er_sde/simple（Krea2 Turbo 系）；精炼 4steps denoise0.3\n"
    "• 16GB：默认 896×1152；显存够可提到 1024×1280 / 1536 边\n"
    "• 布局坐标沿用单图定稿，勿被模板默认坐标覆盖"
)

POWER_LORA = [
    {},
    {"type": "PowerLoraLoaderHeaderWidget"},
    {
        "on": True,
        "lora": "Niji_Sweet_Spot-KREA2_v1.safetensors",
        "strength": 0.85,
        "strengthTwo": None,
    },
    {
        "on": True,
        "lora": "lora_krea2_nd_dark.safetensors",
        "strength": 0.65,
        "strengthTwo": None,
    },
    {},
    "",
]

STYLE_TRIGGERS_ZH = "@NJSW33T, @Cornflower, 杰作, 最佳质量, 超高清, 高细节, 柔光, 空灵氛围"
STYLE_TRIGGERS_EN = (
    "@NJSW33T, @Cornflower, masterpiece, best quality, absurdres, "
    "highly detailed, soft lighting, ethereal atmosphere"
)


def _new_link(wf: dict, src: int, src_slot: int, dst: int, dst_slot: int, typ: str) -> int:
    lid = int(wf.get("last_link_id") or 0) + 1
    wf["last_link_id"] = lid
    wf["links"].append([lid, src, src_slot, dst, dst_slot, typ])
    return lid


def _set_out_links(node: dict, slot: int, links: list[int]) -> None:
    outs = node.get("outputs") or []
    if slot < len(outs):
        outs[slot]["links"] = links
        outs[slot]["slot_index"] = slot


def _set_in_link(node: dict, slot: int, link_id: int | None) -> None:
    inputs = node.get("inputs") or []
    if slot < len(inputs):
        inputs[slot]["link"] = link_id


def _ensure_loader_stack(wf: dict, nodes: dict) -> None:
    """If source is still Checkpoint-based SDXL, insert UNET/CLIP/VAE/Aura/CFG like Anima."""
    n1 = nodes.get(1) or {}
    if n1.get("type") == "UNETLoader" and CLIP_ID in nodes and VAE_ID in nodes:
        return

    ck = nodes[1]
    nodes[1] = {
        "id": UNET_ID,
        "type": "UNETLoader",
        "pos": list(ck["pos"]),
        "size": [320, 100],
        "flags": {},
        "order": ck.get("order", 0),
        "mode": 0,
        "inputs": [],
        "outputs": [
            {
                "localized_name": "MODEL",
                "name": "MODEL",
                "type": "MODEL",
                "slot_index": 0,
                "links": [],
            }
        ],
        "title": "Krea2 UNET (换这里)",
        "properties": {"Node name for S&R": "UNETLoader"},
        "widgets_values": ["moodyKrea2Mix_cutieXEDITION.safetensors", "default"],
    }
    nodes[CLIP_ID] = {
        "id": CLIP_ID,
        "type": "CLIPLoader",
        "pos": [-300, 280],
        "size": [360, 130],
        "flags": {},
        "order": 1,
        "mode": 0,
        "inputs": [],
        "outputs": [
            {
                "localized_name": "CLIP",
                "name": "CLIP",
                "type": "CLIP",
                "slot_index": 0,
                "links": [],
            }
        ],
        "title": "Qwen3-VL CLIP (krea2)",
        "properties": {"Node name for S&R": "CLIPLoader"},
        "widgets_values": ["qwen3vl_4b_fp8_scaled.safetensors", "krea2", "default"],
    }
    nodes[VAE_ID] = {
        "id": VAE_ID,
        "type": "VAELoader",
        "pos": [-300, 440],
        "size": [320, 80],
        "flags": {},
        "order": 2,
        "mode": 0,
        "inputs": [],
        "outputs": [
            {
                "localized_name": "VAE",
                "name": "VAE",
                "type": "VAE",
                "slot_index": 0,
                "links": [],
            }
        ],
        "title": "Qwen Image VAE",
        "properties": {"Node name for S&R": "VAELoader"},
        "widgets_values": ["qwen_image_vae.safetensors"],
    }
    pl = nodes[120]
    nodes[AURA_ID] = {
        "id": AURA_ID,
        "type": "ModelSamplingAuraFlow",
        "pos": [610, 300],
        "size": [280, 60],
        "flags": {},
        "order": 12,
        "mode": 0,
        "inputs": [{"name": "model", "type": "MODEL", "link": None}],
        "outputs": [{"name": "MODEL", "type": "MODEL", "links": []}],
        "title": "AuraFlow shift",
        "properties": {"Node name for S&R": "ModelSamplingAuraFlow"},
        "widgets_values": [1.15],
    }
    nodes[CFGN_ID] = {
        "id": CFGN_ID,
        "type": "CFGNorm",
        "pos": [610, 390],
        "size": [280, 60],
        "flags": {},
        "order": 13,
        "mode": 0,
        "inputs": [{"name": "model", "type": "MODEL", "link": None}],
        "outputs": [{"name": "patched_model", "type": "MODEL", "links": []}],
        "title": "CFGNorm",
        "properties": {"Node name for S&R": "CFGNorm"},
        "widgets_values": [1],
    }

    drop_link_ids = set()
    for L in wf["links"]:
        lid, src, src_slot, dst, dst_slot, typ = L
        if src == 1:
            drop_link_ids.add(lid)
        if src == 120 and src_slot == 0 and dst in (121, 21):
            drop_link_ids.add(lid)

    wf["links"] = [L for L in wf["links"] if L[0] not in drop_link_ids]
    for n in nodes.values():
        for inp in n.get("inputs") or []:
            if inp.get("link") in drop_link_ids:
                inp["link"] = None
    for nid in (1, 120, 121):
        if nid in nodes:
            for o in nodes[nid].get("outputs") or []:
                if o.get("links"):
                    o["links"] = [x for x in o["links"] if x not in drop_link_ids]

    l_unet = _new_link(wf, UNET_ID, 0, 120, 0, "MODEL")
    _set_out_links(nodes[UNET_ID], 0, [l_unet])
    _set_in_link(nodes[120], 0, l_unet)

    l_clip = _new_link(wf, CLIP_ID, 0, 120, 1, "CLIP")
    _set_out_links(nodes[CLIP_ID], 0, [l_clip])
    _set_in_link(nodes[120], 1, l_clip)

    l_vae_dec = _new_link(wf, VAE_ID, 0, 17, 1, "VAE")
    l_vae_fd = _new_link(wf, VAE_ID, 0, 21, 3, "VAE")
    _set_out_links(nodes[VAE_ID], 0, [l_vae_dec, l_vae_fd])
    _set_in_link(nodes[17], 1, l_vae_dec)
    _set_in_link(nodes[21], 3, l_vae_fd)

    l_pl_aura = _new_link(wf, 120, 0, AURA_ID, 0, "MODEL")
    l_aura_cfg = _new_link(wf, AURA_ID, 0, CFGN_ID, 0, "MODEL")
    l_cfg_lane = _new_link(wf, CFGN_ID, 0, 121, 0, "MODEL")
    l_cfg_face = _new_link(wf, CFGN_ID, 0, 21, 1, "MODEL")
    nodes[120]["outputs"][0]["links"] = [l_pl_aura]
    _set_in_link(nodes[AURA_ID], 0, l_pl_aura)
    _set_out_links(nodes[AURA_ID], 0, [l_aura_cfg])
    _set_in_link(nodes[CFGN_ID], 0, l_aura_cfg)
    _set_out_links(nodes[CFGN_ID], 0, [l_cfg_lane, l_cfg_face])
    _set_in_link(nodes[121], 0, l_cfg_lane)
    _set_in_link(nodes[21], 1, l_cfg_face)


def main() -> None:
    if ANIMA.is_file():
        src = ANIMA
    elif ARCH.is_file():
        src = ARCH
    else:
        src = SRC
    wf = json.loads(src.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in wf["nodes"]}

    _ensure_loader_stack(wf, nodes)

    # Retarget loaders / sampling for Krea2 Moody
    nodes[1]["type"] = "UNETLoader"
    nodes[1]["title"] = "Krea2 UNET (换这里)"
    nodes[1]["widgets_values"] = ["moodyKrea2Mix_cutieXEDITION.safetensors", "default"]
    nodes[1]["properties"] = {"Node name for S&R": "UNETLoader"}

    nodes[CLIP_ID]["type"] = "CLIPLoader"
    nodes[CLIP_ID]["title"] = "Qwen3-VL CLIP (krea2)"
    nodes[CLIP_ID]["widgets_values"] = [
        "qwen3vl_4b_fp8_scaled.safetensors",
        "krea2",
        "default",
    ]
    nodes[CLIP_ID]["properties"] = {"Node name for S&R": "CLIPLoader"}
    # slightly wider for long TE filename
    nodes[CLIP_ID]["size"] = [360, 130]

    nodes[VAE_ID]["widgets_values"] = ["qwen_image_vae.safetensors"]
    nodes[VAE_ID]["title"] = "Qwen Image VAE"

    nodes[AURA_ID]["widgets_values"] = [1.15]
    nodes[AURA_ID]["title"] = "AuraFlow shift (Krea μ≈1.15)"
    nodes[CFGN_ID]["widgets_values"] = [1]

    nodes[28]["title"] = "Krea2 单图 · TriPose布局"
    nodes[28]["widgets_values"] = [NOTE]
    nodes[24]["widgets_values"] = ["Krea2_MoodyCutie_single"]
    nodes[120]["widgets_values"] = copy.deepcopy(POWER_LORA)
    nodes[120]["title"] = "多 LoRA (Niji·Cornflower)"

    if 27 in nodes and nodes[27].get("type") == "Seed (rgthree)":
        wv = nodes[27].get("widgets_values") or [-1, "", "", ""]
        wv[0] = -1
        nodes[27]["widgets_values"] = wv

    nodes[8]["widgets_values"] = [896, 1152, 1]
    nodes[8]["title"] = "Latent 896×1152"

    # Turbo-style defaults (Moody Mix is turbo-family)
    nodes[14]["widgets_values"] = [0, "fixed", 8, 1.0, "er_sde", "simple", 1]
    nodes[14]["title"] = "Sampler (Krea2 Turbo 8/CFG1)"
    nodes[113]["widgets_values"] = [0, "fixed", 4, 1.0, "euler", "simple", 0.3]
    nodes[113]["title"] = "精炼 Sampler (4·denoise0.3)"

    fd = nodes[21]["widgets_values"]
    fd[5] = 8
    fd[6] = 1.0
    fd[7] = "er_sde"
    fd[8] = "simple"
    fd[9] = 0.35

    # Style triggers live in 质量 lane (kept through tagmap)
    if 130 in nodes:
        nodes[130]["widgets_values"] = [STYLE_TRIGGERS_ZH]
    if 131 in nodes:
        wv = list(nodes[131].get("widgets_values") or [])
        while len(wv) < 6:
            wv.append("")
        wv[5] = STYLE_TRIGGERS_EN
        nodes[131]["widgets_values"] = wv

    for g in wf.get("groups") or []:
        title = g.get("title") or ""
        if "操作栏" in title or "Checkpoint" in title or "Anima UNET" in title:
            g["title"] = "操作栏 · Krea2 UNET / 多LoRA / Aura·CFG / Seed / 开·采样"
            b = g.get("bounding") or [240, 20, 1900, 250]
            g["bounding"] = [b[0], b[1], b[2], max(b[3], 460)]
        if title.startswith("单路采样"):
            g["title"] = "单路采样 · 放大 / 精炼 (Krea2)"

    wf["id"] = "cf-tripose-krea2-single-v1"
    wf["last_node_id"] = max(wf.get("last_node_id") or 0, CLIP_ID, VAE_ID, AURA_ID, CFGN_ID)
    wf["nodes"] = [nodes[i] for i in sorted(nodes)]

    text = json.dumps(wf, ensure_ascii=False, indent=2)
    OUT_KIT.parent.mkdir(parents=True, exist_ok=True)
    OUT_KIT.write_text(text, encoding="utf-8")
    OUT_WS.write_text(text, encoding="utf-8")
    for d in COMFY_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        (d / OUT_WS.name).write_text(text, encoding="utf-8")
        (d / "CF-TriPose-Krea2-single.json").write_text(text, encoding="utf-8")

    print("source:", str(src))
    print("wrote:", str(OUT_KIT))
    print("wrote:", str(OUT_WS))
    print("nodes", len(wf["nodes"]), "links", len(wf["links"]))


if __name__ == "__main__":
    main()
