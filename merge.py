# /// script
# requires-python = ">=3.11"
# ///
"""Merge extracted chapter data + enrichment into final data.json.

Reads:
  extracted/{book}/*.json    per-chapter LLM extractions
  enriched/{book}.json       cross-chapter LLM enrichment
  data.json                  current data.json (for star coords + books 2/3)

Writes:
  data.json                  rebuilt with book 1 regenerated from extractions

Preserves stars (astronomical coordinates) and books 2/3 (hand-curated).
Regenerates book 1 bobs/travels/events/chapters from extractions.
Adds new top-level fields: technologies, communications, combat, infrastructure,
personalities, character_arcs, plot_arcs, factions, faction_events, alien_species,
threads, quotes, themes, scenes, incoming_threats.
"""
from __future__ import annotations

import glob
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
BOOK = 1


# ---------------------------------------------------------------------------
# Year precision
# ---------------------------------------------------------------------------

MONTH_TO_FRAC = {
    "January": 0.04, "February": 0.12, "March": 0.21, "April": 0.29,
    "May": 0.37, "June": 0.46, "July": 0.54, "August": 0.62,
    "September": 0.71, "October": 0.79, "November": 0.87, "December": 0.96,
}


def year_precise(year: int, month: str | None) -> float:
    if not year:
        return 0.0
    return float(year) + MONTH_TO_FRAC.get(month or "", 0.5)


# ---------------------------------------------------------------------------
# Name normalizer (cycle-safe)
# ---------------------------------------------------------------------------


class Normalizer:
    """Resolves variant → canonical name with cycle detection.

    Built from enriched name_aliases. We honor existing data.json star keys
    as ground truth (their canonical wins over the enricher's choice).
    """

    def __init__(self, aliases: list[dict], existing_stars: set[str]):
        self.map: dict[str, str] = {}
        self.existing_stars = existing_stars
        for a in aliases:
            v, c = a["variant"], a["canonical"]
            if v == c:
                continue
            # If either side matches an existing star key, prefer that side as canonical
            if a.get("kind") == "star_system":
                if v in existing_stars and c not in existing_stars:
                    self.map[c] = v
                    continue
                if c in existing_stars and v not in existing_stars:
                    self.map[v] = c
                    continue
            self.map[v] = c

    def __call__(self, name: str | None) -> str | None:
        if name is None:
            return None
        seen = set()
        cur = name
        while cur in self.map and cur not in seen:
            seen.add(cur)
            cur = self.map[cur]
        return cur


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_chapters() -> list[dict]:
    files = sorted(glob.glob(str(ROOT / "extracted" / str(BOOK) / "*.json")))
    return [json.loads(Path(f).read_text()) for f in files]


def load_enrichment() -> dict:
    return json.loads((ROOT / "enriched" / f"{BOOK}.json").read_text())


def load_data_json() -> dict:
    return json.loads((ROOT / "data.json").read_text())


# ---------------------------------------------------------------------------
# Build: stars
# ---------------------------------------------------------------------------


def build_stars(existing: dict, chapters: list[dict], norm: Normalizer) -> dict:
    """Preserve existing stars; add stubs for any new systems referenced."""
    stars = dict(existing)  # shallow copy
    for d in chapters:
        for ss in d.get("star_systems", []):
            name = norm(ss["name"])
            if name and name not in stars and name != "in_transit":
                # Add stub - frontend has customLayout to position unknown stars
                stars[name] = {
                    "name": name,
                    "ra_h": 0,
                    "dec_deg": 0,
                    "distance_ly": 30,  # default plausible distance
                }
    return stars


# ---------------------------------------------------------------------------
# Build: chapters list
# ---------------------------------------------------------------------------


def build_chapters_list(chapters: list[dict]) -> list[dict]:
    """Per-chapter list for the chapter-select dropdown.

    Spoiler-safe label: just chapter number + POV + year. No LLM-derived
    plot summary, no location (location can spoil where a character has
    arrived for the first time).
    """
    out = []
    for d in chapters:
        m = d["metadata"]
        ch = m["chapter"]
        yp = year_precise(m["year"], m.get("month"))
        label = f"Ch {ch} - {m['pov']} ({m['year']})"
        out.append({
            "ch": ch,
            "label": label,
            "code": f"B{BOOK}C{ch}",
            "maxYear": yp,
            "pov": m["pov"],
            "location": m["location"],
            "year": m["year"],
            "month": m.get("month"),
        })
    return out


