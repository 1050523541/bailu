# -*- coding: utf-8 -*-
"""Build Wan2.2 I2V dual hi-lo workflow in TriPose-single layout style."""
from __future__ import annotations

import json
from pathlib import Path

OUT_WS = Path(r"E:\OneDrive\ComfyUI work flow\Wan2.2-I2V-单图框架.json")
OUT_KIT = Path(r"E:\OneDrive\ComfyUI work flow\packages\tripose-kit\workflows\CF-Wan22-I2V-single-frame.json")
COMFY_DIRS = [
    Path(r"E:\AIGC\ComfyUI-aki-v3\ComfyUI\user\default\workflows"),
    Path(r"E:\AIGC\ComfyUI-aki-v3\ComfyUI\user\workflows"),
]

NOTE = (
    "## Wan2.2 I2V · DaSiWa SnatchKiss Lightspeed\n\n"
    "布局沿用 TriPose 单图分区：操作栏 / 提示词 / 采样 / 输出。\n\n"
    "**模型（成对）**\n"
    "- Hi：`DasiwaWAN22I2V14BLightspeed_snatchkissHighV11`\n"
    "- Lo：`DasiwaWAN22I2V14BLightspeed_snatchkissLowV11`（必下，与 High 同页）\n"
    "- CLIP：`umt5_xxl_fp8_e4m3fn_scaled`（type=wan）\n"
    "- VAE：`wan_2.1_vae`\n"
    "- Lightspeed = Lightning 已烘焙 → **不要**再叠 lightx2v LoRA\n\n"
    "**用法 · 16GB**\n"
    "1. 换「起始图像」（Anima/TriPose/Krea2 出图）\n"
    "2. 中文运动提示 → 映射；重点写动作/镜头/环境动效\n"
    "3. 默认：4steps · CFG1 · shift5 · 480×832 · 49帧 · 16fps ≈3s\n"
    "4. 显存够再把帧提到 81（≈5s）或边长提到 720p\n"
    "5. 风格 LoRA 可塞 Hi/Lo Power Lora 空槽（Wan I2V 训的；先 0.3–0.6）\n"
    "6. Low 直链（pruned≈13.53GB）：https://civitai.com/api/download/models/2953485\n"
    "7. 配套：UMT5 / wan_2.1_vae 见 Comfy-Org Wan_2.1 / Wan_2.2 repackaged\n"
)

NEG = (
    "过曝, 欠曝, 静态, 运动模糊, 剧烈抖动, 镜头跳变, 闪烁, 抽搐, 肢体变形, 手指畸形, "
    "多余肢体, 角色复制, 身份漂移, 服装突变, 背景突变, 低清晰度, 低质量, JPEG压缩残留, "
    "字幕, 文字, 水印, 标志, "
    "The tones are vibrant, overexposed, static, details are unclear, subtitles, "
    "worst quality, low quality, motionless image, jitter, flicker"
)

POS_ZH = (
    "二次元少女, 柔和哥特洛丽塔, 蕾丝与缎带,\n"
    "缓缓转头看向镜头, 发丝与缎带随风轻摆, 微笑, 轻微推镜,\n"
    "动作连贯, 人物稳定, 电影感柔光"
)


def node(nid, ntype, pos, size, title=None, widgets=None, inputs=None, outputs=None, **extra):
    n = {
        "id": nid,
        "type": ntype,
        "pos": list(pos),
        "size": list(size),
        "flags": {},
        "order": 0,
        "mode": 0,
        "inputs": inputs or [],
        "outputs": outputs or [],
        "properties": {"Node name for S&R": ntype},
        "widgets_values": widgets if widgets is not None else [],
    }
    if title:
        n["title"] = title
    n.update(extra)
    return n


def out(name, typ, links=None, slot=0):
    return {
        "name": name,
        "type": typ,
        "slot_index": slot,
        "links": links or [],
    }


def inp(name, typ, link=None, shape=None):
    d = {"name": name, "type": typ, "link": link}
    if shape is not None:
        d["shape"] = shape
    return d


