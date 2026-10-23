#!/usr/bin/env python3
"""Regression tests for ordered lists in generated Note pages."""
from __future__ import annotations
from html.parser import HTMLParser
import json
import re

from generate_note_pages import NOTES_HTML, DIRECT, REMOVED, render_body, note_slug, note_content, strip_md


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
        # The heading is independent of the authored first paragraph/quote.
        assert note_content(n["title"], n["body"]) == (headline, n["body"].strip()), ident

    # A title-only Note must not render its imported, entity-corrupted
    # summary as a second paragraph with the same text.
    automation_note = notes["80206153"]
    assert automation_note["title"] == "What you can't automate is to know what you should be trying to do."
    assert automation_note["summary"] == automation_note["title"]
    assert "&x27;" not in automation_note["summary"]
    assert render_body(automation_note["body"]) == ""
    assert automation_note["body"] == ""
    assert note_slug(automation_note) == "what-you-can-t-automate-is-to-know-what-you-should-be-trying-to-do-80206153"
    assert note_content(automation_note["title"], automation_note["body"]) == (automation_note["title"], "")

    # The original one-paragraph memory must be displayed below a short title,
    # never truncated into a headline or repeated as a summary paragraph.
    summer_note = notes["227585143"]
    summer_opening = "2013, the summer of my life. The summer I fell in love."
    assert summer_note["title"] == "Derya, 2013"
    assert summer_note["body"].startswith(summer_opening)
    assert summer_note["body"].endswith("she made me laugh.")
    assert summer_note["body"].count(summer_opening) == 1
    assert note_slug(summer_note) == "2013-the-summer-of-my-life-the-summer-i-fell-in-love-the-first-time-we-m-227585143"
    assert note_content(summer_note["title"], summer_note["body"]) == (summer_note["title"], summer_note["body"])
    summer_page = (NOTES_HTML.parent / "n" / note_slug(summer_note) / "index.html").read_text(encoding="utf-8")
    assert "<h1>Derya, 2013</h1>" in summer_page
    assert f'<article class="body"><p>{summer_note["body"]}</p></article>' in summer_page
    assert summer_page.count(summer_note["body"]) == 1

    # Whole-archive presentation audit: check what readers see, not merely
    # source-text overlap. Many titles legitimately appear in the source body,
    # but note_content should remove them from the displayed article.
    def presentation_text(text: str) -> str:
        plain = re.sub(r"[\W_]+", " ", strip_md(text).casefold())
        return re.sub(r"\s+", " ", plain).strip()

    presentation_errors = []
    for ident, note in notes.items():
        raw_title = str(note.get("title") or "")
        source_body = str(note.get("body") or "")
        if not render_body(source_body):
            fallback = str(note.get("summary") or note.get("excerpt") or "")
            if strip_md(fallback).casefold() != strip_md(raw_title).casefold():
                source_body = fallback
        shown_title, shown_body = note_content(raw_title, source_body)
        title_normalized = presentation_text(shown_title)
        body_normalized = presentation_text(shown_body)
        if len(title_normalized) >= 18 and (
            body_normalized == title_normalized or
            body_normalized.startswith(title_normalized + " ")
        ):
            presentation_errors.append(f"{ident}: headline repeated in article opening")
        if len(shown_title) > 230:
            presentation_errors.append(f"{ident}: headline contains an entire paragraph")
        if re.search(r"&(x27|quot);", str(note.get("summary") or "")):
            presentation_errors.append(f"{ident}: malformed/encoded text in summary")
    assert not presentation_errors, "\\n".join(presentation_errors)

    # Distinct headlines must retain the existing published URLs.
    restored = {
        "336302261": "judgment-framework-epistemically-examine-the-principles-336302261",
        "211335608": "my-modified-ooda-loop-the-pc-uda-loop-1-211335608",
        "81369757": "note-81369757",
        "80229568": "every-piece-of-evidence-that-affects-our-confidence-in-an-outcome-change-80229568",
        "80239952": "we-should-expect-to-receive-rewards-and-benefits-for-using-our-skills-an-80239952",
    }
    for ident, old_slug in restored.items():
        assert note_slug(notes[ident]) == old_slug, ident
    assert notes["336302261"]["title"] == "Judgment Framework"
    assert notes["211335608"]["body"].startswith("1. Problem:")
    assert notes["81369757"]["title"] == "Chesterton’s Fence"
    assert "https://fs.blog/chestertons-fence/" in notes["81369757"]["body"]

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
