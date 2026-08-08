import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

const MAPPED_NAME = "映射结果 (英文)";
const UNMAPPED_NAME = "未命中标签";
const PREVIEW_NAMES = new Set([MAPPED_NAME, UNMAPPED_NAME]);

const dictCache = new Map();

function splitTags(text) {
  return String(text || "")
    .split(/[,，、\n]+/)
    .map((p) => p.trim())
    .filter(Boolean);
}

function normalizeKey(s) {
  return String(s || "")
    .trim()
    .replace(/\s+/g, "");
}

function expandValue(val) {
  return splitTags(val);
}

function mapTags(text, table, keepUnknown, passthroughEnglish) {
  const lookup = {};
  for (const [k, v] of Object.entries(table || {})) {
    lookup[k] = v;
    lookup[normalizeKey(k)] = v;
  }

  const mapped = [];
  const unmapped = [];
  const seen = new Set();
  const latinRe = /^[A-Za-z0-9][A-Za-z0-9 \-_'()/:+.]*$/;

  const addTags = (tags) => {
    for (const t of tags) {
      const key = String(t).toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      mapped.push(t);
    }
  };

  for (const seg of splitTags(text)) {
    let hit = lookup[seg];
    if (hit == null) hit = lookup[normalizeKey(seg)];
    if (hit != null) {
      addTags(expandValue(hit));
      continue;
    }
    if (passthroughEnglish && latinRe.test(seg)) {
      addTags([seg]);
      continue;
    }
    unmapped.push(seg);
    if (keepUnknown === "keep") addTags([seg]);
  }

  return {
    mapped: mapped.join(", "),
    unmapped: unmapped.join(", "),
  };
}

async function fetchDictionary(dictionary, customPath) {
  const key = `${dictionary}||${customPath || ""}`;
  if (dictCache.has(key)) return dictCache.get(key);
  const qs = new URLSearchParams({
    dictionary: dictionary || "zh_danbooru+design",
    custom_path: customPath || "",
  });
  const res = await api.fetchApi(`/tripose/zh_tagmap?${qs.toString()}`);
  if (!res.ok) throw new Error(`tagmap fetch failed: ${res.status}`);
  const data = await res.json();
  const table = data?.table || {};
  dictCache.set(key, table);
  return table;
}

function widgetByName(node, name) {
  return (node.widgets || []).find((w) => w.name === name);
}

function snapshotSize(node) {
  if (!node?.size || node.size.length < 2) return null;
  return [node.size[0], node.size[1]];
}

function restoreSize(node, size) {
  if (!size || !node) return;
  // Keep the user's manually arranged node geometry.
  node.size[0] = size[0];
  node.size[1] = size[1];
  if (typeof node.setSize === "function") {
    node.setSize([size[0], size[1]]);
  }
}

function pinPreviewWidget(widget) {
  if (!widget || widget.__triposePinned) return;
  widget.__triposePinned = true;
  if (widget.inputEl) {
    widget.inputEl.readOnly = true;
    widget.inputEl.style.overflowY = "auto";
    widget.inputEl.style.resize = "none";
  }
  // Content length must not drive node height.
  widget.computeSize = function (width) {
    return [width || 200, 60];
  };
}

function ensurePreviewWidgets(node) {
  const sizeBefore = snapshotSize(node);
  let added = false;

  if (!widgetByName(node, MAPPED_NAME)) {
    const mapped = ComfyWidgets.STRING(
      node,
      MAPPED_NAME,
      [
        "STRING",
        {
          default: "",
          multiline: true,
          placeholder: "映射后的英文标签会显示在这里…",
        },
      ],
      app
    );
    pinPreviewWidget(mapped.widget);
    mapped.widget.inputEl.style.opacity = "0.95";
    added = true;
  } else {
    pinPreviewWidget(widgetByName(node, MAPPED_NAME));
  }

  if (!widgetByName(node, UNMAPPED_NAME)) {
    const unmapped = ComfyWidgets.STRING(
      node,
      UNMAPPED_NAME,
      [
        "STRING",
        {
          default: "",
          multiline: true,
          placeholder: "词表未命中（开 Google 兜底时，Queue 会译成英文）…",
        },
      ],
      app
    );
    pinPreviewWidget(unmapped.widget);
    unmapped.widget.inputEl.style.opacity = "0.85";
    added = true;
  } else {
    pinPreviewWidget(widgetByName(node, UNMAPPED_NAME));
  }

  // Never computeSize() after the user has a saved/manual size.
  if (sizeBefore) {
    restoreSize(node, sizeBefore);
  } else if (added && !node.__triposeHasUserSize) {
    try {
      node.setSize?.(node.computeSize());
    } catch (_) {
      /* ignore */
    }
  }
}

function setPreview(node, mapped, unmapped) {
  const locked = snapshotSize(node);
  const mw = widgetByName(node, MAPPED_NAME);
  const uw = widgetByName(node, UNMAPPED_NAME);
  if (mw) mw.value = mapped || "";
  if (uw) uw.value = unmapped || "";
  restoreSize(node, locked);
  app.graph?.setDirtyCanvas?.(true, false);
}

function readLinkedText(node) {
  const input = (node.inputs || []).find((i) => i.name === "text");
  if (!input || input.link == null) return "";
  const link = app.graph.links[input.link];
  if (!link) return "";
  const origin = app.graph.getNodeById(link.origin_id);
  if (!origin) return "";
  const w =
    (origin.widgets || []).find(
      (x) =>
        x.type === "customtext" ||
        x.type === "text" ||
        x.type === "string" ||
        typeof x.value === "string"
    ) || (origin.widgets || [])[0];
  return w && typeof w.value === "string" ? w.value : "";
}

function repairShiftedWidgets(node) {
  // After google_fallback / lexicon migration, old graphs may have:
  // dictionary='', custom_path='keep', keep_unknown=true
  // or a deleted mini-dict name like zh_danbooru+nsfw.
  const d = widgetByName(node, "dictionary");
  const p = widgetByName(node, "custom_path");
  const k = widgetByName(node, "keep_unknown");
  const pass = widgetByName(node, "passthrough_english");
  const g = widgetByName(node, "google_fallback");
  if (!d || !k) return false;

  let changed = false;

  const keepBad =
    k.value === true ||
    k.value === false ||
    k.value === "true" ||
    k.value === "false";
  if (p && (p.value === "keep" || p.value === "drop")) {
    k.value = p.value;
    p.value = "";
    changed = true;
  } else if (keepBad) {
    k.value = "keep";
    changed = true;
  }

  // Valid: danbooru_zh+nsfw (default), danbooru_zh, custom.
  // Migrate deleted mini-dict / bare names → danbooru_zh+nsfw.
  const dictOk =
    d.value === "danbooru_zh+nsfw" ||
    d.value === "danbooru_zh" ||
    d.value === "custom";
  if (!dictOk) {
    d.value = "danbooru_zh+nsfw";
    changed = true;
  }

  if (pass && typeof pass.value !== "boolean") {
    pass.value = true;
    changed = true;
  }
  if (g && typeof g.value !== "boolean") {
    g.value = true; // Google default on for Queue (preview still skips Google)
    changed = true;
  }
  return changed;
}

function readMapOptions(node) {
  repairShiftedWidgets(node);
  const dictionary = widgetByName(node, "dictionary")?.value || "danbooru_zh+nsfw";
  const customPath = widgetByName(node, "custom_path")?.value || "";
  const keepUnknown = widgetByName(node, "keep_unknown")?.value || "keep";
  const passthrough = widgetByName(node, "passthrough_english")?.value;
  const google = widgetByName(node, "google_fallback")?.value;
  let dict = "danbooru_zh+nsfw";
  if (dictionary === "custom") dict = "custom";
  else if (dictionary === "danbooru_zh") dict = "danbooru_zh";
  return {
    dictionary: dict,
    customPath,
    keepUnknown: keepUnknown === "drop" ? "drop" : "keep",
    passthroughEnglish: passthrough !== false && passthrough !== "no",
    // Preview never uses Google; Queue respects widget (default off).
    googleFallback: google === true || google === "开" || google === "yes",
  };
}

async function mapOnServer(text, opts) {
  const res = await api.fetchApi("/tripose/zh_tagmap/map", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: text || "",
      dictionary: opts.dictionary,
      custom_path: opts.customPath,
      keep_unknown: opts.keepUnknown,
      passthrough_english: opts.passthroughEnglish,
      // Never Google in live preview — it floods the network and blocks Queue.
      google_fallback: false,
    }),
  });
  if (!res.ok) throw new Error(`tagmap map failed: ${res.status}`);
  return await res.json();
}

