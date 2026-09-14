"""
Step 3: bookshelf grid — reads the library index and generates a grid of
book covers, each linking to that video's already-rendered note page.

Deliberate separation of concerns: this script does NOT render note
content itself — it only lists what's in the library and links to pages
notes_renderer.py already produced (see src/main.py's auto-render step,
which writes each note to output/notes/<video_id>.html). If a rendering
bug shows up, you know to look in notes_renderer.py, not here, and vice
versa. Mixing the two would make bugs harder to isolate.

No real cover art exists (no thumbnails, no generated images), so each
book gets a deterministic color from a fixed palette based on a hash of
its video_id. Deterministic matters here specifically: the same video
should always get the same color across regenerations, otherwise the
shelf visually "shuffles" every time you rebuild it for no reason, which
would make it harder to recognize books at a glance over time.
"""

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from library.library_index import LibraryIndex

_FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=Kalam:wght@400;700'
    '&display=swap" rel="stylesheet">'
)

# Muted, notebook-adjacent palette — not primary-color-loud, so the shelf
# still feels like it belongs with the handwritten note aesthetic rather
# than looking like an unrelated UI kit dropped on top of it.
_SPINE_COLORS = [
    "#2c5f7c", "#7c3f2c", "#3f7c4a", "#6b4c8a",
    "#8a5a2c", "#2c6b6b", "#7c2c4f", "#4a5a2c",
]

_CSS = """
* { box-sizing: border-box; }

body {
  margin: 0;
  padding: 50px 30px;
  background: #e7e2d6;
  font-family: 'Kalam', cursive;
  color: #2b2b2b;
}

h1.shelf-title {
  text-align: center;
  font-size: 2.4em;
  color: #2b2b2b;
  margin-bottom: 6px;
}

p.shelf-subtitle {
  text-align: center;
  color: #6b6b6b;
  margin-bottom: 40px;
}

.shelf {
  max-width: 1100px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 26px;
  align-items: end;
}

.book {
  display: block;
  text-decoration: none;
  color: inherit;
  perspective: 400px;
}

.spine {
  /* A4 ratio (595:842, same as the actual note pages) via aspect-ratio
     rather than a fixed height — this way the card stays true to real
     page proportions no matter how wide the grid makes each column,
     instead of drifting off-ratio at different screen widths. */
  aspect-ratio: 595 / 842;
  width: 100%;
  border-radius: 4px 8px 8px 4px;
  box-shadow:
    inset 4px 0 0 rgba(0,0,0,0.15),
    0 6px 14px rgba(0,0,0,0.25);
  padding: 16px 12px;
  display: flex;
  align-items: flex-start;
  color: #fdfcf3;
  font-size: 1.05em;
  line-height: 1.3;
  transition: transform 0.15s ease;
}

.book:hover .spine {
  transform: translateY(-6px) rotate(-1deg);
}

.empty-shelf {
  text-align: center;
  color: #6b6b6b;
  font-size: 1.2em;
  margin-top: 60px;
}

.add-form {
  max-width: 600px;
  margin: 0 auto 40px auto;
  display: flex;
  gap: 10px;
}

.add-form input {
  flex: 1;
  font-family: 'Kalam', cursive;
  font-size: 1.05em;
  padding: 10px 14px;
  border: 2px solid #c9c2ab;
  border-radius: 8px;
  background: #fdfcf3;
  color: #2b2b2b;
}

.add-form input:focus {
  outline: none;
  border-color: var(--accent, #2c5f7c);
}

.add-form button {
  font-family: 'Kalam', cursive;
  font-size: 1.05em;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: #2c5f7c;
  color: #fdfcf3;
  cursor: pointer;
}

.add-form button:disabled {
  opacity: 0.5;
  cursor: default;
}

.add-status {
  max-width: 600px;
  margin: -20px auto 30px auto;
  text-align: center;
  font-size: 0.95em;
  min-height: 1.4em;
}

.add-status.error { color: #8a2c2c; }
.add-status.working { color: #6b6b6b; }
"""


def _esc(text: str) -> str:
    return html.escape(text or "")


def _color_for(video_id: str) -> str:
    # Simple deterministic hash -> palette index. Doesn't need to be
    # cryptographically anything, just stable and reasonably spread out.
    index = sum(ord(c) for c in video_id) % len(_SPINE_COLORS)
    return _SPINE_COLORS[index]


def _book_card(entry: dict, href_fmt: str) -> str:
    video_id = entry["video_id"]
    title = entry["title"]
    color = _color_for(video_id)
    href = href_fmt.format(video_id=video_id)

    return f"""
    <a class="book" href="{_esc(href)}">
      <div class="spine" style="background:{color};">{_esc(title)}</div>
    </a>
    """


_ADD_FORM_SCRIPT = """
<script>
  const form = document.getElementById('addForm');
  const input = document.getElementById('videoUrl');
  const button = document.getElementById('addBtn');
  const status = document.getElementById('addStatus');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = input.value.trim();
    if (!url) return;

    button.disabled = true;
    status.className = 'add-status working';
    // Gemini has to actually watch the video before responding, which
    // can genuinely take a while for a real lecture — this message
    // exists specifically so the person doesn't think it's frozen or
    // broken during that wait.
    status.textContent = 'Generating notes... this can take a minute for longer videos.';

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Generation failed.');
      }

      status.className = 'add-status';
      status.textContent = `Added "${data.title}" — refreshing shelf...`;
      window.location.reload();
    } catch (err) {
      status.className = 'add-status error';
      status.textContent = err.message;
      button.disabled = false;
    }
  });
</script>
"""


def render_shelf_html(entries: list, href_fmt: str = "notes/{video_id}.html") -> str:
    """
    href_fmt controls how book links are built — defaults to the static
    file layout (src/main.py writes each note to output/notes/<id>.html).
    The Step 5 FastAPI app passes "/notes/{video_id}" instead, since it
    serves notes as dynamic routes rather than files on disk. Keeping
    this as a parameter rather than hardcoding either format means this
    same render function works unchanged for both the static CLI
    workflow and the web app.

    The add-video form (paste a URL, POST to /api/generate) only
    actually functions when this page is served by the FastAPI app —
    that endpoint doesn't exist for the static-file CLI workflow. It's
    included unconditionally anyway: harmless to show in static mode
    (submitting just fails with a network error), and this page's real
    purpose going forward is being served by the app, not opened as a
    bare file — see docs/ROADMAP.md Step 6.
    """
    if not entries:
        body = '<p class="empty-shelf">No books yet — generate some notes first.</p>'
    else:
        cards = "".join(_book_card(e, href_fmt) for e in entries)
        body = f'<div class="shelf">{cards}</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Virtual Shelf</title>
{_FONT_LINK}
<style>{_CSS}</style>
</head>
<body>
  <h1 class="shelf-title">Virtual Shelf</h1>
  <p class="shelf-subtitle">{len(entries)} book{'s' if len(entries) != 1 else ''} on the shelf</p>

  <form class="add-form" id="addForm">
    <input type="url" id="videoUrl" placeholder="Paste a YouTube lecture link..." required>
    <button type="submit" id="addBtn">Add to Shelf</button>
  </form>
  <p class="add-status" id="addStatus"></p>

  {body}
{_ADD_FORM_SCRIPT}
</body>
</html>
"""


def main():
    library = LibraryIndex(path="./cache/library.json")
    entries = library.list_all()

    html_out = render_shelf_html(entries)

    out_path = Path("output") / "shelf.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"Rendered shelf -> {out_path} ({len(entries)} books)")


if __name__ == "__main__":
    main()