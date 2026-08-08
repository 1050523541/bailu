# -*- coding: utf-8 -*-
"""
TriPose Utils — Chinese short-tag dictionary mapper + OC design helpers for ComfyUI.
"""

from aiohttp import web

from .nodes_tagmap import NODE_CLASS_MAPPINGS as _TAG_MAP
from .nodes_tagmap import NODE_DISPLAY_NAME_MAPPINGS as _TAG_DISPLAY
from .nodes_tagmap import (
    _coerce_options,
    _resolve_dictionaries_ex,
    lexicon_info,
    map_tags,
)

from .nodes_oc import NODE_CLASS_MAPPINGS as _OC_MAP
from .nodes_oc import NODE_DISPLAY_NAME_MAPPINGS as _OC_DISPLAY

from .nodes_semantic import NODE_CLASS_MAPPINGS as _SEM_MAP
from .nodes_semantic import NODE_DISPLAY_NAME_MAPPINGS as _SEM_DISPLAY

from .nodes_pose import NODE_CLASS_MAPPINGS as _POSE_MAP
from .nodes_pose import NODE_DISPLAY_NAME_MAPPINGS as _POSE_DISPLAY

from .nodes_layout import NODE_CLASS_MAPPINGS as _LAY_MAP
from .nodes_layout import NODE_DISPLAY_NAME_MAPPINGS as _LAY_DISPLAY

NODE_CLASS_MAPPINGS = {}
NODE_CLASS_MAPPINGS.update(_TAG_MAP)
NODE_CLASS_MAPPINGS.update(_OC_MAP)
NODE_CLASS_MAPPINGS.update(_SEM_MAP)
NODE_CLASS_MAPPINGS.update(_POSE_MAP)
NODE_CLASS_MAPPINGS.update(_LAY_MAP)

NODE_DISPLAY_NAME_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS.update(_TAG_DISPLAY)
NODE_DISPLAY_NAME_MAPPINGS.update(_OC_DISPLAY)
NODE_DISPLAY_NAME_MAPPINGS.update(_SEM_DISPLAY)
NODE_DISPLAY_NAME_MAPPINGS.update(_POSE_DISPLAY)
NODE_DISPLAY_NAME_MAPPINGS.update(_LAY_DISPLAY)

WEB_DIRECTORY = "./web"

try:
    from server import PromptServer

    @PromptServer.instance.routes.get("/tripose/zh_tagmap")
    async def tripose_zh_tagmap(request):
        """Return kit overlay only (not the 300k lexicon) for lightweight UI."""
        dictionary = request.rel_url.query.get("dictionary", "zh_danbooru+nsfw")
        custom_path = request.rel_url.query.get("custom_path", "")
        try:
            overlay = _resolve_dictionaries_ex(
                dictionary, custom_path, include_lexicon=False
            )
            info = lexicon_info()
        except Exception as exc:  # noqa: BLE001
            return web.json_response({"error": str(exc), "table": {}}, status=400)
        return web.json_response(
            {
                "dictionary": dictionary,
                "table": overlay,
                "lexicon": info,
                "note": "table is kit overlay only; use POST /tripose/zh_tagmap/map for full lexicon lookup",
            }
        )

    @PromptServer.instance.routes.post("/tripose/zh_tagmap/map")
    async def tripose_zh_tagmap_map(request):
        """Server-side map: lexicon + kit overlay (+ optional google)."""
        try:
            data = await request.json()
        except Exception:
            data = {}
        text = data.get("text", "")
        dictionary = data.get("dictionary", "zh_danbooru+nsfw")
        custom_path = data.get("custom_path", "")
        keep_unknown = data.get("keep_unknown", "keep")
        passthrough = data.get("passthrough_english", True)
        google_fallback = bool(data.get("google_fallback", False))
        dictionary, custom_path, keep_unknown = _coerce_options(
            dictionary, custom_path, keep_unknown
        )
        try:
            table = _resolve_dictionaries_ex(
                dictionary, custom_path, include_lexicon=True
            )
            mapped, unmapped = map_tags(
                text,
                table,
                keep_unknown,
                bool(passthrough),
                google_fallback=google_fallback,
            )
            info = lexicon_info()
        except Exception as exc:  # noqa: BLE001
            return web.json_response({"error": str(exc)}, status=400)
        return web.json_response(
            {
                "mapped": mapped,
                "unmapped": unmapped,
                "lexicon": info,
            }
        )

except Exception:
    pass

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
