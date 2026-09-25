"""
Grand-library theme: two towering walls of wooden shelves flanking a
warm, glowing central archway (search + add-book + stats), matching a
design reference the user provided — a warm, atmospheric, magical
library interior.

Deliberately different construction from the earlier tree version (see
docs/DECISIONS.md): every element here is a NORMAL in-flow HTML block —
stacked shelf rows in two columns, no absolute positioning, no
procedural bezier curve math. The tree's bugs (branches/shelves
separating on zoom, a flex column collapsing to zero width) all traced
back to either percentage math against an absolutely-positioned-only
container, or SVG scaling quirks. Plain flexbox rows sidestep that whole
class of failure — there's nothing here that can "come apart" at
different zoom levels or shelf counts, because nothing is pinned to a
coordinate system that has to match something else's.

Shelves split alternately into left/right columns (even index -> left,
odd -> right), each column just stacking shelf-row blocks vertically —
arbitrarily many shelves means a taller page, not a broken layout.
"""

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from library.library_index import LibraryIndex

_FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700'
    '&family=Cormorant+Garamond:wght@600;700&display=swap" rel="stylesheet">'
)

_SPINE_COLORS = [
    "#8a2c3d", "#2c5f7c", "#3f7c4a", "#6b4c8a",
    "#c17a2c", "#2c6b6b", "#a54a6b", "#5a7c2c",
]

