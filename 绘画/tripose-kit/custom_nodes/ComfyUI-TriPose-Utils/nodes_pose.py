# -*- coding: utf-8 -*-
"""Fixed OpenPose-style pose guides for expression sheet / turnaround / standing reveal."""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import torch


def _try_import_draw():
    """Use controlnet_aux OpenPose drawer when available."""
    try:
        from custom_controlnet_aux.open_pose.util import draw_bodypose, draw_facepose  # type: ignore
        from custom_controlnet_aux.open_pose.body import Keypoint  # type: ignore

        return draw_bodypose, draw_facepose, Keypoint
    except Exception:
        pass
    try:
        # package path used by some installs
        from comfyui_controlnet_aux.src.custom_controlnet_aux.open_pose.util import (  # type: ignore
            draw_bodypose,
            draw_facepose,
        )
        from comfyui_controlnet_aux.src.custom_controlnet_aux.open_pose.body import Keypoint  # type: ignore

        return draw_bodypose, draw_facepose, Keypoint
    except Exception:
        return None, None, None


def _kp(Keypoint, x: float, y: float):
    return Keypoint(x=float(x), y=float(y), score=1.0)


def _standing_keypoints(Keypoint, cx: float = 0.5, top: float = 0.08, scale: float = 0.85):
    """Normalized OpenPose body keypoints (18) for a front standing figure."""
    # indices 0..17 matching open_pose util limbSeq (1-based in limbSeq)
    # 0 nose, 1 neck, 2 Rsho, 3 Relb, 4 Rwri, 5 Lsho, 6 Lelb, 7 Lwri,
    # 8 Rhip, 9 Rkne, 10 Rank, 11 Lhip, 12 Lkne, 13 Lank, 14 Reye, 15 Leye, 16 Rear, 17 Lear
    h = scale
    nose_y = top + 0.06 * h
    neck_y = top + 0.14 * h
    hip_y = top + 0.48 * h
    knee_y = top + 0.70 * h
    ank_y = top + 0.92 * h
    sh_w = 0.11 * scale
    hip_w = 0.08 * scale
    arm_out = 0.16 * scale
    pts = [None] * 18
    pts[0] = _kp(Keypoint, cx, nose_y)
    pts[1] = _kp(Keypoint, cx, neck_y)
    pts[2] = _kp(Keypoint, cx - sh_w, neck_y + 0.02 * h)
    pts[3] = _kp(Keypoint, cx - arm_out, neck_y + 0.18 * h)
    pts[4] = _kp(Keypoint, cx - arm_out - 0.02, neck_y + 0.32 * h)
    pts[5] = _kp(Keypoint, cx + sh_w, neck_y + 0.02 * h)
    pts[6] = _kp(Keypoint, cx + arm_out, neck_y + 0.18 * h)
    pts[7] = _kp(Keypoint, cx + arm_out + 0.02, neck_y + 0.32 * h)
    pts[8] = _kp(Keypoint, cx - hip_w, hip_y)
    pts[9] = _kp(Keypoint, cx - hip_w, knee_y)
    pts[10] = _kp(Keypoint, cx - hip_w, ank_y)
    pts[11] = _kp(Keypoint, cx + hip_w, hip_y)
    pts[12] = _kp(Keypoint, cx + hip_w, knee_y)
    pts[13] = _kp(Keypoint, cx + hip_w, ank_y)
    pts[14] = _kp(Keypoint, cx - 0.025, nose_y - 0.01 * h)
    pts[15] = _kp(Keypoint, cx + 0.025, nose_y - 0.01 * h)
    pts[16] = _kp(Keypoint, cx - 0.05, nose_y)
    pts[17] = _kp(Keypoint, cx + 0.05, nose_y)
    return pts


