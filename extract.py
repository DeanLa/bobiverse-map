# /// script
# requires-python = ">=3.11"
# dependencies = ["openai", "pydantic"]
# ///
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class PovKnowledge(BaseModel):
    believes: list[str] = Field(
        default_factory=list,
        description="Things the POV treats as true but may be wrong or out of date",
    )
    learns: list[str] = Field(
        default_factory=list,
        description="Facts new to the POV this chapter",
    )
    unaware_of: list[str] = Field(
        default_factory=list,
        description="Things the reader/others know that the POV does not; only fill if the narration makes this contrast explicit",
    )


class ChapterMetadata(BaseModel):
    chapter: int = Field(description="Integer chapter number from the header")
    pov: str = Field(description="Character whose perspective this chapter is told from")
    year: int = Field(description="Integer year from the chapter header")
    month: str | None = Field(description="Full month name from header, or null if only year given")
    location: str = Field(description="Star system from header. Use 'Sol' for Earth. Use 'in_transit' if traveling.")
    notes: str | None = Field(description="Flag ambiguity about dating or location, or null")
    pov_knowledge: PovKnowledge = Field(
        default_factory=PovKnowledge,
        description="What the POV character thinks they know, learns, or is unaware of in this chapter",
    )


class CharacterPresent(BaseModel):
    name: str = Field(description="Canonical character name matching the recap")
    type: Literal["replicant", "human", "ai", "alien_individual", "alien_species", "ship"]
    location: str = Field(description="Star system where character is")
    status: Literal["active", "in_transit", "destroyed", "presumed_destroyed", "mentioned_only"]
    transit_from: str | None = Field(description="If in_transit, origin star system")
    transit_to: str | None = Field(description="If in_transit, destination star system")
    notes: str | None = None


class Personality(BaseModel):
    traits: list[str] = Field(
        default_factory=list,
        description="2-5 short adjectives the chapter actually establishes (e.g. 'scholarly', 'hot-tempered')",
    )
    role: Literal[
        "researcher", "explorer", "diplomat", "combat",
        "colony_admin", "autofactory", "unknown",
    ] = Field(default="unknown", description="The niche the character fills among the Bobs")
    nickname_origin: str | None = Field(
        default=None,
        description="Why the character chose their name (e.g. 'Homer Simpson reference'). Null if not explained.",
    )
    quirks: str | None = Field(
        default=None,
        description="One-line memorable description of what makes them distinct",
    )


class NewCharacter(BaseModel):
    name: str = Field(description="Canonical name for new character")
    type: Literal["replicant", "human", "ai", "alien_individual", "alien_species", "ship"]
    parent: str | None = Field(description="Creator/parent name, e.g. 'Bob' for his clones")
    generation: int | None = Field(description="Clone generation (Bob=1, his clones=2, etc). Null for non-replicants.")
    location: str = Field(description="Star system where introduced")
    faction: str | None = Field(description="e.g. 'FAITH', 'Brazilian Empire', null for Bobs")
    personality: Personality = Field(
        default_factory=Personality,
        description="Character personality sketch. Bobs especially should have traits and role filled.",
    )
    notes: str | None = None


class Destruction(BaseModel):
    name: str = Field(description="Destroyed character/entity name")
    type: Literal["replicant", "human", "ai", "alien_individual", "alien_species", "ship"]
    cause: str = Field(description="One sentence describing cause of destruction")
    location: str = Field(description="Star system where destruction occurred")
    certainty: Literal["confirmed", "presumed"] = Field(
        description="'confirmed' if definitively destroyed on-page, 'presumed' if likely dead but not certain"
    )


class Resolution(BaseModel):
    character: str = Field(description="Character whose fate is being resolved")
    original_chapter: int = Field(description="Chapter where the presumed destruction occurred")
    outcome: Literal["confirmed_destroyed", "survived"] = Field(
        description="Whether the character is confirmed dead or revealed to have survived"
    )
    notes: str | None = None


