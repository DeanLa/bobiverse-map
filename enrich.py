# /// script
# requires-python = ">=3.11"
# dependencies = ["openai", "pydantic"]
# ///
"""Single-shot enrichment pass over all extracted chapters of one book.

Reads every extracted/{book}/*.json, condenses it for the LLM, calls the model
once with structured output, and writes enriched/{book}.json.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic output models
# ---------------------------------------------------------------------------


class CanonicalCharacter(BaseModel):
    name: str = Field(description="Canonical display name")
    type: Literal["replicant", "human", "ai", "alien_individual", "ship"]
    parent: str | None = Field(default=None, description="Canonical parent/creator name")
    generation: int | None = None
    faction: str | None = None
    first_chapter: int
    last_chapter: int
    status: Literal["active", "destroyed", "presumed_destroyed", "survived", "unknown"]
    aliases: list[str] = Field(default_factory=list, description="Alternate spellings seen")


class CharacterArc(BaseModel):
    name: str = Field(description="Canonical name matching canonical_cast")
    arc: str = Field(description="2-4 sentences describing the character's trajectory across the corpus")


class PlotArc(BaseModel):
    name: str = Field(description="Short arc name like 'Bob at FAITH'")
    chapter_start: int
    chapter_end: int
    description: str = Field(description="One-sentence summary")
    key_characters: list[str] = Field(default_factory=list)


class ImplicitResolution(BaseModel):
    character: str = Field(description="Canonical name")
    original_chapter: int = Field(description="Chapter where presumed destruction occurred")
    outcome: Literal["confirmed_destroyed", "survived"]
    reasoning: str = Field(description="One sentence explaining the call")


class CanonicalTech(BaseModel):
    name: str = Field(description="Canonical short name")
    description: str = Field(description="One-line description")
    aliases: list[str] = Field(default_factory=list)
    first_mentioned_chapter: int | None = None
    first_invented_chapter: int | None = None
    first_deployed_chapter: int | None = None
    tier: Literal["foundational", "applied", "weapons", "comms", "infrastructure", "medical", "unknown"] = "unknown"


class CanonicalFaction(BaseModel):
    name: str = Field(description="Canonical faction name")
    description: str = Field(description="One-sentence summary of what they are")
    aliases: list[str] = Field(default_factory=list)
    first_chapter: int | None = None
    trajectory: str = Field(description="Short trajectory like 'dominant → fractured → collapsed'")


class NamedCombat(BaseModel):
    name: str = Field(description="Canonical battle name, e.g. 'Battle of Epsilon Eridani, 2144'")
    chapter: int
    year: int | None = None
    location: str
    participants: list[str] = Field(default_factory=list, description="Canonical participant names")
    outcome: str = Field(description="One-line outcome")


class NameAlias(BaseModel):
    variant: str
    canonical: str
    kind: Literal["character", "star_system", "planet", "ship", "technology", "faction", "species"]


class Enrichment(BaseModel):
    canonical_cast: list[CanonicalCharacter]
    name_aliases: list[NameAlias]
    character_arcs: list[CharacterArc]
    plot_arcs: list[PlotArc]
    resolutions_implicit: list[ImplicitResolution]
    technology_canonical: list[CanonicalTech]
    faction_canonical: list[CanonicalFaction]
    combat_named: list[NamedCombat]


# ---------------------------------------------------------------------------
# Input condensation
# ---------------------------------------------------------------------------


def condense_chapter(d: dict) -> dict:
    """Reduce a chapter extraction to the fields the enricher needs."""
    m = d["metadata"]
    s = d["summary"]
    return {
        "chapter": m["chapter"],
        "year": m["year"],
        "month": m.get("month"),
        "pov": m["pov"],
        "location": m["location"],
        "one_line": s["one_line"],
        "paragraph": s["paragraph"],
        "characters_present": [
            {"name": c["name"], "type": c["type"], "status": c.get("status")}
            for c in d.get("characters_present", [])
        ],
        "new_characters": [
            {
                "name": c["name"],
                "type": c["type"],
                "parent": c.get("parent"),
                "generation": c.get("generation"),
                "faction": c.get("faction"),
                "personality_traits": (c.get("personality") or {}).get("traits", []),
                "role": (c.get("personality") or {}).get("role"),
            }
            for c in d.get("new_characters", [])
        ],
        "destructions": [
            {"name": x["name"], "certainty": x["certainty"], "cause": x.get("cause")}
            for x in d.get("destructions", [])
        ],
        "resolutions": [
            {"character": r["character"], "outcome": r["outcome"]}
            for r in d.get("resolutions", [])
        ],
        "movements": [
            {"char": m["character"], "type": m["type"], "from": m.get("from"), "to": m.get("to")}
            for m in d.get("movements", [])
        ],
        "star_systems": [
            {"name": ss["name"], "role": ss["role"]}
            for ss in d.get("star_systems", [])
        ],
        "planets_discovered": [
            p["name"] for p in d.get("planets", []) if p.get("status") == "discovered"
        ],
        "technologies": [
            {"name": t["name"], "event": t["event"], "by": t.get("by")}
            for t in d.get("technologies", [])
        ],
        "factions_in_events": sorted({fe["faction"] for fe in d.get("faction_events", [])}),
        "alien_species": [
            {"name": sp["name"], "event": sp["event"]}
            for sp in d.get("alien_species", [])
        ],
        "combat": [
            {
                "location": c["location"],
                "victor": c.get("victor"),
                "participants": [p["name"] for p in c.get("participants", [])],
            }
            for c in d.get("combat", [])
        ],
        "threads_opened": [{"id": t["id"], "text": t.get("text")} for t in d.get("threads_opened", [])],
        "threads_resolved": [t["id"] for t in d.get("threads_resolved", [])],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="One-shot enrichment over all extracted chapters")
    parser.add_argument("--book", type=int, required=True)
    parser.add_argument("--model", default="gpt-5.4-2026-03-05")
    args = parser.parse_args()

    root = Path(__file__).parent
    chapter_files = sorted(glob.glob(str(root / "extracted" / str(args.book) / "*.json")))
    if not chapter_files:
        sys.exit(f"No extracted chapters found for book {args.book}")

    condensed = []
    for f in chapter_files:
        d = json.loads(Path(f).read_text())
        condensed.append(condense_chapter(d))

    system_prompt = (root / "prompts" / "enrich.md").read_text()
    user_message = (
        f"Book {args.book} contains {len(condensed)} chapters. Here is the condensed extraction:\n\n"
        + json.dumps(condensed, ensure_ascii=False, indent=2)
    )

    print(f"Enriching book {args.book} from {len(chapter_files)} chapters...")
    print(f"Input size: ~{len(user_message) / 1024:.1f} KB ({len(user_message) // 4} tokens approx)")

    client = OpenAI()
    completion = client.beta.chat.completions.parse(
        model=args.model,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        response_format=Enrichment,
    )

    enrichment = completion.choices[0].message.parsed
    if enrichment is None:
        sys.exit("Error: model returned no parsed output (possible refusal)")

    out_dir = root / "enriched"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{args.book}.json"
    out_path.write_text(json.dumps(enrichment.model_dump(), indent=2, ensure_ascii=False) + "\n")

    # Summary to stdout
    print(f"Written: {out_path}")
    print(
        f"  canonical_cast={len(enrichment.canonical_cast)}  "
        f"aliases={len(enrichment.name_aliases)}  "
        f"arcs={len(enrichment.character_arcs)}  "
        f"plot_arcs={len(enrichment.plot_arcs)}"
    )
    print(
        f"  resolutions={len(enrichment.resolutions_implicit)}  "
        f"tech={len(enrichment.technology_canonical)}  "
        f"factions={len(enrichment.faction_canonical)}  "
        f"combats={len(enrichment.combat_named)}"
    )


if __name__ == "__main__":
    main()
