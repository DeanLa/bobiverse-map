#!/usr/bin/env python3
"""Merge adjacent Markdown H2 headings into a single H2 heading.

Example:
    ## 13. Bob - August 17, 2133 -

    ## En Route

becomes:
    ## 13. Bob - August 17, 2133 -  En Route
"""

from __future__ import annotations

import argparse
from pathlib import Path


def is_h2_heading(line: str) -> bool:
    return line.startswith("## ") and not line.startswith("### ")


def heading_text(line: str) -> str:
    return line[3:].strip()


def merge_h2_headings(text: str) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    merges = 0
    index = 0

    while index < len(lines):
        line = lines[index]

        if not is_h2_heading(line):
            output.append(line)
            index += 1
            continue

        parts = [heading_text(line)]
        cursor = index + 1
        skipped_blank_lines: list[str] = []

        while cursor < len(lines):
            if lines[cursor].strip() == "":
                skipped_blank_lines.append(lines[cursor])
                cursor += 1
                continue

            if not is_h2_heading(lines[cursor]):
                break

            parts.append(heading_text(lines[cursor]))
            merges += 1
            cursor += 1
            skipped_blank_lines = []

        if len(parts) == 1:
            output.append(line)
            output.extend(skipped_blank_lines)
        else:
            newline = "\r\n" if line.endswith("\r\n") else "\n"
            output.append(f"## {'  '.join(parts)}{newline}")

        index = cursor

    return "".join(output), merges


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge consecutive Markdown H2 headings separated only by blank lines."
    )
    parser.add_argument("path", type=Path, help="Markdown file to process")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Rewrite the file in place. Without this, only reports the merge count.",
    )
    args = parser.parse_args()

    original = args.path.read_text(encoding="utf-8-sig")
    updated, merges = merge_h2_headings(original)

    if args.write and updated != original:
        args.path.write_text(updated, encoding="utf-8")

    action = "merged" if args.write else "would merge"
    print(f"{action} {merges} consecutive H2 heading(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
