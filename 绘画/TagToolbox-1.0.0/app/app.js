(() => {
  "use strict";

  const STORAGE_KEY = "tagtoolbox.activeMode.v1";
  const CHILD_ASSET_STAMP = "20260802-slot-colors-v2";
  const MODES = {
    toolbox: {
      label: "词库组合",
      page: "./toolbox.html",
      status: "词库检索、筛选与提示词组合",
    },
    editor: {
      label: "分类编辑",
      page: "./editor.html",
      status: "修改即时写入 SQLite；可创建保存点并导出完整词库",
    },
  };

  const host = document.querySelector("#mode-host");
  const loading = document.querySelector("#mode-loading");
  const statusText = document.querySelector("#mode-status-text");
  const statusDot = document.querySelector("#mode-status-dot");
  const datasetEl = document.querySelector("#mode-dataset");
  const editorActions = document.querySelector("#mode-editor-actions");
  const editorCmdButtons = [...document.querySelectorAll("[data-editor-cmd]")];
  const tabs = [...document.querySelectorAll("[data-mode]")];

  /** @type {Record<string, HTMLIFrameElement|null>} */
  const frames = { toolbox: null, editor: null };
  let activeMode = "";
  let editorDirty = false;
  let switching = false;
  let toolboxDataset = "";
  let editorChrome = null;

  function requestedMode() {
    const params = new URLSearchParams(window.location.search);
    const direct = params.get("mode");
    if (direct && MODES[direct]) {
      return direct;
    }
    const acceptance = params.get("accept") || "";
    if (acceptance.includes("classification-editor") || acceptance.includes("editor-ui")) {
      return "editor";
    }
    const saved = window.localStorage.getItem(STORAGE_KEY);
    return MODES[saved] ? saved : "toolbox";
  }

  function childUrl(mode) {
    const url = new URL(MODES[mode].page, window.location.href);
    url.searchParams.set("embedded", "1");
    url.searchParams.set("v", CHILD_ASSET_STAMP);
    const acceptance = new URLSearchParams(window.location.search).get("accept");
    if (acceptance) {
      url.searchParams.set("accept", acceptance);
    }
    return `${url.pathname}${url.search}`;
  }

  function setEditorActionsVisible(visible) {
    editorActions.hidden = !visible;
  }

  function applyEditorChrome(chrome) {
    editorChrome = chrome;
    if (!chrome) {
      return;
    }
    const undo = editorActions.querySelector('[data-editor-cmd="undo"]');
    const redo = editorActions.querySelector('[data-editor-cmd="redo"]');
    const snapshot = editorActions.querySelector('[data-editor-cmd="snapshot"]');
    const manage = editorActions.querySelector('[data-editor-cmd="manage-saves"]');
    const exportBtn = editorActions.querySelector('[data-editor-cmd="export"]');
    if (undo) undo.disabled = !chrome.canUndo;
    if (redo) redo.disabled = !chrome.canRedo;
    if (snapshot) {
      snapshot.disabled = Boolean(chrome.busySnapshot);
      snapshot.textContent = chrome.busySnapshot ? "保存中…" : "保存进度";
    }
    if (manage) manage.disabled = Boolean(chrome.busySnapshot);
    if (exportBtn) {
      exportBtn.disabled = Boolean(chrome.busyExport);
      exportBtn.textContent = chrome.busyExport ? "导出中…" : "导出";
    }
  }

  function reflect(mode, ready = false) {
    tabs.forEach((tab) => {
      const selected = tab.dataset.mode === mode;
      tab.classList.toggle("is-active", selected);
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    document.title = `${MODES[mode].label} · Tag Toolbox`;
    setEditorActionsVisible(mode === "editor");

    if (mode === "toolbox" && ready && toolboxDataset) {
      statusText.hidden = true;
      statusText.textContent = "";
      datasetEl.hidden = false;
      datasetEl.textContent = toolboxDataset;
      statusDot.classList.add("is-ready");
      statusDot.classList.remove("is-dirty");
      return;
    }

    if (mode === "editor") {
      statusText.hidden = true;
      statusText.textContent = "";
      if (editorChrome) {
        datasetEl.hidden = false;
        datasetEl.textContent = [
          editorChrome.revisionLabel,
          editorChrome.saveStatus,
          editorDirty ? "有未同步到词库的改动" : "",
        ].filter(Boolean).join(" · ");
        statusDot.classList.toggle("is-ready", !editorDirty);
        statusDot.classList.toggle("is-dirty", editorDirty);
        applyEditorChrome(editorChrome);
      } else {
        datasetEl.hidden = true;
        datasetEl.textContent = "";
        statusText.hidden = false;
        statusText.textContent = ready
          ? MODES.editor.status
          : `正在载入${MODES.editor.label}…`;
        statusDot.classList.remove("is-ready", "is-dirty");
      }
      return;
    }

    statusText.hidden = false;
    statusText.textContent = ready ? MODES[mode].status : `正在载入${MODES[mode].label}…`;
    datasetEl.hidden = true;
    datasetEl.textContent = "";
    statusDot.classList.remove("is-ready", "is-dirty");
  }

  function hideLoading() {
    loading.hidden = true;
  }

  function showLoading(message) {
    loading.hidden = false;
    const label = loading.querySelector("span:last-child");
    if (label) {
      label.textContent = message || "正在载入工具模式…";
    }
  }

  function discardFrame(mode) {
    const frame = frames[mode];
    if (!frame) {
      return;
    }
    frame.remove();
    frames[mode] = null;
    if (mode === "editor") {
      editorChrome = null;
    }
  }

  function showFrame(mode) {
    Object.entries(frames).forEach(([key, frame]) => {
      if (!frame) {
        return;
      }
      const active = key === mode;
      frame.hidden = !active;
      frame.classList.toggle("is-ready", active);
      frame.setAttribute("aria-hidden", String(!active));
    });
  }

  function createFrame(mode) {
    const frame = document.createElement("iframe");
    frame.className = "mode-frame";
    frame.title = `Tag Toolbox · ${MODES[mode].label}`;
    frame.dataset.mode = mode;
    frame.src = childUrl(mode);
    frames[mode] = frame;
    host.append(frame);
    return new Promise((resolve, reject) => {
      frame.addEventListener(
        "load",
        () => {
          if (frames[mode] !== frame) {
            resolve(false);
            return;
          }
          resolve(true);
        },
        { once: true },
      );
      frame.addEventListener(
        "error",
        () => {
          if (frames[mode] === frame) {
            reject(new Error("mode frame failed"));
          } else {
            resolve(false);
          }
        },
        { once: true },
      );
    });
  }

  async function ensureFrame(mode, { forceReload = false } = {}) {
    if (forceReload) {
      discardFrame(mode);
    }
    if (frames[mode]) {
      return frames[mode];
    }
    showLoading(`正在载入${MODES[mode].label}…`);
    reflect(mode, false);
    await createFrame(mode);
    return frames[mode];
  }

  async function setMode(mode, options = {}) {
    if (!MODES[mode] || switching) {
      return;
    }
    if (mode === activeMode && frames[mode] && !options.forceReload) {
      showFrame(mode);
      reflect(mode, true);
      hideLoading();
      return;
    }

    switching = true;
    try {
      const mustReloadToolbox =
        mode === "toolbox"
        && editorDirty
        && frames.toolbox
        && activeMode === "editor";

      if (mustReloadToolbox) {
        discardFrame("toolbox");
        editorDirty = false;
        toolboxDataset = "";
      }

      await ensureFrame(mode, { forceReload: Boolean(options.forceReload) });
      activeMode = mode;
      window.localStorage.setItem(STORAGE_KEY, mode);
      showFrame(mode);
      reflect(mode, true);
      hideLoading();

      if (!options.keepUrl) {
        const url = new URL(window.location.href);
        url.searchParams.set("mode", mode);
        window.history.replaceState({ mode }, "", url);
      }
    } catch {
      showLoading("模式载入失败，请刷新页面重试。");
      statusText.hidden = false;
      statusText.textContent = "载入失败";
    } finally {
      switching = false;
    }
  }

  function postEditorCommand(command) {
    const frame = frames.editor;
    if (!frame || !frame.contentWindow) {
      return;
    }
    frame.contentWindow.postMessage(
      {
        source: "tagtoolbox-shell",
        type: "editor-command",
        command,
      },
      window.location.origin,
    );
  }

  window.addEventListener("message", (event) => {
    if (event.origin !== window.location.origin) {
      return;
    }
    const data = event.data;
    if (!data || typeof data !== "object") {
      return;
    }
    if (data.source === "tagtoolbox-editor" && data.type === "editor-session") {
      editorDirty = Boolean(data.dirty);
      if (activeMode === "editor") {
        reflect("editor", true);
      }
      return;
    }
    if (data.source === "tagtoolbox-editor" && data.type === "editor-chrome") {
      editorDirty = Boolean(data.dirty);
      applyEditorChrome({
        canUndo: Boolean(data.canUndo),
        canRedo: Boolean(data.canRedo),
        busySnapshot: Boolean(data.busySnapshot),
        busyExport: Boolean(data.busyExport),
        revisionLabel: data.revisionLabel || "",
        saveStatus: data.saveStatus || "",
      });
      if (activeMode === "editor") {
        reflect("editor", true);
      }
      return;
    }
    if (data.source === "tagtoolbox-toolbox" && data.type === "toolbox-status") {
      toolboxDataset = data.ready
        ? (data.summary || data.badge || "本地数据已就绪")
        : (data.badge || data.summary || "加载失败");
      if (activeMode === "toolbox") {
        reflect("toolbox", true);
      }
    }
  });

  editorCmdButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const command = button.dataset.editorCmd;
      if (command) {
        postEditorCommand(command);
      }
    });
  });

  tabs.forEach((tab) => {
    tab.setAttribute("role", "tab");
    tab.addEventListener("click", () => setMode(tab.dataset.mode));
    tab.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) {
        return;
      }
      event.preventDefault();
      const index = tabs.indexOf(tab);
      const direction = event.key === "ArrowRight" ? 1 : -1;
      const next = tabs[(index + direction + tabs.length) % tabs.length];
      next.focus();
      next.click();
    });
  });

  window.addEventListener("popstate", () => setMode(requestedMode(), { keepUrl: true }));
  setMode(requestedMode(), { keepUrl: true });
})();
