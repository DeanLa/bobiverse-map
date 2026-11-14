from __future__ import annotations

import argparse
import posixpath
import re
import shutil
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


XML_NS = {
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
    "dc": "http://purl.org/dc/elements/1.1/",
    "ncx": "http://www.daisy.org/z3986/2005/ncx/",
    "opf": "http://www.idpf.org/2007/opf",
}


BOOK_NUMBER_RE = re.compile(r"Bobiverse[_ -]*(\d+)|Book\s+(\d+)", re.IGNORECASE)
NUMBERED_TITLE_RE = re.compile(r"^\s*(\d+)\s*[.)]?\s*(.+?)\s*$")
CHAPTER_WORD_TITLE_RE = re.compile(r"^\s*Chapter\s+([A-Za-z-]+):\s*(.+?)\s*$", re.IGNORECASE)
PART_TITLE_RE = re.compile(r"^\s*Part\s+(\d+)\b", re.IGNORECASE)
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


@dataclass
class TocEntry:
    index: int
    title: str
    source: str


class MarkdownHTMLParser(HTMLParser):
    block_tags = {
        "address",
        "article",
        "aside",
        "blockquote",
        "body",
        "dd",
        "div",
        "dl",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tr",
        "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.emphasis_stack: list[str] = []
        self.current_p_classes: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {name.lower(): value or "" for name, value in attrs}
        if tag in {"script", "style", "head"}:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == "p":
            self.current_p_classes.append(attr_map.get("class", ""))
            if "fleuron" in attr_map.get("class", "").lower():
                self._block()
                self.parts.append("***")
                self._block()
                return
        if tag in self.block_tags:
            self._block()
        if tag in {"em", "i"} or "italic" in attr_map.get("class", "").lower():
            self.parts.append("*")
            self.emphasis_stack.append("*")
        elif tag in {"strong", "b"} or "bold" in attr_map.get("class", "").lower():
            self.parts.append("**")
            self.emphasis_stack.append("**")
        elif tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "head"} and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in {"em", "i", "strong", "b", "span"} and self.emphasis_stack:
            self.parts.append(self.emphasis_stack.pop())
        if tag == "p" and self.current_p_classes:
            self.current_p_classes.pop()
        if tag in self.block_tags:
            self._block()

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = data.replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text)
        if text.strip():
            self.parts.append(text)

    def markdown(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"(?m)^\s+$", "", text)
        text = re.sub(r"\n\*\*\s*\*\*\n", "\n", text)
        return text.strip()

    def _block(self) -> None:
        current = "".join(self.parts)
        if current and not current.endswith("\n\n"):
            self.parts.append("\n\n" if not current.endswith("\n") else "\n")


def read_text(zf: zipfile.ZipFile, path: str) -> str:
    return zf.read(path).decode("utf-8", errors="replace")


def clean_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.replace("\xa0", " ")).strip()


