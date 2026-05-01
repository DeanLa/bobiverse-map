---
description: Audit the Bobiverse chapter extractions for gaps, quality issues, and prompt/code drift
---

# Audit extractions for gaps & quality

You are auditing the Bobiverse chapter-extraction pipeline. Your job is to find
**data quality issues, gaps, and prompt/code drift** - not suggest new features
(the user already has a backlog for that in `merge-backlog.md`).

## What to read first

1. `prompts/system.md` - the LLM schema + field guidance
2. `extract.py` - the Pydantic models and recap rendering
3. `merge-backlog.md` - design intent and how each field will be used
4. `extracted/1/*.json` (and `extracted/2/*.json`, etc. if they exist)

Skim `extract.py` only enough to know which fields exist; don't re-read line by line.

## What to check, organized by severity

### Critical (silent data loss or corruption)

- **Prompt/code drift.** A field in the system-prompt schema block that has no Pydantic model, or vice versa. An enum value allowed in one place but not the other. Fields whose `description` in code contradicts the prose in the prompt.
- **Schema-missing in old files.** Top-level fields that exist in the current schema but are absent from older `extracted/*/*.json` files. List which files, which fields.
- **Type regression.** A character whose `type` goes backwards (e.g. `replicant` in ch N, `human` in ch N+M without a merge/resurrection explanation). This is the canonical bug the current prompt was supposed to fix - verify it actually did.
- **Invalid enum values** in extracted data. The Pydantic parse would have caught these, but run a sanity check anyway.
- **Orphan resolutions / threads.** A `threads_resolved` entry whose `id` never appeared in any prior `threads_opened`. A `resolutions` entry whose `character` was never `presumed_destroyed`.
- **Matching travel halves.** Departures without arrivals (or arrivals without departures) within a plausible chapter range. Some of these are genuine (long transits), but all of them should be noted - the merge step needs to reconcile.

### Quality (extraction is weaker than the schema allows)

- **Canonical name drift.** Same entity with multiple spellings across chapters (`Bob` vs `Bob-1`, `Epsilon Eridani` vs `Eps Eri`, `GUPPI` vs `Guppy`, `Omicron2 Eridani` vs `40 Eridani`). Produce a table of all suspected drifts with chapter examples.
- **Field under-population.** Fields where the LLM is silently skipping content. Compute per-field non-empty rate across all chapters. Flag any field under 25% non-empty in chapters where you'd expect it. Be specific: "combat is 0/20 but chapters 8, 12, 15 clearly contain combat per the `events` list".
- **World-state bloat.** Count characters in the final chapter's `world_state_after.active_characters`. If more than ~25 humans, list the ones with no events or mentions in the last 5 chapters - they're probably dead weight from the one-off-human problem.
- **Recap size.** Render the recap for the most recent chapter (re-use `world_state_to_recap` logic if easy, else estimate line count from `world_state_after`). Flag if over 60 lines - that's a lot of context cost per chapter.
- **Orphan characters in events.** Names that appear in `events[].characters` or `summary.paragraph` but are nowhere in `characters_present` or `new_characters` for that chapter.
- **Duplicate within-chapter entries.** Same technology, planet, or system listed twice in the same chapter's extraction.
- **Thin personality data.** `new_characters` entries of `type: replicant` where `personality.traits` is empty or `role` is `unknown`.
- **Missing companion / cargo on known group-travels.** Chapters that describe multiple characters leaving together should have `companions` filled. Spot-check.

### Drift from documented intent

- **merge-backlog.md vs reality.** Fields in the backlog marked as populated but the data is weak. Fields where the backlog's "what it enables" depends on data that isn't actually being extracted well.
- **Extraction plan contradictions.** `extraction-plan.md` describes the original design. Any contradictions between it and the current `system.md`? Are they intentional?

## How to check programmatically

Run aggregations via `uv run python -c '...'` (per project convention, never plain `python`). Good patterns:

```python
# Per-field non-empty rate
import json, glob
from collections import Counter
empty_count = Counter()
total = 0
for f in sorted(glob.glob('extracted/1/*.json')):
    d = json.load(open(f))
    total += 1
    for k, v in d.items():
        if isinstance(v, list) and not v:
            empty_count[k] += 1
```

```python
# Canonical name drift
import json, glob, re
names_by_chapter = {}
for f in sorted(glob.glob('extracted/*/*.json')):
    d = json.load(open(f))
    for c in d.get('characters_present', []) + d.get('new_characters', []):
        names_by_chapter.setdefault(c['name'].lower(), []).append((f, c['name']))
# Find names that case-fold to the same key but have varying spellings
```

Don't hesitate to spawn an **Explore agent** if you need to cross-reference the
chapter source text against extractions (e.g. "chapter 8 text says 'armed raid'
but combat is empty - is the extraction wrong?").

## Output

Write a single response, no headers or filler, tightly scannable. Structure:

```
## Critical issues
- [one line each, include file path + chapter number when applicable]

## Quality issues
- [grouped by category: naming, under-population, thread hygiene, etc.]

## Prompt/code drift
- [one line each, reference system.md section and extract.py class]

## Field coverage table
| field | present | non-empty | expected-where | observed-where |

## Canonical name drift table (only if drifts exist)
| canonical | variants seen | chapters |

## Recommended next prompt edits
- [specific edits to system.md or extract.py, with the rationale]

## Chapters worth re-extracting after those edits
- [list + brief reason each]
```

Cap each narrative section under 200 words. The tables can be as long as they
need to be. No end-of-response summary - the tables ARE the summary.

## What NOT to do

- Do not suggest new extraction fields. That's out of scope; refer to `merge-backlog.md`.
- Do not re-run the extractor yourself - you're auditing the existing output.
- Do not edit `prompts/system.md` or `extract.py`. Propose edits; let the user approve.
- Do not rewrite the report in your own format - follow the structure above.