class Movement(BaseModel):
    character: str = Field(description="Name of character who moved")
    type: Literal["departure", "arrival"]
    from_system: str = Field(alias="from", description="Origin star system")
    to_system: str = Field(alias="to", description="Destination star system")
    ship: str | None = Field(default=None, description="Ship the character is traveling on, if named")
    companions: list[str] = Field(
        default_factory=list,
        description="Other characters traveling on the same ship",
    )
    cargo: str | None = Field(default=None, description="Short description of cargo if notable")
    drive: Literal["SURGE", "chemical", "unknown"] = Field(
        default="unknown",
        description="Propulsion type. SURGE is default post-2145 Bob drive.",
    )
    max_g: float | None = Field(default=None, description="Peak acceleration in G, if stated")
    notes: str | None = Field(default=None, description="Context like 'with colony ships' or 'pursuing Medeiros'")

    model_config = {"populate_by_name": True}


class StarSystem(BaseModel):
    name: str = Field(description="Canonical star system name")
    role: Literal["setting", "destination", "mentioned", "discovered"]
    notes: str | None = None


class Planet(BaseModel):
    name: str = Field(description="Planet name if named, otherwise 'System N' like 'Delta Eridani 3'")
    star_system: str = Field(description="Parent star system")
    orbital_position: int | None = Field(description="Planet number from star, or null")
    type: Literal["rocky", "gas_giant", "moon", "asteroid_belt"]
    habitable: bool | None = None
    features: str | None = Field(default=None, description="Brief: atmosphere, water, life, resources")
    life: str | None = Field(default=None, description="Description of life discovered, or null")
    status: Literal["discovered", "surveyed", "colonized", "mentioned"]
    notes: str | None = None


class Technology(BaseModel):
    name: str = Field(description="Short canonical name, e.g. 'SCUT', 'SURGE drive'")
    full_name: str | None = Field(
        default=None,
        description="Full or descriptive name, e.g. 'Subspace Communication'",
    )
    event: Literal["mentioned", "invented", "first_tested", "deployed", "upgraded", "failed"]
    by: str | None = Field(default=None, description="Character or faction responsible")
    location: str | None = Field(default=None, description="Star system where the event happens")
    notes: str | None = None


class FactionEvent(BaseModel):
    faction: str = Field(description="Canonical faction name, e.g. 'FAITH', 'USE', 'Brazilian Empire'")
    type: Literal[
        "founded", "war_declared", "war_ended", "treaty",
        "coup", "collapse", "internal_purge", "leadership_change",
        "territory_change", "policy_change", "persecution",
    ]
    counterparty: str | None = Field(default=None, description="Other faction involved, if any")
    text: str = Field(description="One sentence describing what happened")
    location: str | None = None
    notes: str | None = None


class Communication(BaseModel):
    from_character: str = Field(description="Sender name")
    from_system: str = Field(description="Sending star system")
    to_character: str = Field(description="Recipient name, or 'broadcast'")
    to_system: str | None = Field(
        default=None,
        description="Receiving star system, or null for broadcast",
    )
    medium: Literal["radio", "SCUT", "SUDDAR_ping", "BobNet", "courier", "unknown"]
    direction: Literal["sent", "received", "both"]
    contents_summary: str = Field(description="One-sentence message content")
    notes: str | None = None


class CombatParticipant(BaseModel):
    name: str
    side: Literal["A", "B", "C"]
    ship: str | None = None
    outcome: Literal[
        "unharmed", "damaged", "disabled", "captured",
        "destroyed", "presumed_destroyed", "retreated",
    ]


class Combat(BaseModel):
    participants: list[CombatParticipant]
    location: str
    weapons: list[str] = Field(default_factory=list)
    victor: Literal["A", "B", "C", "draw", "inconclusive"]
    duration: Literal["brief skirmish", "prolonged battle", "siege"] | None = None
    notes: str | None = None