def slugify(text: str) -> str:
    text = clean_title(text).lower()
    text = text.replace("omicron2", "2-omicron")
    text = re.sub(r"[’']", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "untitled"


def package_path(zf: zipfile.ZipFile) -> str:
    container = ET.fromstring(read_text(zf, "META-INF/container.xml"))
    rootfile = container.find(".//container:rootfile", XML_NS)
    if rootfile is None or not rootfile.attrib.get("full-path"):
        raise ValueError("EPUB container does not include a rootfile entry")
    return rootfile.attrib["full-path"]


def package_metadata(zf: zipfile.ZipFile, opf_path: str) -> tuple[str, str]:
    package = ET.fromstring(read_text(zf, opf_path))
    title = package.find(".//dc:title", XML_NS)
    creator = package.find(".//dc:creator", XML_NS)
    return (
        clean_title(title.text) if title is not None and title.text else "",
        clean_title(creator.text) if creator is not None and creator.text else "",
    )


def toc_path(zf: zipfile.ZipFile, opf_path: str) -> str:
    package = ET.fromstring(read_text(zf, opf_path))
    manifest = {
        item.attrib.get("id", ""): item.attrib.get("href", "")
        for item in package.findall(".//opf:manifest/opf:item", XML_NS)
    }
    spine = package.find(".//opf:spine", XML_NS)
    toc_id = spine.attrib.get("toc") if spine is not None else ""
    href = manifest.get(toc_id, "toc.ncx")
    return posixpath.normpath(posixpath.join(posixpath.dirname(opf_path), href))


def spine_paths(zf: zipfile.ZipFile, opf_path: str) -> list[str]:
    package = ET.fromstring(read_text(zf, opf_path))
    manifest = {
        item.attrib.get("id", ""): item.attrib.get("href", "")
        for item in package.findall(".//opf:manifest/opf:item", XML_NS)
    }
    base = posixpath.dirname(opf_path)
    paths: list[str] = []
    for itemref in package.findall(".//opf:spine/opf:itemref", XML_NS):
        href = manifest.get(itemref.attrib.get("idref", ""), "")
        if href:
            paths.append(posixpath.normpath(posixpath.join(base, href)))
    return paths


def toc_entries(zf: zipfile.ZipFile, ncx_path: str) -> list[TocEntry]:
    ncx = ET.fromstring(read_text(zf, ncx_path))
    entries: list[TocEntry] = []
    base = posixpath.dirname(ncx_path)
    for index, point in enumerate(ncx.findall(".//ncx:navPoint", XML_NS), start=1):
        label = point.find("./ncx:navLabel/ncx:text", XML_NS)
        content = point.find("./ncx:content", XML_NS)
        title = clean_title(label.text) if label is not None and label.text else ""
        src = content.attrib.get("src", "") if content is not None else ""
        if title and src:
            source = posixpath.normpath(posixpath.join(base, src.split("#", 1)[0]))
            entries.append(TocEntry(index=index, title=title, source=source))
    return entries


def html_to_markdown(zf: zipfile.ZipFile, source: str) -> str:
    parser = MarkdownHTMLParser()
    parser.feed(read_text(zf, source))
    parser.close()
    return parser.markdown()


def strip_leading_heading(markdown: str, canonical_title: str) -> str:
    lines = markdown.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return ""
    first = re.sub(r"^[#*\s]+|[#*\s]+$", "", lines[0]).strip()
    first_core = NUMBERED_TITLE_RE.sub(r"\2", first).strip()
    canonical_core = title_core(clean_title(canonical_title))
    word_heading = re.match(r"^\s*Chapter\s+[A-Za-z-]+:\s*$", first, re.IGNORECASE)
    if word_heading and len(lines) > 1 and clean_title(lines[1]) == canonical_core:
        del lines[:2]
        while lines and not lines[0].strip():
            lines.pop(0)
        return "\n".join(lines).strip()
    if first == canonical_title or first_core == canonical_core:
        lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines).strip()


def title_core(title: str) -> str:
    numbered = NUMBERED_TITLE_RE.match(title)
    if numbered:
        return clean_title(numbered.group(2))
    word_title = CHAPTER_WORD_TITLE_RE.match(title)
    if word_title:
        return clean_title(word_title.group(2))
    return clean_title(title)


def is_numbered_chapter(title: str) -> bool:
    cleaned = clean_title(title)
    return bool(NUMBERED_TITLE_RE.match(cleaned) or CHAPTER_WORD_TITLE_RE.match(cleaned))


def chapter_number_and_title(title: str) -> tuple[int, str]:
    cleaned = clean_title(title)
    match = NUMBERED_TITLE_RE.match(cleaned)
    if match:
        return int(match.group(1)), clean_title(match.group(2))
    word_match = CHAPTER_WORD_TITLE_RE.match(cleaned)
    if word_match:
        return number_word_to_int(word_match.group(1)), clean_title(word_match.group(2))
    raise ValueError(f"Not a numbered chapter title: {title}")


def number_word_to_int(text: str) -> int:
    total = 0
    for part in text.lower().split("-"):
        if part not in NUMBER_WORDS:
            raise ValueError(f"Unknown chapter number word: {text}")
        total += NUMBER_WORDS[part]
    return total


def book_number(epub_path: Path, title: str) -> int:
    match = BOOK_NUMBER_RE.search(epub_path.name) or BOOK_NUMBER_RE.search(title)
    if not match:
        raise ValueError(f"Could not determine book number for {epub_path.name}")
    return int(match.group(1) or match.group(2))


