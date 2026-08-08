(() => {
  "use strict";

  const EMBEDDED = new URLSearchParams(window.location.search).get("embedded") === "1";
  if (EMBEDDED) {
    document.body.classList.add("embedded");
  }

  const PAGE_SIZE = 300;
  const ALL_ID = "__all__";
  const UNCLASSIFIED_ID = "__unclassified__";

  const elements = {
    loadingOverlay: document.getElementById("loading-overlay"),
    loadingTitle: document.getElementById("loading-title"),
    loadingDetail: document.getElementById("loading-detail"),
    editorShell: document.getElementById("editor-shell"),
    datasetSummary: document.getElementById("dataset-summary"),
    saveStatus: document.getElementById("save-status"),
    revisionBadge: document.getElementById("revision-badge"),
    undoButton: document.getElementById("undo-button"),
    redoButton: document.getElementById("redo-button"),
    snapshotButton: document.getElementById("snapshot-button"),
    manageSavesButton: document.getElementById("manage-saves-button"),
    exportButton: document.getElementById("export-button"),
    activeFilterLabel: document.getElementById("active-filter-label"),
    resultSummary: document.getElementById("result-summary"),
    searchInput: document.getElementById("search-input"),
    clearSearch: document.getElementById("clear-search"),
    sourceFilter: document.getElementById("source-filter"),
    safetyFilter: document.getElementById("safety-filter"),
    statusFilter: document.getElementById("status-filter"),
    sortFilter: document.getElementById("sort-filter"),
    selectionSummary: document.getElementById("selection-summary"),
    selectPage: document.getElementById("select-page"),
    selectAllResults: document.getElementById("select-all-results"),
    clearSelected: document.getElementById("clear-selected"),
    unassignSelected: document.getElementById("unassign-selected"),
    tagViewport: document.getElementById("tag-viewport"),
    selectionRectangle: document.getElementById("selection-rectangle"),
    tagGrid: document.getElementById("tag-grid"),
    tagEmpty: document.getElementById("tag-empty"),
    previousPage: document.getElementById("previous-page"),
    nextPage: document.getElementById("next-page"),
    pageSummary: document.getElementById("page-summary"),
    createRoot: document.getElementById("create-root"),
    expandAll: document.getElementById("expand-all"),
    collapseAll: document.getElementById("collapse-all"),
    taxonomySummary: document.getElementById("taxonomy-summary"),
    taxonomyTree: document.getElementById("taxonomy-tree"),
    historyList: document.getElementById("history-list"),
    nodeDialog: document.getElementById("node-dialog"),
    nodeForm: document.getElementById("node-form"),
    nodeDialogTitle: document.getElementById("node-dialog-title"),
    nodeDialogHint: document.getElementById("node-dialog-hint"),
    nodeMode: document.getElementById("node-mode"),
    nodeId: document.getElementById("node-id"),
    nodeParentId: document.getElementById("node-parent-id"),
    nodeLabel: document.getElementById("node-label"),
    closeNodeDialog: document.getElementById("close-node-dialog"),
    cancelNodeDialog: document.getElementById("cancel-node-dialog"),
    submitNodeDialog: document.getElementById("submit-node-dialog"),
    savesDialog: document.getElementById("saves-dialog"),
    savesList: document.getElementById("saves-list"),
    closeSavesDialog: document.getElementById("close-saves-dialog"),
    refreshSavesButton: document.getElementById("refresh-saves-button"),
    saveFromDialogButton: document.getElementById("save-from-dialog-button"),
    dragPreview: document.getElementById("drag-preview"),
    toast: document.getElementById("toast"),
  };

  const state = {
    bootstrap: null,
    revision: 0,
    baselineRevision: null,
    sessionDirty: false,
    nodes: new Map(),
    roots: [],
    expanded: new Set(),
    activeNodeId: "",
    items: [],
    total: 0,
    offset: 0,
    selection: new Set(),
    selectionAll: false,
    lastSelectedIndex: -1,
    loadingTags: false,
    searchTimer: 0,
    toastTimer: 0,
    dragging: false,
    box: null,
  };

  function publishEditorChrome(extra = {}) {
    if (!EMBEDDED || window.parent === window) {
      return;
    }
    const history = state.bootstrap?.history || {};
    const persistence = state.bootstrap?.persistence || {};
    window.parent.postMessage(
      {
        source: "tagtoolbox-editor",
        type: "editor-chrome",
        dirty: Boolean(state.sessionDirty),
        revision: state.revision,
        revisionLabel: Number.isInteger(state.revision) ? `revision ${state.revision}` : "",
        saveStatus: persistence.auto_saved_at
          ? `已自动保存 · ${persistence.auto_saved_at}`
          : (state.bootstrap ? "已自动保存到独立编辑库" : ""),
        canUndo: Boolean(history.can_undo),
        canRedo: Boolean(history.can_redo),
        busySnapshot: Boolean(extra.busySnapshot),
        busyExport: Boolean(extra.busyExport),
      },
      window.location.origin,
    );
    window.parent.postMessage(
      {
        source: "tagtoolbox-editor",
        type: "editor-session",
        dirty: Boolean(state.sessionDirty),
        revision: state.revision,
      },
      window.location.origin,
    );
  }

  function publishEditorSession() {
    publishEditorChrome();
  }

  function markSessionDirty() {
    state.sessionDirty = true;
    // Always republish so the shell can mark toolbox stale again after a prior reload.
    publishEditorChrome();
  }

  function formatNumber(value) {
    return new Intl.NumberFormat("zh-CN").format(Number(value) || 0);
  }

  function createNode(tag, className = "", text = "") {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== "") node.textContent = text;
    return node;
  }

  function showToast(message) {
    clearTimeout(state.toastTimer);
    elements.toast.textContent = message;
    elements.toast.classList.add("is-visible");
    state.toastTimer = window.setTimeout(() => {
      elements.toast.classList.remove("is-visible");
    }, 3600);
  }

  async function api(path, options = {}) {
    const config = {
      method: options.method || "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    };
    if (options.body !== undefined) {
      config.headers["Content-Type"] = "application/json";
      config.body = JSON.stringify(options.body);
    }
    const response = await fetch(path, config);
    let payload;
    try {
      payload = await response.json();
    } catch {
      throw new Error(`${path} 返回了无效 JSON`);
    }
    if (!response.ok) {
      const error = new Error(payload.error || `${path} 请求失败`);
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  async function mutate(path, method, body = {}) {
    try {
      const beforeRevision = state.revision;
      const payload = await api(path, {
        method,
        body: { ...body, revision: state.revision },
      });
      if (Number.isInteger(payload.revision)) state.revision = payload.revision;
      const taxonomyTouching = !path.startsWith("/api/export")
        && path !== "/api/saves"
        && path !== "/api/snapshot";
      if (
        taxonomyTouching
        && (
          payload.unchanged === false
          || (Number.isInteger(payload.revision) && payload.revision !== beforeRevision)
        )
      ) {
        markSessionDirty();
      }
      return payload;
    } catch (error) {
      if (error.status === 409) {
        await refreshBootstrap({ keepExpansion: true });
        showToast("页面版本已刷新，请重新执行刚才的操作。");
      }
      throw error;
    }
  }

  function flattenNodes(nodes, parent = null) {
    for (const node of nodes) {
      state.nodes.set(node.id, node);
      node.parent = parent;
      flattenNodes(node.children || [], node);
    }
  }

  function rebuildNodeIndex() {
    state.nodes = new Map();
    state.roots = state.bootstrap.taxonomy.roots || [];
    flattenNodes(state.roots);
    if (state.expanded.size === 0) {
      for (const root of state.roots) state.expanded.add(root.id);
    }
  }

  function currentFilters() {
    return {
      query: elements.searchInput.value.trim(),
      source: elements.sourceFilter.value,
      safety: elements.safetyFilter.value,
      status: elements.statusFilter.value,
      sort: elements.sortFilter.value,
      node_id: state.activeNodeId,
      scope: "descendants",
    };
  }

  function queryString(filters, includePage = true) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== "" && value !== undefined && value !== null) {
        params.set(key, String(value));
      }
    }
    if (includePage) {
      params.set("limit", String(PAGE_SIZE));
      params.set("offset", String(state.offset));
    }
    return params.toString();
  }

  function activeNodeLabel() {
    if (state.activeNodeId === UNCLASSIFIED_ID) return "未归类队列";
    if (!state.activeNodeId) return "全部分类";
    const node = state.nodes.get(state.activeNodeId);
    return node ? node.path_labels.join(" / ") : "全部分类";
  }

  function selectionCount() {
    return state.selectionAll ? state.total : state.selection.size;
  }

  function clearSelection({ render = true } = {}) {
    state.selection.clear();
    state.selectionAll = false;
    state.lastSelectedIndex = -1;
    if (render) {
      updateSelectionUi();
      updateCardSelection();
    }
  }

  function selectionPayload() {
    if (state.selectionAll) {
      return {
        mode: "query",
        filters: currentFilters(),
      };
    }
    return {
      mode: "explicit",
      ids: [...state.selection],
    };
  }

  function updateSelectionUi() {
    const count = selectionCount();
    if (state.selectionAll) {
      elements.selectionSummary.textContent =
        `已选择当前结果全部 ${formatNumber(count)} 个标签`;
    } else if (count) {
      elements.selectionSummary.textContent = `已选择 ${formatNumber(count)} 个标签`;
    } else {
      elements.selectionSummary.textContent = "未选择标签";
    }
    elements.clearSelected.disabled = count === 0;
    elements.unassignSelected.disabled = count === 0;
    elements.selectPage.disabled = state.items.length === 0;
    elements.selectAllResults.disabled = state.total === 0;
  }

  function updateCardSelection() {
    const cards = elements.tagGrid.querySelectorAll(".tag-card[data-tag-id]");
    for (const card of cards) {
      const selected = state.selectionAll || state.selection.has(card.dataset.tagId);
      card.classList.toggle("is-selected", selected);
      card.setAttribute("aria-pressed", String(selected));
    }
  }

  function renderTags() {
    const fragment = document.createDocumentFragment();
    state.items.forEach((tag, index) => {
      const card = createNode("button", "tag-card");
      card.type = "button";
      card.draggable = true;
      card.dataset.tagId = tag.id;
      card.dataset.index = String(index);
      card.setAttribute("aria-pressed", "false");
      card.title = [
        tag.path.length ? tag.path.join(" / ") : "未归类",
        `source=${tag.source}`,
        `safety=${tag.safety}`,
        `heat=${formatNumber(tag.post_count)}`,
      ].join(" · ");

      const name = createNode("span", "tag-name", tag.zh || tag.en);
      const heat = createNode("span", "tag-heat", formatNumber(tag.post_count));
      const english = createNode("span", "tag-en", tag.en);
      const path = createNode(
        "span",
        "tag-path",
        tag.path.length ? tag.path.join(" / ") : "未归类",
      );
      card.append(name, heat, english, path);
      fragment.append(card);
    });
    elements.tagGrid.replaceChildren(fragment);
    elements.tagEmpty.hidden = state.items.length > 0;
    updateCardSelection();
  }

  function updatePager() {
    const first = state.total ? state.offset + 1 : 0;
    const last = Math.min(state.offset + state.items.length, state.total);
    const page = Math.floor(state.offset / PAGE_SIZE) + 1;
    const pages = Math.max(1, Math.ceil(state.total / PAGE_SIZE));
    elements.resultSummary.textContent =
      `${formatNumber(first)}–${formatNumber(last)} / ${formatNumber(state.total)}`;
    elements.pageSummary.textContent =
      `第 ${formatNumber(page)} / ${formatNumber(pages)} 页`;
    elements.previousPage.disabled = state.offset <= 0 || state.loadingTags;
    elements.nextPage.disabled =
      state.offset + state.items.length >= state.total || state.loadingTags;
    elements.activeFilterLabel.textContent = activeNodeLabel();
  }

  async function loadTags({ resetPage = false, clearSelected = false } = {}) {
    if (resetPage) state.offset = 0;
    if (clearSelected) clearSelection({ render: false });
    state.loadingTags = true;
    elements.tagGrid.setAttribute("aria-busy", "true");
    elements.resultSummary.textContent = "正在查询…";
    updatePager();
    try {
      const payload = await api(`/api/tags?${queryString(currentFilters())}`);
      state.items = payload.items;
      state.total = payload.total;
      state.offset = payload.offset;
      renderTags();
      updateSelectionUi();
      updatePager();
    } catch (error) {
      showToast(error.message);
      throw error;
    } finally {
      state.loadingTags = false;
      elements.tagGrid.removeAttribute("aria-busy");
      updatePager();
    }
  }

  function treeAction(symbol, title, action, node) {
    const button = createNode("button", "tree-action", symbol);
    button.type = "button";
    button.title = title;
    button.dataset.treeAction = action;
    button.dataset.nodeId = node.id;
    return button;
  }

  function renderTreeNode(node) {
    const item = createNode("li", "tree-node");
    item.dataset.nodeId = node.id;
    item.setAttribute("role", "treeitem");
    item.setAttribute("aria-level", String(node.depth));

    const row = createNode("div", "tree-row");
    row.dataset.dropNode = node.id;
    row.dataset.nodeId = node.id;
    if (state.activeNodeId === node.id) row.classList.add("is-active");

    const hasChildren = Array.isArray(node.children) && node.children.length > 0;
    const toggle = createNode("button", "tree-toggle", hasChildren
      ? (state.expanded.has(node.id) ? "▾" : "▸")
      : "·");
    toggle.type = "button";
    toggle.dataset.treeAction = "toggle";
    toggle.dataset.nodeId = node.id;
    toggle.disabled = !hasChildren;
    toggle.setAttribute(
      "aria-label",
      state.expanded.has(node.id) ? "折叠子分类" : "展开子分类",
    );

    const label = createNode("button", "tree-label");
    label.type = "button";
    label.dataset.treeAction = "filter";
    label.dataset.nodeId = node.id;
    const strong = createNode("strong", "", node.label);
    const small = createNode("small", "", `L${node.depth}`);
    label.append(strong, small);

    const count = createNode("span", "tree-count", formatNumber(node.total_count));
    count.title = `直接 ${formatNumber(node.direct_count)} / 含子类 ${formatNumber(node.total_count)}`;

    const actions = createNode("span", "tree-actions");
    if (node.depth < 5) {
      actions.append(treeAction("+", "新建子分类", "create-child", node));
    }
    actions.append(
      treeAction("✎", "重命名", "rename", node),
      treeAction("↑", "上移", "up", node),
      treeAction("↓", "下移", "down", node),
      treeAction("×", "删除分类", "delete", node),
    );
    actions.lastElementChild.classList.add("delete");
    row.append(toggle, label, count, actions);
    item.append(row);

    if (hasChildren) {
      const list = createNode("ul", "tree-list tree-children");
      list.setAttribute("role", "group");
      if (!state.expanded.has(node.id)) list.hidden = true;
      for (const child of node.children) list.append(renderTreeNode(child));
      item.append(list);
    }
    return item;
  }

  function renderTaxonomy() {
    const fragment = document.createDocumentFragment();
    const allRow = createNode("div", "tree-row");
    allRow.dataset.nodeId = ALL_ID;
    if (!state.activeNodeId) allRow.classList.add("is-active");
    const allMarker = createNode("span", "tree-toggle", "◆");
    const allLabel = createNode("button", "tree-label");
    allLabel.type = "button";
    allLabel.dataset.treeAction = "filter";
    allLabel.dataset.nodeId = ALL_ID;
    allLabel.append(
      createNode("strong", "", "全部分类"),
      createNode("small", "", "系统"),
    );
    allRow.append(
      allMarker,
      allLabel,
      createNode("span", "tree-count", formatNumber(state.bootstrap.total)),
      createNode("span", "tree-actions"),
    );
    fragment.append(allRow);

    const unclassified = createNode("div", "tree-row unclassified-row");
    unclassified.dataset.dropNode = UNCLASSIFIED_ID;
    unclassified.dataset.nodeId = UNCLASSIFIED_ID;
    if (state.activeNodeId === UNCLASSIFIED_ID) unclassified.classList.add("is-active");
    const marker = createNode("span", "tree-toggle", "!");
    const label = createNode("button", "tree-label");
    label.type = "button";
    label.dataset.treeAction = "filter";
    label.dataset.nodeId = UNCLASSIFIED_ID;
    label.append(
      createNode("strong", "", "未归类队列"),
      createNode("small", "", "系统"),
    );
    const count = createNode(
      "span",
      "tree-count",
      formatNumber(state.bootstrap.taxonomy.unclassified_count),
    );
    unclassified.append(marker, label, count, createNode("span", "tree-actions"));
    fragment.append(unclassified);

    const list = createNode("ul", "tree-list");
    list.setAttribute("role", "group");
    for (const root of state.roots) list.append(renderTreeNode(root));
    fragment.append(list);
    elements.taxonomyTree.replaceChildren(fragment);
    elements.taxonomySummary.textContent =
      `${formatNumber(state.bootstrap.taxonomy.node_count)} 个节点 · ` +
      `${formatNumber(state.bootstrap.taxonomy.unclassified_count)} 个未归类`;
  }

  function renderHistory() {
    const history = state.bootstrap.history;
    elements.undoButton.disabled = !history.can_undo;
    elements.redoButton.disabled = !history.can_redo;
    const fragment = document.createDocumentFragment();
    for (const item of history.items) {
      const row = createNode("li", item.applied ? "" : "is-undone");
      const summary = createNode("strong", "", item.summary);
      row.append(summary, document.createTextNode(` · ${item.created_at}`));
      fragment.append(row);
    }
    if (history.items.length === 0) {
      fragment.append(createNode("li", "", "尚无编辑操作"));
    }
    elements.historyList.replaceChildren(fragment);
    publishEditorChrome();
  }

  function renderHeader() {
    elements.datasetSummary.textContent =
      `${formatNumber(state.bootstrap.total)} 个可编辑标签 · ` +
      `独立编辑库 · source ${state.bootstrap.source_build_id.slice(0, 12)}…`;
    elements.revisionBadge.textContent = `revision ${state.revision}`;
    const persistence = state.bootstrap.persistence || {};
    elements.saveStatus.textContent = persistence.auto_saved_at
      ? `已自动保存 · ${persistence.auto_saved_at}`
      : "已自动保存到独立编辑库";
    elements.saveStatus.title =
      `${persistence.database || "classification_editor.sqlite"}` +
      (persistence.last_checkpoint_path
        ? `\n最近进度点：${persistence.last_checkpoint_path}`
        : "");
    elements.editorShell.setAttribute("aria-busy", "false");
    publishEditorChrome();
  }

  async function refreshBootstrap({ keepExpansion = false } = {}) {
    const previousExpanded = keepExpansion ? new Set(state.expanded) : new Set();
    const payload = await api("/api/bootstrap");
    state.bootstrap = payload;
    state.revision = payload.revision;
    if (state.baselineRevision === null) {
      state.baselineRevision = payload.revision;
      state.sessionDirty = false;
      publishEditorSession();
    }
    state.expanded = previousExpanded;
    rebuildNodeIndex();
    if (state.activeNodeId && state.activeNodeId !== UNCLASSIFIED_ID
        && !state.nodes.has(state.activeNodeId)) {
      state.activeNodeId = UNCLASSIFIED_ID;
    }
    renderHeader();
    renderTaxonomy();
    renderHistory();
  }

  function openNodeDialog(mode, node = null) {
    elements.nodeMode.value = mode;
    elements.nodeId.value = node ? node.id : "";
    elements.nodeParentId.value =
      mode === "create-root" ? "" : node ? node.id : "";
    if (mode === "rename") {
      elements.nodeDialogTitle.textContent = `重命名 L${node.depth} 分类`;
      elements.nodeLabel.value = node.label;
      elements.nodeDialogHint.textContent =
        "重命名只修改显示名称，已有标签归属不会变化。";
    } else {
      const depth = mode === "create-root" ? 1 : node.depth + 1;
      elements.nodeDialogTitle.textContent = `创建 L${depth} 分类`;
      elements.nodeLabel.value = "";
      elements.nodeDialogHint.textContent =
        mode === "create-root"
          ? "新分类会作为一级分类加入树底部。"
          : `父分类：${node.path_labels.join(" / ")}`;
    }
    elements.nodeDialog.showModal();
    requestAnimationFrame(() => elements.nodeLabel.focus());
  }

  function closeNodeDialog() {
    elements.nodeDialog.close();
  }

  async function submitNodeDialog(event) {
    event.preventDefault();
    const mode = elements.nodeMode.value;
    const label = elements.nodeLabel.value.trim();
    if (!label) return;
    elements.submitNodeDialog.disabled = true;
    try {
      if (mode === "rename") {
        const nodeId = elements.nodeId.value;
        await mutate(`/api/taxonomy/${encodeURIComponent(nodeId)}`, "PATCH", { label });
        showToast(`已重命名为「${label}」`);
      } else {
        const parentId = elements.nodeParentId.value || null;
        await mutate("/api/taxonomy", "POST", {
          label,
          parent_id: parentId,
        });
        showToast(`已创建「${label}」`);
      }
      closeNodeDialog();
      await refreshBootstrap({ keepExpansion: true });
      if (mode !== "rename" && elements.nodeParentId.value) {
        state.expanded.add(elements.nodeParentId.value);
        renderTaxonomy();
      }
    } catch (error) {
      showToast(error.message);
    } finally {
      elements.submitNodeDialog.disabled = false;
    }
  }

  async function reorderNode(nodeId, direction) {
    try {
      const payload = await mutate(
        `/api/taxonomy/${encodeURIComponent(nodeId)}`,
        "POST",
        { action: "reorder", direction },
      );
      if (!payload.unchanged) {
        await refreshBootstrap({ keepExpansion: true });
        showToast("分类顺序已更新");
      }
    } catch (error) {
      showToast(error.message);
    }
  }

  async function deleteNode(node) {
    const message =
      `确认删除「${node.path_labels.join(" / ")}」？\n\n` +
      `将删除 ${formatNumber(countNodes(node))} 个分类节点；` +
      `${formatNumber(node.total_count)} 个标签会进入“未归类队列”。`;
    if (!window.confirm(message)) return;
    try {
      const payload = await mutate(
        `/api/taxonomy/${encodeURIComponent(node.id)}`,
        "DELETE",
        { confirm: true },
      );
      if (state.activeNodeId === node.id || isDescendantOfActive(node)) {
        state.activeNodeId = UNCLASSIFIED_ID;
      }
      clearSelection({ render: false });
      await refreshBootstrap({ keepExpansion: true });
      await loadTags({ resetPage: true });
      showToast(
        `已删除 ${formatNumber(payload.deleted_nodes)} 个节点；` +
        `${formatNumber(payload.unclassified_tags)} 个标签进入未归类`,
      );
    } catch (error) {
      showToast(error.message);
    }
  }

  function countNodes(node) {
    return 1 + (node.children || []).reduce((sum, child) => sum + countNodes(child), 0);
  }

  function isDescendantOfActive(node) {
    if (!state.activeNodeId || state.activeNodeId === UNCLASSIFIED_ID) return false;
    let current = node.parent;
    while (current) {
      if (current.id === state.activeNodeId) return true;
      current = current.parent;
    }
    return false;
  }

  async function assignSelected(nodeId) {
    const count = selectionCount();
    if (!count) {
      showToast("请先选择标签");
      return;
    }
    const target = nodeId === UNCLASSIFIED_ID
      ? "未归类队列"
      : state.nodes.get(nodeId)?.path_labels.join(" / ");
    if (!target) {
      showToast("目标分类不存在");
      return;
    }
    try {
      const payload = await mutate("/api/assign", "POST", {
        node_id: nodeId,
        selection: selectionPayload(),
      });
      clearSelection({ render: false });
      await refreshBootstrap({ keepExpansion: true });
      await loadTags({ resetPage: false });
      showToast(
        payload.updated
          ? `已将 ${formatNumber(payload.updated)} 个标签归入「${target}」`
          : "选中标签已经位于该分类",
      );
    } catch (error) {
      showToast(error.message);
    }
  }

  function setSingleSelection(index, event) {
    const tag = state.items[index];
    if (!tag) return;
    if (state.selectionAll) clearSelection({ render: false });
    if (event.shiftKey && state.lastSelectedIndex >= 0) {
      if (!event.ctrlKey && !event.metaKey) state.selection.clear();
      const start = Math.min(state.lastSelectedIndex, index);
      const end = Math.max(state.lastSelectedIndex, index);
      for (let position = start; position <= end; position += 1) {
        state.selection.add(state.items[position].id);
      }
    } else if (event.ctrlKey || event.metaKey) {
      if (state.selection.has(tag.id)) state.selection.delete(tag.id);
      else state.selection.add(tag.id);
      state.lastSelectedIndex = index;
    } else {
      state.selection.clear();
      state.selection.add(tag.id);
      state.lastSelectedIndex = index;
    }
    updateSelectionUi();
    updateCardSelection();
  }

  function startBoxSelection(event) {
    if (event.button !== 0 || event.target.closest(".tag-card")) return;
    const rect = elements.tagViewport.getBoundingClientRect();
    state.box = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      add: event.ctrlKey || event.metaKey,
      viewportRect: rect,
    };
    if (!state.box.add) clearSelection({ render: false });
    elements.tagViewport.setPointerCapture(event.pointerId);
    elements.selectionRectangle.hidden = false;
    updateSelectionRectangle(event.clientX, event.clientY);
    event.preventDefault();
  }

  function updateSelectionRectangle(clientX, clientY) {
    if (!state.box) return;
    const rect = state.box.viewportRect;
    const left = Math.max(rect.left, Math.min(state.box.startX, clientX));
    const top = Math.max(rect.top, Math.min(state.box.startY, clientY));
    const right = Math.min(rect.right, Math.max(state.box.startX, clientX));
    const bottom = Math.min(rect.bottom, Math.max(state.box.startY, clientY));
    const scrollLeft = elements.tagViewport.scrollLeft;
    const scrollTop = elements.tagViewport.scrollTop;
    elements.selectionRectangle.style.left = `${left - rect.left + scrollLeft}px`;
    elements.selectionRectangle.style.top = `${top - rect.top + scrollTop}px`;
    elements.selectionRectangle.style.width = `${Math.max(0, right - left)}px`;
    elements.selectionRectangle.style.height = `${Math.max(0, bottom - top)}px`;
    state.box.current = { left, top, right, bottom };
  }

  function moveBoxSelection(event) {
    if (!state.box || event.pointerId !== state.box.pointerId) return;
    updateSelectionRectangle(event.clientX, event.clientY);
  }

  function finishBoxSelection(event) {
    if (!state.box || event.pointerId !== state.box.pointerId) return;
    const selectionRect = state.box.current;
    for (const card of elements.tagGrid.querySelectorAll(".tag-card[data-tag-id]")) {
      const cardRect = card.getBoundingClientRect();
      const intersects = !(
        cardRect.right < selectionRect.left
        || cardRect.left > selectionRect.right
        || cardRect.bottom < selectionRect.top
        || cardRect.top > selectionRect.bottom
      );
      if (intersects) state.selection.add(card.dataset.tagId);
    }
    elements.selectionRectangle.hidden = true;
    elements.selectionRectangle.removeAttribute("style");
    elements.tagViewport.releasePointerCapture(event.pointerId);
    state.box = null;
    state.selectionAll = false;
    updateSelectionUi();
    updateCardSelection();
  }

  function beginDrag(card, event) {
    const tagId = card.dataset.tagId;
    if (!state.selectionAll && !state.selection.has(tagId)) {
      state.selection.clear();
      state.selection.add(tagId);
      state.lastSelectedIndex = Number(card.dataset.index);
      updateSelectionUi();
      updateCardSelection();
    }
    state.dragging = true;
    card.classList.add("is-dragging");
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", tagId);
    elements.dragPreview.hidden = false;
    elements.dragPreview.textContent =
      `拖动 ${formatNumber(selectionCount())} 个标签到分类节点`;
  }

  function endDrag(card) {
    state.dragging = false;
    if (card) card.classList.remove("is-dragging");
    elements.dragPreview.hidden = true;
    for (const row of elements.taxonomyTree.querySelectorAll(".is-drop-target")) {
      row.classList.remove("is-drop-target");
    }
  }

  async function performHistory(action) {
    try {
      const payload = await mutate(`/api/history/${action}`, "POST");
      await refreshBootstrap({ keepExpansion: true });
      await loadTags({ resetPage: false, clearSelected: true });
      if (payload.unchanged) showToast(action === "undo" ? "没有可撤销操作" : "没有可重做操作");
      else showToast(action === "undo" ? `已撤销：${payload.undone}` : `已重做：${payload.redone}`);
    } catch (error) {
      showToast(error.message);
    }
  }

  async function createSnapshot() {
    elements.snapshotButton.disabled = true;
    elements.saveFromDialogButton.disabled = true;
    elements.snapshotButton.textContent = "正在保存…";
    publishEditorChrome({ busySnapshot: true });
    try {
      const payload = await mutate("/api/saves", "POST");
      await refreshBootstrap({ keepExpansion: true });
      if (elements.savesDialog.open) await refreshSaves();
      showToast(`进度已保存：${payload.snapshot}`);
    } catch (error) {
      showToast(error.message);
    } finally {
      elements.snapshotButton.disabled = false;
      elements.saveFromDialogButton.disabled = false;
      elements.snapshotButton.textContent = "保存进度";
      publishEditorChrome({ busySnapshot: false });
    }
  }

  async function refreshSaves() {
    elements.savesList.textContent = "正在读取进度点…";
    try {
      const payload = await api("/api/saves");
      const fragment = document.createDocumentFragment();
      for (const save of payload.items) {
        const row = createNode("article", "save-row");
        const detail = createNode("div");
        detail.append(
          createNode("strong", "", save.name),
          createNode(
            "span",
            "",
            `revision ${save.revision} · ${save.created_at} · ` +
            `${formatNumber(Math.round(save.bytes / 1024 / 1024))} MB`,
          ),
          createNode("span", "save-path", save.path),
        );
        const restore = createNode("button", "button compact", "恢复此进度");
        restore.type = "button";
        restore.dataset.restoreSave = save.id;
        row.append(detail, restore);
        fragment.append(row);
      }
      if (payload.items.length === 0) {
        fragment.append(createNode("p", "", "尚未创建手工进度点。"));
      }
      elements.savesList.replaceChildren(fragment);
    } catch (error) {
      elements.savesList.textContent = error.message;
    }
  }

  async function openSavesDialog() {
    elements.savesDialog.showModal();
    await refreshSaves();
  }

  async function restoreSave(saveId) {
    if (!window.confirm(
      "恢复后，当前状态会先自动另存一个进度点，再切换到所选进度。继续吗？",
    )) return;
    elements.savesList.setAttribute("aria-busy", "true");
    try {
      const payload = await mutate("/api/saves/restore", "POST", {
        save_id: saveId,
      });
      await refreshBootstrap();
      await loadTags({ resetPage: true, clearSelected: true });
      await refreshSaves();
      showToast(
        `已恢复进度；恢复前状态保存在 ${payload.pre_restore_save_id}`,
      );
    } catch (error) {
      showToast(error.message);
    } finally {
      elements.savesList.removeAttribute("aria-busy");
    }
  }

  async function exportBundle() {
    elements.exportButton.disabled = true;
    elements.exportButton.textContent = "正在导出…";
    publishEditorChrome({ busyExport: true });
    try {
      const payload = await mutate("/api/export", "POST");
      await refreshBootstrap({ keepExpansion: true });
      const download = document.createElement("a");
      download.href = payload.download_url;
      download.download = "";
      document.body.append(download);
      download.click();
      download.remove();
      showToast(`导出完成：${payload.archive}`);
    } catch (error) {
      showToast(error.message);
    } finally {
      elements.exportButton.disabled = false;
      elements.exportButton.textContent = "导出词库和分类";
      publishEditorChrome({ busyExport: false });
    }
  }

  function handleShellCommand(command) {
    if (command === "undo") {
      performHistory("undo");
      return;
    }
    if (command === "redo") {
      performHistory("redo");
      return;
    }
    if (command === "snapshot") {
      createSnapshot();
      return;
    }
    if (command === "manage-saves") {
      openSavesDialog();
      return;
    }
    if (command === "export") {
      exportBundle();
    }
  }

  function bindEvents() {
    elements.searchInput.addEventListener("input", () => {
      clearTimeout(state.searchTimer);
      state.searchTimer = window.setTimeout(() => {
        loadTags({ resetPage: true, clearSelected: true });
      }, 220);
    });
    elements.clearSearch.addEventListener("click", () => {
      elements.searchInput.value = "";
      loadTags({ resetPage: true, clearSelected: true });
      elements.searchInput.focus();
    });
    for (const select of [
      elements.sourceFilter,
      elements.safetyFilter,
      elements.statusFilter,
      elements.sortFilter,
    ]) {
      select.addEventListener("change", () => {
        loadTags({ resetPage: true, clearSelected: true });
      });
    }

    elements.previousPage.addEventListener("click", () => {
      state.offset = Math.max(0, state.offset - PAGE_SIZE);
      state.lastSelectedIndex = -1;
      loadTags();
    });
    elements.nextPage.addEventListener("click", () => {
      state.offset += PAGE_SIZE;
      state.lastSelectedIndex = -1;
      loadTags();
    });
    elements.selectPage.addEventListener("click", () => {
      if (state.selectionAll) clearSelection({ render: false });
      for (const tag of state.items) state.selection.add(tag.id);
      updateSelectionUi();
      updateCardSelection();
    });
    elements.selectAllResults.addEventListener("click", () => {
      state.selection.clear();
      state.selectionAll = true;
      updateSelectionUi();
      updateCardSelection();
    });
    elements.clearSelected.addEventListener("click", () => clearSelection());
    elements.unassignSelected.addEventListener("click", () => assignSelected(UNCLASSIFIED_ID));

    elements.tagGrid.addEventListener("click", (event) => {
      const card = event.target.closest(".tag-card[data-tag-id]");
      if (!card) return;
      setSingleSelection(Number(card.dataset.index), event);
    });
    elements.tagGrid.addEventListener("dragstart", (event) => {
      const card = event.target.closest(".tag-card[data-tag-id]");
      if (card) beginDrag(card, event);
    });
    elements.tagGrid.addEventListener("dragend", (event) => {
      endDrag(event.target.closest(".tag-card[data-tag-id]"));
    });

    elements.tagViewport.addEventListener("pointerdown", startBoxSelection);
    elements.tagViewport.addEventListener("pointermove", moveBoxSelection);
    elements.tagViewport.addEventListener("pointerup", finishBoxSelection);
    elements.tagViewport.addEventListener("pointercancel", finishBoxSelection);

    elements.createRoot.addEventListener("click", () => openNodeDialog("create-root"));
    elements.expandAll.addEventListener("click", () => {
      state.expanded = new Set(state.nodes.keys());
      renderTaxonomy();
    });
    elements.collapseAll.addEventListener("click", () => {
      state.expanded.clear();
      renderTaxonomy();
    });

    elements.taxonomyTree.addEventListener("click", (event) => {
      const control = event.target.closest("[data-tree-action]");
      if (!control) return;
      const action = control.dataset.treeAction;
      const nodeId = control.dataset.nodeId;
      const node = state.nodes.get(nodeId);
      if (action === "toggle" && node) {
        if (state.expanded.has(nodeId)) state.expanded.delete(nodeId);
        else state.expanded.add(nodeId);
        renderTaxonomy();
      } else if (action === "filter") {
        state.activeNodeId = nodeId === ALL_ID ? "" : nodeId;
        renderTaxonomy();
        loadTags({ resetPage: true, clearSelected: true });
      } else if (action === "create-child" && node) {
        openNodeDialog("create-child", node);
      } else if (action === "rename" && node) {
        openNodeDialog("rename", node);
      } else if (action === "delete" && node) {
        deleteNode(node);
      } else if ((action === "up" || action === "down") && node) {
        reorderNode(nodeId, action);
      }
    });
    elements.taxonomyTree.addEventListener("dragover", (event) => {
      const row = event.target.closest("[data-drop-node]");
      if (!row || !state.dragging) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      for (const previous of elements.taxonomyTree.querySelectorAll(".is-drop-target")) {
        if (previous !== row) previous.classList.remove("is-drop-target");
      }
      row.classList.add("is-drop-target");
      const nodeId = row.dataset.dropNode;
      const target = nodeId === UNCLASSIFIED_ID
        ? "未归类队列"
        : state.nodes.get(nodeId)?.path_labels.join(" / ");
      elements.dragPreview.textContent =
        `将 ${formatNumber(selectionCount())} 个标签归入：${target || "未知分类"}`;
    });
    elements.taxonomyTree.addEventListener("dragleave", (event) => {
      const row = event.target.closest("[data-drop-node]");
      if (row && !row.contains(event.relatedTarget)) row.classList.remove("is-drop-target");
    });
    elements.taxonomyTree.addEventListener("drop", (event) => {
      const row = event.target.closest("[data-drop-node]");
      if (!row) return;
      event.preventDefault();
      const nodeId = row.dataset.dropNode;
      endDrag(elements.tagGrid.querySelector(".tag-card.is-dragging"));
      assignSelected(nodeId);
    });

    elements.nodeForm.addEventListener("submit", submitNodeDialog);
    elements.closeNodeDialog.addEventListener("click", closeNodeDialog);
    elements.cancelNodeDialog.addEventListener("click", closeNodeDialog);
    elements.undoButton.addEventListener("click", () => performHistory("undo"));
    elements.redoButton.addEventListener("click", () => performHistory("redo"));
    elements.snapshotButton.addEventListener("click", createSnapshot);
    elements.manageSavesButton.addEventListener("click", openSavesDialog);
    elements.exportButton.addEventListener("click", exportBundle);
    window.addEventListener("message", (event) => {
      if (event.origin !== window.location.origin) {
        return;
      }
      const data = event.data;
      if (!data || data.source !== "tagtoolbox-shell" || data.type !== "editor-command") {
        return;
      }
      handleShellCommand(data.command);
    });
    elements.closeSavesDialog.addEventListener("click", () => elements.savesDialog.close());
    elements.refreshSavesButton.addEventListener("click", refreshSaves);
    elements.saveFromDialogButton.addEventListener("click", createSnapshot);
    elements.savesList.addEventListener("click", (event) => {
      const button = event.target.closest("[data-restore-save]");
      if (button) restoreSave(button.dataset.restoreSave);
    });

    document.addEventListener("keydown", (event) => {
      if (!(event.ctrlKey || event.metaKey)) return;
      const target = event.target;
      if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) return;
      if (event.key.toLowerCase() === "z" && !event.shiftKey) {
        event.preventDefault();
        performHistory("undo");
      } else if (
        event.key.toLowerCase() === "y"
        || (event.key.toLowerCase() === "z" && event.shiftKey)
      ) {
        event.preventDefault();
        performHistory("redo");
      }
    });
  }

  async function boot() {
    bindEvents();
    try {
      await refreshBootstrap();
      await loadTags();
      elements.loadingOverlay.hidden = true;
    } catch (error) {
      elements.loadingTitle.textContent = "无法连接分类编辑服务";
      elements.loadingDetail.textContent =
        `${error.message}。请使用 editor_server.py 启动 8765 端口。`;
      console.error(error);
    }
  }

  boot();
})();
