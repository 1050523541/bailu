# -*- coding: utf-8 -*-
"""Azur Lane–style character reveal layout compositor."""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import torch
from PIL import Image, ImageDraw


def _to_pil(t: torch.Tensor) -> Image.Image:
    arr = (t[0].detach().cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def _to_tensor(im: Image.Image) -> torch.Tensor:
    arr = np.array(im.convert("RGB")).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None, ...]


def _resize_h(im: Image.Image, h: int) -> Image.Image:
    if im.height == h:
        return im
    w = max(1, int(round(im.width * (h / float(im.height)))))
    return im.resize((w, h), Image.Resampling.LANCZOS)


def _resize_w(im: Image.Image, w: int) -> Image.Image:
    if im.width == w:
        return im
    h = max(1, int(round(im.height * (w / float(im.width)))))
    return im.resize((w, h), Image.Resampling.LANCZOS)


def _fit_box(im: Image.Image, box_w: int, box_h: int, bg=(255, 255, 255)) -> Image.Image:
    scale = min(box_w / float(im.width), box_h / float(im.height))
    nw = max(1, int(round(im.width * scale)))
    nh = max(1, int(round(im.height * scale)))
    resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (box_w, box_h), bg)
    canvas.paste(resized, ((box_w - nw) // 2, (box_h - nh) // 2))
    return canvas


def _tensor_to_pils(t: torch.Tensor) -> List[Image.Image]:
    """IMAGE tensor [B,H,W,C] → list of PIL images."""
    arr = (t.detach().cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    if arr.ndim == 3:
        return [Image.fromarray(arr, mode="RGB")]
    return [Image.fromarray(arr[i], mode="RGB") for i in range(arr.shape[0])]


def _circle_crop(im: Image.Image, size: int, bg=(255, 255, 255), border=3, border_color=(220, 220, 230)) -> Image.Image:
    """Square→circle inset. Center crop."""
    w, h = im.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    sq = im.crop((left, top, left + side, top + side)).resize((size, size), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (size, size), bg)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    inset = border + 1
    draw.ellipse((inset, inset, size - 1 - inset, size - 1 - inset), fill=255)
    canvas.paste(sq, (0, 0), mask)

    ring = ImageDraw.Draw(canvas)
    ring.ellipse((border // 2, border // 2, size - 1 - border // 2, size - 1 - border // 2), outline=border_color, width=border)
    return canvas


def _panel_frame(im: Image.Image, bg=(255, 255, 255), pad=6, border=2, border_color=(210, 210, 220)) -> Image.Image:
    w, h = im.size
    canvas = Image.new("RGB", (w + pad * 2, h + pad * 2), bg)
    canvas.paste(im, (pad, pad))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((pad - border, pad - border, pad + w + border - 1, pad + h + border - 1), outline=border_color, width=border)
    return canvas


def _split_grid(im: Image.Image, cols: int, rows: int) -> List[Image.Image]:
    w, h = im.size
    cw, rh = w // cols, h // rows
    cells = []
    for r in range(rows):
        for c in range(cols):
            cells.append(im.crop((c * cw, r * rh, (c + 1) * cw, (r + 1) * rh)))
    return cells


def _split_detail_stack(im: Image.Image, n: int = 2) -> List[Image.Image]:
    w, h = im.size
    ph = h // max(1, n)
    return [im.crop((0, i * ph, w, (i + 1) * ph if i < n - 1 else h)) for i in range(n)]


def _main_bust_crop(im: Image.Image) -> Image.Image:
    """Upper ~55% bust / group close-up window from standing art (square)."""
    w, h = im.size
    crop_h = max(1, int(round(h * 0.55)))
    # Prefer a square from the upper body; widen slightly if portrait is narrow.
    side = min(w, crop_h)
    top = max(0, int(h * 0.04))
    if top + side > h:
        top = max(0, h - side)
    left = (w - side) // 2
    return im.crop((left, top, left + side, top + side))


def _main_face_crop(im: Image.Image, index: int = 0, total: int = 1) -> Image.Image:
    """Legacy upper-face window (kept for expression_sheet / expr_faces mode)."""
    w, h = im.size
    side = min(w, int(h * 0.42))
    top = max(0, int(h * 0.06))
    if top + side > h:
        top = max(0, h - side)
    if total <= 1:
        left = (w - side) // 2
    else:
        span = max(0, w - side)
        left = int(span * (0.35 + 0.3 * (index / max(1, total - 1))))
    return im.crop((left, top, left + side, top + side))


class TriPoseAzurRevealLayout:
    """Azur Lane character-reveal master sheet with a single bust bubble by default."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "main_image": ("IMAGE",),
                "expr_cols": ("INT", {"default": 2, "min": 1, "max": 6, "step": 1}),
                "expr_rows": ("INT", {"default": 2, "min": 1, "max": 4, "step": 1}),
                "max_expr": ("INT", {"default": 0, "min": 0, "max": 12, "step": 1}),
                "face_size": ("INT", {"default": 280, "min": 96, "max": 400, "step": 8}),
                "gap": ("INT", {"default": 16, "min": 0, "max": 64, "step": 1}),
                "margin": ("INT", {"default": 24, "min": 0, "max": 80, "step": 1}),
                "bg": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "canvas_h": ("INT", {"default": 1400, "min": 512, "max": 2048, "step": 8}),
                "expr_style": (["circle", "square"], {"default": "circle"}),
                "main_max_w": ("INT", {"default": 980, "min": 400, "max": 1400, "step": 8}),
                "expr_from": (
                    ["auto", "batch", "grid", "from_main"],
                    {
                        "default": "auto",
                        "tooltip": "Only used when inset_mode=expr_faces and expression_sheet is connected.",
                    },
                ),
                "inset_mode": (
                    ["bust_bubble", "off", "expr_faces"],
                    {
                        "default": "bust_bubble",
                        "tooltip": "bust_bubble: one upper-body circle from main; off: main only; expr_faces: legacy expression / face grid.",
                    },
                ),
                "include_detail": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "label_on": "detail on",
                        "label_off": "detail off",
                        "tooltip": "When off, detail_strip is ignored even if connected.",
                    },
                ),
                "detail_style": (
                    ["circle", "square"],
                    {
                        "default": "circle",
                        "tooltip": "circle = 裙底圆气泡 (matches bust bubble). square = framed panel (legacy stamp look).",
                    },
                ),
            },
            "optional": {
                "expression_sheet": ("IMAGE",),
                "detail_strip": ("IMAGE",),
                "detail_panels": ("INT", {"default": 1, "min": 1, "max": 4, "step": 1}),
                "detail_h": ("INT", {"default": 320, "min": 120, "max": 600, "step": 8}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "status")
    FUNCTION = "compose"
    CATEGORY = "TriPose"
    DESCRIPTION = (
        "Azur Lane reveal: left = one bust close-up bubble (default) + optional detail; "
        "center = full-body standing art. Skirt/turnaround stay as separate saves."
    )

    def compose(
        self,
        main_image,
        expr_cols,
        expr_rows,
        max_expr,
        face_size,
        gap,
        margin,
        bg,
        canvas_h,
        expr_style,
        main_max_w,
        expr_from="auto",
        inset_mode="bust_bubble",
        include_detail=False,
        detail_style="circle",
        expression_sheet=None,
        detail_strip=None,
        detail_panels=1,
        detail_h=320,
    ):
        fill = int(round(float(bg) * 255))
        color = (fill, fill, fill)

        main = _to_pil(main_image)
        cells: List[Image.Image] = []
        src = "none"
        mode = str(inset_mode or "bust_bubble")

        if mode == "bust_bubble":
            cells = [_main_bust_crop(main)]
            src = "bust_bubble×1"
        elif mode == "expr_faces" and expression_sheet is not None and int(max_expr) > 0:
            expr_t = expression_sheet
            b = int(expr_t.shape[0]) if hasattr(expr_t, "shape") else 1
            emode = expr_from
            if emode == "auto":
                emode = "batch" if b > 1 else "grid"
            if emode == "from_main":
                emode = "batch" if b > 1 else "grid"
            if emode == "batch":
                cells = _tensor_to_pils(expr_t)[: int(max_expr)]
                src = f"batch×{len(cells)}"
            else:
                expr = _to_pil(expr_t)
                cells = _split_grid(expr, int(expr_cols), int(expr_rows))[: int(max_expr)]
                src = f"grid{expr_cols}x{expr_rows}"
        elif mode == "expr_faces" and int(max_expr) > 0:
            n = min(int(max_expr), 2)
            cells = [_main_face_crop(main, i, n) for i in range(n)]
            src = f"from_main×{len(cells)}"
        # mode == "off" → no left insets from faces/bust

        left_panels: List[Image.Image] = []
        fs = int(face_size)
        for cell in cells:
            if expr_style == "circle":
                left_panels.append(_circle_crop(cell, fs, color))
            else:
                left_panels.append(_panel_frame(_fit_box(cell, fs, fs, color), color))

        detail_count = 0
        if include_detail and detail_strip is not None:
            details = _split_detail_stack(_to_pil(detail_strip), int(detail_panels))
            dstyle = str(detail_style or "circle")
            # Prefer square bubble size so 裙底圆气泡 matches bust circle scale
            dsize = max(int(face_size), min(int(detail_h), int(face_size) + 80))
            for d in details:
                if dstyle == "circle":
                    left_panels.append(_circle_crop(d, dsize, color))
                else:
                    left_panels.append(
                        _panel_frame(
                            _fit_box(d, int(face_size), int(detail_h), color),
                            color,
                            pad=4,
                            border=2,
                            border_color=(200, 160, 180),
                        )
                    )
            detail_count = len(details)

        left_h = sum(p.height for p in left_panels) + gap * max(0, len(left_panels) - 1) if left_panels else 0
        left_w = max((p.width for p in left_panels), default=0)

        avail_h = int(canvas_h) - 2 * int(margin)
        if left_h > avail_h and left_h > 0:
            scale = avail_h / float(left_h)
            new_panels = []
            for p in left_panels:
                nw = max(1, int(round(p.width * scale)))
                nh = max(1, int(round(p.height * scale)))
                new_panels.append(p.resize((nw, nh), Image.Resampling.LANCZOS))
            left_panels = new_panels
            left_w = max(p.width for p in left_panels) if left_panels else 0
            left_h = sum(p.height for p in left_panels) + gap * max(0, len(left_panels) - 1)

        main_h = avail_h
        main_fitted = _resize_h(main, main_h)
        if main_fitted.width > int(main_max_w):
            main_fitted = _resize_w(main_fitted, int(main_max_w))
            main_fitted = _fit_box(main_fitted, main_fitted.width, main_h, color)

        left_gap = int(gap) if left_w > 0 else 0
        total_w = int(margin) + left_w + left_gap + main_fitted.width + int(margin)
        total_h = int(canvas_h)
        canvas = Image.new("RGB", (total_w, total_h), color)

        y = int(margin)
        for p in left_panels:
            x = int(margin) + (left_w - p.width) // 2
            canvas.paste(p, (x, y))
            y += p.height + int(gap)

        mx = int(margin) + left_w + left_gap
        my = int(margin) + (avail_h - main_fitted.height) // 2
        canvas.paste(main_fitted, (mx, my))

        status = (
            f"azur_reveal_v6: inset={src}/{expr_style}, details={detail_count}/"
            f"{detail_style}, size={canvas.size[0]}x{canvas.size[1]}"
        )
        return (_to_tensor(canvas), status)


NODE_CLASS_MAPPINGS = {
    "TriPoseAzurRevealLayout": TriPoseAzurRevealLayout,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TriPoseAzurRevealLayout": "TriPose 碧蓝公布布局",
}
