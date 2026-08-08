# -*- coding: utf-8 -*-
"""OC Design helpers: optional IPAdapter, optional ref load, image stack."""
from __future__ import annotations

import os
from typing import Optional, Tuple

import folder_paths
import node_helpers
import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence


def _blank_image(h: int = 8, w: int = 8) -> torch.Tensor:
    return torch.zeros((1, h, w, 3), dtype=torch.float32)


def _has_valid_image(image: Optional[torch.Tensor], min_side: int = 16, std_eps: float = 1e-3) -> bool:
    if image is None:
        return False
    if not isinstance(image, torch.Tensor):
        return False
    if image.ndim != 4 or image.shape[0] < 1:
        return False
    _, h, w, _ = image.shape
    if min(h, w) < min_side:
        return False
    # near-constant / empty placeholder → treat as no ref
    try:
        if float(image.float().std()) < std_eps:
            return False
    except Exception:
        return False
    return True


class TriPoseOptionalLoadImage:
    """Reference image with explicit (none). Clearing / (none) means no IPAdapter."""

    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = []
        if os.path.isdir(input_dir):
            files = [
                f
                for f in os.listdir(input_dir)
                if os.path.isfile(os.path.join(input_dir, f))
            ]
            files = folder_paths.filter_files_content_types(files, ["image"])
        return {
            "required": {
                "image": (["(none)"] + sorted(files), {"image_upload": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "BOOLEAN")
    RETURN_NAMES = ("image", "has_image")
    FUNCTION = "load"
    CATEGORY = "TriPose"
    DESCRIPTION = "Optional reference image. Choose (none) or clear to disable IPAdapter."

    def load(self, image: str):
        if not image or image == "(none)":
            return (_blank_image(), False)

        image_path = folder_paths.get_annotated_filepath(image)
        img = node_helpers.pillow(Image.open, image_path)

        output_images = []
        for i in ImageSequence.Iterator(img):
            i = node_helpers.pillow(ImageOps.exif_transpose, i)
            if i.mode == "I":
                i = i.point(lambda j: j * (1 / 255))
            rgb = i.convert("RGB")
            arr = np.array(rgb).astype(np.float32) / 255.0
            output_images.append(torch.from_numpy(arr)[None, ...])

        if len(output_images) == 1:
            out = output_images[0]
        else:
            out = torch.cat(output_images, dim=0)
        return (out, True)

    @classmethod
    def IS_CHANGED(cls, image):
        if not image or image == "(none)":
            return "(none)"
        image_path = folder_paths.get_annotated_filepath(image)
        m = os.path.getmtime(image_path)
        return f"{image_path}:{m}"

    @classmethod
    def VALIDATE_INPUTS(cls, image):
        if not image or image == "(none)":
            return True
        if not folder_paths.exists_annotated_filepath(image):
            return f"Invalid image file: {image}"
        return True


class TriPoseOptionalIPAdapter:
    """Apply IPAdapter only when a valid reference image is provided; otherwise pass-through MODEL."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "preset": (
                    [
                        "LIGHT - SD1.5 only (low strength)",
                        "STANDARD (medium strength)",
                        "VIT-G (medium strength)",
                        "PLUS (high strength)",
                        "PLUS FACE (portraits)",
                        "FULL FACE - SD1.5 only (portraits stronger)",
                    ],
                    {"default": "PLUS FACE (portraits)"},
                ),
                "weight": ("FLOAT", {"default": 0.78, "min": -1.0, "max": 5.0, "step": 0.05}),
                "weight_type": (
                    [
                        "linear",
                        "ease in",
                        "ease out",
                        "ease in-out",
                        "style transfer",
                        "composition",
                        "strong style transfer",
                        "style and composition",
                    ],
                    {"default": "linear"},
                ),
                "start_at": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.001}),
                "end_at": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.001}),
                "min_side": ("INT", {"default": 16, "min": 1, "max": 512, "step": 1}),
            },
            "optional": {
                "image": ("IMAGE",),
                "has_image": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("MODEL", "STRING")
    RETURN_NAMES = ("model", "status")
    FUNCTION = "apply"
    CATEGORY = "TriPose"
    DESCRIPTION = (
        "If image is missing/blank/(none), returns the original MODEL unchanged "
        "(does not load IPAdapter). When a real ref is present, loads+applies IPAdapter."
    )

    def apply(
        self,
        model,
        preset,
        weight,
        weight_type,
        start_at,
        end_at,
        min_side,
        image=None,
        has_image=True,
    ):
        if has_image is False or not _has_valid_image(image, min_side=min_side):
            return (model, "bypass: no reference image")

        try:
            # Prefer Comfy's already-registered node classes (most reliable import path)
            from nodes import NODE_CLASS_MAPPINGS as COMFY_NODES  # type: ignore

            LoaderCls = COMFY_NODES.get("IPAdapterUnifiedLoader")
            AdvCls = COMFY_NODES.get("IPAdapterAdvanced")
            if LoaderCls is None or AdvCls is None:
                raise ImportError("IPAdapterUnifiedLoader / IPAdapterAdvanced not registered")
            loader = LoaderCls()
            model2, ipadapter = loader.load_models(model, preset)
            adv = AdvCls()
            out = adv.apply_ipadapter(
                model=model2,
                ipadapter=ipadapter,
                image=image,
                weight=float(weight),
                weight_type=weight_type,
                combine_embeds="concat",
                start_at=float(start_at),
                end_at=float(end_at),
                embeds_scaling="V only",
            )
            return (out[0], f"applied: preset={preset}, weight={weight}")
        except Exception as e:
            # Keep generation alive if IPAdapter weights/nodes are missing
            return (model, f"bypass: IPAdapter failed ({e})")


class TriPoseImageStack:
    """Stack 2–3 images into one master sheet (row / column / grid2)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image1": ("IMAGE",),
                "image2": ("IMAGE",),
                "layout": (["row", "column", "grid2"], {"default": "row"}),
                "gap": ("INT", {"default": 16, "min": 0, "max": 128, "step": 1}),
                "bg": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "target_height": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 8}),
            },
            "optional": {
                "image3": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "stack"
    CATEGORY = "TriPose"
    DESCRIPTION = "Combine design / expression / turnaround into one composite sheet."

    def _to_pil(self, t: torch.Tensor) -> Image.Image:
        arr = (t.detach().cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
        return Image.fromarray(arr, mode="RGB")

    def _resize_h(self, im: Image.Image, th: int) -> Image.Image:
        if th <= 0 or im.height == th:
            return im
        nw = max(1, int(round(im.width * (th / float(im.height)))))
        return im.resize((nw, th), Image.Resampling.LANCZOS)

    def _resize_w(self, im: Image.Image, tw: int) -> Image.Image:
        if tw <= 0 or im.width == tw:
            return im
        nh = max(1, int(round(im.height * (tw / float(im.width)))))
        return im.resize((tw, nh), Image.Resampling.LANCZOS)

    def stack(self, image1, image2, layout, gap, bg, target_height, image3=None):
        imgs = [self._to_pil(image1[0]), self._to_pil(image2[0])]
        if image3 is not None:
            imgs.append(self._to_pil(image3[0]))

        fill = int(round(float(bg) * 255))
        color = (fill, fill, fill)

        if layout == "row":
            th = target_height if target_height > 0 else max(i.height for i in imgs)
            imgs = [self._resize_h(i, th) for i in imgs]
            w = sum(i.width for i in imgs) + gap * (len(imgs) - 1)
            h = th
            canvas = Image.new("RGB", (w, h), color)
            x = 0
            for i in imgs:
                canvas.paste(i, (x, 0))
                x += i.width + gap
        elif layout == "column":
            tw = max(i.width for i in imgs)
            if target_height > 0:
                # scale each so widths match first; height hint ignored for column except via width
                pass
            imgs = [self._resize_w(i, tw) for i in imgs]
            w = tw
            h = sum(i.height for i in imgs) + gap * (len(imgs) - 1)
            canvas = Image.new("RGB", (w, h), color)
            y = 0
            for i in imgs:
                canvas.paste(i, (0, y))
                y += i.height + gap
        else:  # grid2: 2 on first row, 3rd centered below if present
            th = target_height if target_height > 0 else max(i.height for i in imgs[:2])
            top = [self._resize_h(i, th) for i in imgs[:2]]
            row_w = sum(i.width for i in top) + gap
            if len(imgs) == 2:
                canvas = Image.new("RGB", (row_w, th), color)
                canvas.paste(top[0], (0, 0))
                canvas.paste(top[1], (top[0].width + gap, 0))
            else:
                bottom = self._resize_h(imgs[2], th)
                w = max(row_w, bottom.width)
                h = th * 2 + gap
                canvas = Image.new("RGB", (w, h), color)
                x0 = (w - row_w) // 2
                canvas.paste(top[0], (x0, 0))
                canvas.paste(top[1], (x0 + top[0].width + gap, 0))
                canvas.paste(bottom, ((w - bottom.width) // 2, th + gap))

        out = np.array(canvas).astype(np.float32) / 255.0
        return (torch.from_numpy(out)[None, ...],)


NODE_CLASS_MAPPINGS = {
    "TriPoseOptionalLoadImage": TriPoseOptionalLoadImage,
    "TriPoseOptionalIPAdapter": TriPoseOptionalIPAdapter,
    "TriPoseImageStack": TriPoseImageStack,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TriPoseOptionalLoadImage": "TriPose 可选参考图",
    "TriPoseOptionalIPAdapter": "TriPose 可选IPAdapter",
    "TriPoseImageStack": "TriPose 三图拼合",
}


class TriPoseExecGate:
    """Force execution order: wait for depend IMAGE, then pass MODEL through."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
            },
            "optional": {
                "depend_image": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "gate"
    CATEGORY = "TriPose"
    DESCRIPTION = (
        "Execution barrier. Connect previous stage IMAGE to depend_image so this "
        "MODEL only flows after that stage finishes (设定→表情→三视图→裙底→主图)."
    )

    def gate(self, model, depend_image=None):
        if depend_image is not None:
            _ = depend_image.shape
        return (model,)


NODE_CLASS_MAPPINGS["TriPoseExecGate"] = TriPoseExecGate
NODE_DISPLAY_NAME_MAPPINGS["TriPoseExecGate"] = "TriPose 执行顺序门"


class TriPoseLaneEnable:
    """Per-lane on/off: when off, block this MODEL branch so Sampler→Save is skipped."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "enabled": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "label_on": "开",
                        "label_off": "关",
                        "tooltip": "关=本轮跳过该路采样/精炼/FaceDetailer/Save（其它路不受影响）",
                    },
                ),
            },
        }

    RETURN_TYPES = ("MODEL", "BOOLEAN")
    RETURN_NAMES = ("model", "enabled")
    FUNCTION = "apply"
    CATEGORY = "TriPose"
    DESCRIPTION = (
        "三态立绘分路开关。开：MODEL 原样通过；关：输出 ExecutionBlocker，"
        "下游整条链路不执行，便于只开「正常」快速校准角色。"
        "第二输出 enabled 供串行门判断上一路是否开启。"
    )

    def apply(self, model, enabled=True):
        if enabled:
            return (model, True)
        try:
            from comfy_execution.graph import ExecutionBlocker
        except ImportError:  # pragma: no cover — older Comfy
            raise RuntimeError(
                "TriPoseLaneEnable requires ComfyUI ExecutionBlocker "
                "(ComfyUI >= 0.2). Upgrade ComfyUI or leave the lane enabled."
            ) from None
        return (ExecutionBlocker(None), False)


