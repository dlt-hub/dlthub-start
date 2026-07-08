"""A styled action button (anywidget) on the dlthub palette.

Replaces marimo's default buttons (which can't be themed - shadow DOM) so the
query controls match the rest of the design. Each click increments `clicks`,
which marimo treats as a reactive value.

With `route` set, a click instead posts `{type: "dlthub:navigate", route}` to
the embedding dltHub app, which validates the route against its allowlist and
navigates for us — the iframe sandbox blocks the notebook from navigating
anywhere itself. No-op when nothing is listening (standalone marimo).
"""

from __future__ import annotations

import anywidget
import traitlets

_ESM = r"""
const ICONS = {
  run: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
    ' stroke-linecap="round" stroke-linejoin="round">' +
    '<polygon points="6 3 20 12 6 21 6 3"/></svg>',
  arrow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
    ' stroke-linecap="round" stroke-linejoin="round">' +
    '<line x1="5" y1="12" x2="19" y2="12"/>' +
    '<polyline points="12 5 19 12 12 19"/></svg>',
};

function render({ model, el }) {
  const btn = document.createElement("button");
  const variant = model.get("variant") || "secondary";
  const size = model.get("size") || "md";
  btn.className = "dlt-btn dlt-btn-" + variant + (size === "lg" ? " dlt-btn-lg" : "");
  const ic = ICONS[model.get("icon")] || "";
  btn.innerHTML = ic + "<span>" + (model.get("label") || "") + "</span>";
  btn.addEventListener("click", () => {
    const route = model.get("route");
    if (route) {
      // "*" is safe: the message carries no data, only a route name the
      // parent checks against its own allowlist. No clicks sync — nothing
      // reads it, and the trait change would re-run dependent cells.
      if (window.parent !== window) {
        window.parent.postMessage({ type: "dlthub:navigate", route: route }, "*");
      }
      return;
    }
    model.set("clicks", (model.get("clicks") || 0) + 1);
    model.save_changes();
  });
  el.appendChild(btn);
}
export default { render };
"""

_CSS = r"""
.dlt-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font: 600 14px/1 ui-sans-serif, system-ui, sans-serif;
  border-radius: 6px;
  padding: 9px 16px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.dlt-btn svg { width: 14px; height: 14px; }
.dlt-btn-lg { font-size: 16px; padding: 12px 24px; gap: 9px; }
.dlt-btn-lg svg { width: 16px; height: 16px; }
.dlt-btn-primary { background: #5c57c6; color: #fff; border-color: #5c57c6; }
.dlt-btn-primary:hover { background: #4b3fb0; border-color: #4b3fb0; }
.dlt-btn-start { background: #36A83D; color: #fff; border-color: #36A83D; }
.dlt-btn-start:hover { background: #2F9D38; border-color: #2F9D38; }
.dlt-btn-secondary {
  background: #ecedf1; color: #191937; border-color: #E4E4E7;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
}
.dlt-btn-secondary:hover { background: #ECEBF5; border-color: #AAA8D4; }
.dlt-btn-ghost {
  background: transparent; color: #5c57c6; border-color: transparent;
}
.dlt-btn-ghost:hover { background: #ECEBF5; border-color: transparent; }
"""


class ActionButton(anywidget.AnyWidget):
    _esm = _ESM
    _css = _CSS

    label = traitlets.Unicode("").tag(sync=True)
    variant = traitlets.Unicode("secondary").tag(sync=True)
    icon = traitlets.Unicode("").tag(sync=True)
    size = traitlets.Unicode("md").tag(sync=True)
    route = traitlets.Unicode("").tag(sync=True)
    clicks = traitlets.Int(0).tag(sync=True)
