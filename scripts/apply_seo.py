#!/usr/bin/env python3
from __future__ import annotations
import html, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://mattlane66.github.io"
GENERIC_IMAGE = SITE + "/assets/working-form-flow-crisp-v3.jpg"
AUTHOR = {"@type":"Person","@id":SITE+"/#person","name":"Matt Lane","url":SITE+"/"}
PERSON = {
    "@type":"Person","@id":SITE+"/#person","name":"Matt Lane","url":SITE+"/",
    "jobTitle":"Product Strategist and AI-Native Design Engineer",
    "image":SITE+"/assets/about-matt-lane-2x.avif",
    "sameAs":["https://github.com/mattlane66","https://www.linkedin.com/in/matthewhlane/"]
}

CONFIG = {
 "index.html": {
   "title":"Matt Lane — Product Strategist & AI-Native Design Engineer",
   "description":"Product strategist and AI-native design engineer Matt Lane: case studies, side projects, thinking tools, research, and notes from 0→1 product work.",
   "url":SITE+"/","image":GENERIC_IMAGE,"image_alt":"Matt Lane product strategy and interaction map",
   "ld":{"@context":"https://schema.org","@graph":[PERSON,{"@type":"WebSite","@id":SITE+"/#website","url":SITE+"/","name":"Matt Lane","author":{"@id":SITE+"/#person"}},{"@type":"WebPage","@id":SITE+"/#webpage","url":SITE+"/","name":"Matt Lane — Product Strategist & AI-Native Design Engineer","isPartOf":{"@id":SITE+"/#website"},"about":{"@id":SITE+"/#person"}}]}
 },
 "about/index.html": {
   "title":"About Matt Lane — Product Strategist & AI-Native Design Engineer",
   "description":"About Matt Lane, a product strategist and AI-native design engineer working across product strategy, interaction design, AI, and 0→1 product development.",
   "url":SITE+"/about/","image":GENERIC_IMAGE,"image_alt":"Matt Lane product strategy and interaction map",
   "ld":{"@context":"https://schema.org","@graph":[PERSON,{"@type":"ProfilePage","@id":SITE+"/about/#page","url":SITE+"/about/","name":"About Matt Lane","mainEntity":{"@id":SITE+"/#person"}}]}
 },
 "splice/index.html": {
   "title":"Splice Create / Stacks — Product Leadership Case · Matt Lane",
   "description":"Matt Lane’s product leadership at Splice: the strategy, scope decisions, and learning behind the CoSo song starter and its evolution into Create / Stacks.",
   "url":SITE+"/splice/","image":SITE+"/assets/splice-case-preview.png","image_alt":"Preview of Matt Lane’s Splice Create / Stacks product case study",
   "ld":{"@context":"https://schema.org","@type":"CreativeWork","@id":SITE+"/splice/#case","name":"Splice Create / Stacks — Product Leadership Case","description":"Matt Lane’s product leadership at Splice: the strategy, scope decisions, and learning behind the CoSo song starter and its evolution into Create / Stacks.","url":SITE+"/splice/","image":SITE+"/assets/splice-case-preview.png","author":AUTHOR,"genre":"Product case study"}
 },
 "nyshex/index.html": {
   "title":"NYSHEX — Product Strategy Case Study · Matt Lane",
   "description":"A product strategy case study of Matt Lane’s NYSHEX work, showing how product framing, boundaries, and decision-making shaped the work.",
   "url":SITE+"/nyshex/","image":GENERIC_IMAGE,"image_alt":"Matt Lane product strategy and interaction map",
   "ld":{"@context":"https://schema.org","@type":"CreativeWork","@id":SITE+"/nyshex/#case","name":"NYSHEX — Product Strategy Case Study","description":"A product strategy case study of Matt Lane’s NYSHEX work, showing how product framing, boundaries, and decision-making shaped the work.","url":SITE+"/nyshex/","author":AUTHOR,"genre":"Product case study"}
 },
 "codeai/index.html": {
   "title":"CodeAI — AI Tutor in Web Lab · Matt Lane",
   "description":"A product case study about Matt Lane’s leadership of AI Tutor and Teaching Assistant at Code.org, now CodeAI, with a focus on AI Tutor inside Web Lab.",
   "url":SITE+"/codeai/","image":GENERIC_IMAGE,"image_alt":"Matt Lane product strategy and interaction map",
   "ld":{"@context":"https://schema.org","@type":"CreativeWork","@id":SITE+"/codeai/#case","name":"CodeAI — AI Tutor in Web Lab","description":"A product case study about Matt Lane’s leadership of AI Tutor and Teaching Assistant at Code.org, now CodeAI, with a focus on AI Tutor inside Web Lab.","url":SITE+"/codeai/","author":AUTHOR,"genre":"Product case study"}
 },
 "fit-check/index.html": {
   "title":"The Fit Check Error Model — Matt Lane",
   "description":"An interactive visual guide to the Fit Check Error Model: framing, conformance, effect, Fit Checks, Reverse Fit, and backward diagnosis.",
   "url":SITE+"/fit-check/","image":SITE+"/assets/fit-check-preview.png","image_alt":"The Fit Check Error Model visual framework",
   "ld":{"@context":"https://schema.org","@type":"CreativeWork","@id":SITE+"/fit-check/#model","name":"The Fit Check Error Model","description":"An interactive visual guide to the Fit Check Error Model: framing, conformance, effect, Fit Checks, Reverse Fit, and backward diagnosis.","url":SITE+"/fit-check/","image":SITE+"/assets/fit-check-preview.png","author":AUTHOR,"genre":"Product strategy method"}
 },
 "notes/index.html": {
   "title":"Notes — Matt Lane",
   "description":"Working thoughts, fragments, propositions, and notes by Matt Lane on products, systems, judgment, AI, writing, and learning.",
   "url":SITE+"/notes/","image":GENERIC_IMAGE,"image_alt":"Matt Lane product strategy and interaction map",
   "ld":{"@context":"https://schema.org","@type":"CollectionPage","@id":SITE+"/notes/#collection","name":"Notes — Matt Lane","description":"Working thoughts, fragments, propositions, and notes by Matt Lane on products, systems, judgment, AI, writing, and learning.","url":SITE+"/notes/","author":AUTHOR}
 },
 "planning-tools/index.html": {
   "title":"Planning Skills Lab — Human + Agent Planning · Matt Lane",
   "description":"A click-through human and agent collaboration walkthrough from messy evidence to a build-ready slice.",
   "url":SITE+"/planning-tools/","image":SITE+"/assets/planning-skills-lab-preview.jpg","image_alt":"Planning Skills Lab human and agent planning walkthrough",
   "ld":{"@context":"https://schema.org","@type":"CreativeWork","@id":SITE+"/planning-tools/#lab","name":"Planning Skills Lab","description":"A click-through human and agent collaboration walkthrough from messy evidence to a build-ready slice.","url":SITE+"/planning-tools/","image":SITE+"/assets/planning-skills-lab-preview.jpg","author":AUTHOR,"genre":"Interactive planning tool"}
 }
}