_CSS = """
* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: 'Poppins', sans-serif;
  background: radial-gradient(ellipse at 50% 0%, #3a2a1a 0%, #1a120b 55%, #0d0906 100%);
  color: #f0e6d0;
  min-height: 100vh;
}

.scene {
  max-width: 1300px;
  margin: 0 auto;
  padding: 30px 24px 60px;
}

.scene-header {
  text-align: center;
  margin-bottom: 30px;
}

.scene-title {
  font-family: 'Cormorant Garamond', serif;
  font-size: 2.6em;
  font-weight: 700;
  margin: 0;
  color: #f4e4c0;
  text-shadow: 0 0 24px rgba(244, 228, 160, 0.35);
}

.scene-subtitle {
  color: #c9b896;
  font-size: 0.95em;
  margin-top: 4px;
}

.nav-strip {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.nav-pill {
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 0.82em;
  text-decoration: none;
  color: #d8c9a8;
  background: rgba(255,255,255,0.06);
}

.nav-pill.active { background: #c17a2c; color: #1a120b; font-weight: 600; }
.nav-pill.disabled { opacity: 0.4; cursor: default; }

.scene-row {
  display: flex;
  gap: 26px;
  align-items: flex-start;
}

.shelf-wall {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.hero-panel {
  flex: 0 0 380px;
  background: radial-gradient(ellipse at 50% 30%, rgba(244,228,160,0.16), rgba(20,14,8,0.0) 70%),
              rgba(30, 21, 13, 0.75);
  border: 1px solid rgba(244,228,160,0.25);
  border-radius: 16px;
  padding: 22px;
  box-shadow: 0 0 60px rgba(244,228,160,0.08), inset 0 0 40px rgba(0,0,0,0.4);
}

.hero-title {
  font-family: 'Cormorant Garamond', serif;
  font-size: 1.3em;
  font-weight: 700;
  color: #f4e4c0;
  margin: 0 0 12px 0;
}

.search-box {
  width: 100%;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid rgba(244,228,160,0.3);
  background: rgba(0,0,0,0.35);
  color: #f0e6d0;
  font-family: 'Poppins', sans-serif;
  font-size: 0.9em;
  margin-bottom: 16px;
}

.search-box::placeholder { color: #a89878; }
.search-box:focus { outline: none; border-color: #c17a2c; }

.add-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.add-form input {
  font-family: 'Poppins', sans-serif;
  font-size: 0.88em;
  padding: 9px 12px;
  border-radius: 8px;
  border: 1px solid rgba(244,228,160,0.25);
  background: rgba(0,0,0,0.3);
  color: #f0e6d0;
}

.add-form input::placeholder { color: #a89878; }
.add-form input:focus { outline: none; border-color: #c17a2c; }

.add-form button {
  font-family: 'Poppins', sans-serif;
  font-weight: 600;
  font-size: 0.9em;
  padding: 9px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(180deg, #d68f3d, #b5701f);
  color: #1a120b;
  cursor: pointer;
}

.add-form button:disabled { opacity: 0.5; cursor: default; }

.add-status {
  font-size: 0.8em;
  min-height: 1.2em;
  margin-bottom: 12px;
  color: #c9b896;
}

.add-status.error { color: #e08a8a; }

.hero-stats {
  display: flex;
  justify-content: space-between;
  font-size: 0.85em;
  color: #d8c9a8;
  padding: 10px 0;
  border-top: 1px solid rgba(244,228,160,0.15);
  border-bottom: 1px solid rgba(244,228,160,0.15);
  margin-bottom: 12px;
}

.hero-stats b { color: #f4e4c0; }

.recent-list { margin-bottom: 6px; }

.recent-item {
  display: block;
  text-decoration: none;
  padding: 6px 0;
  border-bottom: 1px solid rgba(244,228,160,0.08);
}

.recent-title { color: #f0e6d0; font-size: 0.85em; font-weight: 500; }
.recent-shelf { color: #a89878; font-size: 0.78em; }

.back-link {
  display: inline-block;
  color: #d8a44a;
  text-decoration: none;
  margin-bottom: 14px;
  font-size: 0.9em;
}
.back-link:hover { text-decoration: underline; }

/* ---------- Shelf row (wall of shelves, no absolute positioning) ---------- */
.shelf-row { display: block; text-decoration: none; color: inherit; }

.shelf-plaque {
  display: inline-block;
  background: #2a1c10;
  color: #f0e6d0;
  font-size: 0.78em;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 3px;
  margin-bottom: 4px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.4);
}

.shelf-plank {
  background: linear-gradient(180deg, #8a5a2f, #5a3a1d);
  border-radius: 4px;
  box-shadow: 0 8px 14px rgba(0,0,0,0.45), inset 0 -3px 0 rgba(0,0,0,0.25);
  padding: 10px 10px 0 10px;
  display: flex;
  align-items: flex-end;
  gap: 4px;
  min-height: 64px;
  overflow: hidden;
  position: relative;
}

.mini-spine {
  width: 14px;
  border-radius: 2px 2px 0 0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.3);
}

.leaf-accent {
  position: absolute;
  top: -8px;
  font-size: 1.1em;
  opacity: 0.8;
}

.shelf-count {
  font-size: 0.72em;
  color: #a89878;
  margin-top: 4px;
}

.shelf-actions {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}

.shelf-actions button {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(244,228,160,0.2);
  border-radius: 5px;
  font-family: 'Poppins', sans-serif;
  font-size: 0.68em;
  color: #d8c9a8;
  padding: 2px 7px;
  cursor: pointer;
}
.shelf-actions button:hover { background: rgba(255,255,255,0.12); }

.empty-state {
  text-align: center;
  color: #a89878;
  font-size: 1em;
  margin: 40px 0;
}

/* ---------- Book grid (individual shelf page) ---------- */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 24px 28px;
  align-items: end;
}

.grid-item { position: relative; padding-bottom: 30px; }

.spine {
  aspect-ratio: 595 / 842;
  width: 100%;
  border-radius: 4px 8px 8px 4px;
  box-shadow: inset 4px 0 0 rgba(0,0,0,0.2), 0 8px 16px rgba(0,0,0,0.4);
  padding: 14px 10px;
  display: flex;
  align-items: flex-end;
  color: #f0e6d0;
  font-size: 0.92em;
  line-height: 1.25;
  text-decoration: none;
}

.grid-item .shelf-actions { position: absolute; bottom: 0; left: 0; }

/* ---------- Polish pass ---------- */
a, button { transition: all 0.15s ease; }

.shelf-row:hover .shelf-plank {
  filter: brightness(1.1);
  box-shadow: 0 10px 18px rgba(0,0,0,0.5), inset 0 -3px 0 rgba(0,0,0,0.25);
}

.grid-item:hover .spine { transform: translateY(-4px); box-shadow: inset 4px 0 0 rgba(0,0,0,0.2), 0 12px 22px rgba(0,0,0,0.5); }

.nav-pill:not(.disabled):not(.active):hover { background: rgba(255,255,255,0.12); }

.create-shelf-btn {
  width: 100%;
  padding: 10px;
  border: 1px solid rgba(244,228,160,0.3);
  background: rgba(193,122,44,0.12);
  color: #e0c896;
  border-radius: 8px;
  font-family: 'Poppins', sans-serif;
  font-weight: 500;
  font-size: 0.85em;
  cursor: pointer;
}

.create-shelf-btn:hover { background: rgba(193,122,44,0.25); border-color: #c17a2c; }

.hero-panel, .shelf-plank, .spine { transition: box-shadow 0.2s ease, transform 0.2s ease, filter 0.2s ease; }
"""


def _esc(text: str) -> str:
    return html.escape(text or "")


def _color_for(key: str) -> str:
    return _SPINE_COLORS[sum(ord(c) for c in key) % len(_SPINE_COLORS)]


