"""
Step 2: render structured notes JSON into a standalone, paginated
handwritten-style HTML file — real flip-through pages, not one long scroll.

Design choices worth understanding, not just the code:

1. Standalone .html output, no server. Fastest possible loop for iterating
   on visual design — generate, open in browser, tweak CSS, regenerate.
   A server/frontend framework is Step 5+ territory (see docs/ROADMAP.md).

2. Pagination unit = one concept per page, one diagram per page, title
   page first. Simple and deterministic regardless of content length —
   no fragile text-measurement/reflow logic needed to pack variable-length
   content into fixed page heights. The trade-off: a genuinely huge
   concept could overflow its page and need to scroll within that page.
   Acceptable for now; revisit if it actually happens on real notes.

3. "Flipping" is CSS scroll-snap, not display:none page-swapping. All
   pages stay in normal document flow; Prev/Next just smooth-scrolls to
   the next page's position. This matters specifically because of
   Mermaid: it measures the DOM element it's rendering into when the
   page loads. A diagram sitting inside a display:none container would
   get measured as zero-size and render broken. Scroll-snap never hides
   anything, so every diagram is always a real, measurable element.

4. Two fonts, not one. "Kalam" (handwriting) for prose, a monospace
   stack for code syntax — a single handwriting font for code is
   genuinely hard to read regardless of how charming it looks.

5. Mermaid's built-in `look: "handDrawn"` config — a rough.js-based
   sketchy rendering mode Mermaid ships since v10.5+, instead of us
   hand-rolling wobble/sketch effects ourselves.

6. Everything injected into the HTML is html.escape()'d first, INCLUDING
   mermaid diagram source. Gemini sometimes emits literal "<br/>" inside
   diagram node labels for multi-line text. Unescaped, the browser's HTML
   parser would convert that into a real <br> element before Mermaid ever
   sees it, stripping the text Mermaid's own parser needs. Escaped to
   "&lt;br/&gt;", the browser treats it as plain text, which decodes back
   to the literal characters "<br/>" in the DOM's text content — exactly
   what Mermaid expects to parse itself.
"""

import html
import json
import sys
from pathlib import Path

_FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=Kalam:wght@400;700'
    '&display=swap" rel="stylesheet">'
)

_MERMAID_SCRIPT = (
    '<script type="module">'
    "import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';"
    "mermaid.initialize({ startOnLoad: true, look: 'handDrawn', theme: 'neutral' });"
    "</script>"
)

_CSS = """
:root {
  --paper: #fdfcf3;
  --ink: #2b2b2b;
  --ink-soft: #45494a;
  --line: #b9d4e8;
  --margin-line: #e2a3a3;
  --accent: #2c5f7c;
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  height: 100%;
  overflow: hidden;
  background: #e7e2d6;
  font-family: 'Kalam', cursive;
  color: var(--ink);
}

/* Scroll-snap container — this IS the "book". Each .sheet inside it is
   one page; navigating snaps to whichever sheet is next, left-to-right,
   like actually turning pages rather than scrolling down a list. */
.book {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: row;
  overflow-x: scroll;
  overflow-y: hidden;
  scroll-snap-type: x mandatory;
}

.sheet {
  flex: 0 0 100vw;
  height: 100vh;
  scroll-snap-align: start;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 30px 20px;
}

.sheet-inner {
  max-width: 780px;
  width: 100%;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
  background:
    repeating-linear-gradient(
      var(--paper),
      var(--paper) 34px,
      var(--line) 35px
    );
  background-attachment: local;
  border-radius: 4px;
  box-shadow: 0 6px 24px rgba(0,0,0,0.18);
  padding: 44px 36px 44px 66px;
  position: relative;
}

.sheet-inner::before {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  left: 42px;
  width: 2px;
  background: var(--margin-line);
  opacity: 0.6;
}

h1.title {
  font-size: 2.1em;
  margin: 0 0 4px 0;
  color: var(--accent);
  transform: rotate(-0.4deg);
}

p.overview {
  font-size: 1.15em;
  color: var(--ink-soft);
  margin-top: 20px;
}

.concept h2 {
  font-size: 1.6em;
  margin: 0 0 14px 0;
  color: var(--accent);
  display: inline-block;
  transform: rotate(-0.3deg);
}

.field-label {
  font-weight: 700;
  color: var(--accent);
  font-size: 1.05em;
  margin-top: 14px;
}

.field-body {
  margin: 2px 0 0 4px;
  font-size: 1.08em;
  line-height: 1.55;
}

.syntax-box {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.9em;
  background: #f4f1e6;
  border: 1px solid #d8d2bd;
  border-left: 4px solid var(--accent);
  border-radius: 3px;
  padding: 10px 14px;
  margin-top: 6px;
  white-space: pre-wrap;
  color: #333;
}

.key-points {
  margin: 4px 0 0 20px;
  padding: 0;
}

.key-points li {
  margin-bottom: 4px;
  font-size: 1.08em;
}

.diagram-title {
  font-weight: 700;
  font-size: 1.4em;
  margin-bottom: 14px;
  color: var(--accent);
  transform: rotate(-0.3deg);
}

pre.mermaid {
  background: #fbfaf3;
  border: 1px solid #d8d2bd;
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
}

/* Nav bar — fixed, sits above the book */
.nav {
  position: fixed;
  bottom: 18px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 16px;
  background: rgba(43, 43, 43, 0.85);
  color: #fdfcf3;
  padding: 10px 20px;
  border-radius: 999px;
  font-family: 'Kalam', cursive;
  font-size: 1em;
  z-index: 10;
  box-shadow: 0 4px 14px rgba(0,0,0,0.25);
}

.nav button {
  background: none;
  border: none;
  color: #fdfcf3;
  font-family: 'Kalam', cursive;
  font-size: 1.1em;
  cursor: pointer;
  padding: 2px 8px;
}

.nav button:disabled {
  opacity: 0.35;
  cursor: default;
}

.nav .counter {
  min-width: 70px;
  text-align: center;
}
"""