def attr(s: str) -> str:
    return html.escape(str(s), quote=True)

def inject(page: str, cfg: dict) -> str:
    page = re.sub(r"<title>[\s\S]*?</title>", f"<title>{cfg['title']}</title>", page, count=1, flags=re.I)
    page = re.sub(r'<meta\b(?=[^>]*\bname=(["\'])description\1)[^>]*>\s*', "", page, flags=re.I)
    page = re.sub(r'<link\b(?=[^>]*\brel=(["\'])canonical\1)[^>]*>\s*', "", page, flags=re.I)
    page = re.sub(r'<meta\b(?=[^>]*\bproperty=(["\'])og:[^"\']+\1)[^>]*>\s*', "", page, flags=re.I)
    page = re.sub(r'<meta\b(?=[^>]*\bname=(["\'])twitter:[^"\']+\1)[^>]*>\s*', "", page, flags=re.I)
    page = re.sub(r'<meta\b(?=[^>]*\bname=(["\'])robots\1)[^>]*>\s*', "", page, flags=re.I)
    page = re.sub(r'<script\b[^>]*type=(["\'])application/ld\+json\1[^>]*>[\s\S]*?</script>\s*', "", page, flags=re.I)
    block = "\n".join([
        f'<meta name="description" content="{attr(cfg["description"])}">',
        '<meta name="robots" content="index,follow,max-image-preview:large">',
        f'<link rel="canonical" href="{attr(cfg["url"])}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Matt Lane">',
        f'<meta property="og:url" content="{attr(cfg["url"])}">',
        f'<meta property="og:title" content="{attr(cfg["title"])}">',
        f'<meta property="og:description" content="{attr(cfg["description"])}">',
        f'<meta property="og:image" content="{attr(cfg["image"])}">',
        f'<meta property="og:image:alt" content="{attr(cfg["image_alt"])}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{attr(cfg["title"])}">',
        f'<meta name="twitter:description" content="{attr(cfg["description"])}">',
        f'<meta name="twitter:image" content="{attr(cfg["image"])}">',
        '<script type="application/ld+json">'+json.dumps(cfg["ld"], ensure_ascii=False, separators=(",",":"))+'</script>',
        ''
    ])
    m = re.search(r"<style\b", page, re.I)
    if m:
        page = page[:m.start()] + block + page[m.start():]
    else:
        page = re.sub(r"</head>", block+"</head>", page, count=1, flags=re.I)
    return page

