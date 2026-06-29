"""Schema overview accordion — raw loaded tables at a glance.

An anywidget that shows the raw ingestion tables as collapsible rows.
Collapsed: table name + row count + chevron.
Expanded: full column list with PK/FK/type pills (identical language to the
schema explorer). No copy icons — this surface is for navigation only.

Driven by a `payload` list-of-dicts trait:
  [{ table, rows, columns: [{name, type, role, fk_target}] }, ...]
"""

from __future__ import annotations

import anywidget
import traitlets

_ESM = r"""
// Chevron SVG (thin line-style, lucide family: fill=none, stroke=currentColor,
// round caps/joins). Two orientations: right (collapsed) and down (expanded).
function chevron(down) {
  const pts = down ? "6 9 12 15 18 9" : "9 6 15 12 9 18";
  return (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none"' +
    ' stroke="currentColor" stroke-width="2" stroke-linecap="round"' +
    ' stroke-linejoin="round"><polyline points="' + pts + '"/></svg>'
  );
}

// Pill HTML helpers — exact same classes used in schema_explorer.py.
function pill(cls, text) {
  return '<span class="sov-pill ' + cls + '">' + text + '</span>';
}
function rolePill(role) {
  if (role === "pk") return pill("pill-pk", "PK");
  if (role === "fk") return pill("pill-fk", "FK");
  return "";
}
function typePill(dtype) {
  return pill("pill-neutral", dtype);
}

function legacyCopy(text) {
  return new Promise((resolve, reject) => {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.top = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      ok ? resolve() : reject();
    } catch (err) {
      reject(err);
    }
  });
}

function copyText(text) {
  if (!text) return Promise.reject();
  if (window.isSecureContext && navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text).catch(() => legacyCopy(text));
  }
  return legacyCopy(text);
}

// Sparkle copy glyph + menu mini-icons — same motif as schema_explorer.py.
const COPY =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"' +
  ' stroke-linecap="round" stroke-linejoin="round">' +
  '<path d="M3.5 14.5h-1a1.8 1.8 0 0 1-1.8-1.8V3.8A1.8 1.8 0 0 1 2.5 2h6.7A1.8 1.8 0 0 1 11 3.8v.7"/>' +
  '<rect x="4.5" y="7" width="11.5" height="13" rx="2"/>' +
  '<path d="M19.5 0.2L20.75 3.25L23.8 4.5L20.75 5.75L19.5 8.8L18.25 5.75L15.2 4.5L18.25 3.25Z" fill="#5c57c6" stroke="none"/>' +
  '<path d="M11 0L11.7 1.5L13.2 2.2L11.7 2.9L11 4.4L10.3 2.9L8.8 2.2L10.3 1.5Z" fill="#5c57c6" stroke="none"/>' +
  '</svg>';
const ICON_LOGS =
  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"' +
  ' stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' +
  '<rect x="4" y="2" width="14" height="20" rx="2"/>' +
  '<line x1="8" y1="9" x2="16" y2="9"/>' +
  '<line x1="8" y1="13" x2="14" y2="13"/>' +
  '<line x1="8" y1="17" x2="11" y2="17"/>' +
  '</svg>';
const ICON_TRACES =
  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"' +
  ' stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' +
  '<circle cx="4" cy="12" r="3" fill="currentColor" stroke="none"/>' +
  '<circle cx="12" cy="12" r="3" fill="currentColor" stroke="none"/>' +
  '<circle cx="20" cy="12" r="3" fill="currentColor" stroke="none"/>' +
  '<line x1="7" y1="12" x2="9" y2="12"/>' +
  '<line x1="15" y1="12" x2="17" y2="12"/>' +
  '</svg>';

// Inject global styles for the body-appended split-copy menu once per page load.
if (!document.getElementById("sov-global-styles")) {
  const s = document.createElement("style");
  s.id = "sov-global-styles";
  s.textContent = `
    .sov-pipmenu {
      position: fixed; width: 160px; background: #ffffff; border: 1px solid #E4E4E7;
      border-radius: 6px; box-shadow: 0 4px 6px -1px rgba(16,24,40,.10), 0 2px 4px -2px rgba(16,24,40,.10);
      padding: 4px; z-index: 1000; display: none; flex-direction: column;
      font-family: ui-sans-serif, system-ui, sans-serif;
    }
    .sov-pipmenu.open { display: flex; }
    .sov-pipmenu-row {
      display: inline-flex; align-items: center; gap: 8px; width: 100%;
      text-align: left; font: 500 13px/1 ui-sans-serif, system-ui, sans-serif;
      color: #191937; background: transparent; border: none; border-radius: 6px;
      padding: 7px 10px; cursor: pointer; transition: background 0.1s ease, color 0.1s ease;
    }
    .sov-pipmenu-row:hover { background: #f4f4f5; color: #191937; }
    .sov-pipmenu-row svg { flex-shrink: 0; color: #6A6A7E; }
    .sov-tip-global {
      position: fixed; background: #191937; color: #fff;
      font: 500 12px/1.4 ui-sans-serif, system-ui, sans-serif;
      padding: 7px 10px; border-radius: 6px;
      max-width: 280px; white-space: normal;
      pointer-events: none; opacity: 0; transition: opacity 0.12s ease;
      z-index: 1001; box-shadow: 0 6px 16px rgba(16,24,40,.25);
    }
    .sov-tip-global.show { opacity: 1; }
  `;
  document.head.appendChild(s);
}

function render({ model, el }) {
  el.className = "sov-root";
  el.style.position = "relative";

  function toast(msg) {
    const t = document.createElement("div");
    t.className = "sov-toast";
    t.textContent = "Copied: " + msg;
    el.appendChild(t);
    requestAnimationFrame(() => t.classList.add("show"));
    setTimeout(() => { t.classList.remove("show"); setTimeout(() => t.remove(), 250); }, 1500);
  }

  // Dark split-copy popover anchored to `trigger`, appended to <body> so the
  // card's overflow never clips it. Flips above the trigger near the viewport bottom.
  function makeMenu(trigger, items) {
    const menu = document.createElement("div");
    menu.className = "sov-pipmenu";
    menu.innerHTML = items.map((it) =>
      '<button class="sov-pipmenu-row" data-action="' + it.action + '">' + it.icon + it.label + '</button>'
    ).join("");
    document.body.appendChild(menu);

    let closeTimer = null;
    function openMenu() {
      clearTimeout(closeTimer);
      menu.classList.add("open");
      const rect = trigger.getBoundingClientRect();
      const menuHeight = menu.offsetHeight || 80;
      const menuWidth = menu.offsetWidth || 170;
      if (rect.right - menuWidth < 8) {
        menu.style.right = ""; menu.style.left = "8px";
      } else {
        menu.style.left = ""; menu.style.right = (window.innerWidth - rect.right) + "px";
      }
      if (rect.bottom + menuHeight > window.innerHeight) {
        menu.style.top = ""; menu.style.bottom = (window.innerHeight - rect.top + 4) + "px";
      } else {
        menu.style.bottom = ""; menu.style.top = (rect.bottom + 4) + "px";
      }
    }
    function scheduleClose() {
      clearTimeout(closeTimer);
      closeTimer = setTimeout(() => menu.classList.remove("open"), 120);
    }
    trigger.addEventListener("mouseenter", openMenu);
    trigger.addEventListener("mouseleave", scheduleClose);
    menu.addEventListener("mouseenter", () => clearTimeout(closeTimer));
    menu.addEventListener("mouseleave", scheduleClose);
    trigger.addEventListener("focus", openMenu);
    trigger.addEventListener("blur", scheduleClose);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") menu.classList.remove("open"); });
    menu.addEventListener("click", (evt) => {
      const row = evt.target.closest("[data-action]");
      if (!row) return;
      const it = items.find((x) => x.action === row.dataset.action);
      menu.classList.remove("open");
      if (it) copyText(it.getText()).then(() => toast(it.toast)).catch(() => {});
    });
  }

  // Custom hover tooltip — fixed in viewport, body-appended so it's never clipped.
  const tip = document.createElement("div");
  tip.className = "sov-tip-global";
  document.body.appendChild(tip);
  function attachTip(elm, text) {
    elm.addEventListener("mouseenter", () => { tip.textContent = text; tip.classList.add("show"); });
    elm.addEventListener("mousemove", (e) => {
      tip.style.left = (e.clientX + 14) + "px";
      tip.style.top = (e.clientY + 16) + "px";
    });
    elm.addEventListener("mouseleave", () => tip.classList.remove("show"));
  }

  function rebuild() {
    el.innerHTML = "";

    const tables = model.get("payload") || [];

    // ---- header row ----
    const hdr = document.createElement("div");
    hdr.className = "sov-header";

    // The pipeline tag (+ its logs/traces copy icon) stands in for a title —
    // no separate "Loaded tables" heading.
    const tags = document.createElement("span");
    tags.className = "sov-tags";

    const pipetag = document.createElement("span");
    pipetag.className = "sov-pill sov-pipetag";
    pipetag.textContent = "sample_shop";
    tags.appendChild(pipetag);

    // Pipeline split-copy button: hover reveals a popover (logs / traces),
    // copying AI-ready run context for the pipeline the user just ran.
    const pcopy = document.createElement("button");
    pcopy.className = "sov-iconbtn";
    pcopy.innerHTML = COPY;
    tags.appendChild(pcopy);
    makeMenu(pcopy, [
      { action: "logs", icon: ICON_LOGS, label: "Copy logs",
        getText: () => model.get("logs") || "[No pipeline logs available]", toast: "pipeline logs" },
      { action: "traces", icon: ICON_TRACES, label: "Copy traces",
        getText: () => model.get("traces") || "[No pipeline trace available]", toast: "pipeline traces" },
    ]);

    hdr.appendChild(tags);
    el.appendChild(hdr);

    // ---- accordion ----
    const list = document.createElement("div");
    list.className = "sov-list";

    const openState = new Array(tables.length).fill(false);
    if (tables.length > 0) openState[0] = true;

    let pickedTable = null;
    let pickedCols = [];
    function buildQuery() {
      const sel = pickedCols.length ? pickedCols.join(", ") : "*";
      return 'SELECT ' + sel + '\nFROM "' + pickedTable + '"\nLIMIT 100';
    }

    function renderList() {
      list.innerHTML = "";
      tables.forEach((tbl, idx) => {
        const isOpen = openState[idx];

        // ---- collapsed row ----
        const item = document.createElement("div");
        item.className = "sov-item" + (isOpen ? " sov-item-open" : "");

        const isSelected = pickedTable === tbl.table;
        const trigger = document.createElement("button");
        trigger.className = "sov-trigger" + (isSelected ? " sov-trigger-selected" : "");
        trigger.setAttribute("aria-expanded", isOpen ? "true" : "false");

        const nameSpan = document.createElement("span");
        nameSpan.className = "sov-tname";
        nameSpan.textContent = tbl.table;

        const meta = document.createElement("span");
        meta.className = "sov-meta";

        const rowBadge = document.createElement("span");
        rowBadge.className = "sov-row-count";
        rowBadge.textContent =
          tbl.rows != null
            ? tbl.rows.toLocaleString() + " rows"
            : "—";

        const chev = document.createElement("span");
        chev.className = "sov-chevron";
        chev.innerHTML = chevron(isOpen);

        meta.appendChild(rowBadge);
        meta.appendChild(chev);

        trigger.appendChild(nameSpan);
        trigger.appendChild(meta);

        trigger.addEventListener("click", () => {
          const wasOpen = openState[idx];
          openState.fill(false);
          openState[idx] = !wasOpen;
          pickedTable = tbl.table;
          pickedCols = [];
          model.set("query_build", buildQuery());
          model.save_changes();
          renderList();
        });

        item.appendChild(trigger);

        // ---- expanded columns ----
        if (isOpen) {
          const cols = document.createElement("div");
          cols.className = "sov-cols";

          (tbl.columns || []).forEach((col) => {
            const row = document.createElement("div");
            const picked = pickedTable === tbl.table && pickedCols.includes(col.name);
            row.className = "sov-col-row" + (picked ? " sov-col-picked" : "");
            row.addEventListener("click", () => {
              if (pickedTable !== tbl.table) {
                pickedTable = tbl.table; pickedCols = [col.name];
              } else {
                const i = pickedCols.indexOf(col.name);
                if (i >= 0) pickedCols.splice(i, 1); else pickedCols.push(col.name);
              }
              model.set("query_build", buildQuery());
              model.save_changes();
              renderList();
            });

            const left = document.createElement("span");
            left.className = "sov-col-left";

            const nameEl = document.createElement("span");
            nameEl.className = "sov-col-name";
            nameEl.textContent = col.name;

            left.appendChild(nameEl);
            if (col.role) {
              // Build the role pill as an element so an FK can carry a hover
              // tooltip with its matching key instead of writing it inline.
              const k = document.createElement("span");
              k.className = "sov-pill " + (col.role === "pk" ? "pill-pk" : "pill-fk");
              k.textContent = col.role.toUpperCase();
              if (col.role === "fk" && col.fk_target) {
                k.classList.add("sov-fk-pill");
                attachTip(k, "→ " + col.fk_target);
              }
              left.appendChild(k);
            }

            const right = document.createElement("span");
            right.className = "sov-col-right";
            right.innerHTML = typePill(col.type);

            row.appendChild(left);
            row.appendChild(right);
            cols.appendChild(row);
          });

          item.appendChild(cols);
        }

        list.appendChild(item);
      });
    }

    renderList();
    el.appendChild(list);
  }

  rebuild();
  model.on("change:payload", rebuild);
}

export default { render };
"""

