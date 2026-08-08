(() => {
  "use strict";

  const EMBEDDED = new URLSearchParams(window.location.search).get("embedded") === "1";
  if (EMBEDDED) {
    document.body.classList.add("embedded");
  }

  function publishShellStatus(payload) {
    if (!EMBEDDED || window.parent === window) {
      return;
    }
    window.parent.postMessage(
      {
        source: "tagtoolbox-toolbox",
        type: "toolbox-status",
        ...payload,
      },
      window.location.origin,
    );
  }

  const DATA_ROOT = new URL("./data/", window.location.href);
  const MANIFEST_URL = new URL("manifest.json?editor-bridge=1", DATA_ROOT);
  const RENDER_LIMIT = 2500;
  const PRESET_LIMIT = 80;
  const PRESET_HISTORY_LIMIT = 12;
  const PRESET_IMAGE_LIMIT = 48;
  const PRESET_STORAGE_KEY = "tag-toolbox-v3:kits";
  const LAYOUT_STORAGE_KEY = "tag-toolbox-v3:v1-layout";
  const PRESET_TYPES = [
    { id: "character", label: "角色设计", hint: "主体 / 外貌 / 表情 / 服装 等身份向组合" },
    { id: "scene", label: "场景设计", hint: "地点 / 环境 / 氛围 / 时空" },
    { id: "outfit", label: "服装设计", hint: "服饰 / 配饰 / 装扮" },
    { id: "action", label: "动作组", hint: "姿势 / 动作 / 交互" },
    { id: "expression", label: "表情", hint: "情绪 / 表情 / 反应" },
    { id: "free", label: "自由组合", hint: "未分型或旧版 Kit" },
  ];

  const ALLOWED_CONFIDENCE = new Set(["high", "medium", "low", "unknown"]);
  const ALLOWED_STATUS = new Set(["classified", "review", "entity"]);
  const ALLOWED_SAFETY = new Set(["safe", "sensitive", "adult", "blocked", "unknown"]);
  const ALLOWED_SOURCE = new Set(["m", "n", "b"]);
  const ALLOWED_CATEGORY = new Set([-1, 0, 4]);

  const FALLBACK_SLOTS = [
    ["visual", "视觉-表现-生成"],
    ["camera", "镜头-构图-结构"],
    ["person", "人物-主体"],
    ["look", "外貌-身体"],
    ["outfit", "服饰-配饰-装扮"],
    ["action", "姿势-动作-交互"],
    ["expression", "情绪-表情-反应"],
    ["scene", "场景-环境-时空"],
    ["object", "物件-装备-载具"],
    ["graphic", "文字-图形-符号-界面"],
    ["reference", "作品-文化-引用"],
    ["adult", "成人-性行为"],
    ["abnormal", "猎奇-非常规"],
    ["negative", "负面提示词"],
    ["character", "作品角色"],
  ].map(([id, label]) => ({ id, label, tree: [], order: [], labelMap: {} }));

  const SLOT_COLOR_KEYS = new Set([
    "visual", "camera", "person", "look", "outfit", "action", "expression",
    "scene", "object", "graphic", "reference", "adult", "abnormal",
    "negative", "character", "artist", "review", "other",
    "quality", "style", "subject",
  ]);

  const SLOT_COLOR_ALIASES = {
    quality: "visual",
    style: "visual",
    subject: "person",
  };

  function slotColorKey(slotId) {
    const raw = String(slotId || "").trim();
    if (!raw) return "other";
    if (SLOT_COLOR_KEYS.has(raw)) return SLOT_COLOR_ALIASES[raw] || raw;
    const stripped = raw.replace(/^v\d+-/i, "");
    if (SLOT_COLOR_KEYS.has(stripped)) return SLOT_COLOR_ALIASES[stripped] || stripped;
    if (/(?:^|[-_/])negative$/i.test(raw)) return "negative";
    if (/(?:^|[-_/])artist$/i.test(raw)) return "artist";
    if (/(?:^|[-_/])character$/i.test(raw)) return "character";
    if (/(?:^|[-_/])abnormal$/i.test(raw)) return "abnormal";
    return "other";
  }

  const ARTIST_SLOT = {
    id: "artist",
    label: "画师",
    tree: [],
    order: [],
    labelMap: {},
  };

  const SOURCE_OPTIONS = [
    ["all", "全部来源"],
    ["m", "Main"],
    ["n", "NSFW"],
    ["b", "双源"],
  ];

  const SAFETY_OPTIONS = [
    ["all", "全部安全等级"],
    ["safe", "Safe"],
    ["sensitive", "Sensitive"],
    ["adult", "Adult"],
    ["unknown", "Unknown"],
    ["blocked", "Blocked"],
  ];

  const elements = {
    appShell: document.getElementById("app-shell"),
    loadingOverlay: document.getElementById("loading-overlay"),
    loadingTitle: document.getElementById("loading-title"),
    loadingDetail: document.getElementById("loading-detail"),
    loadingProgress: document.getElementById("loading-progress"),
    loadingStats: document.getElementById("loading-stats"),
    retryLoad: document.getElementById("retry-load"),
    datasetSummary: document.getElementById("dataset-summary"),
    datasetStatus: document.getElementById("dataset-status"),
    shardSummary: document.getElementById("shard-summary"),
    search: document.getElementById("search"),
    clearSearch: document.getElementById("clear-search"),
    typeFilters: document.getElementById("type-filters"),
    sourceToggle: document.getElementById("source-toggle"),
    safetyToggle: document.getElementById("safety-toggle"),
    sourceFilters: document.getElementById("source-filters"),
    safetyFilters: document.getElementById("safety-filters"),
    resetFilters: document.getElementById("reset-filters"),
    subTree: document.getElementById("sub-tree"),
    workBar: document.getElementById("work-bar"),
    workFilter: document.getElementById("work-filter"),
    workFilters: document.getElementById("work-filters"),
    workResizer: document.getElementById("work-resizer"),
    popularitySort: document.getElementById("popularity-sort"),
    resultsSummary: document.getElementById("results-summary"),
    resultsHint: document.getElementById("results-hint"),
    artistLoadStatus: document.getElementById("artist-load-status"),
    resultList: document.getElementById("lex-list"),
    browserTitle: document.getElementById("browser-title"),
    composerTitle: document.getElementById("composer-title"),
    pickedCount: document.getElementById("picked-count"),
    mobilePickedCount: document.getElementById("mobile-picked-count"),
    toggleEmptySlots: document.getElementById("toggle-empty-slots"),
    openPresets: document.getElementById("open-presets"),
    clearSelection: document.getElementById("clear-selection"),
    slotList: document.getElementById("slot-list"),
    presetDialog: document.getElementById("preset-dialog"),
    closePresets: document.getElementById("close-presets"),
    presetTypes: document.getElementById("preset-types"),
    presetListTitle: document.getElementById("preset-list-title"),
    presetListCount: document.getElementById("preset-list-count"),
    presetList: document.getElementById("preset-list"),
    presetName: document.getElementById("preset-name"),
    presetNotes: document.getElementById("preset-notes"),
    presetImages: document.getElementById("preset-images"),
    presetImageCount: document.getElementById("preset-image-count"),
    presetImportImages: document.getElementById("preset-import-images"),
    presetImageInput: document.getElementById("preset-image-input"),
    presetMeta: document.getElementById("preset-meta"),
    presetSaveNew: document.getElementById("preset-save-new"),
    presetOverwrite: document.getElementById("preset-overwrite"),
    presetLoad: document.getElementById("preset-load"),
    presetDelete: document.getElementById("preset-delete"),
    presetHistory: document.getElementById("preset-history"),
    presetHistoryList: document.getElementById("preset-history-list"),
    exportOutput: document.getElementById("export-box"),
    exportSummary: document.getElementById("export-summary"),
    bilingualPanes: document.getElementById("bilingual-panes"),
    bilingualZh: document.getElementById("bilingual-zh"),
    bilingualEn: document.getElementById("bilingual-en"),
    copyExport: document.getElementById("copy-export"),
    colResizer: document.getElementById("col-resizer"),
    rowResizer: document.getElementById("row-resizer"),
    main: document.getElementById("main-content"),
    toast: document.getElementById("toast"),
  };

  const state = {
    manifest: null,
    taxonomy: null,
    works: new Map(),
    tags: [],
    alphaTags: [],
    popularTags: [],
    artists: [],
    alphaArtists: [],
    popularArtists: [],
    artistsLoaded: false,
    artistsLoading: false,
    artistPromise: null,
    byId: new Map(),
    filtered: [],
    slots: FALLBACK_SLOTS,
    slotMap: new Map(FALLBACK_SLOTS.map((slot) => [slot.id, slot])),
    pathLabels: new Map(FALLBACK_SLOTS.map((slot) => [slot.id, slot.label])),
    selected: [],
    typeFilter: "all",
    subGroup: "all",
    subFilter: "all",
    leafFilter: "all",
    sourceFilter: "all",
    safetyFilter: "all",
    sourceEnabled: false,
    safetyEnabled: false,
    workFilter: "all",
    workQuery: "",
    popularitySort: false,
    hideEmptySlots: true,
    collapsedSlots: new Set(),
    exportMode: "en",
    presetType: "character",
    presetSelectedId: "",
    presetDraftImages: [],
    filterRevision: 0,
    searchTimer: 0,
    workTimer: 0,
    toastTimer: 0,
    dragId: null,
    loadController: null,
    loadAttempt: 0,
    ready: false,
  };

  function createNode(name, className, text) {
    const node = document.createElement(name);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function nextFrame() {
    return new Promise((resolve) => {
      if (typeof window.requestAnimationFrame === "function") {
        window.requestAnimationFrame(resolve);
      } else {
        window.setTimeout(resolve, 0);
      }
    });
  }

  function normalizeSearch(value) {
    return String(value || "")
      .normalize("NFKC")
      .toLocaleLowerCase("zh-CN")
      .replaceAll("_", " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function displayEnglish(value) {
    return String(value || "").replaceAll("_", " ");
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString("zh-CN");
  }

  function compareEnglish(left, right) {
    if (left.e < right.e) return -1;
    if (left.e > right.e) return 1;
    return 0;
  }

  function comparePopularity(left, right) {
    return (right.p - left.p) || compareEnglish(left, right);
  }

  function setLoading(percent, title, detail, stats) {
    const safePercent = Math.max(0, Math.min(100, Number(percent) || 0));
    elements.loadingProgress.value = safePercent;
    elements.loadingProgress.textContent = `${Math.round(safePercent)}%`;
    elements.loadingTitle.textContent = title;
    elements.loadingDetail.textContent = detail;
    elements.loadingStats.textContent = stats || `${Math.round(safePercent)}%`;
  }

  function showToast(message) {
    window.clearTimeout(state.toastTimer);
    elements.toast.textContent = String(message);
    elements.toast.classList.add("is-visible");
    state.toastTimer = window.setTimeout(() => {
      elements.toast.classList.remove("is-visible");
    }, 2600);
  }

  function isPlainObject(value) {
    return Boolean(value) && typeof value === "object" && !Array.isArray(value);
  }

  function isV3Schema(value) {
    const version = String(value || "").toLocaleLowerCase("en");
    return version === "3"
      || version.startsWith("3.")
      || version.endsWith("-v3")
      || version.includes("-v3-");
  }

  function safeDataUrl(file) {
    if (typeof file !== "string" || !file.trim()) {
      throw new Error("数据清单包含空文件路径。");
    }
    const clean = file.trim().replaceAll("\\", "/");
    if (/^[a-z][a-z0-9+.-]*:/i.test(clean) || clean.startsWith("//")) {
      throw new Error(`不允许跨源数据路径：${clean}`);
    }
    const url = clean.startsWith("data/")
      ? new URL(`./${clean}`, window.location.href)
      : new URL(clean, DATA_ROOT);
    if (url.origin !== window.location.origin || !url.pathname.startsWith(DATA_ROOT.pathname)) {
      throw new Error(`数据路径越界：${clean}`);
    }
    return url;
  }

  async function fetchJson(url, signal) {
    const response = await fetch(url, {
      cache: state.loadAttempt > 1 ? "no-cache" : "default",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    });
    if (!response.ok) {
      throw new Error(`${url.pathname} 返回 HTTP ${response.status}`);
    }
    try {
      return await response.json();
    } catch (error) {
      throw new Error(`${url.pathname} 不是有效 JSON：${error.message}`);
    }
  }

  function manifestArtifactFile(manifest, name, fallback) {
    const artifact = manifest.artifacts && manifest.artifacts[name];
    if (typeof artifact === "string") return artifact;
    if (isPlainObject(artifact) && typeof artifact.file === "string") return artifact.file;
    const direct = manifest[`${name}_file`];
    if (typeof direct === "string") return direct;
    return fallback;
  }

  function validateShardList(shards, fieldName, seen) {
    for (const [index, shard] of shards.entries()) {
      if (!isPlainObject(shard) || typeof shard.file !== "string") {
        throw new Error(`${fieldName}[${index}] 缺少 file。`);
      }
      if (seen.has(shard.file)) {
        throw new Error(`分片路径重复：${shard.file}`);
      }
      seen.add(shard.file);
      if (!Number.isInteger(shard.count) || shard.count < 0) {
        throw new Error(`${fieldName}[${index}].count 非法。`);
      }
      if (shard.bytes !== undefined && (!Number.isFinite(shard.bytes) || shard.bytes < 0)) {
        throw new Error(`${fieldName}[${index}].bytes 非法。`);
      }
      safeDataUrl(shard.file);
    }
  }

  function validateManifest(manifest) {
    if (!isPlainObject(manifest)) {
      throw new Error("manifest.json 根节点必须是对象。");
    }
    const version = String(manifest.schema_version ?? "");
    if (!isV3Schema(version)) {
      throw new Error(`不支持的数据版本：${version || "缺失"}`);
    }
    if (!Array.isArray(manifest.shards) || manifest.shards.length === 0) {
      throw new Error("manifest.json 未声明任何 shards。");
    }
    const seen = new Set();
    validateShardList(manifest.shards, "shards", seen);
    if (manifest.artist_shards !== undefined) {
      if (!Array.isArray(manifest.artist_shards)) {
        throw new Error("manifest.artist_shards 必须是数组。");
      }
      validateShardList(manifest.artist_shards, "artist_shards", seen);
    }
    return manifest;
  }

  function normalizeWorks(payload) {
    const root = isPlainObject(payload) && isPlainObject(payload.works)
      ? payload.works
      : {};
    const map = new Map();
    for (const [id, value] of Object.entries(root)) {
      if (!id) continue;
      let zh = "";
      if (typeof value === "string") zh = value;
      else if (isPlainObject(value)) zh = String(value.z ?? value.zh ?? value.label ?? "");
      map.set(id, {
        id,
        en: displayEnglish(id),
        zh,
        search: normalizeSearch(`${id} ${zh}`),
      });
    }
    return map;
  }

  function registerPathLabel(id, label) {
    if (typeof id !== "string" || !id) return;
    if (typeof label === "string" && label) state.pathLabels.set(id, label);
    else if (!state.pathLabels.has(id)) state.pathLabels.set(id, id);
  }

  function normalizeTaxonomy(payload) {
    const slots = Array.isArray(payload && payload.slots) ? payload.slots : [];
    state.pathLabels = new Map();
    if (isPlainObject(payload && payload.path_labels)) {
      for (const [path, label] of Object.entries(payload.path_labels)) {
        registerPathLabel(path, label);
      }
    }
    const normalized = [];
    for (const rawSlot of slots) {
      if (!isPlainObject(rawSlot) || typeof rawSlot.id !== "string" || !rawSlot.id) continue;
      if (rawSlot.id === "meta" || rawSlot.id === "artist") continue;
      const labelMap = isPlainObject(rawSlot.label_map) ? rawSlot.label_map : {};
      const slot = {
        id: rawSlot.id,
        label: typeof rawSlot.label === "string" && rawSlot.label ? rawSlot.label : rawSlot.id,
        tree: Array.isArray(rawSlot.tree) ? rawSlot.tree : [],
        order: Array.isArray(rawSlot.order) ? rawSlot.order.filter((id) => typeof id === "string") : [],
        labelMap,
      };
      normalized.push(slot);
      registerPathLabel(slot.id, slot.label);
      for (const [id, label] of Object.entries(labelMap)) registerPathLabel(id, label);
      for (const l2 of slot.tree) {
        if (!isPlainObject(l2)) continue;
        registerPathLabel(l2.id, l2.label);
        if (isPlainObject(l2.l3_meta)) {
          for (const [id, meta] of Object.entries(l2.l3_meta)) {
            registerPathLabel(id, isPlainObject(meta) ? meta.label : id);
            if (isPlainObject(meta) && isPlainObject(meta.l4_meta)) {
              for (const [leafId, leafMeta] of Object.entries(meta.l4_meta)) {
                registerPathLabel(
                  leafId,
                  isPlainObject(leafMeta) ? leafMeta.label : leafId,
                );
              }
            }
          }
        }
      }
    }
    if (normalized.length === 0) {
      for (const fallback of FALLBACK_SLOTS) {
        normalized.push(fallback);
        registerPathLabel(fallback.id, fallback.label);
      }
    }
    state.taxonomy = payload;
    state.slots = normalized;
    state.slotMap = new Map(normalized.map((slot) => [slot.id, slot]));
  }

  function assertStringArray(value, field, location) {
    if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
      throw new Error(`${location}.${field} 必须是 string[]。`);
    }
  }

  function validateHeatFields(raw, location) {
    for (const field of ["p", "pm", "pn"]) {
      if (!Number.isInteger(raw[field]) || raw[field] < 0) {
        throw new Error(`${location}.${field} 必须是非负整数。`);
      }
    }
    if (raw.p !== Math.max(raw.pm, raw.pn)) {
      throw new Error(`${location}.p 必须等于 max(pm,pn)。`);
    }
  }

  function validateCompactRow(raw, location) {
    if (!isPlainObject(raw)) throw new Error(`${location} 必须是对象。`);
    if (typeof raw.e !== "string" || !raw.e.trim()) throw new Error(`${location}.e 缺失。`);
    if (typeof raw.z !== "string") throw new Error(`${location}.z 必须是 string。`);
    assertStringArray(raw.za, "za", location);
    assertStringArray(raw.ea, "ea", location);
    validateHeatFields(raw, location);
    if (!ALLOWED_SOURCE.has(raw.o)) throw new Error(`${location}.o 非法。`);
    if (!ALLOWED_CATEGORY.has(raw.g)) throw new Error(`${location}.g 非法。`);
    if (!Array.isArray(raw.l) || raw.l.length !== 4 || raw.l.some((item) => typeof item !== "string" || !item)) {
      throw new Error(`${location}.l 必须是四段非空路径。`);
    }
    if (!ALLOWED_CONFIDENCE.has(raw.c)) throw new Error(`${location}.c 非法。`);
    if (!ALLOWED_STATUS.has(raw.t)) throw new Error(`${location}.t 非法。`);
    if (!ALLOWED_SAFETY.has(raw.y)) throw new Error(`${location}.y 非法。`);
    if (typeof raw.w !== "string") throw new Error(`${location}.w 必须是 string。`);
    if (raw.t === "entity" && (raw.g !== 4 || raw.l.join("/") !== "character/character/character/character")) {
      throw new Error(`${location} 的角色路径不符合契约。`);
    }
    if (raw.t === "review" && raw.l.join("/") !== "other/unclassified/unclassified/unclassified") {
      throw new Error(`${location} 的 review 路径不符合契约。`);
    }
  }

  function normalizeCompactRow(raw, location) {
    validateCompactRow(raw, location);
    if (state.byId.has(raw.e)) throw new Error(`${location}.e 与已有记录重复：${raw.e}`);
    const zhAliases = [...new Set(raw.za.filter((item) => item && item !== raw.z))];
    const enAliases = [...new Set(raw.ea.filter((item) => item && item !== raw.e))];
    const work = raw.w ? state.works.get(raw.w) : null;
    const pathText = pathLabelsFor(raw.l).join(" ");
    const tag = {
      id: raw.e,
      kind: "tag",
      e: raw.e,
      en: displayEnglish(raw.e),
      z: raw.z,
      za: zhAliases,
      ea: enAliases,
      p: raw.p,
      pm: raw.pm,
      pn: raw.pn,
      o: raw.o,
      g: raw.g,
      l: [...raw.l],
      c: raw.c,
      t: raw.t,
      y: raw.y,
      w: raw.w,
      work,
    };
    tag.search = normalizeSearch([
      raw.e,
      tag.en,
      raw.z,
      ...zhAliases,
      ...enAliases,
      pathText,
      work ? `${work.id} ${work.zh}` : "",
    ].join(" "));
    state.byId.set(tag.id, tag);
    return tag;
  }

  function validateArtistRow(raw, location) {
    if (!isPlainObject(raw)) throw new Error(`${location} 必须是对象。`);
    if (typeof raw.e !== "string" || !raw.e.trim()) throw new Error(`${location}.e 缺失。`);
    if (typeof raw.z !== "string") throw new Error(`${location}.z 必须是 string。`);
    assertStringArray(raw.za, "za", location);
    validateHeatFields(raw, location);
    if (!ALLOWED_SOURCE.has(raw.o)) throw new Error(`${location}.o 非法。`);
    if (!ALLOWED_SAFETY.has(raw.y)) throw new Error(`${location}.y 非法。`);
  }

  function normalizeArtistRow(raw, location) {
    validateArtistRow(raw, location);
    const id = `artist:${raw.e}`;
    if (state.byId.has(id)) throw new Error(`${location}.e 与已有画师重复：${raw.e}`);
    const zhAliases = [...new Set(raw.za.filter((item) => item && item !== raw.z))];
    const tag = {
      id,
      kind: "artist",
      e: raw.e,
      en: displayEnglish(raw.e),
      z: raw.z,
      za: zhAliases,
      ea: [],
      p: raw.p,
      pm: raw.pm,
      pn: raw.pn,
      o: raw.o,
      g: 1,
      l: ["artist", "artist", "artist", "artist"],
      c: "unknown",
      t: "artist",
      y: raw.y,
      w: "",
      work: null,
    };
    tag.search = normalizeSearch([raw.e, tag.en, raw.z, ...zhAliases].join(" "));
    state.byId.set(id, tag);
    return tag;
  }

  function shardTags(payload, expectedIndex, manifestShard) {
    if (!isPlainObject(payload) || !Array.isArray(payload.tags)) {
      throw new Error(`分片 ${expectedIndex + 1} 根节点必须包含 tags[]。`);
    }
    const version = String(payload.schema_version ?? "");
    if (!isV3Schema(version)) {
      throw new Error(`分片 ${expectedIndex + 1} 的 schema_version 非 v3。`);
    }
    if (
      payload.shard !== undefined
      && manifestShard.shard !== undefined
      && String(payload.shard) !== String(manifestShard.shard)
    ) {
      throw new Error(`分片序号不一致：manifest=${manifestShard.shard}，payload=${payload.shard}`);
    }
    return payload.tags;
  }

  function shardArtists(payload, expectedIndex, manifestShard) {
    if (!isPlainObject(payload) || !Array.isArray(payload.artists)) {
      throw new Error(`画师分片 ${expectedIndex + 1} 根节点必须包含 artists[]。`);
    }
    const version = String(payload.schema_version ?? "").toLocaleLowerCase("en");
    if (!version.includes("artist") || !isV3Schema(version)) {
      throw new Error(`画师分片 ${expectedIndex + 1} 的 schema_version 非 artists v3。`);
    }
    if (
      payload.shard !== undefined
      && manifestShard.shard !== undefined
      && String(payload.shard) !== String(manifestShard.shard)
    ) {
      throw new Error(`画师分片序号不一致：manifest=${manifestShard.shard}，payload=${payload.shard}`);
    }
    return payload.artists;
  }

  function expectedRecordCount(manifest) {
    const counts = isPlainObject(manifest.counts) ? manifest.counts : {};
    for (const key of ["browser_total", "records", "tags", "total", "browser_records", "visible_records"]) {
      if (Number.isInteger(counts[key])) return counts[key];
    }
    return manifest.shards.reduce((sum, shard) => sum + shard.count, 0);
  }

  function artistShardCount() {
    const shards = state.manifest && Array.isArray(state.manifest.artist_shards)
      ? state.manifest.artist_shards
      : [];
    return shards.reduce((sum, shard) => sum + shard.count, 0);
  }

  function setSelectOptions(select, options, selectedValue) {
    const fragment = document.createDocumentFragment();
    for (const optionData of options) {
      const option = document.createElement("option");
      option.value = optionData.value;
      option.textContent = optionData.label;
      if (optionData.value === selectedValue) option.selected = true;
      fragment.append(option);
    }
    select.replaceChildren(fragment);
  }

  function makeChip(label, pressed, dataName, dataValue, slotId = "") {
    const button = createNode("button", "chip", label);
    button.type = "button";
    button.setAttribute("aria-pressed", String(pressed));
    if (dataName === "type") button.dataset.type = dataValue;
    else if (dataName === "group") button.dataset.group = dataValue;
    else if (dataName === "sub") button.dataset.sub = dataValue;
    else if (dataName === "leaf") button.dataset.leaf = dataValue;
    else button.dataset[dataName] = dataValue;
    if (slotId) button.dataset.slot = slotColorKey(slotId);
    return button;
  }

  function renderTypeFilters() {
    const fragment = document.createDocumentFragment();
    fragment.append(makeChip("主分类·全部", state.typeFilter === "all", "type", "all"));

    for (const slot of state.slots) {
      fragment.append(makeChip(
        slot.label,
        state.typeFilter === slot.id,
        "type",
        slot.id,
        slot.id,
      ));
    }
    const artistCount = artistShardCount();
    fragment.append(makeChip(
      `画师${artistCount ? ` · ${formatNumber(artistCount)}` : ""}`,
      state.typeFilter === "artist",
      "type",
      "artist",
      "artist",
    ));
    elements.typeFilters.replaceChildren(fragment);
  }

  function renderSwitchFilters() {
    elements.sourceToggle.setAttribute("aria-pressed", String(state.sourceEnabled));
    elements.safetyToggle.setAttribute("aria-pressed", String(state.safetyEnabled));
    elements.sourceFilters.hidden = !state.sourceEnabled;
    elements.safetyFilters.hidden = !state.safetyEnabled;
    const sourceFragment = document.createDocumentFragment();
    for (const [id, label] of SOURCE_OPTIONS) {
      sourceFragment.append(makeChip(label, state.sourceFilter === id, "source", id));
    }
    elements.sourceFilters.replaceChildren(sourceFragment);

    const safetyFragment = document.createDocumentFragment();
    for (const [id, label] of SAFETY_OPTIONS) {
      safetyFragment.append(makeChip(label, state.safetyFilter === id, "safety", id));
    }
    elements.safetyFilters.replaceChildren(safetyFragment);
  }

  function passesSourceSafety(tag) {
    if (state.sourceFilter !== "all" && tag.o !== state.sourceFilter) return false;
    if (state.safetyFilter !== "all" && tag.y !== state.safetyFilter) return false;
    return true;
  }

  function usableTag(tag) {
    return tag.t === "classified" || tag.t === "entity";
  }

  function taxonomyCounts() {
    const maps = [new Map(), new Map(), new Map(), new Map()];
    if (!state.slotMap.has(state.typeFilter)) return maps;
    for (const tag of state.tags) {
      if (!usableTag(tag) || tag.l[0] !== state.typeFilter || !passesSourceSafety(tag)) continue;
      for (let level = 1; level <= 3; level += 1) {
        const id = tag.l[level];
        maps[level].set(id, (maps[level].get(id) || 0) + 1);
      }
    }
    return maps;
  }

  function shortChipLabel(label) {
    const text = String(label || "").trim();
    if (!text) return "";
    // Taxonomy mistakes may store full Chinese paths; chips show leaf only.
    const slash = text.lastIndexOf("/");
    return slash >= 0 ? text.slice(slash + 1).trim() || text : text;
  }

  function labelFor(id) {
    return shortChipLabel(state.pathLabels.get(id) || id);
  }

  function pathLabelsFor(path) {
    const labels = [];
    const parts = [];
    for (const id of path) {
      if (parts.at(-1) === id) continue;
      parts.push(id);
      const fullPath = parts.join("/");
      labels.push(shortChipLabel(state.pathLabels.get(fullPath) || labelFor(id)));
    }
    return labels;
  }

  function isLeafGroup(group) {
    return Boolean(
      group
      && (
        group.leaf
        || (
          Array.isArray(group.children)
          && group.children.length === 1
          && group.children[0] === group.id
        )
      )
    );
  }

  function appendFilterRow(fragment, label, buttons) {
    const row = createNode("div", "sub-tree-row");
    row.append(createNode("span", "sub-tree-label", label), ...buttons);
    fragment.append(row);
  }

  function renderSubTree() {
    const fragment = document.createDocumentFragment();
    const slot = state.slotMap.get(state.typeFilter);
    if (!slot || !Array.isArray(slot.tree) || slot.tree.length === 0) {
      elements.subTree.replaceChildren();
      return;
    }

    elements.subTree.dataset.activeSlot = slotColorKey(slot.id);
    const counts = taxonomyCounts();
    const l2Buttons = [
      makeChip("子分类·全部", state.subGroup === "all", "group", "all", slot.id),
    ];
    for (const group of slot.tree) {
      if (!isPlainObject(group) || typeof group.id !== "string") continue;
      const count = counts[1].get(group.id) || 0;
      if (!count) continue;
      const button = makeChip(
        `${shortChipLabel(group.label || labelFor(group.id))} · ${formatNumber(count)}`,
        state.subGroup === group.id,
        "group",
        group.id,
        slot.id,
      );
      button.classList.add("chip-parent");
      l2Buttons.push(button);
    }
    l2Buttons[0].classList.add("chip-parent");
    appendFilterRow(fragment, "子分类", l2Buttons);

    const activeGroup = slot.tree.find((group) => group && group.id === state.subGroup);
    if (!activeGroup || isLeafGroup(activeGroup)) {
      state.subFilter = "all";
      state.leafFilter = "all";
      elements.subTree.replaceChildren(fragment);
      return;
    }

    const childIds = Array.isArray(activeGroup.children) ? activeGroup.children : [];
    const presentChildIds = childIds.filter((id) => (counts[2].get(id) || 0) > 0);
    const groupCount = counts[1].get(activeGroup.id) || 0;
    const compactedSubFilter = presentChildIds.length === 1
      && (counts[2].get(presentChildIds[0]) || 0) === groupCount
      ? presentChildIds[0]
      : null;

    if (compactedSubFilter) {
      state.subFilter = compactedSubFilter;
    } else {
      if (state.subFilter !== "all" && !presentChildIds.includes(state.subFilter)) {
        state.subFilter = "all";
        state.leafFilter = "all";
      }
      const l3Buttons = [
        makeChip("子类·全部", state.subFilter === "all", "sub", "all", slot.id),
      ];
      for (const id of presentChildIds) {
        const count = counts[2].get(id) || 0;
        const button = makeChip(
          `${shortChipLabel(activeGroup.l3_meta?.[id]?.label || labelFor(id))} · ${formatNumber(count)}`,
          state.subFilter === id && state.leafFilter === "all",
          "sub",
          id,
          slot.id,
        );
        button.classList.add("chip-child");
        l3Buttons.push(button);
      }
      l3Buttons[0].classList.add("chip-child");
      appendFilterRow(fragment, "子类", l3Buttons);
    }

    const activeSubFilter = compactedSubFilter || state.subFilter;
    if (activeSubFilter !== "all" && isPlainObject(activeGroup.l3_meta)) {
      const l3Meta = activeGroup.l3_meta[activeSubFilter];
      const leafIds = isPlainObject(l3Meta) && !l3Meta.leaf && Array.isArray(l3Meta.children)
        ? l3Meta.children
        : [];
      const present = leafIds.filter((id) => (counts[3].get(id) || 0) > 0);
      const subCount = counts[2].get(activeSubFilter) || 0;
      const smallLeafGroupException = activeSubFilter === "emoji";
      if (present.length >= 2 && (subCount >= 30 || smallLeafGroupException)) {
        if (state.leafFilter !== "all" && !present.includes(state.leafFilter)) {
          state.leafFilter = "all";
        }
        const l4Buttons = [
          makeChip("细类·全部", state.leafFilter === "all", "leaf", "all", slot.id),
        ];
        for (const id of present) {
          const button = makeChip(
            `${shortChipLabel(labelFor(id))} · ${formatNumber(counts[3].get(id) || 0)}`,
            state.leafFilter === id,
            "leaf",
            id,
            slot.id,
          );
          button.classList.add("chip-leaf");
          l4Buttons.push(button);
        }
        l4Buttons[0].classList.add("chip-leaf");
        appendFilterRow(fragment, "细类", l4Buttons);
      } else {
        state.leafFilter = "all";
      }
    } else {
      state.leafFilter = "all";
    }
    elements.subTree.replaceChildren(fragment);
  }

  function isWorkBrowseMode() {
    return state.typeFilter === "character";
  }

  function workLabel(workId) {
    if (workId === "none") return "未标注作品";
    const work = state.works.get(workId);
    if (!work) return displayEnglish(workId);
    return work.zh ? `${work.zh} · ${work.en}` : work.en;
  }

  function currentWorks() {
    if (!isWorkBrowseMode()) return [];
    const counts = new Map();
    let none = 0;
    for (const tag of state.tags) {
      if (!usableTag(tag) || tag.l[0] !== "character") continue;
      if (!passesSourceSafety(tag)) continue;
      if (!tag.w) none += 1;
      else counts.set(tag.w, (counts.get(tag.w) || 0) + 1);
    }
    const query = normalizeSearch(state.workQuery);
    let rows = [...counts.entries()]
      .filter(([id]) => {
        if (!query) return true;
        const work = state.works.get(id);
        return Boolean(work && work.search.includes(query))
          || normalizeSearch(id).includes(query);
      })
      .sort((left, right) => (right[1] - left[1]) || left[0].localeCompare(right[0]));
    rows = rows.slice(0, query ? 120 : 200);
    if (
      none > 0
      && (
        !query
        || normalizeSearch("未标注作品 none").includes(query)
      )
    ) {
      rows.push(["none", none]);
    }
    return rows;
  }

  function renderWorkFilters() {
    if (!isWorkBrowseMode()) {
      elements.workBar.classList.remove("is-open");
      elements.workFilters.replaceChildren();
      if (state.workFilter !== "all" || state.workQuery) {
        state.workFilter = "all";
        state.workQuery = "";
        elements.workFilter.value = "";
      }
      return;
    }
    elements.workBar.classList.add("is-open");
    const fragment = document.createDocumentFragment();
    fragment.append(makeChip("作品·全部", state.workFilter === "all", "work", "all"));
    for (const [id, count] of currentWorks()) {
      fragment.append(makeChip(
        `${workLabel(id)} · ${formatNumber(count)}`,
        state.workFilter === id,
        "work",
        id,
      ));
    }
    elements.workFilters.replaceChildren(fragment);
  }

  function renderFilterUi() {
    renderTypeFilters();
    renderSwitchFilters();
    renderSubTree();
    renderWorkFilters();
  }

  function renderPopularitySort() {
    elements.popularitySort.setAttribute("aria-pressed", String(state.popularitySort));
    elements.popularitySort.setAttribute(
      "aria-label",
      `热度排行：已${state.popularitySort ? "开启" : "关闭"}`,
    );
    elements.popularitySort.title = state.popularitySort
      ? "当前按热度排序；点击切换为英文词典顺序"
      : "当前按英文词典顺序；点击切换为热度排序";
    elements.resultsHint.textContent = state.popularitySort
      ? "当前按热度排序 · 最多显示前 2500 条"
      : "默认按英文词典顺序 · 最多显示前 2500 条";
  }

  function filtersForScan() {
    return {
      query: normalizeSearch(elements.search.value),
      l1: state.typeFilter,
      group: state.subGroup,
      sub: state.subFilter,
      leaf: state.leafFilter,
      source: state.sourceFilter,
      safety: state.safetyFilter,
      work: state.workFilter,
    };
  }

  function tagMatchesFilters(tag, filters) {
    if (filters.source !== "all" && tag.o !== filters.source) return false;
    if (filters.safety !== "all" && tag.y !== filters.safety) return false;
    if (filters.query && !tag.search.includes(filters.query)) return false;

    if (filters.l1 === "artist") {
      return tag.kind === "artist";
    }
    if (tag.kind !== "tag") return false;
    if (filters.l1 === "review") {
      return tag.t === "review";
    }
    if (!usableTag(tag)) return false;
    if (filters.l1 !== "all" && tag.l[0] !== filters.l1) return false;
    if (filters.group !== "all" && tag.l[1] !== filters.group) return false;
    if (filters.sub !== "all" && tag.l[2] !== filters.sub) return false;
    if (filters.leaf !== "all" && tag.l[3] !== filters.leaf) return false;
    if (filters.work !== "all") {
      if (filters.work === "none" && tag.w) return false;
      if (filters.work !== "none" && tag.w !== filters.work) return false;
    }
    return true;
  }

  function scanSource() {
    if (state.typeFilter === "artist") {
      return state.popularitySort ? state.popularArtists : state.alphaArtists;
    }
    return state.popularitySort ? state.popularTags : state.alphaTags;
  }

  async function applyFilters() {
    const revision = ++state.filterRevision;
    const filters = filtersForScan();
    const rows = scanSource();
    elements.resultList.setAttribute("aria-busy", "true");
    elements.resultsSummary.textContent = "正在筛选…";
    const matches = [];
    let sliceStart = performance.now();
    for (let index = 0; index < rows.length; index += 1) {
      if (tagMatchesFilters(rows[index], filters)) matches.push(rows[index]);
      if (index % 1500 === 0 && performance.now() - sliceStart > 12) {
        await nextFrame();
        if (revision !== state.filterRevision) return;
        sliceStart = performance.now();
      }
    }
    if (revision !== state.filterRevision) return;
    state.filtered = matches;
    renderResults();
    elements.resultList.setAttribute("aria-busy", "false");
  }

  function selectionFor(id) {
    return state.selected.find((item) => item.id === id) || null;
  }

  function focusResultAction(id) {
    for (const button of elements.resultList.querySelectorAll("button[data-select-id]")) {
      if (button.dataset.selectId === id) {
        button.focus({ preventScroll: true });
        return;
      }
    }
  }

  function focusPickedControl(id) {
    for (const button of elements.slotList.querySelectorAll("button[data-remove-id]")) {
      if (button.dataset.removeId === id) {
        button.focus({ preventScroll: true });
        return;
      }
    }
    elements.composerTitle.focus({ preventScroll: true });
  }

  function tagSlot(tag) {
    if (tag.kind === "artist") return "artist";
    if (tag.t === "review") return "review";
    return tag.l[0];
  }

  function negativeSlot() {
    return state.slots.find((slot) => (
      slot.id === "negative"
      || slot.label === "负面提示词"
      || /(?:^|-)negative$/.test(slot.id)
    )) || null;
  }

  function negativeSlotId() {
    return negativeSlot()?.id || "negative";
  }

  function isNegativeSlotId(slotId) {
    return slotId === negativeSlotId();
  }

  function isNegativeTag(tag) {
    return tag.kind !== "artist" && isNegativeSlotId(tag.l[0]);
  }

  function isSelectable(tag) {
    return tag.kind === "artist"
      ? tag.y !== "blocked"
      : tag.t !== "review" && tag.y !== "blocked";
  }

  function defaultPolarity(tag) {
    if (tag.kind === "artist") return "artist";
    return isNegativeTag(tag) ? "negative" : "positive";
  }

  function tagTitle(tag) {
    if (tag.kind === "artist") {
      return `画师 · source=${tag.o} · safety=${tag.y} · heat=${formatNumber(tag.p)}`;
    }
    const path = pathLabelsFor(tag.l).join(" / ");
    return `${path} · source=${tag.o} · safety=${tag.y} · heat=${formatNumber(tag.p)}`;
  }

  function makeTagCard(tag) {
    const selection = selectionFor(tag.id);
    const selected = Boolean(selection);
    const polarity = selection ? selection.polarity : defaultPolarity(tag);
    const name = tag.z || tag.en;

    const button = createNode("button", "lex-item");
    button.type = "button";
    button.dataset.slot = slotColorKey(tag.kind === "artist" ? "artist" : tagSlot(tag));
    button.dataset.selectId = tag.id;
    button.dataset.polarity = polarity;
    button.setAttribute("aria-pressed", String(selected));
    button.classList.toggle("selected", selected);
    button.setAttribute(
      "aria-label",
      tag.t === "review"
        ? `审阅待复核词 ${name}`
        : `${selected ? "移除" : "添加"}${name}`,
    );
    button.title = tagTitle(tag);
    if (!isSelectable(tag)) {
      button.setAttribute("aria-disabled", "true");
    }

    const dot = createNode("span", "dot");
    dot.setAttribute("aria-hidden", "true");
    button.append(
      dot,
      createNode("span", "zh", name),
      createNode("span", "en", tag.en),
    );
    return button;
  }

  function emptyResultMessage() {
    if (state.typeFilter === "artist") {
      if (state.artistsLoading) return "正在加载独立画师词库…";
      if (!artistShardCount()) return "画师库待生成：manifest 尚未提供 artist_shards。";
    }
    if (state.typeFilter === "review") {
      return "待复核入口没有匹配结果；可缩短搜索词或恢复全部来源与安全等级。";
    }
    return "当前筛选无结果。可点“主分类·全部”，或换个搜索词。";
  }

  function renderResults() {
    const total = state.filtered.length;
    const visibleCount = Math.min(total, RENDER_LIMIT);
    const fragment = document.createDocumentFragment();
    if (!total) {
      fragment.append(createNode("div", "results-empty", emptyResultMessage()));
    } else {
      if (total > visibleCount) {
        fragment.append(createNode(
          "div",
          "list-hint",
          `仅渲染前 ${formatNumber(visibleCount)} 条（共命中 ${formatNumber(total)}）。请用搜索或分类缩小范围。`,
        ));
      }
      for (let index = 0; index < visibleCount; index += 1) {
        fragment.append(makeTagCard(state.filtered[index]));
      }
    }
    elements.resultList.replaceChildren(fragment);
    const libraryTotal = state.typeFilter === "artist" ? state.artists.length : state.tags.length;
    elements.resultsSummary.textContent =
      `${formatNumber(visibleCount)} 显示 / ${formatNumber(total)} 命中 / ${formatNumber(libraryTotal)} 当前库`;
  }

  function defaultPositiveSlot(tag) {
    const proposed = tag.l[0];
    if (!isNegativeSlotId(proposed) && state.slotMap.has(proposed)) return proposed;
    return state.slots.find((slot) => !isNegativeSlotId(slot.id))?.id || state.slots[0].id;
  }

  function toggleSelection(id) {
    const tag = state.byId.get(id);
    if (!tag) return;
    if (tag.t === "review") {
      showToast("待复核词仅供审阅，不进入普通 Prompt 导出。");
      return;
    }
    if (tag.y === "blocked") {
      showToast("Blocked 词不可加入导出。");
      return;
    }
    const index = state.selected.findIndex((item) => item.id === id);
    if (index >= 0) {
      state.selected.splice(index, 1);
      showToast(`已移除 ${tag.z || tag.en}`);
    } else {
      const polarity = defaultPolarity(tag);
      state.selected.push({
        id,
        kind: tag.kind,
        polarity,
        slot: tag.kind === "artist"
          ? "artist"
          : polarity === "negative"
            ? negativeSlotId()
            : defaultPositiveSlot(tag),
      });
      if (tag.kind === "artist") showToast(`${tag.z || tag.en} 已加入画师槽`);
      else showToast(`${tag.z || tag.en} 已入“${slotById(state.selected.at(-1).slot).label}”`);
    }
    renderResults();
    renderComposer();
    focusResultAction(id);
  }

  function composerSlots() {
    const negative = negativeSlot();
    const positive = state.slots.filter((slot) => !isNegativeSlotId(slot.id));
    return negative ? [...positive, ARTIST_SLOT, negative] : [...positive, ARTIST_SLOT];
  }

  function slotById(id) {
    if (id === "artist") return ARTIST_SLOT;
    return state.slotMap.get(id) || state.slots[0];
  }

  function orderedSelections(polarity) {
    const order = polarity === "artist"
      ? ["artist"]
      : state.slots
        .map((slot) => slot.id)
        .filter((id) => (
          polarity === "negative" ? isNegativeSlotId(id) : !isNegativeSlotId(id)
        ));
    const selected = [];
    for (const slotId of order) {
      selected.push(...state.selected.filter(
        (item) => (
          item.polarity === polarity
          && item.slot === slotId
          && (polarity === "artist" ? item.kind === "artist" : item.kind !== "artist")
        ),
      ));
    }
    return selected;
  }

  function positiveTags() {
    return orderedSelections("positive").map((item) => state.byId.get(item.id)).filter(Boolean);
  }

  function negativeTags() {
    return orderedSelections("negative").map((item) => state.byId.get(item.id)).filter(Boolean);
  }

  function artistTags() {
    return orderedSelections("artist").map((item) => state.byId.get(item.id)).filter(Boolean);
  }

  function makePicked(item) {
    const tag = state.byId.get(item.id);
    const picked = createNode("div", "picked");
    picked.draggable = true;
    picked.dataset.selectionId = item.id;
    picked.dataset.slot = slotColorKey(item.slot);
    picked.title = tag ? tagTitle(tag) : "数据集中已不存在";
    picked.append(
      createNode("span", "zh", tag ? (tag.z || tag.en) : item.id),
      createNode("span", "en", tag ? tag.en : "数据中已不存在"),
    );
    const remove = createNode("button", "remove-tag", "×");
    remove.type = "button";
    remove.dataset.removeId = item.id;
    remove.setAttribute("aria-label", `移除 ${tag ? (tag.z || tag.en) : item.id}`);
    picked.append(remove);
    return picked;
  }

  function renderSlots() {
    const fragment = document.createDocumentFragment();
    let rendered = 0;
    for (const slot of composerSlots()) {
      const items = state.selected.filter((item) => item.slot === slot.id);
      if (state.hideEmptySlots && !items.length) continue;
      rendered += 1;
      const card = createNode("section", "slot");
      card.dataset.slot = slotColorKey(slot.id);
      if (state.collapsedSlots.has(slot.id)) card.classList.add("is-collapsed");

      const head = createNode("button", "slot-head");
      head.type = "button";
      head.dataset.toggleSlot = slot.id;
      head.setAttribute("aria-expanded", String(!state.collapsedSlots.has(slot.id)));
      head.append(
        createNode("span", "swatch"),
        createNode("span", "title", slot.label),
        createNode("span", "count", `${items.length} 词`),
      );

      const body = createNode("div", "slot-body");
      body.dataset.dropSlot = slot.id;
      if (!items.length) {
        body.append(createNode("div", "slot-empty", "拖入或从左侧点选"));
      } else {
        for (const item of items) body.append(makePicked(item));
      }
      card.append(head, body);
      fragment.append(card);
    }
    if (!rendered) {
      const empty = createNode("div", "slot-empty-state");
      empty.append(createNode("p", "", "点选左侧标签会按 L1 自动入槽；画师进入独立画师槽。"));
      fragment.append(empty);
    }
    elements.slotList.replaceChildren(fragment);
  }

  function removeSelection(id) {
    const index = state.selected.findIndex((item) => item.id === id);
    if (index < 0) return;
    state.selected.splice(index, 1);
    renderResults();
    renderComposer();
    elements.composerTitle.focus({ preventScroll: true });
  }

  function canMoveToSlot(tag, slotId) {
    if (!tag) return false;
    if (tag.kind === "artist") return slotId === "artist";
    if (isNegativeTag(tag)) return isNegativeSlotId(slotId);
    return slotId !== "artist" && state.slotMap.has(slotId);
  }

  function moveSelectionTo(id, slotId, targetId = "") {
    const index = state.selected.findIndex((item) => item.id === id);
    if (index < 0) return;
    const tag = state.byId.get(id);
    if (!canMoveToSlot(tag, slotId)) {
      showToast(tag && tag.kind === "artist"
        ? "画师只能留在独立画师槽。"
        : "普通标签不能移入画师槽。");
      return;
    }
    const [item] = state.selected.splice(index, 1);
    item.slot = slotId;
    item.polarity = isNegativeSlotId(slotId) ? "negative" : "positive";
    if (tag.kind === "artist") item.polarity = "artist";

    let insertion = targetId
      ? state.selected.findIndex((candidate) => candidate.id === targetId)
      : -1;
    if (insertion < 0) {
      const last = state.selected.map((candidate) => candidate.slot).lastIndexOf(slotId);
      insertion = last >= 0 ? last + 1 : state.selected.length;
    }
    state.selected.splice(insertion, 0, item);
    renderResults();
    renderComposer();
    focusPickedControl(id);
  }

  function exportText() {
    const positive = positiveTags();
    const negative = negativeTags();
    const artists = artistTags();
    if (state.exportMode === "zh") {
      return positive.map((tag) => tag.z || tag.en).join(", ");
    }
    if (state.exportMode === "bilingual") {
      return positive.map((tag) => `${tag.z || tag.en}\t${tag.en}`).join("\n");
    }
    if (state.exportMode === "negative") {
      return negative.map((tag) => tag.en).join(", ");
    }
    if (state.exportMode === "artist") {
      return artists.map((tag) => tag.e).join(", ");
    }
    return positive.map((tag) => tag.en).join(", ");
  }

  function renderExport() {
    const bilingual = state.exportMode === "bilingual";
    elements.exportOutput.classList.toggle("is-hidden", bilingual);
    elements.bilingualPanes.classList.toggle("is-visible", bilingual);
    if (bilingual) {
      const positive = positiveTags();
      elements.bilingualZh.textContent = positive.map((tag) => tag.z || tag.en).join("\n");
      elements.bilingualEn.textContent = positive.map((tag) => tag.en).join("\n");
      elements.exportOutput.value = "";
    } else {
      elements.exportOutput.value = exportText();
      elements.bilingualZh.textContent = "";
      elements.bilingualEn.textContent = "";
    }
    elements.exportSummary.textContent =
      `正向 ${positiveTags().length} · 负向 ${negativeTags().length} · 画师 ${artistTags().length}`;
    for (const button of document.querySelectorAll("[data-export-mode]")) {
      button.setAttribute("aria-pressed", String(button.dataset.exportMode === state.exportMode));
    }
  }

  function renderComposer() {
    const count = state.selected.length;
    elements.pickedCount.textContent = `${count} 词`;
    elements.mobilePickedCount.textContent = String(count);
    elements.toggleEmptySlots.textContent = state.hideEmptySlots ? "显示空槽" : "折叠空槽";
    renderSlots();
    renderExport();
  }

  function presetTypeMeta(typeId) {
    return PRESET_TYPES.find((entry) => entry.id === typeId) || PRESET_TYPES[PRESET_TYPES.length - 1];
  }

  function safePresetImageFile(name) {
    const base = String(name || "").replace(/\\/g, "/").split("/").pop() || "";
    return /^img-[0-9a-f]+\.(jpg|jpeg|png|webp|gif)$/i.test(base) ? base : "";
  }

  function presetImageSrc(image) {
    if (!image) return "";
    if (typeof image.url === "string" && image.url.startsWith("/api/preset-images/")) {
      return image.url;
    }
    const file = safePresetImageFile(image.file);
    if (file) return `/api/preset-images/${file}`;
    if (typeof image.dataUrl === "string" && image.dataUrl.startsWith("data:image/")) {
      return image.dataUrl;
    }
    return "";
  }

  function normalizePresetImage(raw) {
    if (!isPlainObject(raw)) return null;
    const file = safePresetImageFile(raw.file || raw.relPath || "");
    const url = typeof raw.url === "string" && raw.url.startsWith("/api/preset-images/")
      ? raw.url
      : (file ? `/api/preset-images/${file}` : "");
    const dataUrl = typeof raw.dataUrl === "string" && raw.dataUrl.startsWith("data:image/")
      ? raw.dataUrl
      : "";
    if (!file && !url && !dataUrl) return null;
    const path = typeof raw.path === "string" ? raw.path : "";
    const relPath = typeof raw.relPath === "string"
      ? raw.relPath
      : (file ? `preset-images/${file}` : "");
    return {
      id: typeof raw.id === "string" ? raw.id : (file ? file.replace(/\.[^.]+$/, "") : `img-${Math.random().toString(36).slice(2, 8)}`),
      name: typeof raw.name === "string" ? raw.name : "配图",
      mime: typeof raw.mime === "string" ? raw.mime : "image/jpeg",
      width: Number(raw.width) || 0,
      height: Number(raw.height) || 0,
      file,
      relPath,
      path,
      url,
      // Legacy localStorage base64; kept only for old presets.
      ...(dataUrl && !file ? { dataUrl } : {}),
    };
  }

  function normalizePreset(raw) {
    if (!isPlainObject(raw) || typeof raw.id !== "string" || !Array.isArray(raw.items)) {
      return null;
    }
    const type = PRESET_TYPES.some((entry) => entry.id === raw.type) ? raw.type : "free";
    // Old local Kit used `version: 3` as payload schema, not iteration revision.
    const version = Number.isFinite(Number(raw.revision))
      ? Math.max(1, Math.floor(Number(raw.revision)))
      : (raw.schema === "tag-toolbox-preset-v1"
        && Number.isFinite(Number(raw.version))
        && Number(raw.version) >= 1)
        ? Math.floor(Number(raw.version))
        : 1;
    const history = Array.isArray(raw.history)
      ? raw.history.filter((entry) => isPlainObject(entry) && Array.isArray(entry.items)).slice(0, PRESET_HISTORY_LIMIT)
      : [];
    const images = Array.isArray(raw.images)
      ? raw.images.map(normalizePresetImage).filter(Boolean).slice(0, PRESET_IMAGE_LIMIT)
      : [];
    return {
      schema: "tag-toolbox-preset-v1",
      id: raw.id,
      type,
      name: typeof raw.name === "string" && raw.name.trim() ? raw.name.trim() : "未命名预设",
      notes: typeof raw.notes === "string" ? raw.notes : "",
      revision: version,
      createdAt: typeof raw.createdAt === "string" ? raw.createdAt : new Date().toISOString(),
      updatedAt: typeof raw.updatedAt === "string" ? raw.updatedAt : (typeof raw.createdAt === "string" ? raw.createdAt : new Date().toISOString()),
      schemaVersion: typeof raw.schemaVersion === "string" ? raw.schemaVersion : "3",
      items: raw.items,
      images,
      history,
    };
  }

  function clonePresetImages(images) {
    return (Array.isArray(images) ? images : [])
      .map(normalizePresetImage)
      .filter(Boolean)
      .slice(0, PRESET_IMAGE_LIMIT)
      .map((image) => ({ ...image }));
  }

  async function uploadPresetImageFile(file) {
    if (!(file instanceof File) || !String(file.type || "").startsWith("image/")) {
      throw new Error("只支持图片文件");
    }
    const response = await fetch("/api/preset-images", {
      method: "POST",
      headers: {
        "Content-Type": file.type || "application/octet-stream",
        "X-Filename": encodeURIComponent(file.name || "image"),
      },
      body: file,
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    if (!response.ok || !payload || payload.ok === false) {
      throw new Error((payload && payload.error) || `上传失败：${file.name}`);
    }
    const normalized = normalizePresetImage(payload);
    if (!normalized) throw new Error(`上传结果无效：${file.name}`);
    return normalized;
  }

  async function deletePresetImageFile(image) {
    const file = safePresetImageFile(image && image.file);
    if (!file) return;
    try {
      await fetch(`/api/preset-images/${encodeURIComponent(file)}`, { method: "DELETE" });
    } catch {
      // Keep UI responsive even if orphan cleanup fails.
    }
  }

  function persistPresetDraftImages() {
    if (!state.presetSelectedId) return true;
    const presets = readPresets();
    const index = presets.findIndex((preset) => preset.id === state.presetSelectedId);
    if (index < 0) return true;
    presets[index] = {
      ...presets[index],
      images: clonePresetImages(state.presetDraftImages),
      updatedAt: new Date().toISOString(),
    };
    return writePresets(presets);
  }

  function renderPresetImages() {
    const images = clonePresetImages(state.presetDraftImages);
    elements.presetImageCount.textContent = `${images.length} / ${PRESET_IMAGE_LIMIT}`;
    elements.presetImportImages.disabled = images.length >= PRESET_IMAGE_LIMIT;
    if (!images.length) {
      elements.presetImages.replaceChildren(
        createNode("div", "preset-image-empty", "尚未导入配图。可先选中预设再导入，或导入后另存为新预设。"),
      );
      return;
    }
    const fragment = document.createDocumentFragment();
    for (const image of images) {
      const card = createNode("div", "preset-image-card");
      const img = document.createElement("img");
      img.src = presetImageSrc(image);
      img.alt = image.name || "配图";
      img.title = image.path || image.relPath || image.name || "配图";
      img.loading = "lazy";
      const remove = createNode("button", "remove-image", "×");
      remove.type = "button";
      remove.title = "移除配图";
      remove.setAttribute("aria-label", `移除配图 ${image.name || ""}`);
      remove.dataset.removeImageId = image.id;
      card.append(img, remove);
      fragment.append(card);
    }
    elements.presetImages.replaceChildren(fragment);
  }

  function readPresets() {
    try {
      const parsed = JSON.parse(window.localStorage.getItem(PRESET_STORAGE_KEY) || "[]");
      if (!Array.isArray(parsed)) return [];
      return parsed.map(normalizePreset).filter(Boolean);
    } catch {
      return [];
    }
  }

  function writePresets(presets) {
    try {
      window.localStorage.setItem(
        PRESET_STORAGE_KEY,
        JSON.stringify(presets.slice(0, PRESET_LIMIT)),
      );
      return true;
    } catch (error) {
      showToast(`预设保存失败：${error.message}`);
      return false;
    }
  }

  function currentPresetItems() {
    return state.selected.map((item) => ({
      id: item.id,
      kind: item.kind,
      polarity: item.polarity,
      slot: item.slot,
    }));
  }

  function presetsOfType(typeId = state.presetType) {
    return readPresets()
      .filter((preset) => preset.type === typeId)
      .sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)));
  }

  function selectedPreset() {
    if (!state.presetSelectedId) return null;
    return readPresets().find((preset) => preset.id === state.presetSelectedId) || null;
  }

  function renderPresetTypes() {
    const fragment = document.createDocumentFragment();
    for (const type of PRESET_TYPES) {
      const button = createNode("button", "preset-type");
      button.type = "button";
      button.dataset.presetType = type.id;
      button.classList.toggle("is-active", type.id === state.presetType);
      button.textContent = type.label;
      button.title = type.hint;
      fragment.append(button);
    }
    elements.presetTypes.replaceChildren(fragment);
  }

  function renderPresetHistory(preset) {
    const history = preset && Array.isArray(preset.history) ? preset.history : [];
    if (!history.length) {
      elements.presetHistory.hidden = true;
      elements.presetHistoryList.replaceChildren();
      return;
    }
    elements.presetHistory.hidden = false;
    const fragment = document.createDocumentFragment();
    for (const entry of history) {
      const li = createNode(
        "li",
        "",
        `v${entry.revision || "?"} · ${formatNumber((entry.items || []).length)} 词 · ${entry.updatedAt || entry.createdAt || "—"}`,
      );
      fragment.append(li);
    }
    elements.presetHistoryList.replaceChildren(fragment);
  }

  function renderPresetManager() {
    const type = presetTypeMeta(state.presetType);
    const list = presetsOfType(state.presetType);
    if (state.presetSelectedId && !list.some((preset) => preset.id === state.presetSelectedId)) {
      state.presetSelectedId = "";
      state.presetDraftImages = [];
    }
    elements.presetListTitle.textContent = `${type.label}列表`;
    elements.presetListCount.textContent = String(list.length);
    renderPresetTypes();

    if (!list.length) {
      elements.presetList.replaceChildren(
        createNode("div", "preset-empty", `还没有「${type.label}」提示词预设。填写名称后点「另存为新预设」。`),
      );
    } else {
      const fragment = document.createDocumentFragment();
      for (const preset of list) {
        const button = createNode("button", "preset-item");
        button.type = "button";
        button.dataset.presetId = preset.id;
        button.setAttribute("role", "option");
        button.setAttribute("aria-selected", String(preset.id === state.presetSelectedId));
        button.classList.toggle("is-active", preset.id === state.presetSelectedId);
        if (preset.images[0] && presetImageSrc(preset.images[0])) {
          const thumb = document.createElement("img");
          thumb.className = "preset-item-thumb";
          thumb.src = presetImageSrc(preset.images[0]);
          thumb.alt = "";
          button.append(thumb);
        } else {
          button.append(createNode("span", "preset-item-thumb"));
        }
        const copy = createNode("div", "preset-item-copy");
        copy.append(
          createNode("strong", "", preset.name),
          createNode(
            "span",
            "",
            `v${preset.revision} · ${formatNumber(preset.items.length)} 词 · 配图 ${preset.images.length} · ${preset.updatedAt.slice(0, 16).replace("T", " ")}`,
          ),
        );
        button.append(copy);
        fragment.append(button);
      }
      elements.presetList.replaceChildren(fragment);
    }

    const active = selectedPreset();
    if (active) {
      if (document.activeElement !== elements.presetName) {
        elements.presetName.value = active.name;
      }
      if (document.activeElement !== elements.presetNotes) {
        elements.presetNotes.value = active.notes || "";
      }
      elements.presetMeta.textContent =
        `${type.label} · revision v${active.revision} · ${formatNumber(active.items.length)} 词 · 配图 ${formatNumber(active.images.length)}` +
        `\n创建 ${active.createdAt.slice(0, 19).replace("T", " ")}` +
        `\n更新 ${active.updatedAt.slice(0, 19).replace("T", " ")}` +
        (active.notes ? `\n${active.notes}` : "");
      elements.presetOverwrite.disabled = false;
      elements.presetLoad.disabled = false;
      elements.presetDelete.disabled = false;
      renderPresetHistory(active);
    } else {
      elements.presetMeta.textContent =
        `${type.label}：${type.hint}\n当前组合 ${formatNumber(state.selected.length)} 词` +
        (state.presetDraftImages.length
          ? ` · 草稿配图 ${state.presetDraftImages.length}`
          : "") +
        ` 可另存为新提示词预设。`;
      elements.presetOverwrite.disabled = true;
      elements.presetLoad.disabled = true;
      elements.presetDelete.disabled = true;
      renderPresetHistory(null);
    }
    renderPresetImages();
  }

  function openPresetManager() {
    renderPresetManager();
    if (typeof elements.presetDialog.showModal === "function") {
      elements.presetDialog.showModal();
    } else {
      elements.presetDialog.setAttribute("open", "");
    }
    elements.presetName.focus();
  }

  function savePresetAsNew() {
    if (!state.selected.length) {
      showToast("当前组合为空，未保存提示词预设。");
      return;
    }
    const type = presetTypeMeta(state.presetType);
    const name = elements.presetName.value.trim()
      || `${type.label} ${new Date().toLocaleString("zh-CN")}`;
    const now = new Date().toISOString();
    const preset = {
      schema: "tag-toolbox-preset-v1",
      id: `preset-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
      type: state.presetType,
      name,
      notes: elements.presetNotes.value.trim(),
      revision: 1,
      createdAt: now,
      updatedAt: now,
      schemaVersion: state.manifest ? String(state.manifest.schema_version) : "3",
      items: currentPresetItems(),
      images: clonePresetImages(state.presetDraftImages),
      history: [],
    };
    const presets = readPresets();
    presets.unshift(preset);
    if (!writePresets(presets)) return;
    state.presetSelectedId = preset.id;
    state.presetDraftImages = clonePresetImages(preset.images);
    renderPresetManager();
    showToast(`已保存${type.label}提示词预设：${name}`);
  }

  function overwriteSelectedPreset() {
    if (!state.selected.length) {
      showToast("当前组合为空，未覆盖提示词预设。");
      return;
    }
    const presets = readPresets();
    const index = presets.findIndex((preset) => preset.id === state.presetSelectedId);
    if (index < 0) {
      showToast("请先选择要覆盖的提示词预设。");
      return;
    }
    const previous = presets[index];
    const now = new Date().toISOString();
    const snapshot = {
      revision: previous.revision,
      updatedAt: previous.updatedAt,
      notes: previous.notes,
      items: previous.items,
      imageCount: previous.images.length,
    };
    const next = {
      ...previous,
      name: elements.presetName.value.trim() || previous.name,
      notes: elements.presetNotes.value.trim(),
      revision: previous.revision + 1,
      updatedAt: now,
      schemaVersion: state.manifest ? String(state.manifest.schema_version) : previous.schemaVersion,
      items: currentPresetItems(),
      images: clonePresetImages(state.presetDraftImages),
      history: [snapshot, ...(previous.history || [])].slice(0, PRESET_HISTORY_LIMIT),
    };
    presets[index] = next;
    presets.splice(index, 1);
    presets.unshift(next);
    if (!writePresets(presets)) return;
    state.presetSelectedId = next.id;
    state.presetDraftImages = clonePresetImages(next.images);
    renderPresetManager();
    showToast(`已覆盖并升版：${next.name} → v${next.revision}`);
  }

  async function importPresetImages(fileList) {
    const files = [...(fileList || [])].filter((file) => file && String(file.type || "").startsWith("image/"));
    if (!files.length) {
      showToast("请选择图片文件。");
      return;
    }
    const room = PRESET_IMAGE_LIMIT - state.presetDraftImages.length;
    if (room <= 0) {
      showToast(`每个预设最多 ${PRESET_IMAGE_LIMIT} 张配图。`);
      return;
    }
    const accepted = files.slice(0, room);
    let added = 0;
    for (const file of accepted) {
      try {
        const image = await uploadPresetImageFile(file);
        state.presetDraftImages.push(image);
        added += 1;
      } catch (error) {
        showToast(error instanceof Error ? error.message : String(error));
      }
    }
    if (!added) return;
    if (!persistPresetDraftImages()) {
      state.presetDraftImages = state.presetDraftImages.slice(0, -added);
      return;
    }
    renderPresetManager();
    showToast(
      state.presetSelectedId
        ? `已导入 ${added} 张配图到当前预设。`
        : `已导入 ${added} 张草稿配图，另存时会一并写入。`,
    );
  }

  async function removePresetImage(imageId) {
    const before = state.presetDraftImages.length;
    const removed = state.presetDraftImages.find((image) => image.id === imageId);
    state.presetDraftImages = state.presetDraftImages.filter((image) => image.id !== imageId);
    if (state.presetDraftImages.length === before) return;
    if (!persistPresetDraftImages()) {
      if (removed) state.presetDraftImages.push(removed);
      return;
    }
    await deletePresetImageFile(removed);
    renderPresetManager();
    showToast("已移除配图。");
  }

  async function applyPresetItems(preset, toastLabel) {
    if (!preset) {
      showToast("请选择要载入的预设。");
      return;
    }
    if (preset.items.some((item) => isPlainObject(item) && String(item.id || "").startsWith("artist:"))) {
      await ensureArtistsLoaded();
    }
    const restored = [];
    let skipped = 0;
    for (const raw of preset.items) {
      if (!isPlainObject(raw) || typeof raw.id !== "string") {
        skipped += 1;
        continue;
      }
      const tag = state.byId.get(raw.id);
      if (!tag || !isSelectable(tag)) {
        skipped += 1;
        continue;
      }
      const fallbackSlot = tag.kind === "artist"
        ? "artist"
        : isNegativeTag(tag)
          ? negativeSlotId()
          : defaultPositiveSlot(tag);
      const slot = typeof raw.slot === "string" && canMoveToSlot(tag, raw.slot)
        ? raw.slot
        : fallbackSlot;
      const candidate = {
        id: tag.id,
        kind: tag.kind,
        slot,
        polarity: tag.kind === "artist"
          ? "artist"
          : isNegativeSlotId(slot)
            ? "negative"
            : "positive",
      };
      if (!restored.some((item) => item.id === candidate.id)) restored.push(candidate);
    }
    state.selected = restored;
    renderResults();
    renderComposer();
    showToast(
      skipped
        ? `已载入${toastLabel}，跳过 ${skipped} 条失效记录。`
        : `已载入${toastLabel}：${preset.name}`,
    );
  }

  async function loadSelectedPreset() {
    const preset = selectedPreset();
    await applyPresetItems(preset, presetTypeMeta(state.presetType).label);
    if (preset && elements.presetDialog.open) {
      elements.presetDialog.close();
    }
  }

  function deleteSelectedPreset() {
    const presets = readPresets();
    const preset = presets.find((entry) => entry.id === state.presetSelectedId);
    if (!preset) {
      showToast("请选择要删除的提示词预设。");
      return;
    }
    if (!window.confirm(`删除「${presetTypeMeta(preset.type).label}」提示词预设“${preset.name}”？`)) {
      return;
    }
    if (!writePresets(presets.filter((entry) => entry.id !== preset.id))) return;
    state.presetSelectedId = "";
    state.presetDraftImages = [];
    renderPresetManager();
    showToast("提示词预设已删除。");
  }

  async function copyCurrentExport() {
    const text = exportText();
    if (!text) {
      showToast("当前格式没有可复制内容。");
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      showToast("已复制当前格式。");
    } catch {
      if (!elements.exportOutput.classList.contains("is-hidden")) {
        elements.exportOutput.focus();
        elements.exportOutput.select();
      }
      showToast("浏览器未授权剪贴板，已选中文本，请按 Ctrl+C。");
    }
  }

  function resetHierarchy() {
    state.subGroup = "all";
    state.subFilter = "all";
    state.leafFilter = "all";
    state.workFilter = "all";
    state.workQuery = "";
    elements.workFilter.value = "";
  }

  async function selectL1(value) {
    state.typeFilter = value;
    resetHierarchy();
    renderFilterUi();
    if (value === "artist") await ensureArtistsLoaded();
    await applyFilters();
  }

  async function ensureArtistsLoaded() {
    if (state.artistsLoaded) return true;
    if (state.artistPromise) return state.artistPromise;
    const shards = state.manifest && Array.isArray(state.manifest.artist_shards)
      ? state.manifest.artist_shards
      : [];
    if (!shards.length) {
      elements.artistLoadStatus.textContent = "画师库待生成";
      state.filtered = [];
      renderResults();
      return false;
    }
    state.artistPromise = (async () => {
      state.artistsLoading = true;
      elements.artistLoadStatus.textContent = `正在加载画师库 0 / ${shards.length}`;
      try {
        const signal = state.loadController ? state.loadController.signal : undefined;
        for (let index = 0; index < shards.length; index += 1) {
          const shard = shards[index];
          elements.artistLoadStatus.textContent = `正在加载画师库 ${index + 1} / ${shards.length}`;
          const payload = await fetchJson(safeDataUrl(shard.file), signal);
          const rows = shardArtists(payload, index, shard);
          if (rows.length !== shard.count) {
            throw new Error(`${shard.file} 画师数 ${rows.length} 与 manifest ${shard.count} 不一致。`);
          }
          for (let rowIndex = 0; rowIndex < rows.length; rowIndex += 1) {
            state.artists.push(normalizeArtistRow(
              rows[rowIndex],
              `${shard.file}.artists[${rowIndex}]`,
            ));
          }
          await nextFrame();
        }
        const expected = artistShardCount();
        if (state.artists.length !== expected) {
          throw new Error(`画师总数 ${state.artists.length} 与 manifest ${expected} 不一致。`);
        }
        state.alphaArtists = [...state.artists].sort(compareEnglish);
        state.popularArtists = [...state.artists].sort(comparePopularity);
        state.artistsLoaded = true;
        elements.artistLoadStatus.textContent = `画师库 ${formatNumber(state.artists.length)} 条已就绪`;
        renderTypeFilters();
        if (state.typeFilter === "artist") await applyFilters();
        return true;
      } catch (error) {
        if (error && error.name === "AbortError") return false;
        elements.artistLoadStatus.textContent = "画师库加载失败";
        showToast(error instanceof Error ? error.message : String(error));
        return false;
      } finally {
        state.artistsLoading = false;
        state.artistPromise = null;
      }
    })();
    return state.artistPromise;
  }

  function clearAllFilters() {
    elements.search.value = "";
    state.typeFilter = "all";
    state.sourceFilter = "all";
    state.safetyFilter = "all";
    state.sourceEnabled = false;
    state.safetyEnabled = false;
    state.popularitySort = false;
    resetHierarchy();
    renderPopularitySort();
    renderFilterUi();
    applyFilters();
  }

  function clamp(number, min, max) {
    return Math.min(max, Math.max(min, number));
  }

  function applyLayout({ leftPct, footerH, workH } = {}) {
    if (Number.isFinite(leftPct)) {
      document.documentElement.style.setProperty("--left-pct", `${leftPct}%`);
    }
    if (Number.isFinite(footerH)) {
      document.documentElement.style.setProperty("--footer-h", `${footerH}px`);
    }
    if (Number.isFinite(workH)) {
      document.documentElement.style.setProperty("--work-h", `${workH}px`);
    }
  }

  function saveLayout() {
    try {
      const styles = getComputedStyle(document.documentElement);
      window.localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify({
        leftPct: parseFloat(styles.getPropertyValue("--left-pct")),
        footerH: parseFloat(styles.getPropertyValue("--footer-h")),
        workH: parseFloat(styles.getPropertyValue("--work-h")),
      }));
    } catch {
      // Layout persistence is optional.
    }
  }

  function loadLayout() {
    try {
      const value = JSON.parse(window.localStorage.getItem(LAYOUT_STORAGE_KEY) || "null");
      if (!isPlainObject(value)) return;
      applyLayout({
        leftPct: Number.isFinite(value.leftPct) ? clamp(value.leftPct, 22, 78) : 50,
        footerH: Number.isFinite(value.footerH) ? clamp(value.footerH, 96, 420) : 160,
        workH: Number.isFinite(value.workH) ? clamp(value.workH, 64, 420) : 140,
      });
    } catch {
      applyLayout({ leftPct: 50, footerH: 160, workH: 140 });
    }
  }

  function bindResizers() {
    elements.colResizer.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      elements.colResizer.setPointerCapture(event.pointerId);
      document.body.classList.add("resizing-col");
      const rect = elements.main.getBoundingClientRect();
      const onMove = (moveEvent) => {
        applyLayout({
          leftPct: clamp(((moveEvent.clientX - rect.left) / rect.width) * 100, 22, 78),
        });
      };
      const onUp = () => {
        document.body.classList.remove("resizing-col");
        elements.colResizer.removeEventListener("pointermove", onMove);
        elements.colResizer.removeEventListener("pointerup", onUp);
        saveLayout();
      };
      elements.colResizer.addEventListener("pointermove", onMove);
      elements.colResizer.addEventListener("pointerup", onUp);
    });

    elements.rowResizer.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      elements.rowResizer.setPointerCapture(event.pointerId);
      document.body.classList.add("resizing-row");
      const rect = elements.appShell.getBoundingClientRect();
      const onMove = (moveEvent) => {
        applyLayout({
          footerH: clamp(rect.bottom - moveEvent.clientY, 96, Math.floor(rect.height * 0.55)),
        });
      };
      const onUp = () => {
        document.body.classList.remove("resizing-row");
        elements.rowResizer.removeEventListener("pointermove", onMove);
        elements.rowResizer.removeEventListener("pointerup", onUp);
        saveLayout();
      };
      elements.rowResizer.addEventListener("pointermove", onMove);
      elements.rowResizer.addEventListener("pointerup", onUp);
    });

    elements.workResizer.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      event.stopPropagation();
      elements.workResizer.setPointerCapture(event.pointerId);
      document.body.classList.add("resizing-work");
      const startY = event.clientY;
      const startHeight = elements.workFilters.getBoundingClientRect().height;
      const onMove = (moveEvent) => {
        applyLayout({ workH: clamp(startHeight + moveEvent.clientY - startY, 64, 420) });
      };
      const onUp = () => {
        document.body.classList.remove("resizing-work");
        elements.workResizer.removeEventListener("pointermove", onMove);
        elements.workResizer.removeEventListener("pointerup", onUp);
        saveLayout();
      };
      elements.workResizer.addEventListener("pointermove", onMove);
      elements.workResizer.addEventListener("pointerup", onUp);
    });

    elements.colResizer.addEventListener("dblclick", () => {
      applyLayout({ leftPct: 50 });
      saveLayout();
      showToast("左右已重置 50/50");
    });
    elements.rowResizer.addEventListener("dblclick", () => {
      applyLayout({ footerH: 160 });
      saveLayout();
      showToast("导出栏高度已重置");
    });
    elements.workResizer.addEventListener("dblclick", () => {
      applyLayout({ workH: 140 });
      saveLayout();
      showToast("作品栏高度已重置");
    });
  }

  function bindEvents() {
    elements.retryLoad.addEventListener("click", boot);
    elements.clearSearch.addEventListener("click", () => {
      elements.search.value = "";
      elements.search.focus();
      applyFilters();
    });
    elements.search.addEventListener("input", () => {
      window.clearTimeout(state.searchTimer);
      state.searchTimer = window.setTimeout(applyFilters, 120);
    });
    elements.workFilter.addEventListener("input", () => {
      state.workQuery = elements.workFilter.value;
      window.clearTimeout(state.workTimer);
      state.workTimer = window.setTimeout(renderWorkFilters, 100);
    });

    elements.typeFilters.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-type]");
      if (button) selectL1(button.dataset.type);
    });
    elements.sourceToggle.addEventListener("click", () => {
      state.sourceEnabled = !state.sourceEnabled;
      if (!state.sourceEnabled) state.sourceFilter = "all";
      renderFilterUi();
      applyFilters();
    });
    elements.safetyToggle.addEventListener("click", () => {
      state.safetyEnabled = !state.safetyEnabled;
      if (!state.safetyEnabled) state.safetyFilter = "all";
      renderFilterUi();
      applyFilters();
    });
    elements.sourceFilters.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-source]");
      if (!button) return;
      state.sourceFilter = button.dataset.source;
      renderFilterUi();
      applyFilters();
    });
    elements.safetyFilters.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-safety]");
      if (!button) return;
      state.safetyFilter = button.dataset.safety;
      renderFilterUi();
      applyFilters();
    });
    elements.subTree.addEventListener("click", (event) => {
      const group = event.target.closest("button[data-group]");
      const sub = event.target.closest("button[data-sub]");
      const leaf = event.target.closest("button[data-leaf]");
      if (group) {
        state.subGroup = group.dataset.group;
        state.subFilter = "all";
        state.leafFilter = "all";
        state.workFilter = "all";
        state.workQuery = "";
        elements.workFilter.value = "";
      } else if (sub) {
        state.subFilter = sub.dataset.sub;
        state.leafFilter = "all";
      } else if (leaf) {
        state.leafFilter = leaf.dataset.leaf;
      } else {
        return;
      }
      renderSubTree();
      renderWorkFilters();
      applyFilters();
    });
    elements.workFilters.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-work]");
      if (!button) return;
      state.workFilter = button.dataset.work;
      renderWorkFilters();
      applyFilters();
    });
    elements.popularitySort.addEventListener("click", () => {
      state.popularitySort = !state.popularitySort;
      renderPopularitySort();
      applyFilters();
      showToast(state.popularitySort ? "已开启热度排行。" : "已切换为英文词典顺序。");
    });
    elements.resetFilters.addEventListener("click", clearAllFilters);

    elements.resultList.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-select-id]");
      if (button) toggleSelection(button.dataset.selectId);
    });

    elements.toggleEmptySlots.addEventListener("click", () => {
      state.hideEmptySlots = !state.hideEmptySlots;
      renderComposer();
    });
    elements.clearSelection.addEventListener("click", () => {
      if (!state.selected.length) return;
      if (!window.confirm("清空当前正向、负向与画师组合？")) return;
      state.selected = [];
      renderResults();
      renderComposer();
      showToast("组合已清空。");
    });
    elements.slotList.addEventListener("click", (event) => {
      const remove = event.target.closest("button[data-remove-id]");
      if (remove) {
        removeSelection(remove.dataset.removeId);
        return;
      }
      const toggle = event.target.closest("button[data-toggle-slot]");
      if (toggle) {
        const id = toggle.dataset.toggleSlot;
        if (state.collapsedSlots.has(id)) state.collapsedSlots.delete(id);
        else state.collapsedSlots.add(id);
        renderSlots();
      }
    });
    elements.slotList.addEventListener("dragstart", (event) => {
      const picked = event.target.closest(".picked[data-selection-id]");
      if (!picked) return;
      state.dragId = picked.dataset.selectionId;
      picked.classList.add("is-dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", state.dragId);
    });
    elements.slotList.addEventListener("dragend", (event) => {
      const picked = event.target.closest(".picked[data-selection-id]");
      if (picked) picked.classList.remove("is-dragging");
      state.dragId = null;
      for (const slot of elements.slotList.querySelectorAll(".slot")) {
        slot.classList.remove("drop-target");
      }
    });
    elements.slotList.addEventListener("dragover", (event) => {
      const zone = event.target.closest("[data-drop-slot]");
      if (!zone || !state.dragId) return;
      const tag = state.byId.get(state.dragId);
      if (!canMoveToSlot(tag, zone.dataset.dropSlot)) return;
      event.preventDefault();
      zone.closest(".slot")?.classList.add("drop-target");
    });
    elements.slotList.addEventListener("dragleave", (event) => {
      event.target.closest(".slot")?.classList.remove("drop-target");
    });
    elements.slotList.addEventListener("drop", (event) => {
      const zone = event.target.closest("[data-drop-slot]");
      if (!zone) return;
      event.preventDefault();
      const id = event.dataTransfer.getData("text/plain") || state.dragId;
      const over = event.target.closest(".picked[data-selection-id]");
      moveSelectionTo(
        id,
        zone.dataset.dropSlot,
        over && over.dataset.selectionId !== id ? over.dataset.selectionId : "",
      );
    });

    document.querySelector(".export-tabs").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-export-mode]");
      if (!button) return;
      state.exportMode = button.dataset.exportMode;
      renderExport();
    });
    elements.copyExport.addEventListener("click", copyCurrentExport);
    elements.openPresets.addEventListener("click", openPresetManager);
    elements.presetTypes.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-preset-type]");
      if (!button) return;
      state.presetType = button.dataset.presetType;
      state.presetSelectedId = "";
      state.presetDraftImages = [];
      elements.presetName.value = "";
      elements.presetNotes.value = "";
      renderPresetManager();
    });
    elements.presetList.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-preset-id]");
      if (!button) return;
      state.presetSelectedId = button.dataset.presetId;
      const preset = selectedPreset();
      state.presetDraftImages = clonePresetImages(preset ? preset.images : []);
      renderPresetManager();
    });
    elements.presetImportImages.addEventListener("click", () => {
      elements.presetImageInput.click();
    });
    elements.presetImageInput.addEventListener("change", async () => {
      const files = elements.presetImageInput.files;
      elements.presetImageInput.value = "";
      await importPresetImages(files);
    });
    elements.presetImages.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-remove-image-id]");
      if (!button) return;
      void removePresetImage(button.dataset.removeImageId);
    });
    elements.presetSaveNew.addEventListener("click", savePresetAsNew);
    elements.presetOverwrite.addEventListener("click", overwriteSelectedPreset);
    elements.presetLoad.addEventListener("click", () => {
      loadSelectedPreset();
    });
    elements.presetDelete.addEventListener("click", deleteSelectedPreset);

    document.querySelector(".mobile-switcher").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-mobile-target]");
      if (!button) return;
      document.body.dataset.mobileView = button.dataset.mobileTarget;
      for (const candidate of document.querySelectorAll("[data-mobile-target]")) {
        candidate.setAttribute("aria-pressed", String(candidate === button));
      }
      const target = button.dataset.mobileTarget === "compose"
        ? elements.composerTitle
        : elements.browserTitle;
      target.focus({ preventScroll: true });
    });
  }

  function resetLoadedState() {
    state.manifest = null;
    state.taxonomy = null;
    state.works = new Map();
    state.tags = [];
    state.alphaTags = [];
    state.popularTags = [];
    state.artists = [];
    state.alphaArtists = [];
    state.popularArtists = [];
    state.artistsLoaded = false;
    state.artistsLoading = false;
    state.artistPromise = null;
    state.byId = new Map();
    state.filtered = [];
    state.selected = [];
    state.slots = FALLBACK_SLOTS;
    state.slotMap = new Map(FALLBACK_SLOTS.map((slot) => [slot.id, slot]));
    state.pathLabels = new Map(FALLBACK_SLOTS.map((slot) => [slot.id, slot.label]));
    state.typeFilter = "all";
    state.sourceFilter = "all";
    state.safetyFilter = "all";
    state.sourceEnabled = false;
    state.safetyEnabled = false;
    state.popularitySort = false;
    state.hideEmptySlots = true;
    state.collapsedSlots = new Set();
    state.exportMode = "en";
    state.ready = false;
    resetHierarchy();
    elements.search.value = "";
    elements.artistLoadStatus.textContent = "";
    renderPopularitySort();
    renderFilterUi();
    renderComposer();
  }

  async function boot() {
    if (state.loadController) state.loadController.abort();
    state.loadController = new AbortController();
    state.loadAttempt += 1;
    resetLoadedState();
    elements.appShell.setAttribute("inert", "");
    elements.appShell.setAttribute("aria-busy", "true");
    elements.loadingOverlay.classList.remove("is-hidden");
    elements.loadingOverlay.setAttribute("role", "status");
    elements.retryLoad.hidden = true;
    elements.datasetStatus.classList.remove("is-ready");
    elements.datasetStatus.textContent = "加载中";
    elements.search.disabled = true;
    setLoading(2, "正在读取数据清单", "验证 schema v3、分片范围与本地资源路径。", "2%");

    try {
      const signal = state.loadController.signal;
      const manifest = validateManifest(await fetchJson(MANIFEST_URL, signal));
      state.manifest = manifest;

      const taxonomyFile = manifestArtifactFile(manifest, "taxonomy", "taxonomy.json");
      const worksFile = manifestArtifactFile(manifest, "works", "works.json");
      setLoading(
        7,
        "正在加载分类与作品",
        "建立 V1 的 L1→L4 分类胶囊与规范作品索引。",
        `0 / ${manifest.shards.length} 分片`,
      );
      const [taxonomy, worksPayload] = await Promise.all([
        fetchJson(safeDataUrl(taxonomyFile), signal),
        fetchJson(safeDataUrl(worksFile), signal),
      ]);
      normalizeTaxonomy(taxonomy);
      state.works = normalizeWorks(worksPayload);
      renderFilterUi();

      const totalBytes = manifest.shards.reduce(
        (sum, shard) => sum + (Number(shard.bytes) || 0),
        0,
      );
      let loadedBytes = 0;
      let loadedRows = 0;
      for (let index = 0; index < manifest.shards.length; index += 1) {
        const shard = manifest.shards[index];
        const startPercent = 10 + (index / manifest.shards.length) * 80;
        setLoading(
          startPercent,
          `正在加载词库分片 ${index + 1} / ${manifest.shards.length}`,
          shard.file,
          `${formatNumber(loadedRows)} 条${totalBytes
            ? ` · ${(loadedBytes / 1048576).toFixed(1)} / ${(totalBytes / 1048576).toFixed(1)} MB`
            : ""}`,
        );
        const payload = await fetchJson(safeDataUrl(shard.file), signal);
        const rows = shardTags(payload, index, shard);
        if (rows.length !== shard.count) {
          throw new Error(`${shard.file} 条数 ${rows.length} 与 manifest ${shard.count} 不一致。`);
        }
        for (let rowIndex = 0; rowIndex < rows.length; rowIndex += 1) {
          state.tags.push(normalizeCompactRow(
            rows[rowIndex],
            `${shard.file}.tags[${rowIndex}]`,
          ));
        }
        loadedRows += rows.length;
        loadedBytes += Number(shard.bytes) || 0;
        await nextFrame();
      }

      const expected = expectedRecordCount(manifest);
      if (state.tags.length !== expected) {
        throw new Error(`总记录数 ${state.tags.length} 与 manifest ${expected} 不一致。`);
      }
      state.alphaTags = [...state.tags].sort(compareEnglish);
      state.popularTags = [...state.tags].sort(comparePopularity);
      state.ready = true;
      setLoading(
        94,
        "正在建立搜索视图",
        "生成 V1 横向标签流；画师归入一级分类并保持懒加载。",
        `${formatNumber(state.tags.length)} 条`,
      );
      renderFilterUi();
      await applyFilters();
      await nextFrame();

      const version = String(manifest.schema_version);
      const artists = artistShardCount();
      const summary =
        `${formatNumber(state.tags.length)} 语义词${artists ? ` + ${formatNumber(artists)} 画师` : ""} · schema ${version}`;
      const shards =
        `${manifest.shards.length} 词库分片 · ${formatNumber(state.works.size)} 个作品${artists ? " · 画师懒加载" : ""}`;
      elements.datasetSummary.textContent = summary;
      elements.datasetStatus.textContent = "本地数据已就绪";
      elements.datasetStatus.classList.add("is-ready");
      elements.shardSummary.textContent = shards;
      publishShellStatus({
        ready: true,
        summary,
        detail: shards,
        badge: "本地数据已就绪",
      });
      elements.search.disabled = false;
      elements.appShell.removeAttribute("inert");
      elements.appShell.setAttribute("aria-busy", "false");
      elements.loadingOverlay.classList.add("is-hidden");
      setLoading(100, "词库已就绪", "可以按 V1 工作流浏览、分槽与导出。", "100%");
      showToast("V1 分类工作台已就绪。");
    } catch (error) {
      if (error && error.name === "AbortError") return;
      elements.loadingOverlay.setAttribute("role", "alert");
      elements.retryLoad.hidden = false;
      elements.datasetStatus.textContent = "加载失败";
      publishShellStatus({
        ready: false,
        summary: "词库加载失败",
        detail: error instanceof Error ? error.message : String(error),
        badge: "加载失败",
      });
      setLoading(
        0,
        "词库加载失败",
        error instanceof Error ? error.message : String(error),
        "请检查 data/ 产物后重试",
      );
    }
  }

  loadLayout();
  bindResizers();
  bindEvents();
  renderPopularitySort();
  renderFilterUi();
  renderComposer();
  boot();
})();