# ---------------------------------------------------------------------------
# Build: bobs
# ---------------------------------------------------------------------------


def build_bobs(chapters: list[dict], enrichment: dict, norm: Normalizer) -> dict:
    """Replicants + ships from new_characters, joined with canonical_cast for status."""
    canonical_by_name = {c["name"]: c for c in enrichment["canonical_cast"]}
    bobs: dict = {}

    # First pass: every replicant from new_characters
    first_seen_by_name: dict[str, tuple[int, dict]] = {}
    personality_by_name: dict[str, dict] = {}
    for d in chapters:
        ch = d["metadata"]["chapter"]
        for nc in d.get("new_characters", []):
            if nc["type"] != "replicant" and nc["name"] != "Bob":
                continue
            name = norm(nc["name"])
            if name not in first_seen_by_name:
                first_seen_by_name[name] = (ch, d["metadata"])
                p = nc.get("personality") or {}
                personality_by_name[name] = {
                    "traits": p.get("traits", []),
                    "role": p.get("role", "unknown"),
                    "nickname_origin": p.get("nickname_origin"),
                    "quirks": p.get("quirks"),
                }

    # Second pass: destruction info
    destroyed_at: dict[str, tuple[int, str | None]] = {}
    for d in chapters:
        ch = d["metadata"]["chapter"]
        for x in d.get("destructions", []):
            name = norm(x["name"])
            if name not in destroyed_at:
                destroyed_at[name] = (ch, d["metadata"].get("month"))

    # Build entries
    for name, (ch, m) in first_seen_by_name.items():
        canon = canonical_by_name.get(name)
        # Find parent in any chapter's new_characters (canonicalized)
        parent = None
        gen = None
        for d in chapters:
            for nc in d.get("new_characters", []):
                if norm(nc["name"]) == name and nc.get("parent"):
                    parent = norm(nc["parent"])
                    gen = nc.get("generation")
                    break
            if parent:
                break
        # Fallback gen from canonical
        if gen is None and canon:
            gen = canon.get("generation")
        # Bob himself
        if name == "Bob":
            gen = 1
            parent = None

        created = year_precise(m["year"], m.get("month"))
        # Initial location: try to read from new_character.location, normalized
        at = "Sol"
        for d in chapters:
            if d["metadata"]["chapter"] != ch:
                continue
            for nc in d.get("new_characters", []):
                if norm(nc["name"]) == name and nc.get("location"):
                    at = norm(nc["location"]) or at
                    break
            break

        destroyed = None
        if name in destroyed_at:
            d_ch, d_month = destroyed_at[name]
            # Find that chapter to get year
            for d in chapters:
                if d["metadata"]["chapter"] == d_ch:
                    destroyed = year_precise(d["metadata"]["year"], d["metadata"].get("month"))
                    break

        # Bob the human dies in ch1 (2016) but continues as a replicant from ch2 (2133).
        # Treat him as starting at Sol in 2133 with no destruction.
        if name == "Bob":
            created = 2133.0
            at = "Sol"
            destroyed = None

        bobs[name] = {
            "gen": gen if gen is not None else 2,
            "parent": parent,
            "created": created,
            "at": at,
            "destroyed": destroyed,
            "book": BOOK,
            "personality": personality_by_name.get(name, {}),
            "first_chapter": ch,
        }

    # Prune entries that aren't in the Bob family tree (misclassified humans).
    # Walk parent chains; only keep entries reachable from "Bob".
    def in_bob_tree(name: str) -> bool:
        visited: set[str] = set()
        while name:
            if name == "Bob":
                return True
            if name in visited:
                return False
            visited.add(name)
            name = bobs[name]["parent"] if name in bobs else None
        return False

    bobs = {k: v for k, v in bobs.items() if in_bob_tree(k)}
    return bobs


# ---------------------------------------------------------------------------
# Build: travels
# ---------------------------------------------------------------------------


