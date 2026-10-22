#!/usr/bin/env python3
"""Regression tests for ordered lists in generated Note pages."""
from __future__ import annotations
from html.parser import HTMLParser
import json
import re

from generate_note_pages import NOTES_HTML, DIRECT, REMOVED, render_body, note_slug


class ListNumbers(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.top_level = []
        self.nested_bullets = 0

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if tag in ("ol", "ul"):
            start = int(props.get("start", "1")) if tag == "ol" else 1
            self.stack.append({"tag": tag, "next": start})
            if tag == "ul" and len(self.stack) > 1:
                self.nested_bullets += 1
        elif tag == "li" and self.stack:
            current = self.stack[-1]
            if current["tag"] == "ol" and len(self.stack) == 1:
                self.top_level.append(current["next"])
            current["next"] += 1

    def handle_endtag(self, tag):
        if tag in ("ol", "ul") and self.stack:
            assert self.stack[-1]["tag"] == tag
            self.stack.pop()


def rendered_numbers(source: str) -> ListNumbers:
    parser = ListNumbers()
    parser.feed(render_body(source))
    assert not parser.stack
    return parser


def main() -> None:
    source = NOTES_HTML.read_text(encoding="utf-8")
    match = re.search(r'let NOTES=(\[.*?\]);(?=\s*(?:const CATEGORY_KEYS=|const CATS=))', source, re.S)
    assert match, "embedded archive not found"
    notes = {str(n["id"]): n for n in json.loads(match.group(1))}
    notes.update({str(n["id"]): n for n in json.loads(DIRECT.read_text(encoding="utf-8"))})
    for removed_id in json.loads(REMOVED.read_text(encoding="utf-8")):
        notes.pop(str(removed_id), None)

    expected = {
        "299848006": list(range(1, 12)),  # Taste: spaced headings + descriptions
        "211335608": list(range(1, 7)),   # PC²UDA: nested unordered criticism
        "85797688": [1, 2, 3, 4],        # Perspective-taking
        "80202193": [1, 2, 3, 4],        # Product-work categories
        "90731649": [1, 2, 3],          # Three work rhythms (legacy attachment stripped)
    }
    for ident, numbers in expected.items():
        assert ident in notes, f"missing regression Note {ident}"
        got = rendered_numbers(notes[ident]["body"]).top_level
        assert got[:len(numbers)] == numbers, (ident, numbers, got)

    # Editing a Note headline must not invalidate its previously published URL.
    code_note = notes["265799263"]
    assert code_note["title"] == "How to Learn to Read Code Well"
    assert note_slug(code_note) == "the-fastest-path-to-reading-code-well-is-usually-1-265799263"

    # Revised headings should not repeat the opening argument or quotation,
    # and their existing standalone URLs must remain valid.
    renamed_notes = {
        "151458914": ("Can Moral Rules Be Universal?", "if-a-moral-rule-is-grounded-in-shared-human-cognition-reflected-in-cross-151458914", "**If** a moral rule"),
        "83454329": ("The Mad Ones — Jack Kerouac", "the-only-people-for-me-are-the-mad-ones-the-ones-who-are-mad-to-live-mad-83454329", "> [...]the only people"),
    }
    for ident, (headline, permalink, opening) in renamed_notes.items():
        n = notes[ident]
        assert n["title"] == headline, ident
        assert note_slug(n) == permalink, ident
        assert str(n["body"]).startswith(opening), ident

    # Arbitrarily spaced lists must show authored numbers, not restart at one.
    assert rendered_numbers("1. First\n\nDetail\n\n2. Second\n\n3. Third").top_level == [1, 2, 3]
    assert rendered_numbers("1. First\n\n    - Nested detail\n\n2. Second").top_level == [1, 2]
    assert rendered_numbers("1. First\n\n    - Nested detail\n\n2. Second").nested_bullets >= 1
    assert "<script>" not in render_body('<script>alert("x")</script>')
    assert "<strong>" in render_body("**Bold**") and "<em>" in render_body("*Italic*")
    assert "<table>" in render_body("| A | B |\n|---|---|\n| x | y |")

    with_number = 0
    for n in notes.values():
        body = str(n.get("body") or "")
        if re.search(r"(?m)^\s*\d+\.\s+", body):
            with_number += 1
        # Some imported numeric lines are plain prose, indented examples or
        # removed legacy attachments. Ensure every note renders without error;
        # semantic-numbering assertions above cover the known real list cases.
        render_body(body)
    print(f"Passed Note list regressions, including {len(expected)} known cases; rendered {len(notes)} notes ({with_number} numbered).")


if __name__ == "__main__":
    main()
