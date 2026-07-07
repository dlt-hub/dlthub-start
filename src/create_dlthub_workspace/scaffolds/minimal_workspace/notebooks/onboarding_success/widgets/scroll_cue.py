"""Invisible widget that floats a down-arrow when there's content below the fold
and smooth-scrolls to the bottom on click. Styled via onboarding_shell.css
(.dlt-scroll-cue).

marimo's run-mode app scrolls an inner container, not the window, so we detect
the tallest scrollable element instead of assuming the document scrolls.
"""

from __future__ import annotations

import anywidget

_ESM = r"""
function render({ el }) {
  el.style.display = "none";
  if (window.__dltScrollCueBound) return;
  window.__dltScrollCueBound = true;

  const cue = document.createElement("button");
  cue.type = "button";
  cue.className = "dlt-scroll-cue";
  cue.setAttribute("aria-label", "Scroll down");
  cue.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"' +
    ' stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>';
  document.body.appendChild(cue);

  let scroller = document.scrollingElement || document.documentElement;
  function detect() {
    const se = document.scrollingElement || document.documentElement;
    if (se && se.scrollHeight - se.clientHeight > 4) { scroller = se; return; }
    let best = null, bestH = 0;
    for (const e of document.querySelectorAll("body *")) {
      const st = getComputedStyle(e);
      if (/(auto|scroll)/.test(st.overflowY)
          && e.scrollHeight - e.clientHeight > 4
          && e.clientHeight > bestH) {
        best = e; bestH = e.clientHeight;
      }
    }
    if (best) scroller = best;
  }
  function update() {
    const target = document.querySelector(".dlt-next-anchor");
    if (!target) { cue.classList.remove("show"); return; }
    const r = target.getBoundingClientRect();
    cue.classList.toggle("show", r.top > window.innerHeight - 12);
  }

  cue.addEventListener("click", () => {
    scroller.scrollTo({ top: scroller.scrollHeight, behavior: "smooth" });
  });
  window.addEventListener("scroll", update, true);  // capture: catch inner scrolls
  window.addEventListener("resize", () => { detect(); update(); });
  setInterval(() => { detect(); update(); }, 500);  // catch reactive layout changes
  detect(); update();
}
export default { render };
"""


class ScrollCue(anywidget.AnyWidget):
    _esm = _ESM
    _css = ""