_NAV_SCRIPT = """
<script>
  const book = document.querySelector('.book');
  const sheets = Array.from(document.querySelectorAll('.sheet'));
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const counter = document.getElementById('pageCounter');
  let current = 0;

  function updateUI() {
    counter.textContent = `Page ${current + 1} / ${sheets.length}`;
    prevBtn.disabled = current === 0;
    nextBtn.disabled = current === sheets.length - 1;
  }

  function goTo(index) {
    if (index < 0 || index >= sheets.length) return;
    current = index;
    sheets[current].scrollIntoView({ behavior: 'smooth', inline: 'start', block: 'nearest' });
    updateUI();
  }

  prevBtn.addEventListener('click', () => goTo(current - 1));
  nextBtn.addEventListener('click', () => goTo(current + 1));

  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') goTo(current + 1);
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') goTo(current - 1);
  });

  // Keep the counter/buttons in sync if the user scrolls manually
  // instead of clicking Prev/Next.
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        current = sheets.indexOf(entry.target);
        updateUI();
      }
    });
  }, { root: book, threshold: 0.6 });

  sheets.forEach((s) => observer.observe(s));

  updateUI();
</script>
"""


def _esc(text: str) -> str:
    return html.escape(text or "")


def _title_page(data: dict) -> str:
    return f"""
    <section class="sheet">
      <div class="sheet-inner">
        <h1 class="title">{_esc(data['title'])}</h1>
        <p class="overview">{_esc(data['overview'])}</p>
      </div>
    </section>
    """


def _concept_page(concept: dict) -> str:
    syntax = concept.get("syntax", "")
    syntax_html = (
        f'<div class="field-label">Syntax / usage</div>'
        f'<div class="syntax-box">{_esc(syntax)}</div>'
        if syntax
        else ""
    )
    key_points_html = "".join(
        f"<li>{_esc(kp)}</li>" for kp in concept.get("key_points", [])
    )

    return f"""
    <section class="sheet">
      <div class="sheet-inner concept">
        <h2>{_esc(concept['name'])}</h2>

        <div class="field-label">What it is</div>
        <div class="field-body">{_esc(concept['what_it_is'])}</div>

        <div class="field-label">How it works</div>
        <div class="field-body">{_esc(concept['how_it_works'])}</div>

        {syntax_html}

        <div class="field-label">Key points</div>
        <ul class="key-points">{key_points_html}</ul>

        <div class="field-label">When to use</div>
        <div class="field-body">{_esc(concept['when_to_use'])}</div>
      </div>
    </section>
    """


def _diagram_page(diagram: dict, index: int) -> str:
    # Mermaid source escaped too — see module docstring point 6 for why.
    mermaid_src = _esc(diagram["mermaid"])
    return f"""
    <section class="sheet">
      <div class="sheet-inner">
        <div class="diagram-title">[{index}] {_esc(diagram['title'])}</div>
        <pre class="mermaid">{mermaid_src}</pre>
      </div>
    </section>
    """


def render_notes_html(data: dict) -> str:
    pages = [_title_page(data)]
    pages += [_concept_page(c) for c in data["concepts"]]
    pages += [
        _diagram_page(d, i) for i, d in enumerate(data["diagrams"], 1)
    ]
    pages_html = "".join(pages)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{_esc(data['title'])}</title>
{_FONT_LINK}
<style>{_CSS}</style>
</head>
<body>
  <div class="book">
    {pages_html}
  </div>

  <div class="nav">
    <button id="prevBtn">&larr; Prev</button>
    <span class="counter" id="pageCounter"></span>
    <button id="nextBtn">Next &rarr;</button>
  </div>

{_MERMAID_SCRIPT}
{_NAV_SCRIPT}
</body>
</html>
"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/render/notes_renderer.py <path-to-notes.json> [output.html]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output") / "note.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    html_out = render_notes_html(data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"Rendered -> {output_path} ({len(data['concepts']) + len(data['diagrams']) + 1} pages)")


if __name__ == "__main__":
    main()