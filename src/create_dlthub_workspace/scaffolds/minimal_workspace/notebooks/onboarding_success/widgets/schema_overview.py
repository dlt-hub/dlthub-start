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

// Inject the body-appended hover-tooltip styles once per page load.
if (!document.getElementById("sov-global-styles")) {
  const s = document.createElement("style");
  s.id = "sov-global-styles";
  s.textContent = `
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

    // The pipeline tag stands in for a title — no separate "Loaded tables" heading.
    const tags = document.createElement("span");
    tags.className = "sov-tags";

    const pipetag = document.createElement("span");
    pipetag.className = "sov-pill sov-pipetag";
    pipetag.textContent = "sample_shop";
    tags.appendChild(pipetag);

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

.sov-tags {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  position: relative;
}
"""


class SchemaOverview(anywidget.AnyWidget):
    _esm = _ESM
    _css = _CSS

    # List of {table: str, rows: int|None, columns: [{name, type, role, fk_target}]}
    payload = traitlets.List().tag(sync=True)
    query_build = traitlets.Unicode("").tag(sync=True)
