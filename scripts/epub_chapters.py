from __future__ import annotations

import argparse
import csv
import posixpath
import re
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET


XML_NS = {
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
    "dc": "http://purl.org/dc/elements/1.1/",
    "ncx": "http://www.daisy.org/z3986/2005/ncx/",
    "opf": "http://www.idpf.org/2007/opf",
}


@dataclass
class Chapter:
    book: str
    index: int
    title: str
    source: str
    word_count: int
    estimated_start_page: int


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "head", "nav"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "head", "nav"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


def read_text(zf: zipfile.ZipFile, path: str) -> str:
    return zf.read(path).decode("utf-8", errors="replace")


def package_path(zf: zipfile.ZipFile) -> str:
    container = ET.fromstring(read_text(zf, "META-INF/container.xml"))
    rootfile = container.find(".//container:rootfile", XML_NS)
    if rootfile is None or not rootfile.attrib.get("full-path"):
        raise ValueError("EPUB container does not include a rootfile entry")
    return rootfile.attrib["full-path"]


def book_title(zf: zipfile.ZipFile, opf_path: str) -> str:
    package = ET.fromstring(read_text(zf, opf_path))
    title = package.find(".//dc:title", XML_NS)
    return title.text.strip() if title is not None and title.text else ""


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


def nav_points(zf: zipfile.ZipFile, ncx_path: str) -> list[tuple[str, str]]:
    ncx = ET.fromstring(read_text(zf, ncx_path))
    points: list[tuple[str, str]] = []
    base = posixpath.dirname(ncx_path)
    for point in ncx.findall(".//ncx:navPoint", XML_NS):
        label = point.find("./ncx:navLabel/ncx:text", XML_NS)
        content = point.find("./ncx:content", XML_NS)
        title = label.text.strip() if label is not None and label.text else ""
        src = content.attrib.get("src", "") if content is not None else ""
        if title and src:
            source = posixpath.normpath(posixpath.join(base, src.split("#", 1)[0]))
            points.append((title, source))
    return points


def word_count(zf: zipfile.ZipFile, source: str) -> int:
    if source not in zf.namelist():
        return 0
    parser = TextExtractor()
    parser.feed(read_text(zf, source))
    parser.close()
    return len(re.findall(r"\b[\w']+\b", parser.text()))


def chapters_for(epub_path: Path, words_per_page: int) -> list[Chapter]:
    with zipfile.ZipFile(epub_path) as zf:
        opf_path = package_path(zf)
        title = book_title(zf, opf_path) or epub_path.stem
        points = nav_points(zf, toc_path(zf, opf_path))
        chapters: list[Chapter] = []
        cumulative_words = 0
        for index, (chapter_title, source) in enumerate(points, start=1):
            chapters.append(
                Chapter(
                    book=title,
                    index=index,
                    title=chapter_title,
                    source=source,
                    word_count=word_count(zf, source),
                    estimated_start_page=max(1, cumulative_words // words_per_page + 1),
                )
            )
            cumulative_words += chapters[-1].word_count
        return chapters


def write_markdown(path: Path, chapters_by_book: list[tuple[Path, list[Chapter]]]) -> None:
    lines = [
        "# Bobiverse Chapter Index",
        "",
        "EPUB files do not include fixed page numbers. Page starts below are estimates based on 250 words per page.",
        "",
    ]
    for epub_path, chapters in chapters_by_book:
        book_title_value = chapters[0].book if chapters else epub_path.stem
        lines.extend([f"## {book_title_value}", "", "| # | Title | Est. page | Words | Source |", "|---:|---|---:|---:|---|"])
        for chapter in chapters:
            lines.append(
                f"| {chapter.index} | {chapter.title} | {chapter.estimated_start_page} | "
                f"{chapter.word_count} | `{chapter.source}` |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(path: Path, chapters_by_book: list[tuple[Path, list[Chapter]]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["book", "chapter_number", "title", "estimated_start_page", "word_count", "source"])
        for _, chapters in chapters_by_book:
            for chapter in chapters:
                writer.writerow(
                    [
                        chapter.book,
                        chapter.index,
                        chapter.title,
                        chapter.estimated_start_page,
                        chapter.word_count,
                        chapter.source,
                    ]
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract EPUB chapter titles and estimated page starts.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--words-per-page", type=int, default=250)
    args = parser.parse_args()

    epubs = sorted(args.folder.glob("*.epub"))
    chapters_by_book = [(epub, chapters_for(epub, args.words_per_page)) for epub in epubs]
    write_markdown(args.folder / "bobiverse_chapters.md", chapters_by_book)
    write_csv(args.folder / "bobiverse_chapters.csv", chapters_by_book)
    for epub, chapters in chapters_by_book:
        print(f"{epub.name}: {len(chapters)} entries")


if __name__ == "__main__":
    main()