async function refreshLivePreview(node) {
  try {
    ensurePreviewWidgets(node);
    repairShiftedWidgets(node);
    const text = readLinkedText(node);
    const opts = readMapOptions(node);
    const data = await mapOnServer(text, opts);
    setPreview(node, data?.mapped || "", data?.unmapped || "");
  } catch (err) {
    console.warn("[TriPoseZhTagMap] live preview failed", err);
  }
}

function bindLivePreview(node) {
  if (node.__triposeTagmapBound) return;
  node.__triposeTagmapBound = true;

  const schedule = () => {
    clearTimeout(node.__triposeTagmapTimer);
    node.__triposeTagmapTimer = setTimeout(() => refreshLivePreview(node), 180);
  };

  for (const w of node.widgets || []) {
    if (PREVIEW_NAMES.has(w.name)) continue;
    const prev = w.callback;
    w.callback = function () {
      const r = prev?.apply(this, arguments);
      schedule();
      return r;
    };
  }

  const input = (node.inputs || []).find((i) => i.name === "text");
  if (input?.link != null) {
    const link = app.graph.links[input.link];
    const origin = link ? app.graph.getNodeById(link.origin_id) : null;
    if (origin?.widgets) {
      for (const w of origin.widgets) {
        if (typeof w.value !== "string" && w.type !== "customtext") continue;
        const prev = w.callback;
        w.callback = function () {
          const r = prev?.apply(this, arguments);
          schedule();
          return r;
        };
        if (w.inputEl && !w.inputEl.__triposeTagmapBound) {
          w.inputEl.__triposeTagmapBound = true;
          w.inputEl.addEventListener("input", schedule);
          w.inputEl.addEventListener("change", schedule);
        }
      }
    }
  }

  const onConnectionsChange = node.onConnectionsChange;
  node.onConnectionsChange = function () {
    const r = onConnectionsChange?.apply(this, arguments);
    node.__triposeTagmapBound = false;
    bindLivePreview(node);
    schedule();
    return r;
  };

  // Track manual resize so we never auto-shrink afterwards.
  const onResize = node.onResize;
  node.onResize = function (size) {
    node.__triposeHasUserSize = true;
    return onResize?.apply(this, arguments);
  };

  schedule();
}

