"""
Step 2: render structured notes JSON into a standalone handwritten-style
HTML file with REAL text-flow pagination — content continues onto the
next A4-sized page automatically when it doesn't fit, like an actual
document, rather than one fixed box per concept with an internal
scrollbar.

Design choices worth understanding, not just the code:

1. CSS multi-column layout (`columns`), not a JS pagination library. This
   is the key architectural choice here: the browser's own layout engine
   flows continuous HTML content across fixed-width "columns" (our
   A4-sized pages), automatically breaking content that doesn't fit onto
   the next one. No cloning, no DOM manipulation, no third-party library
   internals to debug — this is exactly the kind of native browser
   capability worth using instead of reaching for a library (see
   docs/DECISIONS.md #9 for why a JS pagination library was reverted
   after real, unresolved bugs).

2. Real trade-off, stated honestly: each "page" can no longer be its own
   independently-styled raised card (drop shadow, rounded corners) —
   CSS columns share ONE continuous background across the whole flow.
   The ruled-paper look and red margin line are recreated as repeating
   background patterns (period = one page width) so they land correctly
   on every page anyway; a `column-rule` (a built-in CSS feature for
   exactly this) draws a subtle divider between pages instead.

3. `break-inside: avoid` on each concept/diagram block — a hint to the
   browser to keep a whole concept together on one page where possible.
   It's a hint, not a hard rule: a concept genuinely longer than one full
   page will still split, which is correct, expected behavior for real
   flowing pagination (this is precisely the behavior that was asked
   for — continuation onto the next page — not a bug).

4. `break-after: column` on the title block specifically, so the title
   page still reads as its own first page rather than sharing space with
   the first concept — a deliberate exception to "let everything flow
   freely," since a title immediately followed by unrelated concept text
   on the same page would look wrong.

5. A4 page dimensions in CSS pixels at 72dpi (595 x 842) — the standard
   convention most PDF/print tooling uses for "A4," recognizable and
   consistent.

6. Page-turn motion is explicitly NOT part of this version — deferred
   per docs/ROADMAP.md's Step 2 backlog note and docs/DECISIONS.md #9.
   Navigation here is simple: Prev/Next scrolls exactly one page-width,
   arrow keys do the same. Real curl/flip animation remains a separate,
   later task once this flowing-pagination base is confirmed solid.

7. Mermaid renders via `startOnLoad: true` with no special ordering
   concerns this time — unlike the StPageFlip version, nothing here
   clones or hides DOM elements, so there's no race condition to guard
   against.

8. Everything injected is html.escape()'d, INCLUDING mermaid diagram
   source — Gemini sometimes emits literal "<br/>" inside diagram node
   labels for multi-line text. Unescaped, the browser's HTML parser
   would convert that into a real <br> element before Mermaid ever sees
   it, stripping text Mermaid's own parser needs. Escaped to
   "&lt;br/&gt;", it decodes back to the literal characters in the DOM's
   text content — exactly what Mermaid expects to parse itself.
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
  --page-w: 595px;
  --page-h: 842px;
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

.book-wrap {
  height: 100vh;
  width: 100vw;
  display: flex;
  align-items: center;
  justify-content: center;
}

.book {
  width: var(--page-w);
  height: var(--page-h);
  overflow-x: auto;
  overflow-y: hidden;
  box-shadow: 0 6px 24px rgba(0,0,0,0.25);
}

/* The actual pagination mechanism: content flows continuously and the
   browser breaks it into page-width columns automatically. Two layered
   backgrounds recreate the per-page paper look despite columns sharing
   one continuous background: horizontal ruled lines (repeats vertically,
   looks correct at any page since it only depends on Y position) and a
   red margin line (repeats horizontally with period = one page width,
   so it lands at the same offset on every page). */
.flow {
  columns: 1;
  column-width: var(--page-w);
  column-gap: 0;
  column-rule: 1px dashed rgba(0,0,0,0.15);
  column-fill: auto;
  height: var(--page-h);
  background-color: var(--paper);
  background-image:
    repeating-linear-gradient(
      var(--paper),
      var(--paper) 34px,
      var(--line) 35px
    ),
    repeating-linear-gradient(
      to right,
      transparent 0,
      transparent 40px,
      var(--margin-line) 40px,
      var(--margin-line) 42px,
      transparent 42px,
      transparent var(--page-w)
    );
  padding: 30px 0;
}

.title-block {
  break-after: column;
  padding: 0 30px 0 60px;
}

h1.title {
  font-size: 2em;
  margin: 0 0 8px 0;
  color: var(--accent);
  transform: rotate(-0.4deg);
}

p.overview {
  font-size: 1.05em;
  color: var(--ink-soft);
}

.concept, .diagram-block {
  break-inside: avoid;
  box-decoration-break: clone;
  -webkit-box-decoration-break: clone;
  padding: 0 30px 0 60px;
  margin-bottom: 30px;
}

.concept h2 {
  font-size: 1.4em;
  margin: 0 0 10px 0;
  color: var(--accent);
  transform: rotate(-0.3deg);
}

.field-label {
  font-weight: 700;
  color: var(--accent);
  font-size: 1em;
  margin-top: 10px;
}

.field-body {
  margin: 2px 0 0 4px;
  font-size: 1em;
  line-height: 1.5;
}

.syntax-box {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.82em;
  background: #f4f1e6;
  border: 1px solid #d8d2bd;
  border-left: 4px solid var(--accent);
  border-radius: 3px;
  padding: 8px 12px;
  margin-top: 6px;
  white-space: pre-wrap;
  color: #333;
}

.key-points {
  margin: 4px 0 0 18px;
  padding: 0;
}

.key-points li {
  margin-bottom: 4px;
  font-size: 1em;
}

.diagram-title {
  font-weight: 700;
  font-size: 1.2em;
  margin-bottom: 10px;
  color: var(--accent);
}

pre.mermaid {
  background: #fbfaf3;
  border: 1px solid #d8d2bd;
  border-radius: 6px;
  padding: 10px;
  overflow-x: auto;
  font-size: 0.78em;
}

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

.nav button:disabled { opacity: 0.35; cursor: default; }
.nav .counter { min-width: 70px; text-align: center; }
"""

