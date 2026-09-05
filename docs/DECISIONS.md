# Decisions log

Format: what we decided, why, and what it costs us. Written at decision
time, not reconstructed later — if a decision doesn't have a "cost" line,
that's a bug in this doc, not a free lunch in real life.

## 1. No UI until Step 1 output is proven on 5+ real videos
**Why:** the failure mode for solo tool-builders isn't usually "never
finished the hard part" — it's "built a beautiful shell around a hard part
that was never actually solved." A bookshelf UI makes bad notes *look*
finished, which removes your motivation to go fix them.
**Cost:** slower to get something visually shareable. Accepted deliberately.

## 2. Gemini direct video URL input, not transcript-only
**Why:** transcripts lose slides, diagrams, on-screen equations, code shown
on screen — exactly the content a "lecture notes" tool exists to capture.
This is the actual product differentiator, not an implementation detail.
**Cost:** video-URL input is a narrower, faster-moving corner of the Gemini
API than plain text prompts — model support, duration limits, and syntax
have already shifted across 2026 point releases (see FREE_TIER_LIMITS.md).
This is why the model name lives in config, not hardcoded.

## 3. v1 scope: YouTube video links only, PDF deferred
**Why:** decided [this session]. PDF ingestion is a structurally different
pipeline (no equivalent of "send Google a URL and it watches it" — you'd
extract text/images yourself), so it's really a second integration, not an
extension of the first. Building both at once when the goal is *learning*
the Gemini video integration properly would split focus.
**Cost:** none yet — PDF was already Step-1-scope, not a separate build
step, so this just sequences within Step 1 rather than changing the roadmap.

## 4. Groq provider: interface defined, not wired up yet
**Why:** Groq's llama-3.1-8b-instant is text-only. A real fallback for
*video* notes would need its own transcript-extraction path (e.g.
youtube-transcript-api) feeding text-only prompts — a materially different,
lower-quality pipeline (no slides/diagrams/on-screen text), not a drop-in
swap. Wiring this now, alongside learning the Gemini integration, would be
two unfamiliar things at once.
**Cost:** if Gemini free tier is exhausted or down, there is currently no
fallback — generation just fails until quota resets. Acceptable for v1
while usage is low; revisit before this becomes a real bottleneck.

## 5. Structured JSON output from the model, not freeform markdown
**Why:** parsing "notes + one or more Mermaid diagrams" out of freeform
markdown is fragile — code fences, heading styles, and diagram placement
all vary run to run. Asking the model to return strict JSON
(`{title, notes_markdown, diagrams: [...]}`) and parsing that is far more
reliable, at the cost of a slightly more constrained prompt.
**Cost:** occasional malformed JSON from the model (rare but not zero) —
handled with a strip-fences-and-retry-once pattern in the provider.

## 6. Content-addressed caching, keyed on (video_id, model, prompt_version)
**Why:** caching only on video_id would silently serve stale output after
you improve the prompt or switch models — you'd think a fix worked because
you were reading cached output from before the fix. Keying on all three
means changing the prompt or model naturally invalidates the cache; nothing
extra to remember to clear.
**Cost:** every prompt iteration during development is a full-priced cache
miss. Expected and fine — this is what the free tier is for.

## 7. Config (YAML + .env) decoupled from source
**Why:** free-tier model availability changes without much warning (see
FREE_TIER_LIMITS.md — several models referenced in docs from earlier in
2026 are already gone). Swapping `gemini-2.5-flash` → whatever replaces it
should be a one-line config edit, not a code change + redeploy.
**Cost:** one more file to keep in sync; trivial.

## 8. Notes schema: concept cards, not freeform markdown (prompt_version 2)
**Why:** freeform `notes_markdown` had no hard constraint against
intro/outro filler, restated points, or inconsistent structure across
videos — telling the model "don't add unnecessary stuff" in prose is a
soft constraint that drifts over many runs. Restructuring the schema to
fixed per-concept cards (`what_it_is`, `how_it_works`, `syntax`,
`key_points`, `when_to_use`) makes the shape a hard constraint instead —
there's no field for filler to go into. Also sets up Step 2 well: a
concept-card shape maps naturally to distinct rendered note cards later;
one markdown blob doesn't.
**Cost:** breaking schema change — bumped `prompt_version` to 2 (old
cached entries under version 1 are now dead weight; safe to delete).
Also means `syntax` may legitimately be an empty string for non-code
concepts — anything consuming this data must handle that, not assume
syntax is always present.

## 9. Reverted StPageFlip (real page-curl) back to CSS scroll-snap
**Why:** StPageFlip produced a genuine curl animation and fixed page-size
uniformity, but introduced a persistent content-bleeding bug between the
cover page and adjacent content — survived three rounds of config changes
(showCover, usePortrait toggling, width constraints) and was confirmed
NOT a file:// origin issue (identical bug over a real localhost server).
It also required running a local HTTP server just to test, real added
friction for what should be a zero-dependency static HTML file. Continuing
to debug a third-party library's internals blind, for something explicitly
logged as optional polish (see ROADMAP.md Step 2 backlog note from
earlier), wasn't worth the time. Reverted to the horizontal scroll-snap
version, which had no such issues.
**Cost:** no curl/bend animation — pages slide rather than physically
turn. The "different page sizes" bug this scroll-snap version originally
had is now properly fixed too, with a FIXED height (not max-height) on
`.sheet-inner` — a fix fully within our own CSS, not dependent on a
library we can't fully control.