_CSS = r"""
/* Root is the widget's inner content area.
   Card frame (border, radius, shadow) is provided by the outer wrapper in the
   marimo app — so we strip those here to avoid double-borders. */
.sov-root {
  background: transparent;
  border: none;
  border-radius: 0;
  box-shadow: none;
  padding: 18px 20px;
  box-sizing: border-box;
  font-family: ui-sans-serif, system-ui, sans-serif;
  color: #191937;
}

/* ---- header ---- */
.sov-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
/* pipeline name stands in for the header title — plain text, not a pill
   (compound selector to beat .sov-pill's pill geometry) */
.sov-pill.sov-pipetag {
  background: transparent;
  color: #191937;
  font-size: 16px;
  padding: 0;
  border-radius: 0;
}

/* ---- pill base — exact copy of .se-pill geometry ---- */
/* The explorer uses just two sizes: the 16px tag-title and 13px for everything
   else (names, counts, pills) so the panel content matches the Results table. */
.sov-pill {
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.5;
  padding: 2px 8px;
  border-radius: 6px;
}
/* data-type / materialization tags read as quiet metadata, not bold like the
   semantic PK/FK pills — regular weight and a bright, pale grey so they recede */
.pill-neutral { background: #f5f6f8; color: #6A6A7E; font-weight: 400; }
.pill-indigo  { background: #ECEBF5; color: #5c57c6; }
/* PK/FK use the platform pastel palette (Figma Secondary): aurora-med / dusk-med */
.pill-pk      { background: #a8dee9; color: #191937; }
.pill-fk      { background: #f6b7b3; color: #191937; }

/* ---- accordion list ---- */
.sov-list {
  display: flex;
  flex-direction: column;
  gap: 0;
  max-height: 440px;
  overflow-y: auto;
}

/* ---- trigger button ---- */
.sov-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  background: transparent;
  border: none;
  padding: 8px;
  cursor: pointer;
  text-align: left;
  font-family: ui-sans-serif, system-ui, sans-serif;
  border-radius: 6px;
  transition: background 0.1s ease;
}
.sov-trigger:hover {
  background: #ECEBF5;
}
/* selected = the table currently feeding the query editor */
.sov-trigger-selected .sov-tname { color: #191937; }

.sov-tname {
  font: 400 13px/1.4 ui-sans-serif, system-ui, sans-serif;
  color: #191937;
}

.sov-meta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.sov-row-count {
  font: 400 13px/1.4 ui-sans-serif, system-ui, sans-serif;
  color: #6A6A7E;
}

.sov-chevron {
  color: #6A6A7E;
  display: inline-flex;
  align-items: center;
  transition: color 0.1s ease;
}
.sov-trigger:hover .sov-chevron { color: #6A6A7E; }

/* ---- expanded columns ---- */
/* Indented under the table name so column rows read as subordinate to the
   table they belong to (and never get confused with another table name). */
.sov-cols {
  padding-bottom: 8px;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* column row — exact same geometry as .se-row in schema_explorer.py */
.sov-col-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.1s ease;
}
.sov-col-row:hover { background: #ECEBF5; }
.sov-col-picked { background: color-mix(in oklch, #5c57c6 12%, transparent); }
.sov-col-picked .sov-col-name { color: #5c57c6; font-weight: 600; }

.sov-col-left {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #191937;
  font-size: 13px;
}

.sov-col-name {
  font: 400 13px/1.4 ui-sans-serif, system-ui, sans-serif;
  color: #191937;
}

.sov-col-right {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

/* FK pill carries its matching key on hover (sov-tip-global) — default cursor,
   no question-mark affordance */
.sov-fk-pill { cursor: default; }

/* ---- header copy affordance (logs / traces) ---- */
.sov-tags {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  position: relative;
}
/* shared copy-icon button — resting muted indigo, indigo on hover (same as se-iconbtn) */
.sov-iconbtn {
  border: none; background: transparent; color: #AAA8D4; cursor: pointer;
  padding: 0; width: 24px; height: 24px;
  display: inline-flex; align-items: center; justify-content: center;
  transition: color 0.12s ease;
}
.sov-iconbtn svg { width: 17px; height: 17px; }
.sov-iconbtn:hover { color: #5c57c6; }
.sov-iconbtn:active { color: #191937; }

.sov-toast {
  position: absolute;
  left: 50%; bottom: 16px;
  transform: translateX(-50%);
  background: #191937; color: #fff;
  font: 600 12px/1 ui-sans-serif, system-ui, sans-serif;
  padding: 7px 12px; border-radius: 8px;
  box-shadow: 0 6px 16px rgba(16, 24, 40, 0.2);
  pointer-events: none; opacity: 0; transition: opacity 0.2s ease;
  z-index: 20; white-space: nowrap; max-width: 92%;
}
.sov-toast.show { opacity: 1; }
"""


class SchemaOverview(anywidget.AnyWidget):
    _esm = _ESM
    _css = _CSS

    # List of {table: str, rows: int|None, columns: [{name, type, role, fk_target}]}
    payload = traitlets.List().tag(sync=True)
    # AI-ready run context for the pipeline, copied from the header (logs / traces).
    logs = traitlets.Unicode("").tag(sync=True)
    traces = traitlets.Unicode("").tag(sync=True)
    query_build = traitlets.Unicode("").tag(sync=True)
