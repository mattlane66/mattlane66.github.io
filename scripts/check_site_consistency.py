#!/usr/bin/env python3
"""Cross-surface publishing invariants for the entire static site.

Unlike checks of individual pages, this catches drift between authored Note
sources, the homepage, the Notes archive, 323+ detail pages, article links,
and the sitemap. Run *after* generate_note_pages.py, not instead of it.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import json
import re
import sys

from generate_note_pages import ROOT, SITE, NOTE_CATEGORY_KEYS, slugify

HOME = ROOT / "index.html"
ARCHIVE = ROOT / "notes" / "index.html"
DIRECT = ROOT / "notes" / "direct-notes.json"
REMOVED = ROOT / "notes" / "removed-note-ids.json"
SITEMAP = ROOT / "sitemap.xml"
ARTICLE_ROOT = ROOT / "articles"
STATIC_PAGE_ROOT = ROOT / "notes" / "n"


def active_notes(archive_html: str) -> dict[str, dict]:
    match = re.search(
        r"let NOTES=(\[.*?\]);(?=\s*(?:const CATEGORY_KEYS=|const CATS=))",
        archive_html, re.S,
    )
    if not match:
        raise ValueError("Notes archive: embedded NOTES data not found")
    embedded = json.loads(match.group(1))
    direct = json.loads(DIRECT.read_text(encoding="utf-8"))
    removed = set(map(str, json.loads(REMOVED.read_text(encoding="utf-8"))))
    combined: dict[str, dict] = {}
    for note in embedded:
        combined[str(note["id"])] = note
    for i, note in enumerate(direct):
        if not isinstance(note, dict) or not note.get("title") or not note.get("date"):
            continue
        ident = str(note.get("id") or f"{note['date']}-{note['title']}-{i}")
        ident = re.sub(r"[^a-z0-9_-]+", "-", ident.lower()).strip("-") or f"direct-{i}"
        combined[ident] = {**note, "id": ident}
    return {ident: note for ident, note in combined.items() if ident not in removed}


class LinksAndIds(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])


def verify() -> list[str]:
    errors = []
    archive = ARCHIVE.read_text(encoding="utf-8")
    home = HOME.read_text(encoding="utf-8")
    notes = active_notes(archive)
    expected_count = len(notes)

    # All displayed counters must derive from the active merged/removed Note set.
    counts = re.findall(r'<span id="resultCount"><b>(\d+)</b> notes</span>', archive)
    if counts != [str(expected_count)]:
        errors.append(f"Notes archive total: expected {expected_count}, got {counts}")
    cta = re.findall(
        r'<a\b[^>]*href="\./notes/[^"]*"[^>]*>Browse all (\d+) Notes →</a>',
        home,
    )
    if cta != [str(expected_count)]:
        errors.append(f"Homepage Browse all Notes count: expected {expected_count}, got {cta}")

    # Static archive cards must be complete, unique and point to the right page.
    block = re.search(r"<!-- STATIC_NOTES_START -->(.*?)<!-- STATIC_NOTES_END -->", archive, re.S)
    if not block:
        errors.append("Notes archive: missing static Note cards")
        cards = []
    else:
        cards = re.findall(
            r'<a class="note[^"]*" data-category="([^"]+)" '
            r'data-id="([^"]+)" href="([^"]+)"',
            block.group(1),
        )
    ids = [ident for _, ident, _ in cards]
    if len(cards) != expected_count or len(ids) != len(set(ids)) or set(ids) != set(notes):
        errors.append(
            f"Notes static cards: expected {expected_count} distinct IDs, "
            f"found {len(cards)} cards / {len(set(ids))} distinct"
        )
    for category_key, ident, href in cards:
        note = notes.get(ident)
        if note is None:
            continue
        expected_href = f"./n/{slugify(str(note.get('title', '')))}-{ident}/"
        if href != expected_href:
            errors.append(f"Note {ident}: archive href {href!r}, expected {expected_href!r}")
        expected_category = NOTE_CATEGORY_KEYS.get(str(note.get("category")), "other")
        if category_key != expected_category:
            errors.append(f"Note {ident}: archive category is inconsistent")

    expected_detail = {
        f"{slugify(str(note.get('title', '')))}-{ident}": ident
        for ident, note in notes.items()
    }
    actual_detail = {
        path.parent.name: path
        for path in STATIC_PAGE_ROOT.glob("*/index.html")
    }
    if expected_detail.keys() != actual_detail.keys():
        missing = sorted(expected_detail.keys() - actual_detail.keys())
        extra = sorted(actual_detail.keys() - expected_detail.keys())
        errors.append(f"Note detail pages: {len(missing)} missing {missing[:4]}, {len(extra)} stale {extra[:4]}")
    if len(expected_detail) != expected_count:
        errors.append("Notes: two IDs would collide on the same generated detail-page slug")
    for slug, ident in expected_detail.items():
        path = actual_detail.get(slug)
        if path is None:
            continue
        page = path.read_text(encoding="utf-8")
        canonical = f'{SITE}/notes/n/{slug}/'
        if f'<link rel="canonical" href="{canonical}">' not in page:
            errors.append(f"Note {ident}: incorrect canonical URL")

    article_files = sorted(ARTICLE_ROOT.glob("*/index.html"))
    article_slugs = {path.parent.name for path in article_files}
    linked_slugs = re.findall(
        r'<a class="article-card[^"]*"[^>]*href="\./articles/([^/]+)/',
        home,
    )
    if len(linked_slugs) != len(set(linked_slugs)) or set(linked_slugs) != article_slugs:
        errors.append(
            f"Full articles: {len(article_slugs)} files, {len(linked_slugs)} homepage cards; "
            f"missing {sorted(article_slugs - set(linked_slugs))}"
        )

    # A homepage-curated Note must exist, not merely contain a valid-looking hash.
    linked_note_ids = re.findall(r'href="\./notes/[^"]*#note-([^"]+)"', home)
    for ident in linked_note_ids:
        if ident not in notes:
            errors.append(f"Homepage links to removed or unknown Note: {ident}")

    # The sitemap must represent every published Note and full article exactly once.
    sitemap = SITEMAP.read_text(encoding="utf-8")
    urls = re.findall(r"<loc>([^<]+)</loc>", sitemap)
    if len(urls) != len(set(urls)):
        errors.append("Sitemap contains duplicate URL entries")
    listed = set(urls)
    required = {
        f"{SITE}/notes/n/{slug}/" for slug in expected_detail
    } | {
        f"{SITE}/articles/{slug}/" for slug in article_slugs
    }
    indexed_notes_and_articles = {
        u for u in listed if "/notes/n/" in u or "/articles/" in u
    }
    if required != indexed_notes_and_articles:
        errors.append(
            f"Sitemap drift: {len(required - listed)} missing URLs and "
            f"{len(indexed_notes_and_articles - required)} stale URLs"
        )

    # Check real intra-site fragment links in every page (including generated
    # Note pages); Notes #note-ID hashes are intentionally opened by JavaScript.
    site_pages = [path for path in ROOT.rglob("*.html")
                  if not any(x in {".git", ".github", "publication-preview"} for x in path.parts)]
    parsed: dict[Path, LinksAndIds] = {}
    for page in site_pages:
        if page.relative_to(ROOT).parts[0] == "planning-tools":
            continue  # Separately bundled application with client-side routes.
        parser = LinksAndIds()
        parser.feed(page.read_text(encoding="utf-8", errors="replace"))
        parsed[page.resolve()] = parser
    checked_fragments = 0
    for page, data in parsed.items():
        relative = page.relative_to(ROOT)
        base_url = f"{SITE}/" + ("" if relative.as_posix() == "index.html"
                                 else relative.as_posix()[:-10] if relative.name == "index.html"
                                 else relative.as_posix())
        for href in data.links:
            absolute = urlsplit(urljoin(base_url, href))
            if absolute.netloc != "mattlane66.github.io" or not absolute.fragment:
                continue
            if absolute.path.startswith("/planning-skills-for-agents-and-humans/"):
                continue
            target = ROOT / absolute.path.lstrip("/")
            target = target / "index.html" if absolute.path.endswith("/") or target.is_dir() else target
            resolved = parsed.get(target.resolve())
            if resolved is None:
                continue
            if target.resolve() == ARCHIVE.resolve() and absolute.fragment.startswith("note-"):
                continue
            checked_fragments += 1
            if absolute.fragment not in resolved.ids:
                errors.append(f"{relative}: broken fragment {href} (target lacks #{absolute.fragment})")

    print(
        f"Cross-site consistency: {expected_count} active Notes, "
        f"{len(cards)} archive cards, {len(actual_detail)} detail pages, "
        f"{len(article_files)} full articles, {len(site_pages)} HTML files, "
        f"{len(urls)} sitemap URLs, {checked_fragments} static fragment links."
    )
    return errors


def main() -> int:
    problems = verify()
    for problem in problems:
        print("ERROR:", problem)
    print("PASS: cross-site invariants" if not problems else f"FAILED: {len(problems)} cross-site anomaly/anomalies")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