def build_travels(chapters: list[dict], norm: Normalizer) -> list[dict]:
    """Match departures with arrivals per character."""
    # Pending departures: char -> [(depart_year, from, to, ship, chapter)]
    pending: dict[str, list[dict]] = defaultdict(list)
    travels: list[dict] = []

    for d in chapters:
        ch = d["metadata"]["chapter"]
        ch_year = year_precise(d["metadata"]["year"], d["metadata"].get("month"))
        for m in d.get("movements", []):
            char = norm(m["character"])
            from_sys = norm(m.get("from"))
            to_sys = norm(m.get("to"))
            if not char or not from_sys or not to_sys:
                continue
            ship = m.get("ship")

            if m["type"] == "departure":
                pending[char].append({
                    "depart": ch_year,
                    "from": from_sys,
                    "to": to_sys,
                    "ship": ship,
                    "depart_chapter": ch,
                    "companions": [norm(c) for c in m.get("companions", [])],
                    "drive": m.get("drive", "unknown"),
                    "max_g": m.get("max_g"),
                })
            elif m["type"] == "arrival":
                # Match against earliest pending departure with matching to_sys
                matched = None
                for p in pending[char]:
                    if p["to"] == to_sys and p["depart"] <= ch_year:
                        matched = p
                        break
                if matched:
                    pending[char].remove(matched)
                    travels.append({
                        "bob": char,
                        "from": matched["from"],
                        "depart": matched["depart"],
                        "to": to_sys,
                        "arrive": ch_year,
                        "book": BOOK,
                        "ship": matched["ship"] or ship,
                        "drive": matched["drive"],
                        "max_g": matched["max_g"],
                        "companions": matched["companions"],
                        "depart_chapter": matched["depart_chapter"],
                        "arrive_chapter": ch,
                    })
                else:
                    # Lone arrival - synthesize a travel from somewhere if possible
                    from_s = norm(m.get("from"))
                    if from_s and from_s != to_sys:
                        travels.append({
                            "bob": char,
                            "from": from_s,
                            "depart": ch_year - 1.0,  # rough guess
                            "to": to_sys,
                            "arrive": ch_year,
                            "book": BOOK,
                            "ship": ship,
                            "drive": m.get("drive", "unknown"),
                            "max_g": m.get("max_g"),
                            "companions": [norm(c) for c in m.get("companions", [])],
                            "depart_chapter": None,
                            "arrive_chapter": ch,
                            "synthetic": True,
                        })

    # Convert remaining pending departures (no matching arrival) into ongoing travels
    # by estimating arrival from distance (if we have it) or +5 years
    for char, deps in pending.items():
        for p in deps:
            travels.append({
                "bob": char,
                "from": p["from"],
                "depart": p["depart"],
                "to": p["to"],
                "arrive": p["depart"] + 8,  # conservative; UI will mark as in-transit-on-end
                "book": BOOK,
                "ship": p["ship"],
                "drive": p["drive"],
                "max_g": p["max_g"],
                "companions": p["companions"],
                "depart_chapter": p["depart_chapter"],
                "arrive_chapter": None,
                "in_transit_at_end": True,
            })

    return travels


# ---------------------------------------------------------------------------
# Build: events
# ---------------------------------------------------------------------------


def build_events(chapters: list[dict], norm: Normalizer) -> list[dict]:
    """Pull all major events per chapter for the event log.

    No cap, no ranking, no priority. Granularity is controlled at extract
    time via the prompt; the LLM is told to consolidate aggressively and
    aim for 0-2 major events per chapter. If a chapter genuinely has more
    state changes, they all show up here.

    Destructions[] are NOT added as their own lines (they're covered by major
    events of type="destruction", and they still drive bob.destroyed timestamps
    and the combat list separately).
    """
    events: list[dict] = []
    for d in chapters:
        ch = d["metadata"]["chapter"]
        ch_year = year_precise(d["metadata"]["year"], d["metadata"].get("month"))
        for ev in d.get("events", []):
            if ev.get("significance") != "major":
                continue
            chars = [norm(c) for c in ev.get("characters", []) if c]
            primary = chars[0] if chars else None
            events.append({
                "year": ch_year,
                "text": ev["text"],
                "bob": primary,
                "characters": chars,
                "type": ev["type"],
                "chapter": ch,
                "book": BOOK,
                # UI red-line styling for events the LLM itself marked destruction.
                "destroyed": ev["type"] == "destruction",
            })
    return events


# ---------------------------------------------------------------------------
# Build: technologies (canonical, with timestamps)
# ---------------------------------------------------------------------------


