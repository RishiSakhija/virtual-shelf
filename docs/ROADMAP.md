# Roadmap (build order — do not reorder)

This mirrors the build order you set. Each step has an explicit "done"
condition. Don't start a step until the previous one's condition is met.

## Step 1 — Prove core generation ✅ DONE

**Done when:** you've run this on 5+ real lecture videos across different
subjects and the diagrams are consistently *specific* to the content (not
"here's a generic flowchart of steps"), without hand-editing prompts per video.

**Closed [this session].** 5 videos tested: MCP architecture, sklearn
ColumnTransformer, Gen AI/Agents/Agentic AI, a 45-min lecture, and
sklearn Pipelines. All produced specific, non-generic concept cards and
diagrams — verbatim-correct syntax (e.g. `GridSearchCV` double-underscore
param naming, exact attribute chains) that could only come from reading
on-screen code, not narration alone.

**Scope note on "different subjects":** all 5 skew CS/ML/code-heavy, not
math/proof-heavy. Confirmed deliberately with the user this matches real
intended usage (light ML math is fine; heavy proof-based math isn't a
target use case — user prefers writing that by hand). So this isn't a
gap in the done-condition, it's the done-condition correctly scoped to
actual usage rather than an arbitrary genre checklist.

## Step 2 — Handwriting-style rendering ✅ DONE

**Done when:** a generated note from Step 1 renders legibly and consistently
without per-note manual tweaking.

**Closed [this session].** `src/render/notes_renderer.py` renders any
cached note into a standalone, paginated HTML file — Kalam handwriting
font for prose, monospace for code, Mermaid's `handDrawn` look for
diagrams, horizontal scroll-snap pagination with Prev/Next + arrow-key
navigation + a page counter. Verified on multiple real cached videos.

**Deliberately deferred (not a gap):** a true 3D page-curl/flip animation
(CSS 3D transforms + drag physics or a library like page-flip.js) instead
of the current straight horizontal slide. Doesn't block anything — it's
optional visual polish on the same static-HTML viewer, not gated on Step
3 or any later step. Revisit whenever, standalone.

## Step 3 — Bookshelf UI (IN PROGRESS)
Grid of book covers → click → rendered notes from Step 2.

**Core functionality confirmed working [this session]:** `src/main.py`
now auto-renders every generated note to `output/notes/<video_id>.html`
(predictable path, not the ad-hoc filenames from Step 2 testing).
`src/render/shelf_renderer.py` reads `cache/library.json` and builds a
grid of book cards, each linking to its rendered note. Verified
end-to-end: shelf renders, clicking a book opens the correct note page.

**Not yet confirmed:** grid layout with multiple books (only tested with
one so far) — need to backfill the other already-cached videos and verify
the grid actually wraps into columns, colors stay visually distinct, and
nothing breaks with a real multi-book shelf before calling this step done.

**Explicitly depends on Step 1+2 being solid.** A nice shelf holding weak
notes is not progress — building this early just gives you a prettier way
to notice the generation quality is bad.

## Step 4 — Editable text layer + PDF export
Let users edit rendered notes and export to PDF.

## Deadline [set this session]
Target: end of September 2026 (from Sept 5), all 8 steps, fully deployed
multi-user app with auth. Committed capacity: daily, focused, 1-2+ hrs.

**Weekly plan (de-risking hardest/newest integrations early, not stacking
them all at the end):**
- Week 1 (Sept 5-11): Finish Step 3 (multi-book grid verified), complete
  Step 4 (editable + PDF export). Fully solid local app.
- Week 2 (Sept 12-18): Step 5 (FastAPI conversion), then deploy that BARE
  single-user version to Render immediately — before DB, before auth.
  Fewest possible moving parts while learning deployment for the first
  time.
- Week 3 (Sept 19-25): Step 7, database — migrate off JSON, redeploy.
- Week 4 (Sept 26-30): Step 8, auth — last, on purpose, matching the
  original sequencing logic (needs a real deployed app to attach
  accounts to).

**Explicit contingency, decided now, not discovered under deadline
pressure:** if Week 1-3 slip and Step 7 isn't done by ~Sept 24, the call
is to either move the deadline OR ship the deployed app WITHOUT auth —
a working public multi-note app is still a real finished project; a
rushed, security-shortcut auth implementation is worse than no auth.
Auth becomes month-2 work in that case, not a crisis to cram in.

## Step 5 — CLI → web API (FastAPI), still single-user
Convert `src/main.py`'s logic into HTTP endpoints instead of CLI args.
No database, no auth yet — same functionality, different transport.
**Done when:** you can hit an endpoint and get back the same JSON the
CLI produces today.

## Step 6 — Deploy the single-user API (Render, free tier, no card)
Get the deploy pipeline itself working in isolation, before adding a
database or auth on top of it. If something breaks here, you know
exactly which layer to look at.

## Step 7 — Database (Render Postgres, free tier, no card)
Replace loose `cache/*.json` files with real persistence — a proper
notes library per user, which is also what Step 3's bookshelf actually
needs to list real content instead of one cached file.

## Step 8 — Auth
Added last, once there's a deployed, DB-backed app to actually attach
accounts to. Scope decided [this session]: user wants to deploy this
as a real multi-user project (their first deployment ever) — so this
is genuinely on the roadmap, not scope creep, just deliberately
sequenced last so it isn't the thing blocking everything else.

---

## Known bottleneck to plan around (not a "later" problem)
Free-tier rate limits on both providers will genuinely constrain how many
videos/PDFs you can process per day during development and real usage.
See `docs/FREE_TIER_LIMITS.md`. This is why caching is built in from day
one, not added later — without it you'll burn a meaningful chunk of your
daily quota just re-testing prompts on the same video.