# -*- coding: utf-8 -*-
"""Adapt TriPose single-image layout to Anima (MiaoMiao) loaders.

Preserves node positions / groups / zh-tagmap / Power Lora / refine / FaceDetailer.
Replaces CheckpointLoader with UNET+CLIP+VAE and inserts AuraFlow+CFGNorm on MODEL path.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "workflows" / "CF-TriPose-SDXL-single.json"
# Prefer archived user-tuned layout if present
ARCH = (
    Path(__file__).resolve().parents[1]
    / "workflows"
    / "archive"
    / "CF-TriPose-SDXL-single-v1.0.0.json"
)
OUT_KIT = Path(__file__).resolve().parents[1] / "workflows" / "CF-TriPose-Anima-single.json"
OUT_WS = Path(r"E:\OneDrive\ComfyUI work flow\Anima-MiaoMiao-单图.json")
COMFY_DIRS = [
    Path(r"E:\AIGC\ComfyUI-aki-v3\ComfyUI\user\default\workflows"),
    Path(r"E:\AIGC\ComfyUI-aki-v3\ComfyUI\user\workflows"),
]

UNET_ID, CLIP_ID, VAE_ID = 1, 140, 141
AURA_ID, CFGN_ID = 142, 143

NOTE = (
    "Anima 单图 · 布局沿用 TriPose 单图 v1.0\n"
    "• 加载：UNET(MiaoMiao) + Qwen CLIP + Qwen VAE（非 SDXL Checkpoint）\n"
    "• 操作栏：UNET → Power Lora → AuraFlow/CFGNorm → 开·采样 · Seed\n"
    "• 提示词区/词库映射/放大精炼/FaceDetailer 骨架保留\n"
    "• 默认底模 miaomiao3DHarem_animaLH3D10；可切 miaomiaoHarem_anima15\n"
    "• 品质档：30steps CFG4.5 er_sde/simple；开 Turbo 时改 12steps CFG1\n"
    "• 布局坐标沿用单图定稿，勿被模板默认坐标覆盖"
)

POWER_LORA = [
    {},
    {"type": "PowerLoraLoaderHeaderWidget"},
    {"on": True, "lora": "Anima_AI_Cunnyfunky.safetensors", "strength": 1.0, "strengthTwo": None},
    {"on": False, "lora": "anima\\anima-turbo-lora-v0.1.safetensors", "strength": 1.0, "strengthTwo": None},
    {},
    "",
]


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


def main() -> None:
    src = ARCH if ARCH.is_file() else SRC
    wf = json.loads(src.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in wf["nodes"]}

    # --- Drop Checkpoint; keep id=1 as UNET at same pos ---
    ck = nodes[1]
    unet = {
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
        "title": "Anima UNET (换这里)",
        "properties": {"Node name for S&R": "UNETLoader"},
        "widgets_values": ["miaomiao3DHarem_animaLH3D10.safetensors", "default"],
    }
    nodes[1] = unet

    # CLIP / VAE to the left of ops bar (near Note), keep bar layout intact
    nodes[CLIP_ID] = {
        "id": CLIP_ID,
        "type": "CLIPLoader",
        "pos": [-300, 280],
        "size": [320, 120],
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
        "title": "Qwen3 CLIP (Anima)",
        "properties": {"Node name for S&R": "CLIPLoader"},
        "widgets_values": ["qwen_3_06b_base.safetensors", "stable_diffusion", "default"],
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

    # AuraFlow + CFGNorm under Power Lora (ops column)
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
        "widgets_values": [3.6],
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

    # Note / Save / LoRA / sizes / samplers
    nodes[28]["title"] = "Anima 单图 · TriPose布局"
    nodes[28]["widgets_values"] = [NOTE]
    nodes[24]["widgets_values"] = ["Anima_MiaoMiao_single"]
    nodes[120]["widgets_values"] = copy.deepcopy(POWER_LORA)
    nodes[120]["title"] = "多 LoRA (Cunnyfunky·Turbo可选)"
    nodes[8]["widgets_values"] = [896, 1152, 1]
    nodes[8]["title"] = "Latent 896×1152"
    # Base sampler — Anima quality
    nodes[14]["widgets_values"] = [0, "fixed", 30, 4.5, "er_sde", "simple", 1]
    nodes[14]["title"] = "Sampler (Anima品质)"
    # Refine — gentler for Anima
    nodes[113]["widgets_values"] = [0, "fixed", 20, 4.0, "er_sde", "simple", 0.35]
    nodes[113]["title"] = "精炼 Sampler (denoise0.35)"
    # FaceDetailer sampler widgets indices: seed_mode, steps, cfg, sampler, scheduler, denoise
    fd = nodes[21]["widgets_values"]
    # [guide_size, guide_size_for, max_size, seed, seed_mode, steps, cfg, sampler, scheduler, denoise, ...]
    fd[5] = 20
    fd[6] = 4.0
    fd[7] = "er_sde"
    fd[8] = "simple"
    fd[9] = 0.35

    # --- Rebuild MODEL/CLIP/VAE links ---
    # Remove links involving old Checkpoint outputs (src=1 any slot) — we'll rebuild.
    # Also remove PowerLora MODEL outs to lane/face (223, 232) — rewire via CFGNorm.
    drop_link_ids = set()
    for L in wf["links"]:
        lid, src, src_slot, dst, dst_slot, typ = L
        if src == 1:
            drop_link_ids.add(lid)
        # old Power Lora MODEL → lane / face
        if src == 120 and src_slot == 0 and dst in (121, 21):
            drop_link_ids.add(lid)

    wf["links"] = [L for L in wf["links"] if L[0] not in drop_link_ids]

    # Clear stale input links that pointed at dropped ids
    for n in nodes.values():
        for inp in n.get("inputs") or []:
            if inp.get("link") in drop_link_ids:
                inp["link"] = None

    # Clear stale output link lists for rewired nodes
    for nid in (1, 120, 121):
        if nid in nodes:
            for o in nodes[nid].get("outputs") or []:
                if o.get("links"):
                    o["links"] = [x for x in o["links"] if x not in drop_link_ids]

    # UNET → Power Lora MODEL
    l_unet = _new_link(wf, UNET_ID, 0, 120, 0, "MODEL")
    _set_out_links(nodes[UNET_ID], 0, [l_unet])
    _set_in_link(nodes[120], 0, l_unet)

    # CLIP → Power Lora CLIP
    l_clip = _new_link(wf, CLIP_ID, 0, 120, 1, "CLIP")
    _set_out_links(nodes[CLIP_ID], 0, [l_clip])
    _set_in_link(nodes[120], 1, l_clip)

    # VAE → VAEDecode + FaceDetailer
    l_vae_dec = _new_link(wf, VAE_ID, 0, 17, 1, "VAE")
    l_vae_fd = _new_link(wf, VAE_ID, 0, 21, 3, "VAE")
    _set_out_links(nodes[VAE_ID], 0, [l_vae_dec, l_vae_fd])
    _set_in_link(nodes[17], 1, l_vae_dec)
    _set_in_link(nodes[21], 3, l_vae_fd)

    # Power Lora MODEL → AuraFlow → CFGNorm → LaneEnable + FaceDetailer
    # Find model input slot on Power Lora output consumers
    l_pl_aura = _new_link(wf, 120, 0, AURA_ID, 0, "MODEL")
    l_aura_cfg = _new_link(wf, AURA_ID, 0, CFGN_ID, 0, "MODEL")
    l_cfg_lane = _new_link(wf, CFGN_ID, 0, 121, 0, "MODEL")
    l_cfg_face = _new_link(wf, CFGN_ID, 0, 21, 1, "MODEL")

    # Power Lora MODEL outputs: only Aura now (CLIP outs untouched)
    pl_model_out = nodes[120]["outputs"][0]
    # keep only non-MODEL destinations that weren't dropped; then add aura
    pl_model_out["links"] = [l_pl_aura]

    _set_in_link(nodes[AURA_ID], 0, l_pl_aura)
    _set_out_links(nodes[AURA_ID], 0, [l_aura_cfg])
    _set_in_link(nodes[CFGN_ID], 0, l_aura_cfg)
    _set_out_links(nodes[CFGN_ID], 0, [l_cfg_lane, l_cfg_face])
    _set_in_link(nodes[121], 0, l_cfg_lane)
    _set_in_link(nodes[21], 1, l_cfg_face)

    # Expand ops group slightly for Aura/CFGNorm under Power Lora
    for g in wf.get("groups") or []:
        title = g.get("title") or ""
        if "操作栏" in title or "Checkpoint" in title:
            g["title"] = "操作栏 · Anima UNET / 多LoRA / Aura·CFG / Seed / 开·采样"
            b = g.get("bounding") or [240, 20, 1900, 250]
            # grow downward to cover Aura/CFGNorm
            g["bounding"] = [b[0], b[1], b[2], max(b[3], 460)]
        if title.startswith("单路采样"):
            g["title"] = "单路采样 · 放大 / 精炼 (Anima)"

    wf["id"] = "cf-tripose-anima-single-v1"
    wf["last_node_id"] = max(wf.get("last_node_id") or 0, CLIP_ID, VAE_ID, AURA_ID, CFGN_ID)
    wf["nodes"] = [nodes[i] for i in sorted(nodes)]

    # Write
    text = json.dumps(wf, ensure_ascii=False, indent=2)
    OUT_KIT.parent.mkdir(parents=True, exist_ok=True)
    OUT_KIT.write_text(text, encoding="utf-8")
    OUT_WS.write_text(text, encoding="utf-8")
    for d in COMFY_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        (d / OUT_WS.name).write_text(text, encoding="utf-8")
        (d / "CF-TriPose-Anima-single.json").write_text(text, encoding="utf-8")

    print("source:", str(src))
    print("wrote:", str(OUT_KIT))
    print("wrote:", str(OUT_WS))
    print("nodes", len(wf["nodes"]), "links", len(wf["links"]))


if __name__ == "__main__":
    main()
