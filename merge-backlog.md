# Merge & UI Backlog

Design doc for what the extraction produces and how the **merge step** plus the
**client-side JS** will turn it into views. Grows as new extraction fields land.

## Pipeline recap

```
Books/{N}/*.md
   │
   ▼
extract.py   (one LLM call per chapter, sees system prompt + recap)
   │
   ▼
extracted/{N}/{ch}.json    one file per chapter, carries world_state_after
   │
   ▼
(future)  enrich.py        one global LLM pass over all extracted chapters,
                           filling cross-chapter fields (final arcs, resolutions
                           the per-chapter pass couldn't see, etc.)
   │
   ▼
merge.py      pure code: assemble deterministic derived data, computed from
              all extracted chapters, structured per-chapter for spoiler gating
   │
   ▼
data.json     ships to the browser
   │
   ▼
app.js        filters by reader's chapter on-the-fly, accumulates state,
              renders map + panels
```

## Core principles

1. **LLM extracts facts, code derives state.** Each chapter output is a set of local facts. All accumulation is deterministic code.
2. **Every record carries `chapter`.** JS filters `chapter <= reader_max_chapter` to enforce spoiler gates.
3. **Derive at render time, not at build time.** The merge step does NOT pre-compute "what the reader at chapter 34 sees". It packages deltas; JS accumulates on the slider.
4. **Chapter order ≠ chronological order.** Spoiler gate is chapter number. Timeline placement is `year_precise`. Every field that could be plotted needs both.
5. **The global enrichment pass adds cross-chapter fields.** If a feature can ONLY be done well with all chapters in context (character arcs, foreshadowing resolutions, comparative summaries), it goes into enrich.py, not extract.py.

## How each extraction field plugs into the UI

Each section below covers one field. Structure:
- **What it is** (recap of the extraction schema)
- **What it enables** (view / panel / interaction)
- **Merge step** (what pure code needs to do)
- **Client accumulation** (how JS builds the view as the reader progresses)
- **Global-enrichment opportunity** (what the future final LLM pass could add)

---

## Data quality baseline

Before any new fields, the prompt now enforces:

- **No one-off humans** in `new_characters`. Convention attendees, cameos, waitstaff
  stay out. Rationale: the world state was accumulating ~20 irrelevant Sol humans
  by chapter 14, which polluted the recap and inflated context for every
  subsequent chapter.
- **Identity transitions** (human Bob → replicant Bob) must be emitted as a
  `type: "creation"` event. The character's `type` in `characters_present`
  updates to the new identity immediately; the recap's stale type is ignored.
- **Current-type rule.** `characters_present[].type` reflects present nature,
  not the recap's possibly-stale value.

Merge-step TODO: when assembling the Bob family tree, detect
"Bob comes online as a replicant" creation-events and mark them as the
canonical genesis timestamp for the replicant Bob (separate from human Bob's
death record from chapter 1). The UI should show this as a single timeline
pin, not two disconnected events.

---

## Tier 1: high value

### technologies

**What it is.** Per-chapter entries for named technologies (SCUT, SURGE drive, SUDDAR, autofactory, roamer, etc.) with an `event` (`mentioned | invented | first_tested | deployed | upgraded | failed`), the responsible character/faction, and a location.

**What it enables.**
- **Tech tree panel** - Civ-style tree. Nodes are technologies, edges are prerequisites (added during global enrichment). Each node has a "discovered" timestamp and a "first deployed" timestamp.
- **Map overlays** - A star system can be color-coded by "has SCUT", "has autofactory", "has combat-capable Bob". Hover shows what tech is online there.
- **Reading companion** - Chapter panel lists "new tech this chapter".

**Merge step.**
- Collect all `technologies` entries across chapters, keyed by `name`.
- For each tech, derive:
  - `first_mentioned_chapter`, `first_mentioned_year`
  - `invented_chapter`, `invented_year` (the earliest `invented` entry)
  - `first_deployed_chapter`, `first_deployed_year` (the earliest `deployed` entry)
  - `history`: full chronological list of events
- Ship this as `data.json.technologies` keyed by name.

**Client accumulation.**
- At slider position `ch`, a tech is "known" if `first_mentioned_chapter <= ch`.
- A tech is "operational" at system X if the chapter stream up to `ch` has a `deployed` event at X. JS walks the history and builds a set of currently-operational capabilities per system.
- The map overlay reads from that derived set.