def build_technologies(chapters: list[dict], enrichment: dict, norm: Normalizer) -> list[dict]:
    """Combine canonical tech entries with full per-chapter event history."""
    tech_history: dict[str, list[dict]] = defaultdict(list)
    for d in chapters:
        ch = d["metadata"]["chapter"]
        ch_year = year_precise(d["metadata"]["year"], d["metadata"].get("month"))
        for t in d.get("technologies", []):
            name = norm(t["name"]) or t["name"]
            tech_history[name].append({
                "chapter": ch,
                "year": ch_year,
                "event": t["event"],
                "by": norm(t.get("by")),
                "location": norm(t.get("location")),
            })

    out = []
    canon_by_name = {t["name"]: t for t in enrichment["technology_canonical"]}
    seen = set()
    for canon in enrichment["technology_canonical"]:
        name = canon["name"]
        seen.add(name)
        out.append({
            "name": name,
            "description": canon.get("description"),
            "tier": canon.get("tier", "unknown"),
            "aliases": canon.get("aliases", []),
            "first_mentioned_chapter": canon.get("first_mentioned_chapter"),
            "first_invented_chapter": canon.get("first_invented_chapter"),
            "first_deployed_chapter": canon.get("first_deployed_chapter"),
            "history": sorted(tech_history.get(name, []), key=lambda x: x["chapter"]),
            "book": BOOK,
        })
    # Add any tech with history but no canonical entry
    for name, hist in tech_history.items():
        if name not in seen:
            out.append({
                "name": name,
                "description": None,
                "tier": "unknown",
                "aliases": [],
                "first_mentioned_chapter": min(h["chapter"] for h in hist),
                "first_invented_chapter": next((h["chapter"] for h in hist if h["event"] == "invented"), None),
                "first_deployed_chapter": next((h["chapter"] for h in hist if h["event"] == "deployed"), None),
                "history": sorted(hist, key=lambda x: x["chapter"]),
                "book": BOOK,
            })
    return sorted(out, key=lambda t: t["first_mentioned_chapter"] or 999)


# ---------------------------------------------------------------------------
# Build: communications (with light-speed lag computed)
# ---------------------------------------------------------------------------


def build_communications(chapters: list[dict], stars: dict, norm: Normalizer) -> list[dict]:
    """Match sent/received pairs and compute light-speed lag for radio."""
    out = []
    cid = 0
    sents = []
    receiveds = []
    for d in chapters:
        ch = d["metadata"]["chapter"]
        ch_year = year_precise(d["metadata"]["year"], d["metadata"].get("month"))
        for c in d.get("communications", []):
            entry = {
                "from_character": norm(c["from_character"]),
                "from_system": norm(c["from_system"]),
                "to_character": c["to_character"] if c["to_character"] == "broadcast" else norm(c["to_character"]),
                "to_system": norm(c.get("to_system")),
                "medium": c["medium"],
                "summary": c.get("contents_summary", ""),
                "chapter": ch,
                "year": ch_year,
            }
            if c["direction"] in ("sent", "both"):
                sents.append(entry)
            if c["direction"] in ("received", "both"):
                receiveds.append(entry)

    def _distance(a: str | None, b: str | None) -> float:
        if not a or not b or a == b:
            return 0.0
        sa, sb = stars.get(a), stars.get(b)
        if not sa or not sb:
            return 0.0
        # Use 3D euclidean distance from RA/Dec/d if available
        import math
        def to3d(s):
            ra = s.get("ra_h", 0) * (math.pi / 12)
            dec = s.get("dec_deg", 0) * (math.pi / 180)
            r = s.get("distance_ly", 0)
            return (r * math.cos(dec) * math.cos(ra),
                    r * math.cos(dec) * math.sin(ra),
                    r * math.sin(dec))
        ax, ay, az = to3d(sa)
        bx, by, bz = to3d(sb)
        return math.sqrt((ax-bx)**2 + (ay-by)**2 + (az-bz)**2)

    for s in sents:
        cid += 1
        # Compute lag
        if s["medium"] in ("radio", "SUDDAR_ping"):
            lag = _distance(s["from_system"], s["to_system"])
        else:
            lag = 0.0  # SCUT, BobNet (post-SCUT) are instant
        received_year = s["year"] + lag
        # Try to match a received entry
        match = None
        for r in receiveds:
            if (r["from_system"] == s["from_system"]
                and r["to_system"] == s["to_system"]
                and r["from_character"] == s["from_character"]
                and abs(r["year"] - received_year) < 5):
                match = r
                break
        out.append({
            "id": f"COM{cid:03d}",
            "from_character": s["from_character"],
            "from_system": s["from_system"],
            "to_character": s["to_character"],
            "to_system": s["to_system"],
            "medium": s["medium"],
            "summary": s["summary"],
            "sent_year": s["year"],
            "received_year": received_year,
            "lag_years": lag,
            "sent_chapter": s["chapter"],
            "received_chapter": match["chapter"] if match else None,
            "book": BOOK,
        })

    # Receiveds with no matching sent - add as "received-only"
    matched_keys = {(c["from_character"], c["from_system"], c["sent_year"]) for c in out}
    for r in receiveds:
        key = (r["from_character"], r["from_system"], None)
        if not any(c["received_chapter"] == r["chapter"] for c in out):
            cid += 1
            out.append({
                "id": f"COM{cid:03d}",
                "from_character": r["from_character"],
                "from_system": r["from_system"],
                "to_character": r["to_character"],
                "to_system": r["to_system"],
                "medium": r["medium"],
                "summary": r["summary"],
                "sent_year": None,
                "received_year": r["year"],
                "lag_years": None,
                "sent_chapter": None,
                "received_chapter": r["chapter"],
                "book": BOOK,
                "received_only": True,
            })

    return out