def strip_substack_urls(s: str) -> str:
    # The public SEO pages are site-native. Preserve the note's words, but do not
    # carry old Substack profile/article/image-host URLs into the generated pages.
    s = s or ""
    s = re.sub(r'!\[([^\]]*)\]\((https?://[^)]*substack[^)]*)\)', '', s, flags=re.I)
    s = re.sub(r'\[([^\]]+)\]\((https?://[^)]*substack[^)]*)\)', r'\1', s, flags=re.I)
    s = re.sub(r'https?://[^\s)\]]*substack[^\s)\]]*', '', s, flags=re.I)
    s = re.sub(r'^#{1,6}\s+Attachments?\s*
def strip_md(s: str) -> str:
    s = strip_substack_urls(s)
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', s)
    s = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'https?://\S+', ' ', s)
    s = re.sub(r'[*_#>`~]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def clean_note_title(n: dict) -> str:
    candidates = [n.get("title"), n.get("summary"), n.get("excerpt"), n.get("body")]
    for raw in candidates:
        s = strip_substack_urls(str(raw or ""))
        s = re.sub(r'\bAttachments?\b(?:\s+\d+\.?)*', ' ', s, flags=re.I)
        s = re.sub(r'https?://\S+', ' ', s)
        s = re.sub(r'\s+', ' ', s).strip(' |·,:;-–—')
        if s and not re.fullmatch(r'(image|note\s+\d+)', s, flags=re.I):
            return s[:180].strip()
    return "Untitled note"

def slugify(s: str) -> str:
    s = re.sub(r'https?://\S+', '', s.lower())
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-') or 'note'
    return s[:72].rstrip('-')

def description(n: dict) -> str:
    s = strip_md(str(n.get("summary") or n.get("excerpt") or n.get("body") or n.get("title") or ""))
    if len(s) <= 155: return s
    return re.sub(r'\s+\S*$', '', s[:152]) + '…'

def render_body(s: str) -> str:
    s = strip_substack_urls(s)
    blocks = [b.strip() for b in re.split(r'\n\s*\n', s) if b.strip()]
    out=[]
    for b in blocks:
        lines=b.splitlines()
        if lines and all(re.match(r'^[-*]\s+', x) for x in lines):
            out.append('<ul>'+''.join('<li>'+html.escape(re.sub(r'^[-*]\s+','',x))+'</li>' for x in lines)+'</ul>')
        elif lines and all(re.match(r'^\d+\.\s+', x) for x in lines):
            out.append('<ol>'+''.join('<li>'+html.escape(re.sub(r'^\d+\.\s+','',x))+'</li>' for x in lines)+'</ol>')
        else:
            out.append('<p>'+html.escape(b).replace('\n','<br>')+'</p>')
    return "\n".join(out)

def build_notes() -> list[tuple[str,str]]:
    notes_text=(ROOT/"notes/index.html").read_text(encoding="utf-8")
    m=re.search(r'let NOTES=(\[.*?\]);const CATS=', notes_text, re.S)
    if not m: raise RuntimeError("Could not parse NOTES archive")
    archive=json.loads(m.group(1))
    direct=json.loads((ROOT/"notes/direct-notes.json").read_text(encoding="utf-8"))
    by_id={str(n["id"]):n for n in archive}
    for i,n in enumerate(direct):
        if not isinstance(n,dict) or not n.get("title") or not n.get("date"): continue
        ident=str(n.get("id") or f"{n['date']}-{n['title']}-{i}").lower()
        ident=re.sub(r'[^a-z0-9_-]+','-',ident).strip('-') or f'direct-{i}'
        by_id[ident]={**n,"id":ident}
    notes=sorted(by_id.values(),key=lambda n:(str(n.get("date","")),str(n.get("id",""))),reverse=True)
    out=ROOT/"notes/n"
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    urls=[]
    css='body{margin:0;background:#f2efe7;color:#10100f;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif}.wrap{width:min(900px,calc(100% - 36px));margin:auto}header{border-bottom:1px solid #cfccc1}header .wrap{height:58px;display:flex;align-items:center;justify-content:space-between}a{color:inherit}main{padding:70px 0 100px}.meta{font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:#68675f;margin-bottom:20px}h1{font-size:clamp(42px,7vw,78px);line-height:.96;letter-spacing:-.055em;margin:0 0 34px}article{font:19px/1.68 Georgia,serif;max-width:760px}article p{margin:0 0 1.1em}footer{border-top:1px solid #cfccc1;padding:24px 0 36px;color:#68675f;font-size:12px}'
    for n in notes:
        ident=str(n["id"]); title=clean_note_title(n); slug=f"{slugify(title)}-{ident}"
        folder=out/slug; folder.mkdir()
        url=f"{SITE}/notes/n/{slug}/"; desc=description({**n, "title": title})
        body=render_body(str(n.get("body") or "")); discussion=render_body(str(n.get("discussion") or ""))
        schema={"@context":"https://schema.org","@type":"Article","@id":url+"#article","headline":title,"description":desc,"url":url,"datePublished":str(n.get("date") or ""),"author":AUTHOR,"mainEntityOfPage":url}
        meta=(str(n.get("date") or "") + ((" · "+str(n.get("category"))) if n.get("category") else ""))
        page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><link rel="icon" href="/favicon.svg?v=20260930" type="image/svg+xml"><title>{html.escape(title)} — Matt Lane</title><meta name="description" content="{attr(desc)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{url}"><meta property="og:type" content="article"><meta property="og:site_name" content="Matt Lane"><meta property="og:url" content="{url}"><meta property="og:title" content="{attr(title+' — Matt Lane')}"><meta property="og:description" content="{attr(desc)}"><meta property="og:image" content="{GENERIC_IMAGE}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{attr(title+' — Matt Lane')}"><meta name="twitter:description" content="{attr(desc)}"><meta name="twitter:image" content="{GENERIC_IMAGE}"><script type="application/ld+json">{json.dumps(schema,ensure_ascii=False,separators=(",",":"))}</script><style>{css}</style></head><body><header><div class="wrap"><a href="/notes/">Matt Lane · Notes</a><a href="/notes/">← All notes</a></div></header><main class="wrap"><div class="meta">{html.escape(meta)}</div><h1>{html.escape(title)}</h1><article>{body}</article>{('<section><h2>Discussion</h2><article>'+discussion+'</article></section>') if discussion else ''}</main><footer><div class="wrap">© 2026 Matt Lane</div></footer></body></html>'''
        if "substack" in page.lower():
            raise RuntimeError(f"Substack reference leaked into generated page: {slug}")
        (folder/"index.html").write_text(page,encoding="utf-8")
        urls.append((url,str(n.get("date") or "")))
    return urls

def write_sitemap(note_urls: list[tuple[str,str]]) -> None:
    core=[SITE+"/",SITE+"/about/",SITE+"/splice/",SITE+"/nyshex/",SITE+"/codeai/",SITE+"/fit-check/",SITE+"/planning-tools/",SITE+"/notes/"]
    lines=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lines += [f'  <url><loc>{u}</loc></url>' for u in core]
    lines += [f'  <url><loc>{u}</loc>'+(f'<lastmod>{d}</lastmod>' if d else '')+'</url>' for u,d in note_urls]
    lines.append('</urlset>')
    (ROOT/"sitemap.xml").write_text("\n".join(lines)+"\n",encoding="utf-8")

def main() -> None:
    for rel,cfg in CONFIG.items():
        p=ROOT/rel
        p.write_text(inject(p.read_text(encoding="utf-8"),cfg),encoding="utf-8")
    note_urls=build_notes()
    write_sitemap(note_urls)
    print(f"SEO updated; generated {len(note_urls)} indexable Note pages.")

if __name__=="__main__":
    main()
, '', s, flags=re.I | re.M)
    s = re.sub(r'^\s*\d+\.\s*
def strip_md(s: str) -> str:
    s = strip_substack_urls(s)
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', s)
    s = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'https?://\S+', ' ', s)
    s = re.sub(r'[*_#>`~]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def slugify(s: str) -> str:
    s = re.sub(r'https?://\S+', '', s.lower())
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-') or 'note'
    return s[:72].rstrip('-')

def description(n: dict) -> str:
    s = strip_md(str(n.get("summary") or n.get("excerpt") or n.get("body") or n.get("title") or ""))
    if len(s) <= 155: return s
    return re.sub(r'\s+\S*$', '', s[:152]) + '…'

def render_body(s: str) -> str:
    s = strip_substack_urls(s)
    blocks = [b.strip() for b in re.split(r'\n\s*\n', s) if b.strip()]
    out=[]
    for b in blocks:
        lines=b.splitlines()
        if lines and all(re.match(r'^[-*]\s+', x) for x in lines):
            out.append('<ul>'+''.join('<li>'+html.escape(re.sub(r'^[-*]\s+','',x))+'</li>' for x in lines)+'</ul>')
        elif lines and all(re.match(r'^\d+\.\s+', x) for x in lines):
            out.append('<ol>'+''.join('<li>'+html.escape(re.sub(r'^\d+\.\s+','',x))+'</li>' for x in lines)+'</ol>')
        else:
            out.append('<p>'+html.escape(b).replace('\n','<br>')+'</p>')
    return "\n".join(out)

def build_notes() -> list[tuple[str,str]]:
    notes_text=(ROOT/"notes/index.html").read_text(encoding="utf-8")
    m=re.search(r'let NOTES=(\[.*?\]);const CATS=', notes_text, re.S)
    if not m: raise RuntimeError("Could not parse NOTES archive")
    archive=json.loads(m.group(1))
    direct=json.loads((ROOT/"notes/direct-notes.json").read_text(encoding="utf-8"))
    by_id={str(n["id"]):n for n in archive}
    for i,n in enumerate(direct):
        if not isinstance(n,dict) or not n.get("title") or not n.get("date"): continue
        ident=str(n.get("id") or f"{n['date']}-{n['title']}-{i}").lower()
        ident=re.sub(r'[^a-z0-9_-]+','-',ident).strip('-') or f'direct-{i}'
        by_id[ident]={**n,"id":ident}
    notes=sorted(by_id.values(),key=lambda n:(str(n.get("date","")),str(n.get("id",""))),reverse=True)
    out=ROOT/"notes/n"
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    urls=[]
    css='body{margin:0;background:#f2efe7;color:#10100f;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif}.wrap{width:min(900px,calc(100% - 36px));margin:auto}header{border-bottom:1px solid #cfccc1}header .wrap{height:58px;display:flex;align-items:center;justify-content:space-between}a{color:inherit}main{padding:70px 0 100px}.meta{font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:#68675f;margin-bottom:20px}h1{font-size:clamp(42px,7vw,78px);line-height:.96;letter-spacing:-.055em;margin:0 0 34px}article{font:19px/1.68 Georgia,serif;max-width:760px}article p{margin:0 0 1.1em}footer{border-top:1px solid #cfccc1;padding:24px 0 36px;color:#68675f;font-size:12px}'
    for n in notes:
        ident=str(n["id"]); slug=f"{slugify(str(n.get('title','')))}-{ident}"
        folder=out/slug; folder.mkdir()
        url=f"{SITE}/notes/n/{slug}/"; title=str(n.get("title") or "Untitled note"); desc=description(n)
        body=render_body(str(n.get("body") or "")); discussion=render_body(str(n.get("discussion") or ""))
        schema={"@context":"https://schema.org","@type":"Article","@id":url+"#article","headline":title,"description":desc,"url":url,"datePublished":str(n.get("date") or ""),"author":AUTHOR,"mainEntityOfPage":url}
        meta=(str(n.get("date") or "") + ((" · "+str(n.get("category"))) if n.get("category") else ""))
        page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><link rel="icon" href="/favicon.svg?v=20260930" type="image/svg+xml"><title>{html.escape(title)} — Matt Lane</title><meta name="description" content="{attr(desc)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{url}"><meta property="og:type" content="article"><meta property="og:site_name" content="Matt Lane"><meta property="og:url" content="{url}"><meta property="og:title" content="{attr(title+' — Matt Lane')}"><meta property="og:description" content="{attr(desc)}"><meta property="og:image" content="{GENERIC_IMAGE}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{attr(title+' — Matt Lane')}"><meta name="twitter:description" content="{attr(desc)}"><meta name="twitter:image" content="{GENERIC_IMAGE}"><script type="application/ld+json">{json.dumps(schema,ensure_ascii=False,separators=(",",":"))}</script><style>{css}</style></head><body><header><div class="wrap"><a href="/notes/">Matt Lane · Notes</a><a href="/notes/">← All notes</a></div></header><main class="wrap"><div class="meta">{html.escape(meta)}</div><h1>{html.escape(title)}</h1><article>{body}</article>{('<section><h2>Discussion</h2><article>'+discussion+'</article></section>') if discussion else ''}</main><footer><div class="wrap">© 2026 Matt Lane</div></footer></body></html>'''
        (folder/"index.html").write_text(page,encoding="utf-8")
        urls.append((url,str(n.get("date") or "")))
    return urls

def write_sitemap(note_urls: list[tuple[str,str]]) -> None:
    core=[SITE+"/",SITE+"/about/",SITE+"/splice/",SITE+"/nyshex/",SITE+"/codeai/",SITE+"/fit-check/",SITE+"/planning-tools/",SITE+"/notes/"]
    lines=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lines += [f'  <url><loc>{u}</loc></url>' for u in core]
    lines += [f'  <url><loc>{u}</loc>'+(f'<lastmod>{d}</lastmod>' if d else '')+'</url>' for u,d in note_urls]
    lines.append('</urlset>')
    (ROOT/"sitemap.xml").write_text("\n".join(lines)+"\n",encoding="utf-8")

def main() -> None:
    for rel,cfg in CONFIG.items():
        p=ROOT/rel
        p.write_text(inject(p.read_text(encoding="utf-8"),cfg),encoding="utf-8")
    note_urls=build_notes()
    write_sitemap(note_urls)
    print(f"SEO updated; generated {len(note_urls)} indexable Note pages.")

if __name__=="__main__":
    main()
, '', s, flags=re.M)
    return s