app.registerExtension({
  name: "TriPose.ZhTagMapPreview",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "TriPoseZhTagMap") return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const ret = onNodeCreated?.apply(this, arguments);
      ensurePreviewWidgets(this);
      repairShiftedWidgets(this);
      bindLivePreview(this);
      return ret;
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (info) {
      // Workflow JSON size is the source of truth for layout.
      if (info?.size && info.size.length >= 2) {
        this.__triposeHasUserSize = true;
      }
      const locked = info?.size
        ? [info.size[0], info.size[1]]
        : snapshotSize(this);
      const ret = onConfigure?.apply(this, arguments);
      ensurePreviewWidgets(this);
      repairShiftedWidgets(this);
      // Do not index widgets_values by fixed offsets — google_fallback shifted slots.
      // Named preview widgets / onExecuted are the source of truth after run.
      restoreSize(this, locked);
      bindLivePreview(this);
      return ret;
    };

    const onExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      const locked = snapshotSize(this);
      onExecuted?.apply(this, arguments);
      ensurePreviewWidgets(this);
      const mapped = message?.mapped_text?.[0] ?? "";
      const unmapped = message?.unmapped_text?.[0] ?? "";
      setPreview(this, mapped, unmapped);
      restoreSize(this, locked);
    };
  },
});
