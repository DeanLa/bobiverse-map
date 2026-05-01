# Chapter Data Extraction Plan

## Philosophy

Split work between what an LLM is good at and what code is good at.

**LLM extracts** (subjective, requires reading comprehension):
- Who is in this chapter, where are they, what year/month is it
- New characters introduced (name, type, lineage)
- Characters destroyed/killed
- Notable events (what happened and why it matters)
- Locations mentioned or discovered
- Chapter mood/summary for future UI panels

**Code computes** (deterministic, derived from extracted facts):
- Travel records (Bob was at A in chapter X, at B in chapter Y - the transit is inferred)
- Timeline ordering and maxYear per chapter
- Which stars are "active" at any point
- Bob family tree from parent/child declarations

---

## Extraction Output Schema (per chapter)

### 1. Chapter metadata

Already parseable from the filename (`17 bob-july-2145-epsilon-eridani.md`),
but the LLM should confirm/correct from the chapter header.

```json
{
  "chapter": 17,
  "pov": "Bob",
  "year": 2145,
  "month": "July",
  "location": "Epsilon Eridani",
  "year_precise": 2145.5
}
```

`year_precise` is a decimal encoding of year + month (Jan=.08, Feb=.17, ..., Dec=.99).
The LLM should estimate this from the text. Code can normalize later.

### 2. Characters present

Every Bob (or replicant) that appears or is mentioned as present in this chapter.

```json
{
  "characters_present": [
    {
      "name": "Bob",
      "location": "Epsilon Eridani",
      "status": "active"
    },
    {
      "name": "Bill",
      "location": "Epsilon Eridani",
      "status": "active"
    }
  ]
}
```

`status`: `"active"` | `"in_transit"` | `"destroyed"` | `"mentioned_only"`

If `in_transit`, include `transit_from` and `transit_to`.

### 3. New characters introduced

Only characters that come into existence in this chapter (cloned, built, born).

```json
{
  "new_characters": [
    {
      "name": "Bill",
      "type": "replicant",
      "parent": "Bob",
      "generation": 2,
      "location": "Epsilon Eridani"
    }
  ]
}
```

`type`: `"replicant"` | `"human"` | `"ai"` | `"alien_individual"` | `"alien_species"`

### 4. Character destructions

Characters destroyed or killed in this chapter.

```json
{
  "destructions": [
    {
      "name": "Milo",
      "cause": "Destroyed by Brazilian probe during exploration of 82 Eridani",
      "year_precise": 2165.6
    }
  ]
}
```

### 5. Departures and arrivals

Explicit travel events mentioned in the chapter text. NOT inferred trips -
only what the text explicitly states ("Bob departed for X" or "Riker arrived at Y").

```json
{
  "movements": [
    {
      "character": "Bob",
      "type": "departure",
      "from": "Epsilon Eridani",
      "to": "Delta Eridani"
    },
    {
      "character": "Riker",
      "type": "arrival",
      "at": "Sol",
      "from": "Epsilon Eridani"
    }
  ]
}
```

Code will later match departures to arrivals across chapters to build travel records.

### 6. Star systems

Systems mentioned, discovered, or relevant in this chapter.

```json
{
  "star_systems": [
    {
      "name": "Epsilon Eridani",
      "role": "setting",
      "notes": null
    },
    {
      "name": "Delta Eridani",
      "role": "destination",
      "notes": "Bob selects this as his next exploration target"
    }
  ]
}
```

`role`: `"setting"` | `"destination"` | `"mentioned"` | `"discovered"`

### 7. Events

Key plot events worth showing in the event log. The LLM should extract 1-5 per chapter.
Short, factual descriptions. Not every conversation - focus on things that
change the state of the universe (new clones, battles, discoveries, departures, arrivals,
technology milestones, political events).

```json
{
  "events": [
    {
      "year_precise": 2145.5,
      "text": "Bill, Riker, Milo, and Mario come online at Epsilon Eridani",
      "characters": ["Bill", "Riker", "Milo", "Mario"],
      "significance": "major"
    }
  ]
}
```

`significance`: `"major"` (map-worthy) | `"minor"` (chapter detail, useful for summaries)

### 8. Chapter summary

For future UI features (chapter panel, tooltip, reading companion).

