"""Invisible anywidget that wires up copy-to-clipboard for plain HTML buttons.

marimo's HTML renderer strips inline ``onclick`` handlers (it rebuilds the markup
as React elements), so a ``<button onclick=...>`` inside an ``mo.Html`` block never
fires. This widget runs real JS in the page and installs a single delegated click
listener for any ``.dlt-prompt-copy`` button. The button names what to copy via a
``data-copy`` selector; on click we read that element's text, write it to the
clipboard, and flash the button's ``.pb-copy-label`` to "Copied".

It renders nothing visible — drop one instance anywhere on the page.
"""

from __future__ import annotations

import anywidget
import traitlets

_ESM = r"""
// execCommand isn't governed by the clipboard-write permissions policy, so it
// still works inside an iframe where navigator.clipboard.writeText is blocked.
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

// Try the async Clipboard API, but fall back when it's missing OR rejects — e.g.
// a permissions-policy violation inside the dltHub app's iframe.
function copyText(text) {
  if (window.isSecureContext && navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text).catch(() => legacyCopy(text));
  }
  return legacyCopy(text);
}

function render({ el }) {
  el.style.display = "none";
  if (window.__dltClipboardCopyBound) return;
  window.__dltClipboardCopyBound = true;

  document.addEventListener("click", (e) => {
    const btn = e.target.closest && e.target.closest(".dlt-prompt-copy");
    if (!btn) return;
    // data-copy-text wins (lets the visible text use <br> without polluting the
    // clipboard); otherwise read the element named by data-copy.
    let text = btn.getAttribute("data-copy-text");
    if (!text) {
      const sel = btn.getAttribute("data-copy");
      const src = sel && document.querySelector(sel);
      text = src ? src.textContent.trim() : "";
    }
    text = (text || "").trim();
    if (!text) return;
    copyText(text).then(() => {
      const lbl = btn.querySelector(".pb-copy-label");
      btn.classList.add("copied");
      const prev = lbl ? lbl.textContent : "";
      if (lbl) lbl.textContent = "Copied";
      setTimeout(() => {
        btn.classList.remove("copied");
        if (lbl) lbl.textContent = prev;
      }, 1500);
    }).catch(() => {});
  });
}
export default { render };
"""


class ClipboardCopy(anywidget.AnyWidget):
    _esm = _ESM
    _css = ""
