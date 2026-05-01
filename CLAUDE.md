# Bobiverse Star Map

## What this is

An interactive star map companion for the Bobiverse book series (Dennis E. Taylor).
The user scrubs a timeline (2133-2263) and watches Bob replicants travel between
real star systems, clone new Bobs, get destroyed, and trigger plot events.

Forked from an existing project. The visualization works but the underlying data
is incomplete and occasionally wrong. The goal is to rebuild the data from the
actual book text using LLM-assisted extraction.

## Project structure

```
index.html          Slim HTML shell
style.css           All styles
data.json           App data (stars, bobs, travels, events, chapters, plus 13+ enriched fields)
app.js              ES module - fetches data.json, all rendering/interaction logic
Books/{N}/          Chapter text files (markdown, one per chapter)
prompts/system.md   Per-chapter LLM extraction prompt (schema + field guidance)
prompts/enrich.md   Single-shot LLM enrichment prompt (canonical names + cross-chapter)
extract.py          Per-chapter extractor (Pydantic schema + recap rendering)
enrich.py           Single-shot enricher: one LLM call over all extracted chapters
merge.py            Deterministic merge: extracted + enriched → data.json
extracted/{N}/      Per-chapter extraction outputs, NN.json format
enriched/{N}.json   Per-book enrichment outputs (canonical_cast, name_aliases, etc.)
extraction-plan.md  Original design doc for the extraction schema
merge-backlog.md    Living design doc: how each extracted field becomes UI
```

Requires a local HTTP server for development (`python3 -m http.server`).
Deploys to GitHub Pages as a static site with no build step needed.

## Current goal: LLM data extraction pipeline

Build a Python script that processes chapter files through an LLM to extract
structured data, then a merge script that assembles the final data.json.

### Key design decisions

- **LLM extracts facts, code computes derived data.** The LLM reads a chapter
  and outputs who's present, new characters, destructions, movements, events,
  and summaries. Code then matches departures to arrivals to build travel records,
  assembles the family tree, looks up star coordinates, etc.

- **Chapter order != chronological order.** The books interleave storylines
  (e.g. Riker at Sol in 2158, then Bob at Delta Eridani in 2165, then back to
  Riker in 2158). Every data record carries both `chapter` (reading order, for
  spoiler gating) and `year_precise` (universe time, for map placement).

- **Spoiler gate uses chapter number, not year.** A reader on chapter 34 sees
  all data from chapters 1-34 regardless of in-universe dates.

- **Every chapter is processed, not just "interesting" ones.** Quiet chapters
  still produce summaries and character presence data for future UI features.

- **Each chapter is an independent LLM session.** Context comes from a
  deterministic "recap" built by code from prior chapter outputs, not from
  LLM memory.

### Pipeline

```
chapters → extract.py (LLM per chapter) → extracted/{book}/{ch}.json
extracted/*.json → enrich.py (one global LLM call) → enriched/{book}.json
extracted/*.json + enriched/*.json → merge.py (pure code) → data.json
```

`enrich.py` produces canonical names, name-alias map (variant → canonical),
character arcs, plot arcs, implicit resolutions for presumed-destroyed
characters, canonical technology/faction lists, and named combats. The merge
step uses the alias map as a normalizer when wiring extractions to UI data.

All LLM calls happen at build time (on developer machine). The deployed site
ships only `data.json` - no LLM calls in production, no backend.

See `extraction-plan.md` for the full output schema and field definitions.

### Design principles

- **Extract everything, filter at display time.** The LLM extracts all characters,
  planets, events - even minor ones. A curation pass (one LLM call) decides what's
  important enough for the map. The merge script is deterministic and uses
  the curated list as a filter.

- **Presumed destruction is two-phase.** When a character appears destroyed but
  isn't confirmed, mark `certainty: "presumed"`. A later chapter may resolve it
  with a `resolution` record (`confirmed_destroyed` or `survived`). The map shows
  "presumed dead" until the reader's spoiler gate includes the resolution chapter.

- **Client-side accumulation for spoiler gating.** Since this is a static site,
  `data.json` ships per-chapter deltas. The JS accumulates state up to the
  reader's selected chapter on the timeline slider. No server-side filtering.

## Extraction development conventions

### Schema lives in two files; they must stay in sync

Every extraction field has a dual home:
- `prompts/system.md` - the LLM-facing schema block + prose field guidance
- `extract.py` - the Pydantic model enforcing the response shape

