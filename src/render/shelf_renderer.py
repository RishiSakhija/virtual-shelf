"""
Step 3 (extended): a personal-library model — a home page listing named
shelves as folders (subjects like "Machine Learning" or "AI & Agents"),
each opening to that shelf's own grid of books, rather than one flat
list of every video ever generated.

Shelf assignment is fully manual (decided [this session]): the person
types the shelf name themselves when adding a video — no auto-detection.
A datalist of existing shelf names is offered as a convenience so
reusing a name is easy, but typing a brand new one always works too;
that's what actually creates a shelf, since shelves aren't a separate
stored entity (see library_index.py) — a shelf exists exactly when one
or more entries reference it.

Deliberate separation of concerns unchanged from the original version:
this module does NOT render note content — only library/shelf structure,
linking to pages notes_renderer.py already produced.
"""

import html
import re
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

h1.page-title {
  text-align: center;
  font-size: 2.4em;
  color: #2b2b2b;
  margin-bottom: 6px;
}

p.page-subtitle {
  text-align: center;
  color: #6b6b6b;
  margin-bottom: 30px;
}

.back-link {
  display: block;
  text-align: center;
  color: #2c5f7c;
  text-decoration: none;
  margin-bottom: 20px;
  font-size: 1.05em;
}

.back-link:hover { text-decoration: underline; }

.grid {
  max-width: 1100px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 26px;
  align-items: end;
}

.card-link {
  display: block;
  text-decoration: none;
  color: inherit;
}

.spine, .folder {
  aspect-ratio: 595 / 842;
  width: 100%;
  border-radius: 4px 8px 8px 4px;
  box-shadow:
    inset 4px 0 0 rgba(0,0,0,0.15),
    0 6px 14px rgba(0,0,0,0.25);
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  color: #fdfcf3;
  font-size: 1.05em;
  line-height: 1.3;
  transition: transform 0.15s ease;
}

.card-link:hover .spine,
.card-link:hover .folder {
  transform: translateY(-6px) rotate(-1deg);
}

.folder .folder-icon {
  font-size: 2em;
  margin-bottom: 10px;
  align-self: flex-start;
}

.folder .folder-count {
  font-size: 0.85em;
  opacity: 0.85;
}

.empty-state {
  text-align: center;
  color: #6b6b6b;
  font-size: 1.2em;
  margin-top: 60px;
}

