from __future__ import annotations

import argparse
import posixpath
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


XML_NS = {
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
}


class MarkdownHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.list_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "head", "nav"}:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in {"p", "div", "section", "article"}:
            self._block()
        elif tag in {"br"}:
            self.parts.append("\n")
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._block()
            self.parts.append("#" * int(tag[1]) + " ")
        elif tag in {"em", "i"}:
            self.parts.append("*")
        elif tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag == "blockquote":
            self._block()
            self.parts.append("> ")
        elif tag in {"ul", "ol"}:
            self._block()
            self.list_stack.append(tag)
        elif tag == "li":
            self._block()
            marker = "1. " if self.list_stack and self.list_stack[-1] == "ol" else "- "
            self.parts.append(marker)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "head", "nav"} and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in {"p", "div", "section", "article", "blockquote", "li"}:
            self._block()
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._block()
        elif tag in {"em", "i"}:
            self.parts.append("*")
        elif tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"ul", "ol"}:
            if self.list_stack:
                self.list_stack.pop()
            self._block()

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = re.sub(r"\s+", " ", data)
        if text.strip():
            self.parts.append(text)

    def markdown(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"(?m)^# +\s*$", "", text)
        return text.strip()

    def _block(self) -> None:
        current = "".join(self.parts)
        if current and not current.endswith("\n\n"):
            if current.endswith("\n"):
                self.parts.append("\n")
            else:
                self.parts.append("\n\n")


def read_text(zf: zipfile.ZipFile, path: str) -> str:
    return zf.read(path).decode("utf-8", errors="replace")


def opf_path(zf: zipfile.ZipFile) -> str:
    container = ET.fromstring(read_text(zf, "META-INF/container.xml"))
    rootfile = container.find(".//container:rootfile", XML_NS)
    if rootfile is None:
        raise ValueError("EPUB container does not include a rootfile entry")
    full_path = rootfile.attrib.get("full-path")
    if not full_path:
        raise ValueError("EPUB rootfile entry does not include full-path")
    return full_path


def spine_items(zf: zipfile.ZipFile, package_path: str) -> tuple[str, list[str]]:
    package = ET.fromstring(read_text(zf, package_path))
    title_node = package.find(".//dc:title", XML_NS)
    title = title_node.text.strip() if title_node is not None and title_node.text else ""

    manifest = {
        item.attrib["id"]: item.attrib["href"]
        for item in package.findall(".//opf:manifest/opf:item", XML_NS)
        if "id" in item.attrib and "href" in item.attrib
    }
    base = posixpath.dirname(package_path)
    paths: list[str] = []
    for itemref in package.findall(".//opf:spine/opf:itemref", XML_NS):
        href = manifest.get(itemref.attrib.get("idref", ""))
        if href:
            paths.append(posixpath.normpath(posixpath.join(base, href)))
    return title, paths


def html_to_markdown(html: str) -> str:
    parser = MarkdownHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.markdown()


def convert(epub_path: Path, output_path: Path | None = None) -> Path:
    if output_path is None:
        output_path = epub_path.with_suffix(".md")

    with zipfile.ZipFile(epub_path) as zf:
        package_path = opf_path(zf)
        title, content_paths = spine_items(zf, package_path)
        sections = [html_to_markdown(read_text(zf, path)) for path in content_paths]

    body = "\n\n".join(section for section in sections if section)
    heading = f"# {title}\n\n" if title else ""
    output_path.write_text(heading + body + "\n", encoding="utf-8")
    return output_path


def epub_files(paths: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            files.extend(sorted(path.glob("*.epub")))
        else:
            files.append(path)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert EPUB files to simple Markdown.")
    parser.add_argument("paths", nargs="+", help="EPUB files or folders containing EPUB files")
    args = parser.parse_args()

    for epub_path in epub_files(args.paths):
        output_path = convert(epub_path)
        print(f"{epub_path.name} -> {output_path.name}")


if __name__ == "__main__":
    main()
