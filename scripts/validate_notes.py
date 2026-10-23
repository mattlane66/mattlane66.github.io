#!/usr/bin/env python3
"""Validate directly-authored Notes before generating public pages."""
from __future__ import annotations
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notes" / "direct-notes.json"
CATEGORIES = {
    "AI & future work", "Products & systems", "Judgment & knowledge",
    "Writing & craft", "Life & learning", "Society & institutions",
}

def main() -> int:
    try:
        notes = json.loads(SOURCE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: unable to read {SOURCE}: {exc}")
        return 1
    if not isinstance(notes, list):
        print("ERROR: direct-notes.json must contain a JSON array")
        return 1
    errors, seen = [], set()
    for i, n in enumerate(notes, 1):
        label = f"direct-notes.json #{i}"
        if not isinstance(n, dict):
            errors.append(f"{label}: expected an object")
            continue
        for field in ("id", "date", "title", "body", "category"):
            if not isinstance(n.get(field), str) or not n[field].strip():
                errors.append(f"{label}: missing/empty {field}")
        ident = n.get("id")
        if isinstance(ident, str):
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", ident):
                errors.append(f"{label}: id must contain only lowercase letters, digits, hyphens or underscores")
            if ident in seen:
                errors.append(f"{label}: duplicate id {ident!r}")
            seen.add(ident)
        raw_date = n.get("date")
        if isinstance(raw_date, str):
            try:
                if date.fromisoformat(raw_date).isoformat() != raw_date:
                    raise ValueError("incorrect format")
            except ValueError:
                errors.append(f"{label}: invalid YYYY-MM-DD date")
        cat = n.get("category")
        if isinstance(cat, str) and cat not in CATEGORIES:
            errors.append(f"{label}: unknown category {cat!r}")
        if "related_note_ids" in n:
            related = n["related_note_ids"]
            if not isinstance(related, list) or len(related) > 3:
                errors.append(f"{label}: related_note_ids must be a list of at most three IDs")
            elif any(not isinstance(other, str) or not other.strip() for other in related):
                errors.append(f"{label}: related_note_ids must contain nonempty string IDs")
            elif len(related) != len(set(related)):
                errors.append(f"{label}: duplicate related_note_ids")
            elif ident in related:
                errors.append(f"{label}: cannot reference itself in related_note_ids")
    for problem in errors:
        print("ERROR:", problem)
    if errors:
        return 1
    print(f"Validated {len(notes)} directly authored Notes.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