.add-form {
  max-width: 600px;
  margin: 0 auto 20px auto;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.add-form input {
  flex: 1;
  min-width: 140px;
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
  border-color: #2c5f7c;
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

.add-form button:disabled { opacity: 0.5; cursor: default; }

.add-status {
  max-width: 600px;
  margin: 0 auto 30px auto;
  text-align: center;
  font-size: 0.95em;
  min-height: 1.4em;
}

.add-status.error { color: #8a2c2c; }
.add-status.working { color: #6b6b6b; }

.grid-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.card-actions button {
  background: none;
  border: 1px solid #b3ab90;
  border-radius: 6px;
  font-family: 'Kalam', cursive;
  font-size: 0.85em;
  color: #6b6b6b;
  padding: 3px 8px;
  cursor: pointer;
}

.card-actions button:hover {
  background: #dcd5bd;
}
"""


def _esc(text: str) -> str:
    return html.escape(text or "")


def _color_for(key: str) -> str:
    # Simple deterministic hash -> palette index. Doesn't need to be
    # cryptographically anything, just stable and reasonably spread out.
    index = sum(ord(c) for c in key) % len(_SPINE_COLORS)
    return _SPINE_COLORS[index]


def slugify_shelf(name: str) -> str:
    # For the shelf URL segment — "AI & Agents" -> "ai-agents". Doesn't
    # need to be reversible; the actual shelf NAME used for filtering
    # library entries is passed separately, this is just for a
    # readable-ish URL.
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "shelf"


def _book_card(entry: dict, href_fmt: str) -> str:
    video_id = entry["video_id"]
    title = entry["title"]
    color = _color_for(video_id)
    href = href_fmt.format(video_id=video_id)

    # Action button is a SIBLING of the link, not nested inside it —
    # nesting a clickable button inside an <a> causes both to fire on
    # click (the link navigates AND the button's handler runs), which is
    # exactly the kind of bug that's annoying to debug after the fact.
    return f"""
    <div class="grid-item">
      <a class="card-link" href="{_esc(href)}">
        <div class="spine" style="background:{color};">{_esc(title)}</div>
      </a>
      <div class="card-actions">
        <button onclick="moveBook('{_esc(video_id)}')">Move</button>
      </div>
    </div>
    """


def _folder_card(shelf: dict, href_fmt: str) -> str:
    name = shelf["name"]
    count = shelf["count"]
    color = _color_for(name)
    href = href_fmt.format(shelf_slug=slugify_shelf(name), shelf_name=name)

    return f"""
    <div class="grid-item">
      <a class="card-link" href="{_esc(href)}">
        <div class="folder" style="background:{color};">
          <div class="folder-icon">&#128218;</div>
          <div>{_esc(name)}</div>
          <div class="folder-count">{count} book{'s' if count != 1 else ''}</div>
        </div>
      </a>
      <div class="card-actions">
        <button onclick="renameShelf('{_esc(name)}')">Rename</button>
        <button onclick="deleteShelf('{_esc(name)}')">Delete</button>
      </div>
    </div>
    """


_MANAGE_SCRIPT = """
<script>
  // Functional-first pass — plain browser prompt()/confirm() dialogs,
  // not custom modals. Visual polish is a deliberately separate later
  // task once these operations are confirmed working end-to-end.

  async function renameShelf(oldName) {
    const newName = prompt(`Rename shelf "${oldName}" to:`, oldName);
    if (!newName || !newName.trim() || newName.trim() === oldName) return;
    const res = await fetch('/api/shelf/rename', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_name: oldName, new_name: newName.trim() }),
    });
    if (res.ok) { window.location.reload(); }
    else { alert('Rename failed.'); }
  }

  async function deleteShelf(name) {
    if (!confirm(`Delete shelf "${name}"? Books move to "General" — nothing is actually deleted.`)) return;
    const res = await fetch('/api/shelf/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    if (res.ok) { window.location.reload(); }
    else { alert('Delete failed.'); }
  }

  async function moveBook(videoId) {
    const newShelf = prompt('Move this book to which shelf?');
    if (!newShelf || !newShelf.trim()) return;
    const res = await fetch('/api/book/move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: videoId, new_shelf: newShelf.trim() }),
    });
    if (res.ok) { window.location.reload(); }
    else { alert('Move failed.'); }
  }
</script>
"""


def _add_form_html(shelf_field_html: str) -> str:
    return f"""
    <form class="add-form" id="addForm">
      {shelf_field_html}
      <input type="url" id="videoUrl" placeholder="Paste a YouTube lecture link..." required>
      <button type="submit" id="addBtn">Add</button>
    </form>
    <p class="add-status" id="addStatus"></p>
    """


def _add_form_script() -> str:
    return """
<script>
  const form = document.getElementById('addForm');
  const urlInput = document.getElementById('videoUrl');
  const shelfInput = document.getElementById('shelfName');
  const button = document.getElementById('addBtn');
  const status = document.getElementById('addStatus');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();
    const shelf = shelfInput.value.trim();
    if (!url || !shelf) return;

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
        body: JSON.stringify({ url, shelf }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Generation failed.');
      }

      status.className = 'add-status';
      status.textContent = `Added "${data.title}" to "${shelf}" — refreshing...`;
      window.location.reload();
    } catch (err) {
      status.className = 'add-status error';
      status.textContent = err.message;
      button.disabled = false;
    }
  });