**Global-enrichment opportunity.**
- Prerequisite graph: "SCUT requires subspace transmission research." The per-chapter pass can't see this; a global pass can.
- Canonical-name consolidation: make sure "SCUT" and "Subspace Communication" and "subspace comms" are all the same tech.
- "What this tech changed" narrative: one sentence per tech describing its impact on the story.

---

### faction_events

**What it is.** Per-chapter political state changes for named factions (FAITH, USE, Brazilian Empire, China, Australia, VEHEMENT, etc.) with an event type like `founded`, `war_declared`, `coup`, `territory_change`.

**What it enables.**
- **Sol political timeline** - a horizontal band at the bottom of the map showing faction state over time. FAITH red where it's at war with USE, purple during the civil war arc, grey after collapse.
- **Faction dashboard** - click a faction to see its full trajectory: when founded, conflicts, territory changes, collapses.
- **"Who was in control at Sol in year X"** - powers a tooltip on the Sol node.

**Merge step.**
- Collect all faction_events, keyed by faction name.
- Build per-faction timeline: sorted list of events with chapter + year.
- Detect derived state:
  - `status` at any point: `active | at_war | collapsed | absorbed`
  - `wars`: list of (other_faction, start_chapter, end_chapter) tuples matching `war_declared` to `war_ended`
- Ship `data.json.factions` = { faction_name: { timeline, wars, status_history } }.

**Client accumulation.**
- At slider position `ch`, derive each faction's current state by walking its timeline up to `ch`.
- The Sol overlay can show active wars as red arcs between faction labels.

**Global-enrichment opportunity.**
- War outcomes: the per-chapter pass might see `war_declared` but miss the subtle "war effectively ended" moment. Global pass can close the loop.
- Faction "color" / flavor: give each faction a single-word vibe for UI tinting.

---

### communications

**What it is.** Every explicit message sent or received, with from/to characters and systems, medium (radio, SCUT, BobNet, SUDDAR ping), direction (sent/received/both), and a summary of contents.

**What it enables.**
- **Light-speed lag visualization** - the most unique Bobiverse-native visual. A message sent from Epsilon Eridani to Sol in 2145 arrives at Sol in ~2155 (10.5 ly). Render as a glowing dot traveling along the connecting line. SCUT messages arrive instantly. Nobody else has this.
- **"Information frontier"** overlay - at year Y, what does each system KNOW about what's happened elsewhere? A chapter POV at Sol in 2160 doesn't know what happened at Delta Eridani in 2158 yet because the radio signal hasn't arrived.
- **Message log panel** - per-Bob inbox view. Click a Bob to see what messages they've sent and received.

**Merge step.**
- Match `sent` entries to `received` entries where possible (same contents_summary or adjacent chapters). This is a heuristic - the LLM doesn't always give identical wording.
- Compute light-speed lag for `radio` messages: look up distance between `from_system` and `to_system`, compute travel years, derive `received_year` if only `sent_year` is known.
- For `SCUT`: instantaneous, `received_year == sent_year`.
- Ship `data.json.communications` = list of { id, from_chapter, from_year, to_chapter?, received_year, medium, from_char, to_char, from_system, to_system, summary }.

**Client accumulation.**
- At slider year Y, a message is "in flight" if `sent_year <= Y < received_year`. Render a dot at fraction `(Y - sent_year) / (received_year - sent_year)` along the line from `from_system` to `to_system`.
- At slider chapter `ch`, only messages with `from_chapter <= ch` are known to the reader. Even if a message was "delivered" in-universe before chapter ch, it's only visible if the reader has seen the sending chapter.

**Global-enrichment opportunity.**
- Message threading: link replies to originating messages.
- "Message delayed by" notation: explicit UI text when the received chapter shows a character reacting to old news.
- Detect "lost" messages: sent but never acknowledged.

---

### combat

**What it is.** Structured combat records with participants (grouped by side A/B/C), per-participant outcomes, weapons list, victor, duration. Each chapter can have zero or more combat entries.

**What it enables.**
- **Battle log panel** - scrollable list of every engagement with a "battle card" showing sides, weapons, outcome.
- **Explosion markers on the map** - tick a battle location with an X or flash animation at `year_precise`.
- **Combat stats per character** - "Bob has won 2 battles, been damaged in 3" style profiles.
- **Faction combat ledger** - "Brazilian Empire ships destroyed: 4" over the course of the books.