def main() -> None:
    links = []
    lid = 0

    def link(src, ss, dst, ds, typ):
        nonlocal lid
        lid += 1
        links.append([lid, src, ss, dst, ds, typ])
        return lid

    # --- ids ---
    HI, LO = 1, 2
    CLIP, VAE = 3, 4
    PL_HI, PL_LO = 5, 6
    SHIFT_HI, SHIFT_LO = 7, 8
    SEED = 9
    NOTE_N = 10
    ZH_POS, MAP_POS = 100, 101
    ZH_NEG, MAP_NEG = 108, 109
    ENC_POS, ENC_NEG = 20, 21
    IMG, RESIZE = 30, 31
    WAN_COND = 40
    KS_HI, KS_LO = 50, 51
    DECODE, CREATE, SAVE = 60, 61, 62

    # Lightspeed: lightning baked in — empty Power Lora (Add Lora only; no fake None row)
    pl_hi_w = [
        {},
        {"type": "PowerLoraLoaderHeaderWidget"},
        {},
        "",
    ]
    pl_lo_w = [
        {},
        {"type": "PowerLoraLoaderHeaderWidget"},
        {},
        "",
    ]
    HI_NAME = "DasiwaWAN22I2V14BLightspeed_snatchkissHighV11.safetensors"
    LO_NAME = "DasiwaWAN22I2V14BLightspeed_snatchkissLowV11.safetensors"

    nodes = []

    # Loaders
    nodes.append(
        node(
            HI,
            "UNETLoader",
            [240, 40],
            [360, 100],
            "UNET Hi · SnatchKiss Lightspeed",
            [HI_NAME, "default"],
            outputs=[out("MODEL", "MODEL")],
        )
    )
    nodes.append(
        node(
            LO,
            "UNETLoader",
            [240, 170],
            [360, 100],
            "UNET Lo · SnatchKiss Lightspeed",
            [LO_NAME, "default"],
            outputs=[out("MODEL", "MODEL")],
        )
    )
    nodes.append(
        node(
            CLIP,
            "CLIPLoader",
            [-300, 40],
            [320, 120],
            "UMT5 CLIP (wan)",
            ["umt5_xxl_fp8_e4m3fn_scaled.safetensors", "wan", "default"],
            outputs=[out("CLIP", "CLIP")],
        )
    )
    nodes.append(
        node(
            VAE,
            "VAELoader",
            [-300, 200],
            [320, 80],
            "Wan VAE",
            ["wan_2.1_vae.safetensors"],
            outputs=[out("VAE", "VAE")],
        )
    )

    # Power Lora + shift
    nodes.append(
        node(
            PL_HI,
            "Power Lora Loader (rgthree)",
            [640, 40],
            [560, 220],
            "Hi LoRA (空槽·可加风格，勿叠Lightning)",
            pl_hi_w,
            inputs=[inp("model", "MODEL"), inp("clip", "CLIP")],
            outputs=[out("MODEL", "MODEL"), out("CLIP", "CLIP")],
            **{
                "properties": {
                    "Show Strengths": "Single Strength",
                    "Node name for S&R": "Power Lora Loader (rgthree)",
                }
            },
        )
    )
    nodes.append(
        node(
            PL_LO,
            "Power Lora Loader (rgthree)",
            [640, 270],
            [560, 220],
            "Lo LoRA (空槽·可加风格，勿叠Lightning)",
            pl_lo_w,
            inputs=[inp("model", "MODEL"), inp("clip", "CLIP")],
            outputs=[out("MODEL", "MODEL"), out("CLIP", "CLIP")],
            **{
                "properties": {
                    "Show Strengths": "Single Strength",
                    "Node name for S&R": "Power Lora Loader (rgthree)",
                }
            },
        )
    )
    nodes.append(
        node(
            SHIFT_HI,
            "ModelSamplingSD3",
            [1080, 40],
            [280, 60],
            "Hi shift (Lightning=5)",
            [5.0],
            inputs=[inp("model", "MODEL")],
            outputs=[out("MODEL", "MODEL")],
        )
    )
    nodes.append(
        node(
            SHIFT_LO,
            "ModelSamplingSD3",
            [1080, 140],
            [280, 60],
            "Lo shift (Lightning=5)",
            [5.0],
            inputs=[inp("model", "MODEL")],
            outputs=[out("MODEL", "MODEL")],
        )
    )
    nodes.append(
        node(
            SEED,
            "Seed (rgthree)",
            [1400, 40],
            [260, 130],
            "Seed 同步器",
            [-1, "", "", ""],  # -1 = Randomize Each Time (rgthree Seed)
            outputs=[out("SEED", "INT")],
        )
    )
    nodes.append(
        node(
            NOTE_N,
            "MarkdownNote",
            [-300, 320],
            [520, 360],
            "说明",
            [NOTE],
        )
    )

    # Prompts (TriPose-style zh + map)
    nodes.append(
        node(
            ZH_POS,
            "PrimitiveStringMultiline",
            [240, 520],
            [360, 180],
            "中文 运动提示",
            [POS_ZH],
            outputs=[out("STRING", "STRING")],
        )
    )
    tagmap_widgets = ["danbooru_zh+nsfw", "", "keep", True, False, "", ""]
    tagmap_inputs = [
        inp("text", "STRING"),
        inp("dictionary", "COMBO"),
        inp("custom_path", "STRING"),
        inp("keep_unknown", "COMBO"),
        inp("passthrough_english", "BOOLEAN"),
        inp("google_fallback", "BOOLEAN"),
    ]
    tagmap_outputs = [
        out("mapped_text", "STRING", slot=0),
        out("unmapped_text", "STRING", slot=1),
    ]
    nodes.append(
        node(
            MAP_POS,
            "TriPoseZhTagMap",
            [620, 520],
            [440, 300],
            "映射 运动",
            tagmap_widgets,
            inputs=tagmap_inputs,
            outputs=tagmap_outputs,
        )
    )
    nodes.append(
        node(
            ZH_NEG,
            "PrimitiveStringMultiline",
            [240, 740],
            [360, 160],
            "中文 Negative",
            [NEG],
            outputs=[out("STRING", "STRING")],
        )
    )
    nodes.append(
        node(
            MAP_NEG,
            "TriPoseZhTagMap",
            [620, 740],
            [440, 300],
            "映射 Neg",
            list(tagmap_widgets),
            inputs=[
                inp("text", "STRING"),
                inp("dictionary", "COMBO"),
                inp("custom_path", "STRING"),
                inp("keep_unknown", "COMBO"),
                inp("passthrough_english", "BOOLEAN"),
                inp("google_fallback", "BOOLEAN"),
            ],
            outputs=[
                out("mapped_text", "STRING", slot=0),
                out("unmapped_text", "STRING", slot=1),
            ],
        )
    )
    nodes.append(
        node(
            ENC_POS,
            "CLIPTextEncode",
            [980, 520],
            [360, 160],
            "CLIP 运动 Positive",
            ["(from TriPoseZhTagMap)"],
            inputs=[inp("clip", "CLIP"), inp("text", "STRING")],
            outputs=[out("CONDITIONING", "CONDITIONING")],
        )
    )
    nodes.append(
        node(
            ENC_NEG,
            "CLIPTextEncode",
            [980, 720],
            [360, 160],
            "CLIP Negative",
            ["(from TriPoseZhTagMap)"],
            inputs=[inp("clip", "CLIP"), inp("text", "STRING")],
            outputs=[out("CONDITIONING", "CONDITIONING")],
        )
    )

    # Image + condition
    nodes.append(
        node(
            IMG,
            "LoadImage",
            [240, 960],
            [360, 340],
            "起始图像 / Replace Me",
            ["example.png", "image"],
            outputs=[out("IMAGE", "IMAGE"), out("MASK", "MASK")],
        )
    )
    # ImageResizeKJv2 if available — keep simple: WanImageToVideo has w/h widgets
    nodes.append(
        node(
            WAN_COND,
            "WanImageToVideo",
            [640, 960],
            [400, 260],
            "Wan 图生视频条件",
            [480, 832, 49, 1],  # 16GB first; raise to 81 when stable
            inputs=[
                inp("positive", "CONDITIONING"),
                inp("negative", "CONDITIONING"),
                inp("vae", "VAE"),
                inp("clip_vision_output", "CLIP_VISION_OUTPUT", shape=7),
                inp("start_image", "IMAGE", shape=7),
            ],
            outputs=[
                out("positive", "CONDITIONING", slot=0),
                out("negative", "CONDITIONING", slot=1),
                out("latent", "LATENT", slot=2),
            ],
        )
    )

    # Dual KSamplerAdvanced
    # widgets: add_noise, noise_seed, steps, cfg, sampler, scheduler, start, end, return_leftover, [control_after?]
    # KSamplerAdvanced UI widgets: add_noise, noise_seed, control_after, steps, cfg,
    # sampler, scheduler, start, end, return_leftover
    ks_inputs = [
        inp("model", "MODEL"),
        inp("add_noise", "COMBO"),
        inp("noise_seed", "INT"),
        inp("steps", "INT"),
        inp("cfg", "FLOAT"),
        inp("sampler_name", "COMBO"),
        inp("scheduler", "COMBO"),
        inp("positive", "CONDITIONING"),
        inp("negative", "CONDITIONING"),
        inp("latent_image", "LATENT"),
        inp("start_at_step", "INT"),
        inp("end_at_step", "INT"),
        inp("return_with_leftover_noise", "COMBO"),
    ]
    nodes.append(
        node(
            KS_HI,
            "KSamplerAdvanced",
            [1400, 240],
            [320, 460],
            "Hi Pass (0→2)",
            ["enable", 0, "fixed", 4, 1.0, "euler", "simple", 0, 2, "enable"],
            inputs=ks_inputs,
            outputs=[out("LATENT", "LATENT")],
        )
    )
    nodes.append(
        node(
            KS_LO,
            "KSamplerAdvanced",
            [1760, 240],
            [320, 460],
            "Lo Pass (2→4)",
            ["disable", 0, "fixed", 4, 1.0, "euler", "simple", 2, 4, "disable"],
            inputs=[
                inp("model", "MODEL"),
                inp("add_noise", "COMBO"),
                inp("noise_seed", "INT"),
                inp("steps", "INT"),
                inp("cfg", "FLOAT"),
                inp("sampler_name", "COMBO"),
                inp("scheduler", "COMBO"),
                inp("positive", "CONDITIONING"),
                inp("negative", "CONDITIONING"),
                inp("latent_image", "LATENT"),
                inp("start_at_step", "INT"),
                inp("end_at_step", "INT"),
                inp("return_with_leftover_noise", "COMBO"),
            ],
            outputs=[out("LATENT", "LATENT")],
        )
    )

    nodes.append(
        node(
            DECODE,
            "VAEDecode",
            [2120, 240],
            [260, 60],
            "VAEDecode",
            [],
            inputs=[inp("samples", "LATENT"), inp("vae", "VAE")],
            outputs=[out("IMAGE", "IMAGE")],
        )
    )
    nodes.append(
        node(
            CREATE,
            "CreateVideo",
            [2120, 340],
            [280, 80],
            "CreateVideo 16fps",
            [16],
            inputs=[inp("images", "IMAGE"), inp("audio", "AUDIO", shape=7)],
            outputs=[out("VIDEO", "VIDEO")],
        )
    )
    nodes.append(
        node(
            SAVE,
            "SaveVideo",
            [2120, 460],
            [520, 400],
            "Save 视频",
            ["video/Wan22_SnatchKiss_I2V", "auto", "auto"],
            inputs=[inp("video", "VIDEO")],
            outputs=[],
        )
    )

    by_id = {n["id"]: n for n in nodes}

    def wire(src, ss, dst, ds, typ):
        i = link(src, ss, dst, ds, typ)
        by_id[src]["outputs"][ss]["links"].append(i)
        # find matching input by index among typed inputs — use ds as index into inputs list
        by_id[dst]["inputs"][ds]["link"] = i
        return i

    # Model path: UNET → PowerLora → Shift → KSampler
    wire(HI, 0, PL_HI, 0, "MODEL")
    wire(LO, 0, PL_LO, 0, "MODEL")
    wire(CLIP, 0, PL_HI, 1, "CLIP")
    wire(CLIP, 0, PL_LO, 1, "CLIP")
    wire(PL_HI, 0, SHIFT_HI, 0, "MODEL")
    wire(PL_LO, 0, SHIFT_LO, 0, "MODEL")
    wire(SHIFT_HI, 0, KS_HI, 0, "MODEL")
    wire(SHIFT_LO, 0, KS_LO, 0, "MODEL")

    # CLIP encodes from Hi PowerLora CLIP out (passthrough)
    wire(PL_HI, 1, ENC_POS, 0, "CLIP")
    wire(PL_HI, 1, ENC_NEG, 0, "CLIP")

    # zh → map → encode text
    wire(ZH_POS, 0, MAP_POS, 0, "STRING")
    wire(MAP_POS, 0, ENC_POS, 1, "STRING")
    wire(ZH_NEG, 0, MAP_NEG, 0, "STRING")
    wire(MAP_NEG, 0, ENC_NEG, 1, "STRING")

    # Wan condition
    wire(ENC_POS, 0, WAN_COND, 0, "CONDITIONING")
    wire(ENC_NEG, 0, WAN_COND, 1, "CONDITIONING")
    wire(VAE, 0, WAN_COND, 2, "VAE")
    wire(IMG, 0, WAN_COND, 4, "IMAGE")

    # Samplers: input index map for KSamplerAdvanced
    # 0 model, 1 add_noise, 2 noise_seed, 3 steps, 4 cfg, 5 sampler, 6 scheduler,
    # 7 positive, 8 negative, 9 latent, 10 start, 11 end, 12 return
    wire(WAN_COND, 0, KS_HI, 7, "CONDITIONING")
    wire(WAN_COND, 1, KS_HI, 8, "CONDITIONING")
    wire(WAN_COND, 2, KS_HI, 9, "LATENT")
    wire(WAN_COND, 0, KS_LO, 7, "CONDITIONING")
    wire(WAN_COND, 1, KS_LO, 8, "CONDITIONING")
    wire(KS_HI, 0, KS_LO, 9, "LATENT")
    wire(SEED, 0, KS_HI, 2, "INT")
    wire(SEED, 0, KS_LO, 2, "INT")

    wire(KS_LO, 0, DECODE, 0, "LATENT")
    wire(VAE, 0, DECODE, 1, "VAE")
    wire(DECODE, 0, CREATE, 0, "IMAGE")
    wire(CREATE, 0, SAVE, 0, "VIDEO")

    # Assign orders roughly
    for i, n in enumerate(sorted(nodes, key=lambda x: x["id"])):
        n["order"] = i

    groups = [
        {
            "id": 10,
            "title": "操作栏 · SnatchKiss Hi/Lo / PowerLora空槽 / Shift5 / Seed",
            "bounding": [220, 10, 1480, 480],
            "color": "#3f789e",
            "font_size": 24,
            "flags": {},
        },
        {
            "id": 1,
            "title": "提示词 · 中文运动 / Neg + 映射",
            "bounding": [220, 490, 1160, 430],
            "color": "#A88",
            "font_size": 24,
            "flags": {},
        },
        {
            "id": 2,
            "title": "起始图 · Wan 条件",
            "bounding": [220, 930, 860, 400],
            "color": "#8A8",
            "font_size": 24,
            "flags": {},
        },
        {
            "id": 3,
            "title": "双路采样 Hi→Lo · 解码保存",
            "bounding": [1380, 200, 1300, 700],
            "color": "#88A",
            "font_size": 24,
            "flags": {},
        },
    ]

    wf = {
        "id": "cf-wan22-i2v-tripose-frame",
        "revision": 0,
        "last_node_id": max(n["id"] for n in nodes),
        "last_link_id": lid,
        "nodes": nodes,
        "links": links,
        "groups": groups,
        "config": {},
        "extra": {"ds": {"scale": 0.65, "offset": [80, 20]}},
        "version": 0.4,
    }

    text = json.dumps(wf, ensure_ascii=False, indent=2)
    OUT_WS.write_text(text, encoding="utf-8")
    OUT_KIT.parent.mkdir(parents=True, exist_ok=True)
    OUT_KIT.write_text(text, encoding="utf-8")
    for d in COMFY_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        (d / OUT_WS.name).write_text(text, encoding="utf-8")
        (d / "CF-Wan22-I2V-单图框架.json").write_text(text, encoding="utf-8")

    print("wrote", OUT_WS)
    print("nodes", len(nodes), "links", len(links))


if __name__ == "__main__":
    main()