def _side_keypoints(Keypoint, cx: float = 0.5, top: float = 0.08, scale: float = 0.85, facing: str = "right"):
    """Side-view standing stick (simplified, overlapping limbs)."""
    h = scale
    sign = 1.0 if facing == "right" else -1.0
    nose_y = top + 0.06 * h
    neck_y = top + 0.14 * h
    hip_y = top + 0.48 * h
    knee_y = top + 0.70 * h
    ank_y = top + 0.92 * h
    pts = [None] * 18
    pts[0] = _kp(Keypoint, cx + 0.02 * sign, nose_y)
    pts[1] = _kp(Keypoint, cx, neck_y)
    # near-shoulder collapse for side silhouette
    pts[2] = _kp(Keypoint, cx - 0.01 * sign, neck_y + 0.02 * h)
    pts[3] = _kp(Keypoint, cx + 0.04 * sign, neck_y + 0.20 * h)
    pts[4] = _kp(Keypoint, cx + 0.06 * sign, neck_y + 0.34 * h)
    pts[5] = _kp(Keypoint, cx + 0.01 * sign, neck_y + 0.02 * h)
    pts[6] = _kp(Keypoint, cx + 0.03 * sign, neck_y + 0.20 * h)
    pts[7] = _kp(Keypoint, cx + 0.05 * sign, neck_y + 0.34 * h)
    pts[8] = _kp(Keypoint, cx - 0.01 * sign, hip_y)
    pts[9] = _kp(Keypoint, cx - 0.01 * sign, knee_y)
    pts[10] = _kp(Keypoint, cx - 0.01 * sign, ank_y)
    pts[11] = _kp(Keypoint, cx + 0.01 * sign, hip_y)
    pts[12] = _kp(Keypoint, cx + 0.02 * sign, knee_y)
    pts[13] = _kp(Keypoint, cx + 0.02 * sign, ank_y)
    pts[14] = _kp(Keypoint, cx + 0.03 * sign, nose_y - 0.01 * h)
    pts[15] = None
    pts[16] = _kp(Keypoint, cx - 0.01 * sign, nose_y)
    pts[17] = None
    return pts


def _back_keypoints(Keypoint, cx: float = 0.5, top: float = 0.08, scale: float = 0.85):
    pts = _standing_keypoints(Keypoint, cx, top, scale)
    # hide face points for back view
    pts[0] = _kp(Keypoint, cx, top + 0.07 * scale)  # head center
    pts[14] = None
    pts[15] = None
    pts[16] = _kp(Keypoint, cx - 0.05, top + 0.07 * scale)
    pts[17] = _kp(Keypoint, cx + 0.05, top + 0.07 * scale)
    return pts


def _head_keypoints(Keypoint, cx: float, cy: float, scale: float = 0.9):
    """Head-shot only: large face fills most of the cell so the model cannot invent a standing body.

    No hips/legs/arms. Tiny shoulder stubs only — OpenPose XL needs neck anchors,
    but they stay near the chin line so framing stays portrait/head-only.
    """
    pts = [None] * 18
    # Face blob occupies ~70% of cell height when cy≈0.52 and scale≈0.95
    nose_y = cy - 0.02 * scale
    neck_y = cy + 0.22 * scale
    pts[0] = _kp(Keypoint, cx, nose_y)
    pts[1] = _kp(Keypoint, cx, neck_y)
    # shoulders barely below neck — still reads as cropped bust, not torso
    pts[2] = _kp(Keypoint, cx - 0.10 * scale, neck_y + 0.06 * scale)
    pts[5] = _kp(Keypoint, cx + 0.10 * scale, neck_y + 0.06 * scale)
    # no elbows/wrists/hips/knees/ankles → empty lower cell has no stick to follow as body
    pts[14] = _kp(Keypoint, cx - 0.07 * scale, nose_y - 0.06 * scale)
    pts[15] = _kp(Keypoint, cx + 0.07 * scale, nose_y - 0.06 * scale)
    pts[16] = _kp(Keypoint, cx - 0.16 * scale, nose_y)
    pts[17] = _kp(Keypoint, cx + 0.16 * scale, nose_y)
    return pts


def _skirt_focus_keypoints(Keypoint, cx: float = 0.5):
    """Half-body skirt/crotch focus: left/right hip–thigh only.

    No center-line / pelvis stub — a vertical mid stick + strong OpenPose CN
    often becomes a mystery pole (sometimes with the character butterfly on top).
    """
    pts = [None] * 18
    hip_y = 0.36
    knee_y = 0.72
    ank_y = 0.95
    hip_w = 0.18
    # Independent left / right chains only (no pts[1] center stem)
    pts[8] = _kp(Keypoint, cx - hip_w, hip_y)
    pts[9] = _kp(Keypoint, cx - hip_w - 0.03, knee_y)
    pts[10] = _kp(Keypoint, cx - hip_w - 0.04, ank_y)
    pts[11] = _kp(Keypoint, cx + hip_w, hip_y)
    pts[12] = _kp(Keypoint, cx + hip_w + 0.03, knee_y)
    pts[13] = _kp(Keypoint, cx + hip_w + 0.04, ank_y)
    # Soft waist corners (not center) so framing stays lower-body
    pts[2] = _kp(Keypoint, cx - 0.12, hip_y - 0.08)
    pts[5] = _kp(Keypoint, cx + 0.12, hip_y - 0.08)
    return pts