class AlienSpecies(BaseModel):
    name: str = Field(description="Species name if given, else descriptive")
    event: Literal[
        "first_sighting", "first_contact", "peaceful_interaction",
        "conflict", "observation", "discovery_of_artifact",
    ]
    location: str = Field(description="Star system")
    planet: str | None = None
    tech_level: Literal[
        "pre-industrial", "bronze_age", "industrial",
        "space-faring", "post-human", "unknown",
    ] = "unknown"
    intelligent: bool | None = None
    hostile: bool | None = None
    notes: str | None = None


class Event(BaseModel):
    text: str = Field(description="Short factual description, one sentence")
    characters: list[str] = Field(description="Names of characters involved")
    significance: Literal["major", "minor"]
    type: Literal["discovery", "creation", "destruction", "battle", "political", "technology", "social", "travel"]


class Infrastructure(BaseModel):
    system: str = Field(description="Star system the facility is in")
    type: Literal[
        "autofactory", "mining_base", "skunk_works", "colony",
        "radio_relay", "clone_facility", "defensive_array",
        "shipyard", "research_station",
    ]
    event: Literal["established", "expanded", "destroyed", "upgraded", "abandoned"]
    owner: str = Field(description="Character or faction operating it")
    notes: str | None = None


class HumanColony(BaseModel):
    name: str = Field(description="Colony name if given, else descriptive")
    planet: str
    system: str
    event: Literal[
        "founded", "population_update", "governor_change",
        "catastrophe", "independence", "abandoned",
    ]
    population: int | None = None
    governor: str | None = None
    origin: str | None = Field(default=None, description="Where the colonists came from, if stated")
    notes: str | None = None


class Relationship(BaseModel):
    a: str = Field(description="First character name")
    b: str = Field(description="Second character name")
    type: Literal[
        "friendship", "rivalry", "romance", "mentor",
        "parent_child", "allies", "enemies", "working_partners",
    ]
    event: Literal["established", "strengthened", "strained", "broken", "ended_by_death"]
    text: str = Field(description="One-sentence description of the change in this chapter")
    notes: str | None = None


class Scene(BaseModel):
    order: int = Field(description="1-based scene index within the chapter")
    location: str
    time_offset: str | None = Field(
        default=None,
        description="Relative time from chapter start (e.g. '3 months later', 'the next morning')",
    )
    pov: str | None = Field(
        default=None,
        description="POV character if different from chapter POV",
    )
    summary: str = Field(description="One-sentence scene summary")


class IncomingThreat(BaseModel):
    threat: str = Field(description="Short descriptor, e.g. 'Brazilian probe'")
    detected_at: str = Field(description="Star system that detected the threat")
    origin: str | None = Field(default=None, description="Where the threat came from, if known")
    eta_year: int | None = Field(default=None, description="Year the threat is expected to arrive")
    nature: Literal["hostile", "unknown", "peaceful", "ambiguous"]
    notes: str | None = None


class Quote(BaseModel):
    speaker: str
    text: str = Field(description="Verbatim quote, one sentence")
    context: str = Field(description="One-line context for when/why it was said")


class ThreadOpened(BaseModel):
    id: str = Field(description="Short kebab-case identifier, stable across chapters")
    text: str = Field(description="One-sentence description of the unresolved setup")


class ThreadResolved(BaseModel):
    id: str = Field(description="Must match the id from a prior threads_opened entry")
    text: str = Field(description="One sentence describing how the thread resolved")


class Summary(BaseModel):
    one_line: str = Field(description="Newspaper headline style, one sentence")
    paragraph: str = Field(description="3-5 sentences covering key developments")
    events: list[str] = Field(
        description="Narrative event list ordered by appearance in the chapter. "
        "Each entry is a short natural sentence describing what happens, "
        "written so they read naturally in sequence like a story recap."
    )
    themes: list[str] = Field(
        default_factory=list,
        description="1-4 thematic tags like 'first-contact', 'politics', 'replicant-philosophy'",
    )
    mood: Literal[
        "tense", "reflective", "triumphant", "grief",
        "comedic", "mundane", "hopeful", "dread",
    ] = Field(default="mundane", description="Single dominant emotional tone")
    pov_emotional_arc: str | None = Field(
        default=None,
        description="One sentence on what the POV character experiences emotionally",
    )


