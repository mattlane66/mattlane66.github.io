"""Conservative, deterministic cross-linking for the site-native Notes collection.

Editorially verified pairs are explicit. Future notes can also acquire links
from unusually strong, distinctive title/content agreement. When uncertain,
emit no link: shared category and common vocabulary are not evidence.
No external APIs, embeddings or publishing-time network calls.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

# Each pair describes an actual relationship between two published arguments.
# The IDs and note URLs are stable even when headlines change.
REVIEWED_PAIRS = [["requirements-are-design-work-20261021","shaping-a-buildable-path-20261019"],
    ["requirements-are-design-work-20261021","249420533"],
    ["requirements-are-design-work-20261021","96766775"],
    ["shaping-a-buildable-path-20261019","89034495"],
    ["shaping-a-buildable-path-20261019","104925537"],
    ["shaping-a-buildable-path-20261019","82451399"],
    ["shaping-a-buildable-path-20261019","115947446"],
    ["shaping-a-buildable-path-20261019","appetite-agent-budgeting-20261002"],
    ["appetite-agent-budgeting-20261002","88166226"],
    ["appetite-agent-budgeting-20261002","83177948"],
    ["88166226","83177948"],
    ["ai-native-manifesto-20261023","product-judgment-agentic-era-20261002"],
    ["ai-native-manifesto-20261023","188294577"],
    ["ai-native-manifesto-20261023","appetite-agent-budgeting-20261002"],
    ["ai-language-defaults-20261002","188294577"],
    ["ai-language-defaults-20261002","product-judgment-agentic-era-20261002"],
    ["compounding-value-model-20261023","opportunity-judgment-loop-20261002"],
    ["beauty-of-fit-20261018","80202998"],
    ["beauty-of-fit-20261018","96766775"],
    ["299848006","taste-20261001"],
    ["299848006","85946687"],
    ["299848006","art-of-seeing-20261013"],
    ["art-of-seeing-20261013","93960199"],
    ["art-of-seeing-20261013","taste-20261001"],
    ["82923660","274811111"],
    ["151458914","85836816"],
    ["151458914","111471359"],
    ["85836816","111471359"],
    ["241499841","80214325"],
    ["331235683","334806623"],
    ["331235683","334444706"],
    ["334806623","257977332"],
    ["86447328","80202589"],
    ["86447328","80203864"],
    ["92039125","86559856"],
    ["86559856","80204572"],
    ["86559856","130621438"],
    ["273645818","80909114"],
    ["questions-that-never-change-20261016","168049222"],
    ["178414268","194420599"],
    ["178414268","80200541"],
    ["193737245","194420599"],
    ["223396370","248651582"],
    ["106101095","85797688"],
    ["345298325","coding-vs-product-20261002"],
    ["80202193","90731649"],
    ["192543364","340781018"],
    ["80206153","188294577"],
    ["179787291","96766775"]]

STOP = set("""
a about above across after again against all also am an and any are around as at
be because been before being below between both but by can cannot could did do
does doing down during each either even ever every few for from further get
gets got had has have having he her hers here him his how i if in into is it its
itself just like may me might more most much must my neither new no nor not now
of off on once one only or other our ours out over own per same she should since
so some still such than that the their them themselves then there these they
this those though through to too two under until up upon us use used using
very via was we were what when where whether which while who whom why will
with within without would you your yours
""".split())

def tokens(value: str) -> set[str]:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"https?://\S+", " ", value.lower())
    words = re.findall(r"[a-z][a-z0-9]{2,}", value)
    return {word for word in words if word not in STOP}

def related_notes(notes: list[dict], limit: int = 3) -> dict[str, list[str]]:
    """Return at most three reliable destinations for each note.

    The matching rule deliberately favors precision over recall. Automatic
    links require TWO uncommon words in both headlines, supporting overlap in
    the bodies, and contextual agreement. A generic category match never
    qualifies. Explicit reviewed IDs take precedence over global reviewed pairs,
    then lexical fallback. All results are capped by limit.
    """
    by_id = {str(n["id"]): n for n in notes}
    ids = sorted(by_id)
    headlines = {i: tokens(by_id[i].get("title", "")) for i in ids}
    bodies = {i: tokens(str(by_id[i].get("body") or by_id[i].get("excerpt") or by_id[i].get("summary") or "")[:3500]) for i in ids}
    doc_frequency: Counter[str] = Counter()
    for i in ids:
        doc_frequency.update(headlines[i] | bodies[i])
    unusual = {word for word, freq in doc_frequency.items() if freq <= max(7, len(ids) // 35)}
    scores: dict[str, dict[str, float]] = {i: {} for i in ids}

    def record(a: str, b: str, score: float) -> None:
        if a == b or a not in by_id or b not in by_id:
            return
        scores[a][b] = max(scores[a].get(b, 0), score)
        scores[b][a] = max(scores[b].get(a, 0), score)

    for priority, (a, b) in enumerate(REVIEWED_PAIRS):
        record(a, b, 1000.0 - priority)

    # New notes can declare a small number of human-reviewed relationships.
    # Source metadata is authoritative over old reviewed pairs and lexical
    # suggestions. Links are reciprocal; no second edit to an old note is needed.
    for source in ids:
        note = by_id[source]
        if "related_note_ids" not in note:
            continue
        destinations = note["related_note_ids"]
        if not isinstance(destinations, list) or len(destinations) > limit:
            raise ValueError(f"{source}: related_note_ids must be a list of at most {limit} note IDs")
        if any(not isinstance(target, str) or not target.strip() for target in destinations):
            raise ValueError(f"{source}: related_note_ids must contain nonempty string IDs")
        if len(set(destinations)) != len(destinations):
            raise ValueError(f"{source}: duplicate related_note_ids")
        for priority, target in enumerate(destinations):
            if target == source:
                raise ValueError(f"{source}: a Note cannot link to itself")
            if target not in by_id:
                raise ValueError(f"{source}: related Note ID {target!r} does not exist")
            record(source, target, 2000.0 - priority)

    # A strict lexical fallback, not an attempt to infer semantic similarity
    # from generic words like "design", "human", or "product".
    for offset, a in enumerate(ids):
        for b in ids[offset + 1:]:
            # A publication-time editorial review is authoritative. Even an
            # empty list means "no verified relation": do not invent one from
            # lexical overlap. Reviewed global pairs still apply above.
            if "related_note_ids" in by_id[a] or "related_note_ids" in by_id[b]:
                continue
            shared_title = headlines[a] & headlines[b] & unusual
            if len(shared_title) < 2:
                continue
            shared_body = bodies[a] & bodies[b] & unusual
            if len(shared_body) < 2:
                continue
            if by_id[a].get("category") != by_id[b].get("category") and len(shared_title) < 3:
                continue
            # Exclude notes consisting only of headings and low-information
            # fragments unless they have an explicitly reviewed relation.
            if len(headlines[a] | bodies[a]) < 7 or len(headlines[b] | bodies[b]) < 7:
                continue
            evidence = len(shared_title) * 2 + len(shared_body)
            if evidence < 7:
                continue
            record(a, b, float(evidence))

    return {
        i: [target for target, _ in sorted(
            scores[i].items(), key=lambda item: (-item[1], item[0])
        )[:limit]]
        for i in ids if scores[i]
    }