_NAV_SCRIPT = """
<script>
  const book = document.querySelector('.book');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const counter = document.getElementById('pageCounter');
  const pageStep = book.clientWidth;

  function totalPages() {
    return Math.max(1, Math.round(book.scrollWidth / pageStep));
  }

  function currentPage() {
    return Math.round(book.scrollLeft / pageStep);
  }

  function updateUI() {
    const cur = currentPage();
    const total = totalPages();
    counter.textContent = `Page ${cur + 1} / ${total}`;
    prevBtn.disabled = cur <= 0;
    nextBtn.disabled = cur >= total - 1;
  }

  function goTo(index) {
    book.scrollTo({ left: index * pageStep, behavior: 'smooth' });
  }

  prevBtn.addEventListener('click', () => goTo(currentPage() - 1));
  nextBtn.addEventListener('click', () => goTo(currentPage() + 1));

  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') goTo(currentPage() + 1);
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') goTo(currentPage() - 1);
  });

  let scrollTimeout;
  book.addEventListener('scroll', () => {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(updateUI, 80);
  });

  updateUI();
</script>
"""


def _esc(text: str) -> str:
    return html.escape(text or "")


def _title_block(data: dict) -> str:
    return f"""
    <div class="title-block">
      <h1 class="title">{_esc(data['title'])}</h1>
      <p class="overview">{_esc(data['overview'])}</p>
    </div>
    """


def _concept_block(concept: dict) -> str:
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
    <div class="concept">
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
    """


def _diagram_block(diagram: dict, index: int) -> str:
    mermaid_src = _esc(diagram["mermaid"])
    return f"""
    <div class="diagram-block">
      <div class="diagram-title">[{index}] {_esc(diagram['title'])}</div>
      <pre class="mermaid">{mermaid_src}</pre>
    </div>
    """


def render_notes_html(data: dict) -> str:
    blocks = [_title_block(data)]
    blocks += [_concept_block(c) for c in data["concepts"]]
    blocks += [_diagram_block(d, i) for i, d in enumerate(data["diagrams"], 1)]
    blocks_html = "".join(blocks)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{_esc(data['title'])}</title>
{_FONT_LINK}
<style>{_CSS}</style>
</head>
<body>
  <div class="book-wrap">
    <div class="book">
      <div class="flow">
        {blocks_html}
      </div>
    </div>
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

    print(f"Rendered -> {output_path} (flowing pagination, page count determined by content)")


if __name__ == "__main__":
    main()