def _standing_from_below_keypoints(Keypoint, cx: float = 0.5):
    """Standing figure, worm's-eye / from-below crop (legacy; prefer skirt_focus for 裙底)."""
    pts = [None] * 18
    nose_y, neck_y = 0.10, 0.16
    sh_y = 0.22
    hip_y = 0.48
    knee_y, ank_y = 0.72, 0.92
    pts[0] = _kp(Keypoint, cx, nose_y)
    pts[1] = _kp(Keypoint, cx, neck_y)
    pts[2] = _kp(Keypoint, cx - 0.10, sh_y)
    pts[3] = _kp(Keypoint, cx - 0.14, sh_y + 0.10)
    pts[4] = _kp(Keypoint, cx - 0.12, sh_y + 0.18)
    pts[5] = _kp(Keypoint, cx + 0.10, sh_y)
    pts[6] = _kp(Keypoint, cx + 0.14, sh_y + 0.10)
    pts[7] = _kp(Keypoint, cx + 0.12, sh_y + 0.18)
    pts[8] = _kp(Keypoint, cx - 0.12, hip_y)
    pts[9] = _kp(Keypoint, cx - 0.16, knee_y)
    pts[10] = _kp(Keypoint, cx - 0.18, ank_y)
    pts[11] = _kp(Keypoint, cx + 0.12, hip_y)
    pts[12] = _kp(Keypoint, cx + 0.16, knee_y)
    pts[13] = _kp(Keypoint, cx + 0.18, ank_y)
    pts[14] = _kp(Keypoint, cx - 0.03, nose_y - 0.015)
    pts[15] = _kp(Keypoint, cx + 0.03, nose_y - 0.015)
    pts[16] = _kp(Keypoint, cx - 0.05, nose_y)
    pts[17] = _kp(Keypoint, cx + 0.05, nose_y)
    return pts


def _bust_keypoints(Keypoint, cx: float, cy: float, scale: float = 0.22):
    """Upper-body / bust for expression grid cells — same pose every cell."""
    pts = [None] * 18
    nose_y = cy - 0.08 * scale
    neck_y = cy + 0.02 * scale
    sh_y = cy + 0.10 * scale
    pts[0] = _kp(Keypoint, cx, nose_y)
    pts[1] = _kp(Keypoint, cx, neck_y)
    pts[2] = _kp(Keypoint, cx - 0.12 * scale, sh_y)
    pts[3] = _kp(Keypoint, cx - 0.16 * scale, sh_y + 0.12 * scale)
    pts[4] = _kp(Keypoint, cx - 0.14 * scale, sh_y + 0.22 * scale)
    pts[5] = _kp(Keypoint, cx + 0.12 * scale, sh_y)
    pts[6] = _kp(Keypoint, cx + 0.16 * scale, sh_y + 0.12 * scale)
    pts[7] = _kp(Keypoint, cx + 0.14 * scale, sh_y + 0.22 * scale)
    pts[14] = _kp(Keypoint, cx - 0.03 * scale, nose_y - 0.02 * scale)
    pts[15] = _kp(Keypoint, cx + 0.03 * scale, nose_y - 0.02 * scale)
    pts[16] = _kp(Keypoint, cx - 0.07 * scale, nose_y)
    pts[17] = _kp(Keypoint, cx + 0.07 * scale, nose_y)
    return pts


def _draw_fallback(canvas: np.ndarray, joints: List[Tuple[float, float]], limbs: List[Tuple[int, int]]):
    import cv2

    H, W = canvas.shape[:2]
    for a, b in limbs:
        if a >= len(joints) or b >= len(joints):
            continue
        x1, y1 = joints[a]
        x2, y2 = joints[b]
        cv2.line(canvas, (int(x1 * W), int(y1 * H)), (int(x2 * W), int(y2 * H)), (0, 255, 255), 3)
    for x, y in joints:
        cv2.circle(canvas, (int(x * W), int(y * H)), 4, (255, 0, 255), -1)
    return canvas