```json
{
  "summary": {
    "one_line": "Bob activates his first four clones at Epsilon Eridani.",
    "paragraph": "After establishing infrastructure at Epsilon Eridani, Bob begins the cloning process. Four new replicants come online: Bill, Riker, Milo, and Mario. Each has a distinct personality divergence from Bob. They discuss exploration targets and begin planning their departures to different star systems."
  }
}
```

---

## Fields NOT extracted by LLM (computed by code)

| Field | How it's computed |
|-------|-------------------|
| `travels` (full trip records) | Match departures to arrivals across chapters |
| `year_precise` | Parsed from filename/header: year + month/12 (e.g. July 2145 = 2145.58) |
| `chapter.maxYear` | REMOVED - spoiler gate now uses chapter number, not year |
| Bob family tree | Accumulated from `new_characters` across chapters |
| Star coordinates (ra, dec, distance) | Astronomical catalog lookup, not in the text |
| `book` field | Known from directory structure |

---

## Non-linear Timeline

Chapters are NOT in chronological (universe-time) order. The book interleaves
storylines - e.g. chapters 31-35 alternate between Riker at Sol (2158) and
Bob at Delta Eridani (2165). A chapter set in 2158 might mention plans that
only happen in a later chapter set in 2165.

This means **two independent orderings**:

- **Chapter order** = reading order = the spoiler boundary
- **Year** = universe time = the star map timeline axis

### Rules

1. **Spoiler gate uses chapter number, not year.** A reader on chapter 34
   should see all data from chapters 1-34, even if chapter 34 is set in 2158
   and chapter 30 was set in 2165. The reader has already read chapter 30.

2. **The LLM extracts only what the chapter states as accomplished fact.**
   "Riker plans to send Howard to Omicron2" is a minor event (a plan).
   "Howard departs for Omicron2" is a movement - but only extracted from
   the chapter where it actually happens.

3. **The recap is in chapter order, not year order.** The recap represents
   the reader's knowledge state, which follows reading order. If chapter 33
   is set in 2158 but the reader already saw chapter 30 (set in 2165),
   the recap includes chapter 30's facts.

### Data implications

Every extracted record carries both:
- `chapter`: the chapter number it was extracted from (for spoiler gating)
- `year_precise`: the universe time (for timeline placement)

The app filters by `chapter <= reader_max_chapter`, then plots by `year_precise`.

---

## Recap Strategy

Each chapter is processed independently, but the LLM prompt includes a **recap**:
a structured summary of the world state as of the previous chapter. This is built
by code from all previously extracted data, **in chapter order** (not year order),
because it represents what the reader knows at that point:

```
WORLD STATE BEFORE CHAPTER 17 (chapters 1-16 processed):
Active Bobs: Bob (Epsilon Eridani), Bill (Epsilon Eridani)
Destroyed: none
Known systems: Sol, Epsilon Eridani
Recent events: Bob arrived at Epsilon Eridani, defeated Medeiros
```

This gives the LLM context without sending all prior chapters.
The recap is deterministic - generated from prior extraction output, not from the LLM.

---

## Pipeline Overview

```
chapters/           extracted/           data.json
  1 bob...md   -->    ch01.json    -->
  2 bob...md   -->    ch02.json    -->   merge.py
  ...          -->    ...          -->   (deterministic)
  61 howard... -->    ch61.json    -->
```

1. `extract.py` - sends each chapter to the LLM with system prompt + recap + schema
2. `merge.py` - reads all ch*.json, computes travels, builds final data.json
3. Output is the same data.json the app already consumes

---

## Future Field Ideas

These don't affect the current map but would enable richer UI later:

| Field | Purpose |
|-------|---------|
| `human_characters` | Track named humans (Dr. Landers, Col. Butterworth, etc.) |
| `factions` | FAITH, Brazilian Empire, VEHEMENT, USE, etc. |
| `technologies` | SCUT, SURGE drive, printer, autofactory - when discovered/built |
| `colonies` | Settlement events with population, planet name, governor |
| `species` | Deltans, Others, Pavs - discovery and interaction events |
| `battles` | Structured combat events with participants and outcome |
| `relationships` | Bob-to-human bonds (Howard/Bridget, Bob/Archimedes) |
| `quotes` | Memorable one-liners per chapter |
| `chapter_themes` | Tags like "exploration", "combat", "politics", "philosophy" |
| `planet_details` | Habitability, moons, notable features of discovered worlds |
