#!/usr/bin/env python3
"""Generate indexable static Note pages and sitemap from the site-native Notes archive."""
from __future__ import annotations
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://mattlane66.github.io"
NOTES_HTML = ROOT / "notes" / "index.html"
DIRECT = ROOT / "notes" / "direct-notes.json"
OUT = ROOT / "notes" / "n"
GENERIC_IMAGE = SITE + "/assets/working-form-flow-crisp-v3.jpg"

def strip_substack_urls(value: str) -> str:
    # Public Note pages are site-native. Keep link labels and note text, but
    # omit legacy Substack article, profile, and image-host URLs.
    value = value or ""
    value = re.sub(r'!\[([^\]]*)\]\((https?://[^)]*substack[^)]*)\)', '', value, flags=re.I)
    value = re.sub(r'\[([^\]]+)\]\((https?://[^)]*substack[^)]*)\)', r'\1', value, flags=re.I)
    value = re.sub(r'https?://[^\s)\]]*substack[^\s)\]]*', '', value, flags=re.I)
    value = re.sub(r'^#{1,6}\s+Attachments?\s*$', '', value, flags=re.I | re.M)
    return re.sub(r'^\s*\d+\.\s*$', '', value, flags=re.M)

def slugify(value: str) -> str:
    value = re.sub(r"https?://\S+", "", value.lower())
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "note"
    return value[:72].rstrip("-")

def strip_md(value: str) -> str:
    value = strip_substack_urls(value)
    value = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", value or "")
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"[*_#>`~]", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def description(n: dict) -> str:
    value = strip_md(str(n.get("summary") or n.get("excerpt") or n.get("body") or n.get("title") or ""))
    if len(value) <= 155:
        return value
    return re.sub(r"\s+\S*$", "", value[:152]) + "…"

def seo_title(value: str) -> str:
    if len(value) <= 66:
        return value
    short = re.sub(r"\s+\S*$", "", value[:63]).strip()
    return (short or value[:63]).rstrip(" ,.;:—-") + "…"

def render_body(value: str) -> str:
    value = strip_substack_urls(value)
    blocks = [b.strip() for b in re.split(r"\n\s*\n", value or "") if b.strip()]
    return "\n".join("<p>" + html.escape(b).replace("\n", "<br>") + "</p>" for b in blocks)


def note_content(title: str, body: str) -> tuple[str, str]:
    """Show a repeated opening once; preserve the remaining note verbatim.

    Keep this presentation rule in sync with noteContent in notes/index.html.
    Original titles still determine URLs, so expanding a heading never breaks links.
    """
    title, body = title.strip(), body.strip()
    first = re.split(r"\n\s*\n", body, maxsplit=1)[0]
    heading = re.sub(r"^#{1,5}\s+", "", first)
    heading = re.sub(r"^(\*\*|__)([\s\S]+)\1$", r"\2", heading).strip()
    if title and heading == title:
        return title, body[len(first):].lstrip()
    prefix = re.sub(r"(?:…|\.{3})$", "", title).rstrip()
    if not prefix or not body.startswith(prefix):
        return title, body
    if prefix != title:
        # Complete short, plain-text openings; never promote links or Markdown.
        candidate = first.strip()
        if len(candidate) > 360 or re.search(r"[\n*_\[\]`#>]", candidate):
            sentence = re.match(r'''^[\s\S]*?[.!?]["'”’)]*(?=\s|$)''', body)
            candidate = sentence.group(0) if sentence else ""
        if not candidate or re.search(r"[\n*_\[\]`#>]", candidate):
            return title, body
        title = candidate
    if body.startswith(title) and (len(body) == len(title) or body[len(title)].isspace()):
        body = body[len(title):].lstrip()
    return title, body


def patch_planning_tools() -> None:
    path = ROOT / "planning-tools" / "index.html"
    text = path.read_text(encoding="utf-8")
    marker = '<meta name="x-seo-layer" content="2026-10-01">'
    if marker in text:
        return
    title = "Planning Skills Lab — Human + Agent Planning · Matt Lane"
    desc = "A click-through human and agent collaboration walkthrough from messy evidence to a build-ready slice."
    url = SITE + "/planning-tools/"
    image = SITE + "/assets/planning-skills-lab-preview.jpg"
    text = re.sub(r"<title>[\s\S]*?</title>", f"<title>{title}</title>", text, count=1, flags=re.I)
    text = re.sub(r"<meta\b(?=[^>]*\bname=['\"]description['\"])[^>]*>\s*", "", text, count=1, flags=re.I)
    text = re.sub(r"<link\b(?=[^>]*\brel=['\"]canonical['\"])[^>]*>\s*", "", text, flags=re.I)
    schema = {
        "@context":"https://schema.org","@type":"CreativeWork","@id":url+"#lab",
        "name":"Planning Skills Lab","description":desc,"url":url,"image":image,
        "author":{"@type":"Person","@id":SITE+"/#person","name":"Matt Lane","url":SITE+"/"},
        "genre":"Interactive planning tool",
    }
    block = f"""\n{marker}
<meta name="description" content="{html.escape(desc, quote=True)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Matt Lane">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(desc, quote=True)}">
<meta property="og:image" content="{image}">
<meta property="og:image:alt" content="Planning Skills Lab human and agent planning walkthrough">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(title, quote=True)}">
<meta name="twitter:description" content="{html.escape(desc, quote=True)}">
<meta name="twitter:image" content="{image}">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
"""
    style = re.search(r"<style\b", text, re.I)
    if not style:
        raise SystemExit("Could not find <style> in planning-tools/index.html")
    text = text[:style.start()] + block + text[style.start():]
    path.write_text(text, encoding="utf-8")