Drift between them is a silent bug: the LLM emits what the prompt says, Pydantic rejects it (or worse, accepts a shape the merge step won't see). Adding a field means editing both.

### Backwards-compat rule for schema changes

Old `extracted/*/*.json` files must keep deserializing, because each chapter's extractor loads the previous chapter's `world_state_after`. So:

- New optional fields use `default_factory=list` (lists) or `default=None` (scalars).
- Required fields use `str | None = Field(description=...)` with no default.
- Never remove or rename existing fields; add new ones alongside.
- After any schema edit, verify old files still load:

  ```
  uv run --with pydantic python -c "
  import extract, json
  extract.WorldState(**json.load(open('extracted/1/14.json'))['world_state_after'])
  print('OK')
  "
  ```

### WorldState evolution protocol

Anything that should carry across chapters into the recap goes through `WorldState`. The protocol is four steps in `extract.py`:

1. Add the field to `WorldState` with `default_factory=list`.
2. Update `build_world_state` to accumulate new values (dedupe, preserve order).
3. Update `world_state_to_recap` to render the field so the LLM sees it.
4. Consider whether the prompt should gain explicit guidance to use the canonical names the recap now carries.

Canonical-name enforcement (technologies, factions, species, thread IDs) works this way: once an entity is named in one chapter, subsequent chapters see the exact spelling in the recap and are instructed to reuse it. Add a recap line whenever a new canonical-name category appears.

### merge-backlog.md structure

Each documented field in `merge-backlog.md` follows the same five-part template:

- **What it is** - schema recap
- **What it enables** - concrete views / panels / interactions
- **Merge step** - deterministic code turning per-chapter extractions into per-chapter UI data
- **Client accumulation** - how the JS builds state up to the reader's chapter
- **Global-enrichment opportunity** - what a future whole-corpus LLM pass could add

Keep the structure when documenting new fields; it makes the file scannable and makes the merge step's job explicit.

### Ops: running extractions

- Always `uv run extract.py --book N --ch M`. The `# /// script` block manages OpenAI + Pydantic deps. Never plain `python3` / `python`.
- Chapters must be extracted in order; chapter N reads N-1's `world_state_after`.
- Long loops run in a free tmux pane in the current window (see "Running things in tmux" below), not in the Claude shell.
- Watching a tmux pane for completion: use `grep -Fx "DONE-MARKER"` (exact-line match) against `tmux capture-pane -p -S -N`. Plain `grep` will false-match the echo command itself in the scrollback.
- Re-extraction overwrites `extracted/{N}/{ch:02d}.json` in place. Old files are never auto-deleted.

## UI development conventions

### Spoiler-safe chapter labels

The chapter-select dropdown in the spoiler-config screen shows future chapters too, so labels must NOT reveal plot. Rules:

- Use only `Ch {n} - {pov} ({year})`. POV + year mirrors the book's own chapter headings; the reader already sees them on entering the chapter.
- Never include the LLM `summary.one_line`. It will spoil first-time discoveries.
- Never include `metadata.location`. Knowing Bob's location at chapter N spoils his arrival from prior chapters.
- The label is built in `merge.py:build_chapters_list`; keep that the single source of truth.

### Data.json contract for the JS

`data.json` now ships ~20 top-level fields. When `app.js` reads a new field, default to empty (`DATA.field || []` or `|| {}`) so older data.jsons continue to render. Adding a new field follows: extract → enrich → merge wiring → app.js consumption.

### Smooth timeline patterns (keyframes & interpolation)

Timeline-driven panels (event log, tech list, combat list, etc.) use **proximity-weighted highlighting** rather than binary on/off. The slider playhead is continuous; events are discrete keyframes. Two techniques:

1. **Spread tied keyframes.** Events sharing the same `year_precise` (i.e. same chapter) are spread by tiny micro-offsets at build time so they fire sequentially as the slider sweeps through. See `buildEventLog` in `app.js`.
2. **Smoothstep intensity.** Each item carries a CSS custom property `--intensity` (0..1) computed from its delta to the playhead, eased with `i*i*(3-2*i)`. CSS uses `--intensity` to interpolate `color`, `background-color`, and `border-left-color`. Avoid binary `.active` classes for items that should feel "rolling".

The two knobs are `FADE_IN` (lead-in years before the keyframe brightens) and `FADE_OUT` (recent-past warmth duration). Default 0.4 / 6.0 years.

### Running things in tmux

**Any process that calls an LLM** (`extract.py`, `enrich.py`, future enrichment scripts) MUST run in a free tmux pane in the current window, not in the Claude shell. LLM calls are slow and expensive; running them inline blocks the agent and risks accidental interruption. Same rule applies to the local HTTP server and any other long-lived process.

Pick whichever pane is idle - no specific pane is reserved. List panes:

```
tmux list-panes -a -F "#{session_name}:#{window_index}.#{pane_index} #{pane_current_command}"
```

A pane is idle when its `pane_current_command` is the shell (zsh/bash). Target it with `tmux send-keys -t <pane> "..." Enter`.

### Headless verification

For UI changes, verify via Chrome headless before declaring done. The site supports an autostart hook for this: appending `?autostart=1&year=YYYY` to the URL auto-clicks the start button and jumps the slider to year `YYYY` after init. Useful for screenshot-based regression checks. The hook lives at the bottom of `app.js` and is gated on the query param, so it's harmless in normal use.

## Future UI work (design TBD)

- **Planets on the map.** Extracted planet data (habitability, life, colonies) needs
  to be displayed - likely as sub-nodes within star systems. Implementation to be
  designed later but the extraction pipeline captures the data now.

## Spoiler policy

Dean has finished Book 1. Do not reference plot details from Book 2 onward
unless working with data that was already in the forked project.