**Merge step.**
- Collect all combat entries, assign an ID.
- Derive per-character stats: battles_fought, battles_won, damage_taken, destroyed_in (if any).
- Derive per-faction stats: ship losses, wins, losses.
- Ship `data.json.combat` = list of records, plus `data.json.combat_stats_by_character` and `data.json.combat_stats_by_faction`.

**Client accumulation.**
- Straight chapter-gate filter. Stats reset and recompute as the slider moves (cheap).

**Global-enrichment opportunity.**
- Named battles: "The Battle of Epsilon Eridani" (ch 15). Give each multi-chapter engagement a name.
- Tactical summary: one-sentence post-mortem per battle.

---

### bob_personality (on new_characters)

**What it is.** Nested object on each `new_characters` entry with `traits` (adjectives), `role` (researcher/explorer/diplomat/etc), `nickname_origin`, and `quirks`.

**What it enables.**
- **Bob trading-card panel** - click a Bob, see a styled card with their photo (eventually), role badge, trait tags, one-liner flavor text. Replaces today's "Gen 3 | Parent: Bill".
- **Branch role distribution** - visualize which branches produce researchers vs combat vs explorers.
- **Filter map by role** - "show me only combat Bobs" dims everything else.

**Merge step.**
- Promote personality data from `new_characters` entries onto the top-level `bobs` object that already exists.
- Already-existing legacy bob records without personality data just keep their current sparse data; merge unions the new fields.
- Ship `data.json.bobs[bobId].personality` = { traits, role, nickname_origin, quirks }.

**Client accumulation.**
- A Bob's personality is visible as soon as the chapter that introduces them is reached. No per-chapter accumulation needed - personality is set once on birth.

**Global-enrichment opportunity.**
- Personality arcs: "Bill starts withdrawn, becomes a leader over books 2-3". Per-chapter extraction can't see this; global pass can add `personality_arc` as a separate field.
- Relationship annotations: which Bobs get along, which clash. (See Tier 3 `relationships`.)

---

### alien_species

**What it is.** Per-chapter entries for species-level events (first sighting, first contact, peaceful interaction, conflict), plus `tech_level`, `intelligent`, `hostile` flags. Separate from individual alien characters and from planet-level life descriptions.

**What it enables.**
- **First-contact dossier panel** - click a species to see: home planet, tech level, timeline from first sighting to first contact to current relationship, hostile/peaceful status.
- **Species markers on the map** - a planet with intelligent aliens gets a special glyph.
- **Milestone bar** - "First contact with Deltans, 2165.3" shown as a prominent pin on the timeline slider.

**Merge step.**
- Collect all alien_species entries, keyed by species name.
- Build per-species timeline.
- Derive `relationship` at any point: `unknown | peaceful | cautious | hostile`. A `conflict` event flips to `hostile`; a `peaceful_interaction` flips to `peaceful`.
- Associate species with home planet/system for the map marker.
- Ship `data.json.species` = { name: { timeline, relationship_history, home_planet, home_system, intelligent, tech_level } }.

**Client accumulation.**
- Filter by chapter. At slider position `ch`, a species is "known" if first entry has chapter <= ch. Current relationship is the last entry's implication.

**Global-enrichment opportunity.**
- Species naming cleanup: "Deltans", "the Deltan tribe", "humanoids on Delta Eridani 3" all unify to one species name.
- Linguistic/cultural detail paragraphs summarizing what the reader knows about the species at any point in the series.
- Detection of implied threats or alliances that cross-chapters reveal.

---

## Tier 2: medium value

### chapter_themes + mood (on summary)

**What it is.** `summary.themes` is a list of tags ("first-contact", "politics", "combat"). `summary.mood` is one of a fixed set of emotional tones. `summary.pov_emotional_arc` is one sentence on the POV's inner experience.

**What it enables.**
- **Chapter-filter dropdown** - "show me all first-contact chapters".
- **Theme distribution chart** - how much of the book is politics vs combat vs philosophy.
- **Mood-over-time ribbon** - render a horizontal colored strip under the slider, one cell per chapter, tinted by mood. Lets the reader see at a glance which stretches were tense vs reflective.
- **Rec engine** - "you liked this chapter? here are three others with similar themes".

