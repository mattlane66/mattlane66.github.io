#!/usr/bin/env python3
"""Audit the published full-article HTML for malformed or fragmented structure."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "articles"


class ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_main = 0
        self.h1 = 0
        self.ids: set[str] = set()
        self.errors: list[str] = []
        self.list_stack: list[str] = []
        self.li_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        options = dict(attrs)
        if tag == "main" and "article" in (options.get("class") or "").split():
            self.in_main += 1
        if not self.in_main:
            return
        ident = options.get("id")
        if ident:
            if ident in self.ids:
                self.errors.append(f"duplicate id {ident}")
            self.ids.add(ident)
        if tag == "h1":
            self.h1 += 1
        if tag in ("ul", "ol"):
            self.list_stack.append(tag)
        if tag == "li":
            if not self.list_stack:
                self.errors.append("list item outside an ordered or unordered list")
            self.li_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if not self.in_main:
            return
        if tag == "li":
            self.li_depth -= 1
            if self.li_depth < 0:
                self.errors.append("unexpected closing list item")
                self.li_depth = 0
        if tag in ("ul", "ol"):
            if not self.list_stack or self.list_stack[-1] != tag:
                self.errors.append(f"unexpected closing {tag}")
            else:
                self.list_stack.pop()
        if tag == "main":
            self.in_main -= 1


def main() -> int:
    files = sorted(ARTICLES.glob("*/index.html"))
    assert files, "No full articles found"
    issues: list[str] = []
    for file in files:
        html = file.read_text(encoding="utf-8")
        page = re.search(r'<main\b[^>]*class="[^"]*\barticle\b[^"]*"[^>]*>(.*?)</main>', html, re.S)
        if not page:
            issues.append(f"{file}: article main not found")
            continue
        article = page.group(1)
        if re.search(r"</ul>\s*<ul\b", article, re.I):
            issues.append(f"{file}: adjacent unordered lists need to be one list")
        if re.search(r"</ol>\s*<ol\b", article, re.I):
            issues.append(f"{file}: adjacent ordered lists restart or fragment their numbering")
        parser = ArticleParser()
        parser.feed(html)
        if parser.h1 != 1:
            issues.append(f"{file}: expected exactly one main article heading, found {parser.h1}")
        if parser.list_stack or parser.li_depth:
            issues.append(f"{file}: unclosed list tags or list items")
        issues.extend(f"{file}: {error}" for error in parser.errors)
    for issue in issues:
        print("ERROR:", issue)
    if issues:
        return 1
    print(f"PASS: all {len(files)} full articles have intact headings and properly grouped lists.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
