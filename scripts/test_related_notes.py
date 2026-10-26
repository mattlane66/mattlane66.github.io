#!/usr/bin/env python3
"""Validate relationship precision boundaries and every published related link."""
from __future__ import annotations
from html.parser import HTMLParser
from urllib.parse import urlsplit

from check_site_consistency import active_notes
from generate_note_pages import NOTES_HTML, OUT, ROOT, ARTICLE_RELATED_LINKS, note_slug, augment_custom_note
from related_notes import related_notes

class RelatedLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_related = False
        self.sections = 0
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "aside" and "related-thinking" in attrs.get("class", "").split():
            assert not self.in_related, "Nested related-asides"
            self.in_related = True
            self.sections += 1
        if tag == "a" and self.in_related:
            self.links.append(attrs.get("href", ""))

    def handle_endtag(self, tag):
        if tag == "aside" and self.in_related:
            self.in_related = False

def main() -> None:
    notes = active_notes(NOTES_HTML.read_text(encoding="utf-8"))
    refs = related_notes(list(notes.values()))
    assert refs["requirements-are-design-work-20261021"], "Missing reviewed product links"
    assert "shaping-a-buildable-path-20261019" in refs["requirements-are-design-work-20261021"]
    assert refs["appetite-agent-budgeting-20261002"], "Missing appetite connections"

    # Completely unrelated micro-notes must not attract made-up links.
    lonely = [
        {"id": "x", "title": "The river is warm today", "body": "A short walk under trees.", "category": "Life & learning"},
        {"id": "y", "title": "Enterprise audit billing architecture", "body": "Different database design and contracts.", "category": "Products & systems"},
    ]
    assert related_notes(lonely) == {}

    # A realistic future draft is conceptually related but does not share
    # enough rare headline words to qualify for lexical matching alone.
    # A publication-time editorial choice must create reciprocal links.
    future = {
        "id": "audit-future-shaping-note",
        "title": "Working with agents under uncertainty",
        "body": (
            "Before agents implement software, make judgments about needs, "
            "appetite, design constraints, and the smallest buildable outcome."
        ),
        "category": "Products & systems",
        "related_note_ids": ["shaping-a-buildable-path-20261019"],
    }
    from_review = related_notes([*notes.values(), future])
    assert from_review[future["id"]][0] == "shaping-a-buildable-path-20261019"
    assert future["id"] in from_review["shaping-a-buildable-path-20261019"]

    # An explicit no-match review must not be overridden by similarity alone.
    # This synthetic note deliberately copies an existing note word for word.
    source = notes["requirements-are-design-work-20261021"]
    abstained = {
        **source,
        "id": "audit-reviewed-no-match",
        "related_note_ids": [],
    }
    no_match = related_notes([*notes.values(), abstained])
    assert abstained["id"] not in no_match

    # Bad editorial references are publication failures, never silently
    # dropped or converted into broken links.
    for invalid in (
        ["missing-destination"],
        [future["id"]],
        ["shaping-a-buildable-path-20261019"] * 2,
        ["a", "b", "c", "d"],
        "shaping-a-buildable-path-20261019",
        None,
    ):
        sample = {**future, "related_note_ids": invalid}
        try:
            related_notes([*notes.values(), sample])
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid related_note_ids accepted: {invalid!r}")

    # A regenerated custom interactive page must not accumulate duplicate UI.
    template = "<html><head></head><body><main>Content</main></body></html>"
    relation = '<aside class="related-thinking" aria-label="Related thinking"><h2>Related thinking</h2><ul><li><a href="/notes/n/example/">Example</a></li></ul></aside>'
    once = augment_custom_note(template, relation)
    assert augment_custom_note(once, relation) == once
    assert augment_custom_note(once, "") == template

    linked = 0
    for ident, note in notes.items():
        html_path = OUT / note_slug(note) / "index.html"
        assert html_path.exists(), f"Missing page: {ident}"
        parser = RelatedLinks()
        parser.feed(html_path.read_text(encoding="utf-8"))
        article_links = ARTICLE_RELATED_LINKS.get(ident, [])
        expected = ["/notes/n/" + note_slug(notes[other]) + "/" for other in refs.get(ident, [])]
        expected += [href for href, _ in article_links]
        assert parser.links == expected, (ident, parser.links, expected)
        assert parser.sections == int(bool(expected)), (ident, parser.sections)
        assert len(refs.get(ident, [])) <= 3 and ident not in refs.get(ident, [])
        assert len(expected) == len(set(expected))
        for href in parser.links:
            assert urlsplit(href).query == "" and urlsplit(href).fragment == ""
            assert href.startswith(("/notes/n/", "/articles/")), (ident, href)
            assert (ROOT / href.lstrip("/") / "index.html").exists(), (ident, href)
        for href, _ in article_links:
            article = (ROOT / href.lstrip("/") / "index.html").read_text(encoding="utf-8")
            reciprocal = f'href="/notes/n/{note_slug(note)}/"'
            assert reciprocal in article, (ident, href, "Missing reciprocal article link")
        if expected:
            linked += 1

    archive = NOTES_HTML.read_text(encoding="utf-8")
    assert 'related:related?related.outerHTML:""' in archive
    assert 'body.innerHTML=rendered.body+(rendered.related||"")' in archive
    print(f"Validated related links for {len(notes)} Notes; {linked} have clear matches; others abstained.")

if __name__ == "__main__":
    main()