# ---------------------------------------------------------------------------
# Build: combat
# ---------------------------------------------------------------------------


def build_combat(chapters: list[dict], enrichment: dict, norm: Normalizer) -> list[dict]:
    out = []
    cid = 0
    name_by_chapter = {c["chapter"]: c["name"] for c in enrichment["combat_named"]}
    outcome_by_chapter = {c["chapter"]: c["outcome"] for c in enrichment["combat_named"]}
    for d in chapters:
        ch = d["metadata"]["chapter"]
        ch_year = year_precise(d["metadata"]["year"], d["metadata"].get("month"))
        for c in d.get("combat", []):
            cid += 1
            participants = [
                {**p, "name": norm(p["name"])}
                for p in c.get("participants", [])
            ]
            out.append({
                "id": f"BTL{cid:03d}",
                "name": name_by_chapter.get(ch, f"Combat at {c['location']}, ch{ch}"),
                "outcome_summary": outcome_by_chapter.get(ch),
                "location": norm(c["location"]),
                "year": ch_year,
                "chapter": ch,
                "participants": participants,
                "weapons": c.get("weapons", []),
                "victor": c.get("victor"),
                "duration": c.get("duration"),
                "book": BOOK,
            })
    return out


# ---------------------------------------------------------------------------
# Build: factions, faction_events
# ---------------------------------------------------------------------------


def build_factions(chapters: list[dict], enrichment: dict, norm: Normalizer):
    factions = []
    for f in enrichment["faction_canonical"]:
        factions.append({
            "name": f["name"],
            "description": f["description"],
            "aliases": f.get("aliases", []),
            "first_chapter": f.get("first_chapter"),
            "trajectory": f.get("trajectory"),
            "book": BOOK,
        })
    events = []
    for d in chapters:
        ch = d["metadata"]["chapter"]
        ch_year = year_precise(d["metadata"]["year"], d["metadata"].get("month"))
        for fe in d.get("faction_events", []):
            events.append({
                "faction": norm(fe["faction"]) or fe["faction"],
                "type": fe["type"],
                "counterparty": norm(fe.get("counterparty")),
                "text": fe.get("text"),
                "location": norm(fe.get("location")),
                "year": ch_year,
                "chapter": ch,
                "book": BOOK,
            })
    return factions, events


# ---------------------------------------------------------------------------
# Build: alien_species, infrastructure, threads, quotes, themes, scenes, threats
# ---------------------------------------------------------------------------