def intro_entries(entries: list[TocEntry]) -> list[TocEntry]:
    intro: list[TocEntry] = []
    for entry in entries:
        if is_numbered_chapter(entry.title) or PART_TITLE_RE.match(entry.title):
            break
        intro.append(entry)
    return intro


def pre_toc_intro_sources(spine: list[str], entries: list[TocEntry]) -> list[str]:
    first_source = ""
    for entry in entries:
        if is_numbered_chapter(entry.title) or PART_TITLE_RE.match(entry.title):
            first_source = entry.source
            break
    if not first_source:
        return []
    sources: list[str] = []
    for source in spine:
        if source == first_source:
            break
        sources.append(source)
    return sources


def unique_path(folder: Path, filename: str) -> Path:
    path = folder / filename
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = folder / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def write_file(path: Path, heading: str, body: str = "") -> None:
    content = f"## {heading}\n"
    body = body.strip()
    if body:
        content += f"\n{body}\n"
    path.write_text(content, encoding="utf-8")


def convert_epub(epub_path: Path, output_root: Path, force: bool) -> tuple[Path, int]:
    with zipfile.ZipFile(epub_path) as zf:
        opf_path = package_path(zf)
        title, _creator = package_metadata(zf, opf_path)
        number = book_number(epub_path, title)
        entries = toc_entries(zf, toc_path(zf, opf_path))
        spine = spine_paths(zf, opf_path)
        folder = output_root / f"book-{number}"
        if folder.exists():
            if not force:
                raise FileExistsError(f"{folder} already exists; use --force to replace generated output")
            try:
                shutil.rmtree(folder)
            except PermissionError:
                if any(folder.iterdir()):
                    raise
        folder.mkdir(parents=True, exist_ok=True)

        intro = intro_entries(entries)
        if intro:
            intro_parts: list[str] = []
            for entry in intro:
                body = strip_leading_heading(html_to_markdown(zf, entry.source), entry.title)
                section = f"## {entry.title}"
                if body:
                    section += f"\n\n{body}"
                intro_parts.append(section)
            (folder / "0 Intro.md").write_text("\n\n".join(intro_parts).strip() + "\n", encoding="utf-8")
        else:
            intro_parts = [html_to_markdown(zf, source) for source in pre_toc_intro_sources(spine, entries)]
            intro_text = "\n\n".join(part for part in intro_parts if part).strip()
            if intro_text:
                (folder / "0 Intro.md").write_text(intro_text + "\n", encoding="utf-8")

        current_part = ""
        chapter_index = 0
        part_counts: dict[str, int] = {}
        for entry in entries:
            part_match = PART_TITLE_RE.match(entry.title)
            if part_match:
                current_part = entry.title
                part_number = part_match.group(1)
                part_counts[part_number] = part_counts.get(part_number, 0) + 1
                body = strip_leading_heading(html_to_markdown(zf, entry.source), entry.title)
                write_file(unique_path(folder, f"part-{part_number}.md"), entry.title, body)
                continue

            if not is_numbered_chapter(entry.title):
                continue

            chapter_index += 1
            chapter_number, chapter_title = chapter_number_and_title(entry.title)
            body = strip_leading_heading(html_to_markdown(zf, entry.source), entry.title)
            prefix = str(chapter_number)
            if chapter_index != chapter_number:
                prefix = str(chapter_index)
            filename = f"{prefix} {slugify(chapter_title)}.md"
            heading = f"{chapter_number}. {chapter_title}"
            write_file(unique_path(folder, filename), heading, body)

        return folder, chapter_index


def epub_files(folder: Path) -> Iterable[Path]:
    return sorted(folder.glob("*.epub"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Bobiverse EPUBs into per-book chapter folders.")
    parser.add_argument("folder", type=Path, help="Folder containing EPUB files")
    parser.add_argument("--force", action="store_true", help="Replace generated book-N folders if present")
    args = parser.parse_args()

    for epub_path in epub_files(args.folder):
        folder, count = convert_epub(epub_path, args.folder, args.force)
        print(f"{epub_path.name} -> {folder.name} ({count} chapters)")


if __name__ == "__main__":
    main()