NODE_CLASS_MAPPINGS["TriPoseLaneEnable"] = TriPoseLaneEnable
NODE_DISPLAY_NAME_MAPPINGS["TriPoseLaneEnable"] = "TriPose 立绘分路开关"


class TriPoseSeqGate:
    """Force lane order: wait for prior Save IMAGE when prior lane is on.

    Uses lazy prior_image so a disabled prior lane does not block later lanes.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "prior_lane_on": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "label_on": "等上路",
                        "label_off": "跳过等待",
                        "tooltip": "接上一路开关的 enabled；上路关则不阻塞本路",
                    },
                ),
            },
            "optional": {
                "prior_image": (
                    "IMAGE",
                    {
                        "lazy": True,
                        "tooltip": "接上一路 Save/FaceDetailer 成品图；上路开时等其完成再放行",
                    },
                ),
            },
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "apply"
    CATEGORY = "TriPose"
    DESCRIPTION = (
        "出图串行门：正常→赤裸→事后。上路开启时等上路出图再采样；"
        "上路关闭时立即放行（仍可只开赤裸/事后）。"
    )

    def check_lazy_status(self, model, prior_lane_on, prior_image=None):
        if prior_lane_on and prior_image is None:
            return ["prior_image"]
        return []

    def apply(self, model, prior_lane_on=True, prior_image=None):
        if prior_lane_on and prior_image is not None:
            _ = prior_image.shape
        return (model,)


NODE_CLASS_MAPPINGS["TriPoseSeqGate"] = TriPoseSeqGate
NODE_DISPLAY_NAME_MAPPINGS["TriPoseSeqGate"] = "TriPose 出图串行门"