# --- World state (structured recap) ---


class CharacterState(BaseModel):
    name: str
    type: Literal["replicant", "human", "ai", "alien_individual", "alien_species", "ship"]
    location: str
    status: Literal["active", "destroyed", "presumed_destroyed"]
    destroyed_chapter: int | None = None
    last_seen_chapter: int | None = None


class RecentEvent(BaseModel):
    chapter: int
    text: str


class OpenThread(BaseModel):
    id: str
    text: str
    opened_chapter: int


class WorldState(BaseModel):
    chapters_processed: int = 0
    active_characters: list[CharacterState] = Field(default_factory=list)
    known_star_systems: list[str] = Field(default_factory=list)
    known_planets: list[str] = Field(default_factory=list)
    known_technologies: list[str] = Field(default_factory=list)
    known_factions: list[str] = Field(default_factory=list)
    known_species: list[str] = Field(default_factory=list)
    open_threads: list[OpenThread] = Field(default_factory=list)
    recent_events: list[RecentEvent] = Field(default_factory=list)


# --- Top-level extraction model ---


class ChapterExtraction(BaseModel):
    metadata: ChapterMetadata
    characters_present: list[CharacterPresent]
    new_characters: list[NewCharacter]
    destructions: list[Destruction]
    resolutions: list[Resolution]
    movements: list[Movement]
    star_systems: list[StarSystem]
    planets: list[Planet]
    technologies: list[Technology]
    faction_events: list[FactionEvent]
    communications: list[Communication]
    combat: list[Combat]
    alien_species: list[AlienSpecies]
    infrastructure: list[Infrastructure]
    human_colonies: list[HumanColony]
    relationships: list[Relationship]
    scenes: list[Scene]
    incoming_threats: list[IncomingThreat]
    quotes: list[Quote]
    threads_opened: list[ThreadOpened]
    threads_resolved: list[ThreadResolved]
    events: list[Event]
    summary: Summary


# ---------------------------------------------------------------------------
# World state logic
# ---------------------------------------------------------------------------


