# Roadmap

Numbered task list with a session-by-session plan. Tasks are renumberable, sessions are reorderable. Pick whichever session feels right at the time.

## Done

- **Pipeline:** `build.sh` orchestrates `extract.py` (per-chapter LLM) → `enrich.py` (one global LLM call) → `merge.py` (deterministic) → `data.json`.
- **Extraction schema:** people, places, events, technologies, communications, combat, infrastructure, factions, alien species, threads, quotes, themes, scenes, threats, plus Bob personality cards.
- **Enrichment:** canonical names + alias map, character arcs, named plot arcs, named combats, faction trajectories, implicit resolutions for presumed-destroyed.
- **UI:** tabbed right panel (Events / Tech / Species / Battles / Quotes / Arcs), Bob trading-card modal, light-speed comm dots, mood strip, spoiler-safe chapter labels, smooth event-log highlighting + continuous scroll, cluster spreading.
- **61 book-1 chapters** extracted, enriched, merged.

## Tasks

### Quick wins (data exists; UI doesn't surface it yet)

1. **Infrastructure dashboard on star click.** Tooltip or modal listing autofactories / skunk_works / mining_bases / colonies present at the reader's chapter. 48 records ready in `data.json.infrastructure`.
2. **Open-threads panel.** 65 thread records ready; reader scrubs and sees what's still unresolved.
3. **Faction state ribbon** under the timeline. Thin colored band showing FAITH / USE / Brazilian Empire / VEHEMENT status changes over time.
4. **Theme filter chips** above the event log. 61 chapters have `themes`; click a chip to dim everything else.
5. **Threat radar.** 5 incoming-threat records. Render as fading vector lines on the map with ETA labels.
6. **Plot-arc ribbon** on the timeline. 8 named arcs as colored bands ("Bob under FAITH", "Deltan first-contact", etc.).

### Data quality

7. **Run `/audit-extractions`.** Not re-run since the events consolidation, spoiler-safe label, and factions-not-characters changes. May surface canonical-name drift.
8. **Star coordinates for new systems.** Ragnarok, Odin, Zeta Tucanae, Pi3 Orionis, etc. currently stubbed at `distance_ly: 30`, `ra_h: 0`, `dec_deg: 0`. Real astronomical lookup.
9. **`human_colonies` is empty.** 0 records despite explicit prompt guidance. The LLM may be putting them in `infrastructure[type=colony]` only. Verify whether the overlap rule is firing.
10. **Custom layout positions.** `app.js` `customLayout` covers ~21 stars; new systems pulled in by extractions don't have entries.

### Bigger ticket

11. **Books 2 & 3.** Run `./build.sh --book 2` and `--book 3` once spoiler readiness allows. Will need enrich + merge to handle all three books.
12. **Bob branch colors.** 29 replicants; `BRANCH_HUES` covers ~10. New Bobs (Howard, Calvin, Khan-cohort) collide on the gradient. Hash-based hue assignment from the name would scale.
13. **Speed-aware travel interpolation.** `max_g` and `drive` are extracted but the map still lerps linearly. 2G chemical should visibly take longer than 10G SURGE.
14. **Scene-level scrubbing.** 61 chapters have `scenes` data with time offsets. Slider could land on a scene mid-chapter.
15. **POV-glasses overlay.** `pov_knowledge.believes / learns / unaware_of` is extracted but unused. Toggle: show what the POV believes vs. what the reader knows.

### Polish

16. **Comms toggle remembers preference** (localStorage).
17. **Default starting year.** Dropdown defaults to last chapter; slider lands at 2133 (empty map). Land at the chapter's `maxYear` so first paint isn't blank.
18. **Mood strip click feedback.** Already jumps the slider; could also briefly highlight the destination chapter's events.
19. **Pin pydantic+openai venv.** Smoke-test scripts re-install per run via `uv run --with`. Pin once for faster iteration.

## Per-session workflow

Each session follows the PR workflow from the global CLAUDE.md:

1. `EnterWorktree` to create an isolated branch worktree.
2. Enter plan mode before writing code; get approval first.
3. Granular commits — one logical change per commit (author = `Dean's Agent <deanla+agent@gmail.com>` for github.com remotes).
4. **Don't push until "go ahead" / "looks good"** — avoids noisy PR updates while iterating.
5. Push + create PR.
6. After merge: `gh pr merge N --squash` (no `--delete-branch` from a worktree), `ExitWorktree`, `git pull`.

## Session plan

### Session 1 — Audit & data hygiene

`Tasks 7, 9, 10, 8`

Run the audit first (cheap, may invalidate later plans). Then act on what it finds: empty `human_colonies` is a known issue, custom-layout gaps and stub star coords are blocking the realistic-layout view from being honest. Ends with clean foundation data.

### Session 2 — Map gets clickable & alive

`Tasks 1, 5`

Click a star: see infrastructure at that system. Animated incoming-threat vectors fade in as ETA approaches. Both add overlays/interactions to the map view; complementary work.

### Session 3 — Timeline gets context

`Tasks 3, 6, 17, 18`

Faction-state ribbon and plot-arc ribbon both attach to the timeline area. Bundle in two small UX nits while we're in `app.js`: default starting year + mood-strip click feedback.

### Session 4 — Filtering & navigation

`Tasks 4, 2`

Theme filter chips and an open-threads panel. Both are content-filter UI in the right panel; designing them together avoids inconsistent affordances.

### Session 5 — Bob detail polish

`Tasks 12, 15, 16`

Branch colors get a hash-based assignment (so Howard isn't visually identical to Riker). POV-glasses toggle adds a new way to read the map. Persist comms-toggle to localStorage while we're touching toggles.

### Session 6 — Motion realism

`Tasks 13, 14, 19`

Speed-aware travel + scene-level scrubbing both touch the position-interpolation logic. Pin the venv while we're iterating heavily so feedback loops aren't `uv install` waits.

### Session 7 — Books 2 & 3

`Task 11`

Its own session. Extract → enrich → merge for the next two books, plus any plumbing changes the multi-book data exposes.