**Merge step.**
- No cross-chapter derivation needed. Pass themes/mood/arc through to `data.json.chapter_meta[ch]`.
- Build a `data.json.theme_index` = { theme: [chapter_numbers] } for fast filter lookups.

**Client accumulation.**
- Chapter-gate filter. UI builds the filter dropdown from the theme_index.
- Mood ribbon is pre-built; active part dims future chapters.

**Global-enrichment opportunity.**
- Theme consistency: ensure "politics" and "political" don't both exist. Canonicalize tags.
- Detect thematic arcs: "book 1 chapters 1-10 cluster around 'replicant-philosophy'".

---

### quotes

**What it is.** Up to 1-2 memorable verbatim quotes per chapter, each with a speaker and a one-line context.

**What it enables.**
- **Chapter panel flourish** - each chapter card shows its standout quote.
- **Shareable quote cards** - "copy as image" with attribution.
- **Character voice panel** - all quotes by a single character ("Bob has said 17 memorable things so far").

**Merge step.**
- Collect all quotes, flat list. Tag each with chapter + year.
- Build `data.json.quotes_by_character` = { character: [quote_records] }.

**Client accumulation.**
- Chapter-gate filter.

**Global-enrichment opportunity.**
- Quote uniqueness scoring: dedupe cases where a callback-quote gets logged multiple times.
- Per-character "signature line": pick the single most iconic quote per character.

---

### threads_opened / threads_resolved

**What it is.** Stable kebab-case IDs for unresolved plot threads. `threads_opened` introduces them; `threads_resolved` closes them using the same ID many chapters later. The recap now carries open threads forward so the LLM can re-use IDs for resolutions.

**What it enables.**
- **"What's still open?" panel** - at the reader's current chapter, show all threads that are opened but not yet resolved. Great for a resume-reading prompt.
- **Narrative tension indicator** - count of open threads over time. Tension peaks before big resolution chapters.
- **Payoff links** - click a resolution to jump back to the chapter that opened it.

**Merge step.**
- Walk chapters in order. For each `threads_opened`, record `opened_chapter`. For each `threads_resolved`, find the matching open thread and record `resolved_chapter`.
- A thread with no resolution by end of corpus is "still open".
- Ship `data.json.threads` = [{ id, text_opened, text_resolved, opened_chapter, resolved_chapter, gap_chapters }].

**Client accumulation.**
- At slider position `ch`, a thread is "open" if `opened_chapter <= ch AND (resolved_chapter IS NULL OR resolved_chapter > ch)`.
- "Recently resolved" = threads where `resolved_chapter` is within the last few chapters.

**Global-enrichment opportunity.**
- Dangling-thread detection: explicitly flag threads that the author opened but never closed. Useful for "what the author left unanswered" meta commentary.
- Thread merging: two threads that became the same story arc should be deduped.

---

### infrastructure

**What it is.** Buildings, facilities, and bases at each system - autofactory, mining_base, skunk_works, colony, radio_relay, clone_facility, defensive_array, shipyard, research_station. Each entry is an event (`established | expanded | destroyed | upgraded | abandoned`).

**What it enables.**
- **System dashboard panel** - click a star, see its full base roster: "Epsilon Eridani has autofactory (Bob, 2144), mining_base (Bob, 2144), skunk_works (Bill, 2145), clone_facility (Bill, 2145)".
- **Capability map overlay** - star dot size or glow scales with how much infrastructure is there.
- **"Industrial Bobs" sub-view** - map shows only systems with autofactories, color-coded by owner.

**Merge step.**
- Collect all infrastructure events, keyed by (system, type, owner).
- Walk events to build current state: a facility is `active` from its `established` chapter until `destroyed` / `abandoned`, or upgraded (in which case the record gets a history log).
- Ship `data.json.infrastructure_by_system` = { system: [{ type, owner, established_ch, destroyed_ch?, history }] }.

**Client accumulation.**
- At chapter `ch`, walk the history lists, derive what's currently active per system.

**Global-enrichment opportunity.**
- Infer "size" / "scale" of each facility from the text: tiny mining outpost vs full industrial world.
- Attach infrastructure to specific planets where possible (currently just system-level).

---

### movement enrichment