def build_world_state(prev: WorldState, extraction: ChapterExtraction) -> WorldState:
    ch = extraction.metadata.chapter
    characters = list(prev.active_characters)
    systems = list(prev.known_star_systems)
    planets = list(prev.known_planets)
    events = list(prev.recent_events)

    existing_names = {c.name for c in characters}

    present_names = {cp.name for cp in extraction.characters_present}
    for nc in extraction.new_characters:
        present_names.add(nc.name)

    for nc in extraction.new_characters:
        if nc.name not in existing_names:
            characters.append(CharacterState(
                name=nc.name,
                type=nc.type,
                location=nc.location,
                status="active",
                last_seen_chapter=ch,
            ))
            existing_names.add(nc.name)

    for c in characters:
        if c.name in present_names:
            c.last_seen_chapter = ch

    for d in extraction.destructions:
        for c in characters:
            if c.name == d.name:
                c.status = "destroyed" if d.certainty == "confirmed" else "presumed_destroyed"
                c.destroyed_chapter = ch
                break

    for r in extraction.resolutions:
        for c in characters:
            if c.name == r.character:
                if r.outcome == "confirmed_destroyed":
                    c.status = "destroyed"
                else:
                    c.status = "active"
                    c.destroyed_chapter = None
                break

    for m in extraction.movements:
        for c in characters:
            if c.name == m.character:
                if m.type == "departure":
                    c.location = f"in transit to {m.to_system}"
                else:
                    c.location = m.to_system
                break

    for ss in extraction.star_systems:
        if ss.name not in systems:
            systems.append(ss.name)

    for p in extraction.planets:
        if p.name not in planets:
            planets.append(p.name)

    technologies = list(prev.known_technologies)
    for t in extraction.technologies:
        if t.name not in technologies:
            technologies.append(t.name)

    factions = list(prev.known_factions)
    for fe in extraction.faction_events:
        if fe.faction not in factions:
            factions.append(fe.faction)
    for nc in extraction.new_characters:
        if nc.faction and nc.faction not in factions:
            factions.append(nc.faction)

    species = list(prev.known_species)
    for sp in extraction.alien_species:
        if sp.name not in species:
            species.append(sp.name)

    open_threads = list(prev.open_threads)
    resolved_ids = {r.id for r in extraction.threads_resolved}
    open_threads = [t for t in open_threads if t.id not in resolved_ids]
    existing_thread_ids = {t.id for t in open_threads}
    for to in extraction.threads_opened:
        if to.id not in existing_thread_ids:
            open_threads.append(OpenThread(id=to.id, text=to.text, opened_chapter=ch))

    events.append(RecentEvent(chapter=ch, text=extraction.summary.one_line))
    events = events[-5:]

    return WorldState(
        chapters_processed=ch,
        active_characters=characters,
        known_star_systems=systems,
        known_planets=planets,
        known_technologies=technologies,
        known_factions=factions,
        known_species=species,
        open_threads=open_threads,
        recent_events=events,
    )