def strip_md(s: str) -> str:
    s = strip_substack_urls(s)
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', s)
    s = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'https?://\S+', ' ', s)
    s = re.sub(r'[*_#>`~]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def slugify(s: str) -> str:
    s = re.sub(r'https?://\S+', '', s.lower())
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-') or 'note'
    return s[:72].rstrip('-')

def description(n: dict) -> str:
    s = strip_md(str(n.get("summary") or n.get("excerpt") or n.get("body") or n.get("title") or ""))
    if len(s) <= 155: return s
    return re.sub(r'\s+\S*$', '', s[:152]) + '…'

def render_body(s: str) -> str:
    s = strip_substack_urls(s)
    blocks = [b.strip() for b in re.split(r'\n\s*\n', s) if b.strip()]
    out=[]
    for b in blocks:
        lines=b.splitlines()
        if lines and all(re.match(r'^[-*]\s+', x) for x in lines):
            out.append('<ul>'+''.join('<li>'+html.escape(re.sub(r'^[-*]\s+','',x))+'</li>' for x in lines)+'</ul>')
        elif lines and all(re.match(r'^\d+\.\s+', x) for x in lines):
            out.append('<ol>'+''.join('<li>'+html.escape(re.sub(r'^\d+\.\s+','',x))+'</li>' for x in lines)+'</ol>')
        else:
            out.append('<p>'+html.escape(b).replace('\n','<br>')+'</p>')
    return "\n".join(out)

def build_notes() -> list[tuple[str,str]]:
    notes_text=(ROOT/"notes/index.html").read_text(encoding="utf-8")
    m=re.search(r'let NOTES=(\[.*?\]);const CATS=', notes_text, re.S)
    if not m: raise RuntimeError("Could not parse NOTES archive")
    archive=json.loads(m.group(1))
    direct=json.loads((ROOT/"notes/direct-notes.json").read_text(encoding="utf-8"))
    by_id={str(n["id"]):n for n in archive}
    for i,n in enumerate(direct):
        if not isinstance(n,dict) or not n.get("title") or not n.get("date"): continue
        ident=str(n.get("id") or f"{n['date']}-{n['title']}-{i}").lower()
        ident=re.sub(r'[^a-z0-9_-]+','-',ident).strip('-') or f'direct-{i}'
        by_id[ident]={**n,"id":ident}
    notes=sorted(by_id.values(),key=lambda n:(str(n.get("date","")),str(n.get("id",""))),reverse=True)
    out=ROOT/"notes/n"
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    urls=[]
    css='body{margin:0;background:#f2efe7;color:#10100f;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif}.wrap{width:min(900px,calc(100% - 36px));margin:auto}header{border-bottom:1px solid #cfccc1}header .wrap{height:58px;display:flex;align-items:center;justify-content:space-between}a{color:inherit}main{padding:70px 0 100px}.meta{font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:#68675f;margin-bottom:20px}h1{font-size:clamp(42px,7vw,78px);line-height:.96;letter-spacing:-.055em;margin:0 0 34px}article{font:19px/1.68 Georgia,serif;max-width:760px}article p{margin:0 0 1.1em}footer{border-top:1px solid #cfccc1;padding:24px 0 36px;color:#68675f;font-size:12px}'
    for n in notes:
        ident=str(n["id"]); slug=f"{slugify(str(n.get('title','')))}-{ident}"
        folder=out/slug; folder.mkdir()
        url=f"{SITE}/notes/n/{slug}/"; title=str(n.get("title") or "Untitled note"); desc=description(n)
        body=render_body(str(n.get("body") or "")); discussion=render_body(str(n.get("discussion") or ""))
        schema={"@context":"https://schema.org","@type":"Article","@id":url+"#article","headline":title,"description":desc,"url":url,"datePublished":str(n.get("date") or ""),"author":AUTHOR,"mainEntityOfPage":url}
        meta=(str(n.get("date") or "") + ((" · "+str(n.get("category"))) if n.get("category") else ""))
        page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><link rel="icon" href="/favicon.svg?v=20260930" type="image/svg+xml"><title>{html.escape(title)} — Matt Lane</title><meta name="description" content="{attr(desc)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{url}"><meta property="og:type" content="article"><meta property="og:site_name" content="Matt Lane"><meta property="og:url" content="{url}"><meta property="og:title" content="{attr(title+' — Matt Lane')}"><meta property="og:description" content="{attr(desc)}"><meta property="og:image" content="{GENERIC_IMAGE}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{attr(title+' — Matt Lane')}"><meta name="twitter:description" content="{attr(desc)}"><meta name="twitter:image" content="{GENERIC_IMAGE}"><script type="application/ld+json">{json.dumps(schema,ensure_ascii=False,separators=(",",":"))}</script><style>{css}</style></head><body><header><div class="wrap"><a href="/notes/">Matt Lane · Notes</a><a href="/notes/">← All notes</a></div></header><main class="wrap"><div class="meta">{html.escape(meta)}</div><h1>{html.escape(title)}</h1><article>{body}</article>{('<section><h2>Discussion</h2><article>'+discussion+'</article></section>') if discussion else ''}</main><footer><div class="wrap">© 2026 Matt Lane</div></footer></body></html>'''
        (folder/"index.html").write_text(page,encoding="utf-8")
        urls.append((url,str(n.get("date") or "")))
    return urls

def write_sitemap(note_urls: list[tuple[str,str]]) -> None:
    core=[SITE+"/",SITE+"/about/",SITE+"/splice/",SITE+"/nyshex/",SITE+"/codeai/",SITE+"/fit-check/",SITE+"/planning-tools/",SITE+"/notes/"]
    lines=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lines += [f'  <url><loc>{u}</loc></url>' for u in core]
    lines += [f'  <url><loc>{u}</loc>'+(f'<lastmod>{d}</lastmod>' if d else '')+'</url>' for u,d in note_urls]
    lines.append('</urlset>')
    (ROOT/"sitemap.xml").write_text("\n".join(lines)+"\n",encoding="utf-8")

def main() -> None:
    for rel,cfg in CONFIG.items():
        p=ROOT/rel
        p.write_text(inject(p.read_text(encoding="utf-8"),cfg),encoding="utf-8")
    note_urls=build_notes()
    write_sitemap(note_urls)
    print(f"SEO updated; generated {len(note_urls)} indexable Note pages.")

if __name__=="__main__":
    main()