def slugify_shelf(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "shelf"


def _shelf_row_html(shelf: dict, href_fmt: str) -> str:
    entries = shelf.get("entries", [])
    visible = entries[:10]
    spine_html = "".join(
        f'<div class="mini-spine" style="height:{30 + (idx * 7) % 22}px;'
        f'background:{_color_for(e["video_id"])};"></div>'
        for idx, e in enumerate(visible)
    )
    extra = len(entries) - len(visible)
    count_label = f"{shelf['count']} book{'s' if shelf['count'] != 1 else ''}"
    if extra > 0:
        count_label += f" (+{extra} more)"

    href = href_fmt.format(shelf_slug=slugify_shelf(shelf["name"]), shelf_name=shelf["name"])
    name = shelf["name"]

    return f"""
    <div data-shelf-name="{_esc(name)}">
      <a class="shelf-row" href="{_esc(href)}">
        <div class="shelf-plaque">{_esc(name)}</div>
        <div class="shelf-plank">
          <span class="leaf-accent" style="left:6px;">&#127807;</span>
          {spine_html}
          <span class="leaf-accent" style="right:6px;">&#127807;</span>
        </div>
      </a>
      <div class="shelf-count">{count_label}</div>
      <div class="shelf-actions">
        <button onclick="renameShelf('{_esc(name)}')">Rename</button>
        <button onclick="deleteShelf('{_esc(name)}')">Delete</button>
      </div>
    </div>
    """


_SHARED_SCRIPT = """
<script>
  async function renameShelf(oldName) {
    const newName = prompt(`Rename shelf "${oldName}" to:`, oldName);
    if (!newName || !newName.trim() || newName.trim() === oldName) return;
    const res = await fetch('/api/shelf/rename', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_name: oldName, new_name: newName.trim() }),
    });
    if (res.ok) window.location.reload(); else alert('Rename failed.');
  }

  async function deleteShelf(name) {
    if (!confirm(`Delete shelf "${name}"? Books move to "General" — nothing is deleted.`)) return;
    const res = await fetch('/api/shelf/delete', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    if (res.ok) window.location.reload(); else alert('Delete failed.');
  }

  async function moveBook(videoId) {
    const newShelf = prompt('Move this book to which shelf?');
    if (!newShelf || !newShelf.trim()) return;
    const res = await fetch('/api/book/move', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: videoId, new_shelf: newShelf.trim() }),
    });
    if (res.ok) window.location.reload(); else alert('Move failed.');
  }

  async function createShelf() {
    const name = prompt('New shelf name:');
    if (!name || !name.trim()) return;
    const res = await fetch('/api/shelf/create', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.trim() }),
    });
    if (res.ok) window.location.reload();
    else { const d = await res.json(); alert(d.detail || 'Could not create shelf.'); }
  }

  function initSearch() {
    const box = document.getElementById('searchBox');
    if (!box) return;
    box.addEventListener('input', () => {
      const q = box.value.trim().toLowerCase();
      document.querySelectorAll('[data-search-text]').forEach((el) => {
        el.style.display = (!q || el.dataset.searchText.toLowerCase().includes(q)) ? '' : 'none';
      });
    });
  }
  initSearch();
</script>
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
    status.className = 'add-status';
    status.textContent = 'Generating notes... this can take a minute for longer videos.';

    try {
      const response = await fetch('/api/generate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, shelf }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Generation failed.');
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


def _nav_html(active: str) -> str:
    def pill(label, key, soon=False):
        cls = "nav-pill"
        if key == active:
            cls += " active"
        if soon:
            cls += " disabled"
        return f'<a class="{cls}" href="{"#" if soon else "/"}">{label}{" (soon)" if soon else ""}</a>'

    return f"""<div class="nav-strip">
      {pill("Home", "home")}
      {pill("My Books", "mybooks", True)}
      {pill("Categories", "categories", True)}
      {pill("Reading Goals", "goals", True)}
      {pill("Wishlist", "wishlist", True)}
      {pill("Settings", "settings", True)}
    </div>"""


def _hero_panel_html(shelf_field_html: str, stats_html: str, recent_html: str) -> str:
    return f"""
    <div class="hero-panel">
      <div class="hero-title">&#128218; The Archive</div>
      <input type="text" id="searchBox" class="search-box" placeholder="Search books or shelves...">
      <form class="add-form" id="addForm">
        {shelf_field_html}
        <input type="url" id="videoUrl" placeholder="Paste a YouTube lecture link..." required>
        <button type="submit" id="addBtn">+ Add Book</button>
      </form>
      <p class="add-status" id="addStatus"></p>
      {stats_html}
      <div class="recent-list">{recent_html}</div>
      <button class="create-shelf-btn" onclick="createShelf()">&#127793; Create Empty Shelf</button>
    </div>
    """


def render_library_home_html(shelves_with_entries: list, shelf_href_fmt: str = "/shelf/{shelf_slug}") -> str:
    total_books = sum(s["count"] for s in shelves_with_entries)
    existing_names = [s["name"] for s in shelves_with_entries]
    datalist_options = "".join(f'<option value="{_esc(n)}">' for n in existing_names)
    shelf_field_html = f"""
      <input type="text" id="shelfName" list="shelfOptions" placeholder="Shelf name" required>
      <datalist id="shelfOptions">{datalist_options}</datalist>
    """

    left_shelves = shelves_with_entries[0::2]
    right_shelves = shelves_with_entries[1::2]
    left_html = "".join(_shelf_row_html(s, shelf_href_fmt) for s in left_shelves)
    right_html = "".join(_shelf_row_html(s, shelf_href_fmt) for s in right_shelves)

    all_entries = [e for s in shelves_with_entries for e in s.get("entries", [])]
    recent = sorted(all_entries, key=lambda e: e.get("added_at", ""), reverse=True)[:4]
    recent_html = "".join(f"""
      <a class="recent-item" href="/notes/{_esc(e['video_id'])}">
        <div class="recent-title">{_esc(e['title'])}</div>
        <div class="recent-shelf">{_esc(e.get('shelf', 'General'))}</div>
      </a>
    """ for e in recent) or '<p style="font-size:0.8em;color:#a89878;">Nothing added yet.</p>'

    stats_html = f"""
    <div class="hero-stats">
      <span>Shelves: <b>{len(shelves_with_entries)}</b></span>
      <span>Books: <b>{total_books}</b></span>
    </div>
    """

    hero = _hero_panel_html(shelf_field_html, stats_html, recent_html)

    if shelves_with_entries:
        center_row = f'<div class="shelf-wall">{left_html}</div>{hero}<div class="shelf-wall">{right_html}</div>'
    else:
        hero_empty = _hero_panel_html(shelf_field_html, stats_html, recent_html)
        center_row = f'{hero_empty}<div style="flex:1;"><p class="empty-state">No shelves yet — add your first book to create one.</p></div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Virtual Shelf — The Archive</title>
{_FONT_LINK}
<style>{_CSS}</style>
</head>
<body>
  <div class="scene">
    <div class="scene-header">
      <h1 class="scene-title">Virtual Shelf</h1>
      <p class="scene-subtitle">Your personal archive of knowledge</p>
      {_nav_html("home")}
    </div>
    <div class="scene-row">{center_row}</div>
  </div>
{_add_form_script()}
{_SHARED_SCRIPT}
</body>
</html>
"""


def render_shelf_html(entries: list, shelf_name: str, href_fmt: str = "notes/{video_id}.html", home_href: str = "/") -> str:
    shelf_field_html = f'<input type="hidden" id="shelfName" value="{_esc(shelf_name)}">'

    if not entries:
        body = '<p class="empty-state">No books on this shelf yet — add one above.</p>'
    else:
        cards = "".join(f"""
        <div class="grid-item" data-search-text="{_esc(e['title'])}">
          <a class="spine" style="background:{_color_for(e['video_id'])};"
             href="{_esc(href_fmt.format(video_id=e['video_id']))}">{_esc(e['title'])}</a>
          <div class="shelf-actions"><button onclick="moveBook('{_esc(e['video_id'])}')">Move</button></div>
        </div>
        """ for e in entries)
        body = f'<div class="grid">{cards}</div>'

    hero = _hero_panel_html(shelf_field_html, "", "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{_esc(shelf_name)} — Virtual Shelf</title>
{_FONT_LINK}
<style>{_CSS}</style>
</head>
<body>
  <div class="scene">
    <a class="back-link" href="{_esc(home_href)}">&larr; Back to Library</a>
    <div class="scene-header">
      <h1 class="scene-title">{_esc(shelf_name)}</h1>
      <p class="scene-subtitle">{len(entries)} book{'s' if len(entries) != 1 else ''} on this shelf</p>
    </div>
    <div class="scene-row">
      <div style="flex:1;">{body}</div>
      {hero}
    </div>
  </div>
{_add_form_script()}
{_SHARED_SCRIPT}
</body>
</html>
"""


def main():
    library = LibraryIndex(path="./cache/library.json")
    shelves = library.list_shelves()
    for s in shelves:
        s["entries"] = library.list_by_shelf(s["name"])

    out_dir = Path("output")
    out_dir.mkdir(parents=True, exist_ok=True)

    home_html = render_library_home_html(shelves, shelf_href_fmt="shelf_{shelf_slug}.html")
    with open(out_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(home_html)

    for shelf in shelves:
        shelf_html = render_shelf_html(
            shelf["entries"], shelf["name"], href_fmt="notes/{video_id}.html", home_href="index.html"
        )
        slug = slugify_shelf(shelf["name"])
        with open(out_dir / f"shelf_{slug}.html", "w", encoding="utf-8") as f:
            f.write(shelf_html)

    print(f"Rendered library home + {len(shelves)} shelf page(s) -> {out_dir}/")


if __name__ == "__main__":
    main()