#!/usr/bin/env python3
"""Split a Markdown book into one file per H2 chapter heading."""

from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


PAGE_COMMENT_RE = re.compile(r"^\s*<!--\s*Page\s+\d+\s*-->\s*$", re.IGNORECASE)


@dataclass
class Chapter:
    heading: str
    lines: list[str]


def is_h2_heading(line: str) -> bool:
    return line.startswith("## ") and not line.startswith("### ")


def heading_text(line: str) -> str:
    return line[3:].strip()


def pop_trailing_page_comment(lines: list[str]) -> list[str]:
    trailing_blanks: list[str] = []
    index = len(lines) - 1

    while index >= 0 and lines[index].strip() == "":
        trailing_blanks.insert(0, lines.pop())
        index -= 1

    if lines and PAGE_COMMENT_RE.match(lines[-1]):
        page_comment = [lines.pop()]
        while lines and lines[-1].strip() == "":
            lines.pop()
        return page_comment

    lines.extend(trailing_blanks)
    return []


def split_chapters(text: str) -> list[Chapter]:
    lines = text.splitlines(keepends=True)
    chapters: list[Chapter] = []
    current: Chapter | None = None
    intro: list[str] = []

    for line in lines:
        if not is_h2_heading(line):
            if current is None:
                intro.append(line)
            else:
                current.lines.append(line)
            continue

        carry_page_comment = pop_trailing_page_comment(current.lines if current else intro)
        current = Chapter(heading=heading_text(line), lines=[line, *carry_page_comment])
        chapters.append(current)

    if intro and any(line.strip() for line in intro):
        chapters.insert(0, Chapter(heading="Intro", lines=intro))

    return chapters


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s.-]+", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-.")


def chapter_filename(heading: str) -> str:
    match = re.match(r"^(\d+)\.\s*(.+)$", heading)
    if match:
        number, title = match.groups()
        return f"{number} {slugify(title)}.md"

    return f"{slugify(heading) or 'untitled'}.md"


def unique_path(directory: Path, filename: str, used: set[str]) -> Path:
    path = directory / filename
    if filename.lower() not in used:
        used.add(filename.lower())
        return path

    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = f"{stem}-{counter}{suffix}"
        if candidate.lower() not in used:
            used.add(candidate.lower())
            return directory / candidate
        counter += 1


def write_chapters(chapters: list[Chapter], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    written: list[Path] = []

    for chapter in chapters:
        filename = "0 Intro.md" if chapter.heading == "Intro" else chapter_filename(chapter.heading)
        path = unique_path(output_dir, filename, used)
        path.write_text("".join(chapter.lines), encoding="utf-8")
        written.append(path)

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Split a Markdown file into chapter files by H2 heading.")
    parser.add_argument("source", type=Path, help="Markdown file to split")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("Book 1"),
        help="Folder for chapter files, default: Book 1",
    )
    args = parser.parse_args()

    text = args.source.read_text(encoding="utf-8-sig")
    chapters = split_chapters(text)
    written = write_chapters(chapters, args.output_dir)

    print(f"wrote {len(written)} file(s) to {args.output_dir}")
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