def main() -> None:
    patch_planning_tools()
    text = NOTES_HTML.read_text(encoding="utf-8")
    match = re.search(r"let NOTES=(\[.*?\]);const CATS=", text, re.S)
    if not match:
        raise SystemExit("Could not locate embedded Notes archive")
    notes = json.loads(match.group(1))

    direct = json.loads(DIRECT.read_text(encoding="utf-8"))
    by_id = {str(n["id"]): n for n in notes}
    for i, n in enumerate(direct):
        if not isinstance(n, dict) or not n.get("title") or not n.get("date"):
            continue
        ident = str(n.get("id") or f"{n['date']}-{n['title']}-{i}")
        ident = re.sub(r"[^a-z0-9_-]+", "-", ident.lower()).strip("-") or f"direct-{i}"
        by_id[ident] = {**n, "id": ident}
    notes = sorted(by_id.values(), key=lambda n: (str(n.get("date","")), str(n.get("id",""))), reverse=True)

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    note_urls: list[tuple[str, str]] = []
    for n in notes:
        ident = str(n["id"])
        slug = f"{slugify(str(n.get('title','')))}-{ident}"
        folder = OUT / slug
        folder.mkdir()
        url = f"{SITE}/notes/n/{slug}/"
        title = strip_substack_urls(str(n.get("title") or "")).strip() or "Untitled note"
        desc = description(n)
        source_body = str(n.get("body") or "")
        if not render_body(source_body):
            fallback = str(n.get("summary") or n.get("excerpt") or "")
            if strip_md(fallback).lower() != strip_md(title).lower():
                source_body = fallback
        title, source_body = note_content(title, source_body)
        search_title = seo_title(title)
        body = render_body(source_body)
        discussion = render_body(str(n.get("discussion") or ""))
        category = html.escape(str(n.get("category") or ""))
        date = html.escape(str(n.get("date") or ""))
        schema = {
            "@context":"https://schema.org",
            "@type":"Article",
            "@id":url+"#article",
            "headline":title,
            "description":desc,
            "url":url,
            "datePublished":str(n.get("date") or ""),
            "author":{"@type":"Person","@id":SITE+"/#person","name":"Matt Lane","url":SITE+"/"},
            "mainEntityOfPage":url,
        }
        page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="icon" href="/favicon.svg?v=20260930" type="image/svg+xml">
<title>{html.escape(search_title)} — Matt Lane</title>
<meta name="description" content="{html.escape(desc, quote=True)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Matt Lane">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{html.escape(title + ' — Matt Lane', quote=True)}">
<meta property="og:description" content="{html.escape(desc, quote=True)}">
<meta property="og:image" content="{GENERIC_IMAGE}">
<meta property="og:image:alt" content="Matt Lane product strategy and interaction map">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(title + ' — Matt Lane', quote=True)}">
<meta name="twitter:description" content="{html.escape(desc, quote=True)}">
<meta name="twitter:image" content="{GENERIC_IMAGE}">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
<style>
:root{{--bg:#f2efe7;--paper:#fffefa;--ink:#10100f;--muted:#68675f;--line:#cfccc1;--blue:#173dff;--max:900px}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}}
a{{color:inherit}}.wrap{{width:min(var(--max),calc(100% - 36px));margin:auto}}
.top{{border-bottom:1px solid var(--line)}}.topin{{height:58px;display:flex;align-items:center;justify-content:space-between;gap:18px}}
.brand{{font-weight:800;text-decoration:none;letter-spacing:-.02em}}.back{{font-size:12px;color:var(--muted);text-decoration:none}}
main{{padding:clamp(58px,9vw,110px) 0 100px}}.meta{{font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);margin-bottom:20px}}
h1{{font-size:clamp(42px,7vw,78px);line-height:.96;letter-spacing:-.055em;margin:0 0 34px}}
.body{{font-family:Georgia,"Times New Roman",serif;font-size:19px;line-height:1.68;max-width:760px}}
.body p{{margin:0 0 1.1em}}.discussion{{border-top:1px solid var(--line);margin-top:48px;padding-top:28px}}
.discussion h2{{font-size:18px;letter-spacing:-.02em}}footer{{border-top:1px solid var(--line);padding:24px 0 36px;color:var(--muted);font-size:12px}}
</style>
</head>
<body>
<header class="top"><div class="wrap topin"><a class="brand" href="/notes/">Matt Lane · Notes</a><a class="back" href="/notes/">← All notes</a></div></header>
<main class="wrap"><div class="meta">{date}{(' · ' + category) if category else ''}</div><h1>{html.escape(title)}</h1><article class="body">{body}</article>{('<section class="discussion"><h2>Discussion</h2><div class="body">'+discussion+'</div></section>') if discussion else ''}</main>
<footer><div class="wrap">© 2026 Matt Lane</div></footer>
</body>
</html>"""
        if re.search(r'https?://[^"\'<>\s]*substack', page, flags=re.I):
            raise RuntimeError(f"Substack URL leaked into generated page: {slug}")
        (folder / "index.html").write_text(page, encoding="utf-8")
        note_urls.append((url, str(n.get("date") or "")))

    core = [
        SITE+"/", SITE+"/about/", SITE+"/splice/", SITE+"/nyshex/", SITE+"/codeai/",
        SITE+"/fit-check/", SITE+"/planning-tools/", SITE+"/notes/"
    ]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lines += [f"  <url><loc>{u}</loc></url>" for u in core]
    lines += [f"  <url><loc>{u}</loc><lastmod>{d}</lastmod></url>" for u,d in note_urls if d]
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"Generated {len(notes)} Note pages.")

if __name__ == "__main__":
    main()
