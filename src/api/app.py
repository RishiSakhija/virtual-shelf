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
from render.shelf_renderer import render_shelf_html

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


@app.post("/api/generate")
def generate_notes(req: GenerateRequest):
    """
    Triggers generation for a video URL — same cache-first behavior as
    the CLI (cache hit = free, cache miss = real Gemini call). Returns
    just a status + title rather than the full note JSON; the actual
    rendered page is fetched separately via GET /notes/{video_id}, which
    keeps this endpoint fast and avoids sending the same large payload
    twice (once here, once when the note page is opened).
    """
    try:
        data = generator.generate_from_url(req.url)
    except ValueError as e:
        # extract_video_id raises ValueError for a malformed URL — a
        # client mistake, not a server problem, hence 400 not 500.
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Anything else (Gemini API errors, malformed model response)
        # is a genuine upstream/generation failure.
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}")

    return {"status": "ok", "title": data["title"]}


@app.get("/", response_class=HTMLResponse)
def shelf():
    entries = library.list_all()
    # "/notes/{video_id}" (a route), not "notes/{video_id}.html" (a file
    # path) — the one line that actually differs from the CLI's static
    # output/shelf.html, made possible by shelf_renderer's href_fmt param.
    return render_shelf_html(entries, href_fmt="/notes/{video_id}")


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