def build_species(chapters: list[dict], norm: Normalizer) -> list[dict]:
    by_species: dict[str, dict] = {}
    for d in chapters:
        ch = d["metadata"]["chapter"]
        ch_year = year_precise(d["metadata"]["year"], d["metadata"].get("month"))
        for sp in d.get("alien_species", []):
            name = norm(sp["name"]) or sp["name"]
            cur = by_species.setdefault(name, {
                "name": name,
                "first_chapter": ch,
                "first_year": ch_year,
                "tech_level": sp.get("tech_level"),
                "intelligent": sp.get("intelligent"),
                "hostile": sp.get("hostile"),
                "history": [],
                "book": BOOK,
            })
            cur["history"].append({
                "chapter": ch,
                "year": ch_year,
                "event": sp["event"],
                "location": norm(sp.get("location")),
                "planet": norm(sp.get("planet")),
                "notes": sp.get("notes"),
            })
            # Latest hostile/tech_level overrides
            if sp.get("hostile") is not None:
                cur["hostile"] = sp["hostile"]
            if sp.get("tech_level") and sp["tech_level"] != "unknown":
                cur["tech_level"] = sp["tech_level"]
    return sorted(by_species.values(), key=lambda x: x["first_chapter"])


def build_infrastructure(chapters: list[dict], norm: Normalizer) -> list[dict]:
    out = []
    iid = 0
    for d in chapters:
        ch = d["metadata"]["chapter"]
        ch_year = year_precise(d["metadata"]["year"], d["metadata"].get("month"))
        for inf in d.get("infrastructure", []):
            iid += 1
            out.append({
                "id": f"INF{iid:03d}",
                "system": norm(inf["system"]),
                "type": inf["type"],
                "event": inf["event"],
                "owner": norm(inf["owner"]),
                "chapter": ch,
                "year": ch_year,
                "notes": inf.get("notes"),
                "book": BOOK,
            })
    return out


def build_threads(chapters: list[dict]) -> list[dict]:
    opened: dict[str, dict] = {}
    for d in chapters:
        ch = d["metadata"]["chapter"]
        for t in d.get("threads_opened", []):
            if t["id"] not in opened:
                opened[t["id"]] = {
                    "id": t["id"],
                    "text_opened": t.get("text"),
                    "opened_chapter": ch,
                    "resolved_chapter": None,
                    "text_resolved": None,
                    "book": BOOK,
                }
    for d in chapters:
        ch = d["metadata"]["chapter"]
        for r in d.get("threads_resolved", []):
            if r["id"] in opened and opened[r["id"]]["resolved_chapter"] is None:
                opened[r["id"]]["resolved_chapter"] = ch
                opened[r["id"]]["text_resolved"] = r.get("text")
    return list(opened.values())


def build_quotes(chapters: list[dict], norm: Normalizer) -> list[dict]:
    out = []
    for d in chapters:
        ch = d["metadata"]["chapter"]
        ch_year = year_precise(d["metadata"]["year"], d["metadata"].get("month"))
        for q in d.get("quotes", []):
            out.append({
                "speaker": norm(q["speaker"]) or q["speaker"],
                "text": q["text"],
                "context": q.get("context"),
                "chapter": ch,
                "year": ch_year,
                "book": BOOK,
            })
    return out


def build_themes_and_scenes(chapters: list[dict]) -> tuple[dict, dict]:
    themes_by_chapter = {}
    scenes_by_chapter = {}
    for d in chapters:
        ch = d["metadata"]["chapter"]
        s = d.get("summary", {})
        themes_by_chapter[str(ch)] = {
            "themes": s.get("themes", []),
            "mood": s.get("mood"),
            "pov_emotional_arc": s.get("pov_emotional_arc"),
        }
        scenes_by_chapter[str(ch)] = d.get("scenes", [])
    return themes_by_chapter, scenes_by_chapter