</script>
"""


def render_library_home_html(
    shelves: list, shelf_href_fmt: str = "/shelf/{shelf_slug}"
) -> str:
    """
    The "library room" — every shelf as a folder card, book count shown,
    click through to that shelf's own page. The add-form here has a
    VISIBLE, freely-typed shelf-name field (with a datalist of existing
    names for convenience) since there's no shelf context on this page —
    typing a brand new name is what creates that shelf.
    """
    existing_names = [s["name"] for s in shelves]
    datalist_options = "".join(f'<option value="{_esc(n)}">' for n in existing_names)

    shelf_field_html = f"""
      <input type="text" id="shelfName" list="shelfOptions"
             placeholder="Shelf name (e.g. Machine Learning)" required>
      <datalist id="shelfOptions">{datalist_options}</datalist>
    """

    if not shelves:
        body = '<p class="empty-state">No shelves yet — add your first book above to create one.</p>'
    else:
        cards = "".join(_folder_card(s, shelf_href_fmt) for s in shelves)
        body = f'<div class="grid">{cards}</div>'

    total_books = sum(s["count"] for s in shelves)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Virtual Shelf — Library</title>
{_FONT_LINK}
<style>{_CSS}</style>
</head>
<body>
  <h1 class="page-title">Virtual Shelf</h1>
  <p class="page-subtitle">{len(shelves)} shelf{'ves' if len(shelves) != 1 else ''}, {total_books} book{'s' if total_books != 1 else ''}</p>

  {_add_form_html(shelf_field_html)}

  {body}
{_add_form_script()}
{_MANAGE_SCRIPT}
</body>
</html>
"""


def render_shelf_html(
    entries: list,
    shelf_name: str,
    href_fmt: str = "notes/{video_id}.html",
    home_href: str = "/",
) -> str:
    """
    One shelf's own book grid. The add-form's shelf field is HIDDEN and
    pre-filled with this shelf's name — adding a book from within a
    shelf's page assumes you want it filed here, no retyping needed. To
    file a new book under a different (or new) shelf, use the home
    page's form instead.
    """
    shelf_field_html = f'<input type="hidden" id="shelfName" value="{_esc(shelf_name)}">'

    if not entries:
        body = '<p class="empty-state">No books on this shelf yet — add one above.</p>'
    else:
        cards = "".join(_book_card(e, href_fmt) for e in entries)
        body = f'<div class="grid">{cards}</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{_esc(shelf_name)} — Virtual Shelf</title>
{_FONT_LINK}
<style>{_CSS}</style>
</head>
<body>
  <a class="back-link" href="{_esc(home_href)}">&larr; Back to Library</a>
  <h1 class="page-title">{_esc(shelf_name)}</h1>
  <p class="page-subtitle">{len(entries)} book{'s' if len(entries) != 1 else ''} on this shelf</p>

  {_add_form_html(shelf_field_html)}

  {body}
{_add_form_script()}
{_MANAGE_SCRIPT}
</body>
</html>
"""


def main():
    """
    CLI/static-file path — kept working for local preview, though the
    real personal-library browsing experience (folders, per-shelf pages)
    is what the FastAPI app (Step 5/6) actually serves live. This writes
    one static file per shelf plus a home page, matching the same model.
    """
    library = LibraryIndex(path="./cache/library.json")
    shelves = library.list_shelves()

    out_dir = Path("output")
    out_dir.mkdir(parents=True, exist_ok=True)

    home_html = render_library_home_html(
        shelves, shelf_href_fmt="shelf_{shelf_slug}.html"
    )
    with open(out_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(home_html)

    for shelf in shelves:
        entries = library.list_by_shelf(shelf["name"])
        shelf_html = render_shelf_html(
            entries, shelf["name"], href_fmt="notes/{video_id}.html", home_href="index.html"
        )
        slug = slugify_shelf(shelf["name"])
        with open(out_dir / f"shelf_{slug}.html", "w", encoding="utf-8") as f:
            f.write(shelf_html)

    print(f"Rendered library home + {len(shelves)} shelf page(s) -> {out_dir}/")


if __name__ == "__main__":
    main()