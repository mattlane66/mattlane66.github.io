#!/usr/bin/env python3
"""Dependency-free health checks for the static GitHub Pages site."""
from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://mattlane66.github.io/"
SKIP_DIRS = {".git", ".github"}
GENERATED = {"planning-tools/index.html", "notes/index.html"}
SEO_CORE = {
    "index.html", "about/index.html", "splice/index.html", "nyshex/index.html",
    "codeai/index.html", "fit-check/index.html", "planning-tools/index.html", "notes/index.html",
}

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = False
        self.title_depth = 0
        self.title = ""
        self.viewport = False
        self.description = False
        self.canonical = False
        self.og_title = False
        self.og_description = False
        self.og_image = False
        self.twitter_card = False
        self.json_ld = False
        self.icon = False
        self.h1 = 0
        self.ids = []
        self.refs = []
        self.blank_links = []
        self.images_missing_alt = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = bool(a.get("lang"))
        elif tag == "title":
            self.title_depth += 1
        elif tag == "meta":
            name = (a.get("name") or "").lower()
            if name == "viewport":
                self.viewport = True
            if name == "description" and (a.get("content") or "").strip():
                self.description = True
            if name == "twitter:card" and (a.get("content") or "").strip():
                self.twitter_card = True
            prop = (a.get("property") or "").lower()
            if prop == "og:title" and (a.get("content") or "").strip():
                self.og_title = True
            if prop == "og:description" and (a.get("content") or "").strip():
                self.og_description = True
            if prop == "og:image" and (a.get("content") or "").strip():
                self.og_image = True
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            if "icon" in rel:
                self.icon = True
            if "canonical" in rel and (a.get("href") or "").strip():
                self.canonical = True
            if a.get("href"):
                self.refs.append(a["href"])
        elif tag == "a":
            href = a.get("href")
            if href:
                self.refs.append(href)
            if (a.get("target") or "").lower() == "_blank":
                rel = set((a.get("rel") or "").lower().split())
                if "noopener" not in rel:
                    self.blank_links.append(href or "(missing href)")
        elif tag in {"img", "script", "iframe", "source", "video", "audio"}:
            if tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
                self.json_ld = True
            if a.get("src"):
                self.refs.append(a["src"])
            if tag == "img" and "alt" not in a:
                self.images_missing_alt.append(a.get("src") or "(inline image)")
        if tag == "h1":
            self.h1 += 1
        if a.get("id"):
            self.ids.append(a["id"])

    def handle_endtag(self, tag):
        if tag == "title" and self.title_depth:
            self.title_depth -= 1

    def handle_data(self, data):
        if self.title_depth:
            self.title += data

def repo_path_for_url(page: Path, ref: str) -> Path | None:
    ref = ref.strip()
    if not ref or ref.startswith(("#", "data:", "mailto:", "tel:", "javascript:")):
        return None
    if "${" in ref or ref == "$2":
        return None
    base = urljoin(SITE, page.parent.as_posix().rstrip("/") + ("/" if page.parent.as_posix() != "." else ""))
    u = urlparse(urljoin(base, ref))
    if u.netloc and u.netloc != "mattlane66.github.io":
        return None
    path = u.path.lstrip("/")
    if not path:
        return ROOT / "index.html"
    candidate = ROOT / path
    if u.path.endswith("/") or candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate

def main() -> int:
    errors, warnings = [], []
    html_files = sorted(p for p in ROOT.rglob("*.html") if not any(part in SKIP_DIRS for part in p.parts))
    has_fallback_icon = (ROOT / "favicon.ico").is_file()

    for page in html_files:
        rel = page.relative_to(ROOT).as_posix()
        text = page.read_text(encoding="utf-8", errors="replace")
        parser = PageParser()
        try:
            parser.feed(text)
        except Exception as exc:
            errors.append(f"{rel}: HTML parser error: {exc}")
            continue

        if "<!doctype html" not in text[:300].lower():
            errors.append(f"{rel}: missing HTML5 doctype")
        if not parser.lang:
            errors.append(f"{rel}: <html> is missing lang")
        if not parser.viewport:
            errors.append(f"{rel}: missing viewport meta")
        if not parser.title.strip():
            errors.append(f"{rel}: missing <title>")
        if not parser.description:
            errors.append(f"{rel}: missing meta description")
        if not (parser.icon or has_fallback_icon):
            errors.append(f"{rel}: no favicon available")
        needs_seo = rel in SEO_CORE or rel.startswith("notes/n/")
        if rel.startswith("notes/n/") and re.search(r'https?://[^"\'<>\s]*substack', text, flags=re.I):
            errors.append(f"{rel}: generated Note page contains an old Substack URL")
        if needs_seo:
            if not parser.canonical:
                errors.append(f"{rel}: missing canonical URL")
            if not (parser.og_title and parser.og_description and parser.og_image):
                errors.append(f"{rel}: incomplete Open Graph metadata")
            if not parser.twitter_card:
                errors.append(f"{rel}: missing Twitter card metadata")
            if not parser.json_ld:
                errors.append(f"{rel}: missing JSON-LD structured data")
        if parser.h1 != 1:
            errors.append(f"{rel}: expected exactly one h1, found {parser.h1}")
        if parser.blank_links:
            errors.append(f"{rel}: target=_blank without noopener: {parser.blank_links}")

        duplicate_ids = sorted({x for x in parser.ids if parser.ids.count(x) > 1})
        if duplicate_ids:
            errors.append(f"{rel}: duplicate static ids: {duplicate_ids}")

        for ref in parser.refs:
            target = repo_path_for_url(page.relative_to(ROOT), ref)
            if target is not None and not target.exists():
                errors.append(f"{rel}: missing internal target {ref} -> {target.relative_to(ROOT)}")

        if parser.images_missing_alt:
            warnings.append(f"{rel}: image(s) without alt: {len(parser.images_missing_alt)}")

        size = page.stat().st_size
        if size > 1_000_000 and rel not in GENERATED:
            warnings.append(f"{rel}: large HTML file ({size / 1_000_000:.1f} MB)")
        elif size > 1_000_000:
            warnings.append(f"{rel}: generated standalone artifact ({size / 1_000_000:.1f} MB)")

    for required in ("robots.txt", "sitemap.xml", "favicon.svg", "favicon.ico"):
        if not (ROOT / required).is_file():
            errors.append(f"root: missing {required}")

    sitemap_path = ROOT / "sitemap.xml"
    if sitemap_path.is_file():
        sitemap_text = sitemap_path.read_text(encoding="utf-8", errors="replace")
        locs = re.findall(r"<loc>([^<]+)</loc>", sitemap_text)
        if len(locs) != len(set(locs)):
            errors.append("sitemap.xml: duplicate URLs")
        indexed_pages = []
        for page in html_files:
            rel = page.relative_to(ROOT).as_posix()
            if rel in SEO_CORE or rel.startswith("notes/n/"):
                if rel == "index.html":
                    indexed_pages.append(SITE)
                elif rel.endswith("/index.html"):
                    indexed_pages.append(SITE + rel[:-10])
        missing_from_sitemap = sorted(set(indexed_pages) - set(locs))
        if missing_from_sitemap:
            errors.append(f"sitemap.xml: missing {len(missing_from_sitemap)} indexable page(s): {missing_from_sitemap[:5]}")
    robots_path = ROOT / "robots.txt"
    if robots_path.is_file():
        robots_text = robots_path.read_text(encoding="utf-8", errors="replace")
        if "Sitemap: https://mattlane66.github.io/sitemap.xml" not in robots_text:
            errors.append("robots.txt: missing canonical sitemap declaration")

    print(f"Checked {len(html_files)} HTML pages.")
    for item in warnings:
        print(f"WARNING: {item}")
    for item in errors:
        print(f"ERROR: {item}")

    if errors:
        print(f"\nFAILED: {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"\nPASS: 0 errors, {len(warnings)} warning(s).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