def build_threats(chapters: list[dict], norm: Normalizer) -> list[dict]:
    out = []
    for d in chapters:
        ch = d["metadata"]["chapter"]
        ch_year = year_precise(d["metadata"]["year"], d["metadata"].get("month"))
        for t in d.get("incoming_threats", []):
            out.append({
                "threat": t["threat"],
                "detected_at": norm(t["detected_at"]),
                "origin": norm(t.get("origin")),
                "eta_year": t.get("eta_year"),
                "nature": t.get("nature"),
                "detected_chapter": ch,
                "detected_year": ch_year,
                "book": BOOK,
            })
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print(f"Merging book {BOOK}...")
    chapters = load_chapters()
    enrichment = load_enrichment()
    existing = load_data_json()

    norm = Normalizer(enrichment["name_aliases"], set(existing["stars"].keys()))

    # Stars: preserve + add new
    stars = build_stars(existing["stars"], chapters, norm)
    star_keys = set(stars.keys())

    # Chapters list - book 1 from extractions, 2/3 preserved
    chapters_list = {
        str(BOOK): build_chapters_list(chapters),
        "2": existing["chapters"].get("2", []),
        "3": existing["chapters"].get("3", []),
    }

    # Bobs - book 1 from extractions; preserve books 2/3
    new_bobs = build_bobs(chapters, enrichment, norm)
    all_bobs = {}
    # Books 2/3 from existing data.json
    for bid, b in existing["bobs"].items():
        if b.get("book") in (2, 3):
            all_bobs[bid] = b
    # Book 1 from new_bobs (overwrites any existing book 1 bobs with same name)
    for bid, b in new_bobs.items():
        # Fix unknown/bad locations to nearest plausible
        if b["at"] not in star_keys or b["at"] in {"interstellar space", "unknown", "in_transit"}:
            b["at"] = "Epsilon Eridani" if b["parent"] in {"Bob", "Bill"} else "Sol"
        all_bobs[bid] = b

    # Travels - book 1 from extractions; preserve books 2/3
    new_travels = build_travels(chapters, norm)
    # Drop travels that reference unknown systems
    bad_systems = {"interstellar space", "unknown", "in_transit", None, ""}
    new_travels = [
        t for t in new_travels
        if t["from"] in star_keys and t["to"] in star_keys
        and t["from"] not in bad_systems and t["to"] not in bad_systems
    ]
    all_travels = [t for t in existing["travels"] if t.get("book") in (2, 3)]
    all_travels.extend(new_travels)

    # Events - book 1 from extractions; preserve books 2/3
    new_events = build_events(chapters, norm)
    all_events = [e for e in existing["events"] if e.get("book") in (2, 3)]
    all_events.extend(new_events)

    # New top-level fields
    technologies = build_technologies(chapters, enrichment, norm)
    factions, faction_events = build_factions(chapters, enrichment, norm)
    species = build_species(chapters, norm)
    infrastructure = build_infrastructure(chapters, norm)
    threads = build_threads(chapters)
    quotes = build_quotes(chapters, norm)
    themes_by_chapter, scenes_by_chapter = build_themes_and_scenes(chapters)
    threats = build_threats(chapters, norm)
    communications = build_communications(chapters, stars, norm)
    combat = build_combat(chapters, enrichment, norm)

    # Character arcs as a flat dict
    character_arcs = {a["name"]: a["arc"] for a in enrichment["character_arcs"]}

    # Plot arcs (already book-scoped)
    plot_arcs = [{**a, "book": BOOK} for a in enrichment["plot_arcs"]]

    # Resolutions implicit
    resolutions_implicit = [{**r, "book": BOOK} for r in enrichment["resolutions_implicit"]]

    output = {
        "chapters": chapters_list,
        "stars": stars,
        "bobs": all_bobs,
        "travels": all_travels,
        "events": all_events,
        # New top-level fields
        "technologies": technologies,
        "communications": communications,
        "combat": combat,
        "factions": factions,
        "faction_events": faction_events,
        "alien_species": species,
        "infrastructure": infrastructure,
        "threads": threads,
        "quotes": quotes,
        "themes_by_chapter": themes_by_chapter,
        "scenes_by_chapter": scenes_by_chapter,
        "incoming_threats": threats,
        "character_arcs": character_arcs,
        "plot_arcs": plot_arcs,
        "resolutions_implicit": resolutions_implicit,
    }

    out_path = ROOT / "data.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(f"Written: {out_path}")
    print(f"  chapters book1={len(chapters_list[str(BOOK)])}  stars={len(stars)}  bobs={len(all_bobs)}  travels={len(all_travels)}  events={len(all_events)}")
    print(f"  technologies={len(technologies)}  communications={len(communications)}  combat={len(combat)}")
    print(f"  factions={len(factions)}  faction_events={len(faction_events)}  species={len(species)}")
    print(f"  infrastructure={len(infrastructure)}  threads={len(threads)}  quotes={len(quotes)}  threats={len(threats)}")
    print(f"  plot_arcs={len(plot_arcs)}  character_arcs={len(character_arcs)}")


if __name__ == "__main__":
    main()