**What it is.** `ship`, `companions`, `cargo`, `drive`, `max_g` fields added to each movement entry.

**What it enables.**
- **Correct speed-based interpolation on the map.** Today the Bob's position interpolates linearly between `depart` and `arrive` years. With drive + max_g, we can model a realistic acceleration curve (accel at 2G for half, decel for half, peak velocity in the middle). Bobs traveling at 2G look noticeably slower than Bobs at 10G.
- **Ship-sharing panel** - "who traveled with whom" - a social graph edge between Bobs who shared a ship.
- **Cargo tags on travel lines** - "with colony ships" annotation on the dashed line.
- **Drive-type coloring** - the dashed travel line is dotted for chemical, solid for SURGE.

**Merge step.**
- Movement enrichment data is already joined with travel records during the departure↔arrival matching.
- Derive `traveled_with` graph: for each pair of characters who shared a ship, add an edge with the shared trip.

**Client accumulation.**
- No accumulation logic changes. The existing travel interpolation in `getBobPosition` becomes a lot more realistic with max_g input.

**Global-enrichment opportunity.**
- Ship fates: track each named ship from creation through destruction across movements + combat + destructions.
- Route efficiency analysis: which Bobs took the fastest routes?

---

### pov_knowledge (on metadata)

**What it is.** `metadata.pov_knowledge.believes`, `.learns`, `.unaware_of` - what the POV character thinks they know at this point in the chapter.

**What it enables.**
- **"POV glasses" overlay** - a reader-mode toggle where the map shows what the POV knows rather than what's objectively true. Riker at Sol in 2160 doesn't know about Deltans yet; toggle the overlay and Delta Eridani dims.
- **Irony highlights** - when a POV `believes` something the reader knows is false, flag it subtly.
- **Learning curve visualization** - per-character, how often do they have `learns` entries? Tracks their arc of discovery.

**Merge step.**
- Pass through as-is on `data.json.chapter_meta[ch].pov_knowledge`.
- Global-enrichment can build a per-character "what they know at chapter N" timeline, but per-chapter pass is enough for a decent first version.

**Client accumulation.**
- Straightforward chapter-gate. When rendering POV-glasses overlay, walk each POV's chapters up to `ch` and union their `learns`; subtract things the reader knows from other POVs.

**Global-enrichment opportunity.**
- Build a full "knowledge graph per character". Currently each chapter only knows what its own POV knows in isolation.
- Detect dramatic irony: when POV A's `believes` contradicts POV B's known truth, flag the gap.

---

## Tier 3: nice to have

### human_colonies

**What it is.** Per-event records for human settlements - foundings, population updates, governor changes, catastrophes, abandonments. More specific than `infrastructure[type=colony]`: that's the container, this is the sociology.

**What it enables.**
- **Populated-worlds panel** - "as of year Y, humans live at: Omicron2 Eridani 3 (2M), Delta Pavonis b (450k), ...".
- **Human-presence color** on the map - a planet with a colony glows green; gets bigger as population grows.
- **Colonial history timelines** - per-colony scroll through founding → growth → crises.

**Merge step.**
- Collect, key by (system, planet, name).
- Walk events to derive current population + governor at any point.
- Ship `data.json.human_colonies` = { key: { founded_ch, current_population, governor_history, events[] } }.

**Client accumulation.**
- Chapter-gate walk. UI re-renders the populated-worlds panel as the slider moves.

**Global-enrichment opportunity.**
- Link colonists to their ships of origin.
- Cultural flavor: one sentence per colony describing its distinctive character (religious, scientific, libertarian).

**Overlap with infrastructure.** If both fields exist for the same place, merge.py should link them: the `infrastructure[type=colony]` entry is the physical settlement, the `human_colonies` entry is its sociology. Both share (system, planet, owner) but track different facets.

---

### relationships

**What it is.** Character-to-character bonds: friendship, rivalry, romance, mentor/mentee, alliance, enmity. Per-chapter entries track the relationship changing (`established | strengthened | strained | broken | ended_by_death`).

**What it enables.**
- **Social graph view** - a force-directed graph of all named characters with edges colored by relationship type. Animates over time as slider moves.
- **Character profile: "relationships" tab** - click any Bob to see their known bonds and conflicts.
- **"Who should be in the same scene?" suggestion** - for fan-fic companion use, suggest characters whose arcs intersect.