def _render_bodies(width: int, height: int, bodies: list) -> torch.Tensor:
    draw_bodypose, draw_facepose, Keypoint = _try_import_draw()
    canvas = np.zeros((height, width, 3), dtype=np.uint8)

    if Keypoint is None or draw_bodypose is None:
        # very rough fallback lines
        import cv2

        for body in bodies:
            # body is list of (x,y) or Keypoint-like; fallback expects normalized tuples
            joints = []
            for p in body:
                if p is None:
                    joints.append((0.0, 0.0))
                elif hasattr(p, "x"):
                    joints.append((p.x, p.y))
                else:
                    joints.append(p)
            limbs = [(1, 2), (1, 5), (2, 3), (3, 4), (5, 6), (6, 7), (1, 8), (8, 9), (9, 10), (1, 11), (11, 12), (12, 13)]
            _draw_fallback(canvas, joints, limbs)
    else:
        for pts in bodies:
            canvas = draw_bodypose(canvas, pts, xinsr_stick_scaling=True)
            if draw_facepose is not None:
                try:
                    # facepose expects list of keypoints; skip if unavailable
                    pass
                except Exception:
                    pass

    arr = canvas.astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None, ...]


class TriPosePoseGuide:
    """Generate fixed OpenPose guides so expression/turnaround poses stay consistent."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "layout": (
                    [
                        "expression_heads",
                        "expression_grid",
                        "turnaround_3",
                        "standing_reveal",
                        "standing_from_below",
                        "skirt_focus",
                    ],
                    {"default": "expression_heads"},
                ),
                "width": ("INT", {"default": 1024, "min": 256, "max": 2048, "step": 8}),
                "height": ("INT", {"default": 1024, "min": 256, "max": 2048, "step": 8}),
                "cols": ("INT", {"default": 2, "min": 1, "max": 4, "step": 1}),
                "rows": ("INT", {"default": 2, "min": 1, "max": 4, "step": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("pose_image", "status")
    FUNCTION = "make"
    CATEGORY = "TriPose"
    DESCRIPTION = (
        "Fixed OpenPose stick guide. expression_heads = large identical headshot tiles. "
        "skirt_focus = hips/thighs only for 半身裙底. turnaround_3 = front/side/back."
    )

    def make(self, layout, width, height, cols, rows):
        draw_bodypose, draw_facepose, Keypoint = _try_import_draw()
        if Keypoint is None:
            # still produce something usable
            class _K:
                def __init__(self, x, y, score=1.0):
                    self.x, self.y, self.score = x, y, score

            Keypoint = _K

        bodies = []
        if layout in ("expression_heads", "expression_grid"):
            # Pixel-identical template: draw ONE cell, then tile copies.
            cell_w = max(64, int(width) // int(cols))
            cell_h = max(64, int(height) // int(rows))
            if layout == "expression_heads":
                # Fill cell with oversized head — leaves little room for invented standing bodies
                cell_body = [_head_keypoints(Keypoint, 0.5, 0.52, scale=0.95)]
                kind = "HEADSHOT-FILL"
            else:
                cell_body = [_bust_keypoints(Keypoint, 0.5, 0.42, scale=0.95)]
                kind = "bust"
            cell_img = _render_bodies(cell_w, cell_h, cell_body)
            cell_np = (cell_img[0].detach().cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
            canvas = np.zeros((int(height), int(width), 3), dtype=np.uint8)
            for r in range(int(rows)):
                for c in range(int(cols)):
                    y0, x0 = r * cell_h, c * cell_w
                    y1 = min(y0 + cell_h, int(height))
                    x1 = min(x0 + cell_w, int(width))
                    canvas[y0:y1, x0:x1] = cell_np[: y1 - y0, : x1 - x0]
            arr = canvas.astype(np.float32) / 255.0
            status = f"{layout} {cols}x{rows} IDENTICAL tiled {kind} template"
            return (torch.from_numpy(arr)[None, ...], status)
        elif layout == "turnaround_3":
            bodies = [
                _standing_keypoints(Keypoint, cx=0.18, top=0.06, scale=0.88),
                _side_keypoints(Keypoint, cx=0.50, top=0.06, scale=0.88, facing="right"),
                _back_keypoints(Keypoint, cx=0.82, top=0.06, scale=0.88),
            ]
            status = "turnaround_3 front/side/back"
        elif layout == "standing_from_below":
            bodies = [_standing_from_below_keypoints(Keypoint, cx=0.5)]
            status = "standing_from_below worm's-eye standing (not sitting)"
        elif layout == "skirt_focus":
            bodies = [_skirt_focus_keypoints(Keypoint, cx=0.5)]
            status = "skirt_focus hips+thighs half-body (no head)"
        else:  # standing_reveal
            bodies = [_standing_keypoints(Keypoint, cx=0.50, top=0.05, scale=0.90)]
            status = "standing_reveal full-body"

        img = _render_bodies(int(width), int(height), bodies)
        return (img, status)


NODE_CLASS_MAPPINGS = {
    "TriPosePoseGuide": TriPosePoseGuide,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TriPosePoseGuide": "TriPose 姿态引导(OpenPose)",
}
