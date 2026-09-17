"""
Step 5: FastAPI web backend — the exact same generation logic as the CLI
(src/main.py), exposed over HTTP instead of command-line arguments.
Still single-user, no auth yet (see docs/DECISIONS.md #4 and
docs/ROADMAP.md Step 8 — auth is deliberately last, once there's a real
deployed, DB-backed app to attach accounts to).

Why none of the underlying modules needed to change: NotesGenerator,
CacheManager, LibraryIndex, and the render functions were always plain,
framework-agnostic Python — never entangled with argparse or any
CLI-specific concerns. This file is a thin HTTP wrapper around exactly
that same logic. That separation is what makes swapping the interface
(CLI -> web) cost almost nothing here — proof the earlier architecture
decisions (see docs/DECISIONS.md) were worth the discipline.

Run locally with:
    uvicorn api.app:app --app-dir src --reload --port 8000
Then visit http://localhost:8000/ for the shelf.
"""

import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generation.notes_generator import NotesGenerator
from library.library_index import LibraryIndex
from render.notes_renderer import render_notes_html
from render.shelf_renderer import render_library_home_html, render_shelf_html, slugify_shelf

load_dotenv()


def _load_config(path: str = "config/config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


config = _load_config()
generator = NotesGenerator(config)
library = LibraryIndex(path=f"{config['cache']['dir']}/library.json")

app = FastAPI(title="Virtual Shelf API")


class GenerateRequest(BaseModel):
    url: str
    shelf: str = "General"


class RenameShelfRequest(BaseModel):
    old_name: str
    new_name: str


class DeleteShelfRequest(BaseModel):
    name: str


class MoveBookRequest(BaseModel):
    video_id: str
    new_shelf: str


@app.post("/api/generate")
def generate_notes(req: GenerateRequest):
    """
    Triggers generation for a video URL, filed under the given shelf —
    same cache-first behavior as the CLI (cache hit = free, cache miss =
    real Gemini call). Returns just a status + title rather than the
    full note JSON; the actual rendered page is fetched separately via
    GET /notes/{video_id}, which keeps this endpoint fast and avoids
    sending the same large payload twice.
    """
    try:
        data = generator.generate_from_url(req.url, shelf=req.shelf)
    except ValueError as e:
        # extract_video_id raises ValueError for a malformed URL — a
        # client mistake, not a server problem, hence 400 not 500.
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Anything else (Gemini API errors, malformed model response)
        # is a genuine upstream/generation failure.
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}")

    return {"status": "ok", "title": data["title"]}


@app.post("/api/shelf/rename")
def rename_shelf(req: RenameShelfRequest):
    count = library.rename_shelf(req.old_name, req.new_name)
    return {"status": "ok", "moved": count}


@app.post("/api/shelf/delete")
def delete_shelf(req: DeleteShelfRequest):
    """Un-shelves every book on this shelf back to General — never
    deletes the underlying generated notes (see library_index.py)."""
    count = library.delete_shelf(req.name)
    return {"status": "ok", "moved": count}


@app.post("/api/book/move")
def move_book(req: MoveBookRequest):
    found = library.move_entry(req.video_id, req.new_shelf)
    if not found:
        raise HTTPException(status_code=404, detail="Book not found in library")
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def library_home():
    shelves = library.list_shelves()
    return render_library_home_html(shelves, shelf_href_fmt="/shelf/{shelf_slug}")


@app.get("/shelf/{shelf_slug}", response_class=HTMLResponse)
def shelf_page(shelf_slug: str):
    # Slugs are derived (lossy) from shelf names, so resolve back to the
    # real name by matching slugs — there's no separate stored mapping
    # since shelves aren't their own record (see library_index.py).
    shelves = library.list_shelves()
    match = next((s for s in shelves if slugify_shelf(s["name"]) == shelf_slug), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Shelf not found")

    entries = library.list_by_shelf(match["name"])
    return render_shelf_html(entries, match["name"], href_fmt="/notes/{video_id}", home_href="/")


@app.get("/notes/{video_id}", response_class=HTMLResponse)
def note(video_id: str):
    entries_by_id = {e["video_id"]: e for e in library.list_all()}
    entry = entries_by_id.get(video_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Note not found in library")

    # Cache hit in the overwhelming common case — this only triggers a
    # real Gemini call if the library somehow references a video whose
    # cache entry is missing (e.g. cache was manually cleared).
    data = generator.generate_from_url(entry["url"])
    return render_notes_html(data)