**Merge step.**
- Collect, key by (sorted_names_pair, type). Walk events to derive current-state.
- Derive `current_status` per pair: `none | cordial | close | strained | hostile | broken | dead`.
- Ship `data.json.relationships` = list of records with timeline.

**Client accumulation.**
- Chapter-gate walk. Graph redraws on slider change.

**Global-enrichment opportunity.**
- Arc detection: "Bob and Archimedes went from stranger to mentor over 8 chapters."
- Relationship intensity scoring: rank pairs by how much narrative time they consume.

**Overlap with bob_personality.** Personality is static (who the character IS). Relationships are dynamic (who the character KNOWS and how). Bob's trait "hot-tempered" is personality; "Bob argues with Homer" is a relationship event.

---

### scenes

**What it is.** Subdivides a chapter into its component scenes when the chapter has `***` breaks or internal time jumps. Each scene has `order`, `location`, `time_offset`, optional distinct `pov`, and a one-line `summary`.

**What it enables.**
- **Finer slider granularity** - the timeline slider can land on a specific scene within a chapter rather than just chapter-level.
- **Scene-level time placement** - a chapter dated "July 2145" can span multiple months internally; each scene gets plotted separately on the year axis.
- **"Chapter density" visualization** - chapters with many scenes appear denser on the timeline.

**Merge step.**
- Compute a `year_precise` for each scene, inheriting from chapter + offset. If the LLM gives "3 months later", code can add 0.25 to the chapter's year_precise.
- Ship `data.json.scenes_by_chapter` = { ch: [{ order, year_precise, location, summary }] }.

**Client accumulation.**
- Chapter-gate filter.
- Slider update logic: within a chapter, lerp between scene year_precise values for fine-grained Bob position.

**Global-enrichment opportunity.**
- Better time-offset parsing ("the next morning" → 0.003 years).
- Link scenes that span multiple chapters (e.g. the Medeiros battle stretches across multiple scene-breaks).

---

### incoming_threats

**What it is.** Radar-style records of hostile or unknown forces detected as approaching a system, with an ETA. Closes when the threat engages (at which point the chapter should log `combat` or `alien_species`).

**What it enables.**
- **Threat board panel** - "Incoming: Brazilian probe at Epsilon Eridani, ETA 2144" style sidebar.
- **Radar lines on the map** - draw an incoming vector from the threat's `origin` to `detected_at`, fading in as ETA approaches.
- **Tension scoring** - count of active threats is a narrative-tension heuristic.

**Merge step.**
- Collect threats. Match each threat to its "arrival" event (combat/alien_species entry in a later chapter) using proximity in text similarity + time.
- A threat with no matching arrival event is "ongoing" or "went nowhere".
- Ship `data.json.incoming_threats` = list of records with `resolved_chapter` + `resolution` fields filled in by the merge step.

**Client accumulation.**
- At chapter `ch`, a threat is active if `detected_chapter <= ch` and `resolved_chapter IS NULL OR resolved_chapter > ch`.
- ETA-aware rendering: fade-in on map approaches as slider year approaches the `eta_year`.

**Global-enrichment opportunity.**
- Automated threat-to-outcome matching across chapters.
- Severity scoring: "this threat wiped out a colony" vs "this threat was a false alarm".

**Overlap with communications.** A SUDDAR ping detecting an incoming probe is both a communication (sensor event) and an incoming threat. Extract both and let merge.py link them by the same chapter + system.

---

## Global-enrichment pass ideas (out of scope for extract.py)

Fields that probably only work well with all chapters in context:

- **Character arcs:** per-character emotional trajectory across the series.
- **Foreshadowing resolutions:** "This line in chapter 5 pays off in chapter 42."
- **Retroactive categorization:** Some chapters only become "political" or "first-contact" in hindsight.
- **Canonical name cleanup:** enforce one spelling across the corpus.
- **Cross-reference link graph:** "Bob mentions X (ch 12)" → link to X's first appearance.
- **Theme clustering:** group chapters into story arcs (Sol arc, Deltan arc, Others arc).
- **Character death foreshadowing:** did the text hint this was coming?

The enrichment pass takes `extracted/*.json` + curated cast list and produces
`enriched/*.json` with the same per-chapter structure plus new cross-chapter
fields. Merge.py reads both.