def world_state_to_recap(ws: WorldState, next_chapter: int) -> str:
    if ws.chapters_processed == 0:
        return ""

    lines = [f"WORLD STATE BEFORE CHAPTER {next_chapter} (chapters 0-{ws.chapters_processed} processed):", ""]

    active = [c for c in ws.active_characters if c.status == "active"]
    destroyed = [c for c in ws.active_characters if c.status == "destroyed"]
    presumed = [c for c in ws.active_characters if c.status == "presumed_destroyed"]

    stale_threshold = next_chapter - 10

    replicants = [c for c in active if c.type == "replicant"]
    if replicants:
        lines.append("Active replicants:")
        for c in replicants:
            lines.append(f"  {c.name} - {c.location}")
        lines.append("")

    humans = [c for c in active if c.type == "human"]
    recent_humans = [c for c in humans if (c.last_seen_chapter or 0) >= stale_threshold]
    stale_humans = [c for c in humans if (c.last_seen_chapter or 0) < stale_threshold]
    if recent_humans:
        lines.append("Named humans (recently active):")
        for c in recent_humans:
            lines.append(f"  {c.name} - {c.location}")
        lines.append("")
    if stale_humans:
        names = ", ".join(c.name for c in stale_humans)
        lines.append(f"Other known humans (not seen recently): {names}")
        lines.append("")

    others = [c for c in active if c.type not in ("replicant", "human")]
    if others:
        lines.append("Other entities:")
        for c in others:
            lines.append(f"  {c.name} ({c.type}) - {c.location}")
        lines.append("")

    if destroyed:
        lines.append("Destroyed:")
        for c in destroyed:
            lines.append(f"  {c.name} (ch {c.destroyed_chapter})")
        lines.append("")

    if presumed:
        lines.append("Presumed destroyed:")
        for c in presumed:
            lines.append(f"  {c.name} (ch {c.destroyed_chapter})")
        lines.append("")

    if not destroyed and not presumed:
        lines.append("Destroyed: none yet")
        lines.append("")

    lines.append(f"Known star systems: {', '.join(ws.known_star_systems)}")
    lines.append("")

    if ws.known_planets:
        lines.append("Known planets:")
        for p in ws.known_planets:
            lines.append(f"  {p}")
        lines.append("")

    if ws.known_technologies:
        lines.append(f"Known technologies (use these canonical names): {', '.join(ws.known_technologies)}")
        lines.append("")

    if ws.known_factions:
        lines.append(f"Known factions (use these canonical names): {', '.join(ws.known_factions)}")
        lines.append("")

    if ws.known_species:
        lines.append(f"Known alien species: {', '.join(ws.known_species)}")
        lines.append("")

    if ws.open_threads:
        threads_by_recency = sorted(ws.open_threads, key=lambda t: t.opened_chapter, reverse=True)
        shown_threads = threads_by_recency[:15]
        omitted = len(ws.open_threads) - len(shown_threads)
        lines.append("Open plot threads (use these ids if resolving):")
        for t in shown_threads:
            lines.append(f"  [{t.id}] (opened ch {t.opened_chapter}) {t.text}")
        if omitted > 0:
            lines.append(f"  ... and {omitted} older threads (still open, ids available in world state)")
        lines.append("")

    if ws.recent_events:
        lines.append(f"Recent events (last {len(ws.recent_events)} chapters):")
        for e in ws.recent_events:
            lines.append(f"  Ch {e.chapter}: {e.text}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File finding
# ---------------------------------------------------------------------------


def find_chapter_file(book_dir: Path, chapter: int) -> Path:
    prefix = f"{chapter} "
    for f in sorted(book_dir.iterdir()):
        if f.name.startswith(prefix) and f.suffix == ".md":
            return f
    sys.exit(f"Error: no file starting with '{prefix}' in {book_dir}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Extract structured data from a Bobiverse chapter")
    parser.add_argument("--book", type=int, required=True, help="Book number")
    parser.add_argument("--ch", type=int, required=True, help="Chapter number")
    args = parser.parse_args()

    root = Path(__file__).parent
    book_dir = root / "Books" / str(args.book)
    if not book_dir.is_dir():
        sys.exit(f"Error: book directory not found: {book_dir}")

    chapter_file = find_chapter_file(book_dir, args.ch)
    chapter_text = chapter_file.read_text()

    system_prompt_path = root / "prompts" / "system.md"
    if not system_prompt_path.exists():
        sys.exit(f"Error: system prompt not found: {system_prompt_path}")
    system_prompt = system_prompt_path.read_text()

    extracted_dir = root / "extracted" / str(args.book)
    extracted_dir.mkdir(parents=True, exist_ok=True)

    # Load previous world state
    if args.ch <= 1:
        prev_world_state = WorldState()
    else:
        prev_ch = args.ch - 1
        prev_file = extracted_dir / f"{prev_ch:02d}.json"
        if not prev_file.exists():
            sys.exit(f"Error: chapter {prev_ch} not yet extracted. Run chapters in order.\n"
                     f"  Expected: {prev_file}")
        prev_data = json.loads(prev_file.read_text())
        prev_world_state = WorldState(**prev_data["world_state_after"])

    recap_text = world_state_to_recap(prev_world_state, args.ch)

    # Build user message
    user_parts = []
    if recap_text:
        user_parts.append(recap_text)
        user_parts.append("---\n")
    user_parts.append(chapter_text)
    user_message = "\n".join(user_parts)

    # Call OpenAI
    client = OpenAI()
    print(f"Extracting chapter {args.ch} from {chapter_file.name}...")

    completion = client.beta.chat.completions.parse(
        model="gpt-5.4-2026-03-05",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        response_format=ChapterExtraction,
    )

    extraction = completion.choices[0].message.parsed
    if extraction is None:
        sys.exit("Error: model returned no parsed output (possible refusal)")

    # Build world state after this chapter
    new_world_state = build_world_state(prev_world_state, extraction)

    # Write output
    output = extraction.model_dump(by_alias=True)
    output["world_state_after"] = new_world_state.model_dump()

    out_path = extracted_dir / f"{args.ch:02d}.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")

    print(f"Written: {out_path}")
    print(f"Summary: {extraction.summary.one_line}")


if __name__ == "__main__":
    main()
