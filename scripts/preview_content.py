#!/usr/bin/env python3
"""Make unpublished browser previews of affected HTML pages; never deploy."""
from __future__ import annotations
import argparse
import html
import http.server
import os
import re
import socket
import subprocess
import threading
import zipfile
from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = {"desktop": (1440, 900), "phone": (390, 844)}
MAX_PAGES = 30

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        return

def git_paths(*args: str) -> set[str]:
    process = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or f"git {args} failed")
    return {x.strip() for x in process.stdout.splitlines() if x.strip()}

def changed_pages(base: str) -> list[str]:
    if base:
        changed = git_paths("diff", "--name-only", base, "--")
        changed |= git_paths("ls-files", "--others", "--exclude-standard")
    else:
        changed = {"index.html", "notes/index.html"}
    pages = {p for p in changed if p.endswith(".html") and (ROOT / p).is_file()}
    if ("notes/direct-notes.json" in changed or "notes/removed-note-ids.json" in changed
            or any(p.startswith("notes/n/") for p in changed)):
        pages.add("notes/index.html")
    if any(p.startswith(("articles/", "nyshex/", "splice/", "codeai/", "fit-check/")) for p in changed):
        pages.add("index.html")
    if any(p.startswith("assets/") for p in changed):
        pages.update({"index.html", "about/index.html", "notes/index.html"})
        article = next(iter(sorted((ROOT / "articles").glob("*/index.html"))), None)
        if article:
            pages.add(article.relative_to(ROOT).as_posix())
    if not pages:
        pages = {"index.html"}
    order = lambda p: (0 if p.startswith("notes/n/") else 1 if p.startswith("articles/") else 2, p)
    selected = sorted(pages, key=order)
    if len(selected) > MAX_PAGES:
        raise RuntimeError(f"{len(selected)} changed pages exceed review limit {MAX_PAGES}; split the PR rather than silently omit pages.")
    return selected

def site_url(path: str) -> str:
    if path == "index.html":
        return "/"
    if path.endswith("/index.html"):
        return "/" + quote(path[:-10], safe="/")
    return "/" + quote(path, safe="/")

def site_zip(target: Path, output: Path) -> None:
    excluded = {".git", ".github", "scripts", "publication-preview", "__pycache__"}
    allowed = {".html", ".css", ".js", ".json", ".xml", ".txt", ".svg", ".jpg",
               ".jpeg", ".png", ".gif", ".webp", ".ico", ".woff", ".woff2", ".pdf", ".webm", ".mp4"}
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for file in ROOT.rglob("*"):
            if not file.is_file() or output in file.parents:
                continue
            parts = file.relative_to(ROOT).parts
            if any(part in excluded or part.startswith(".git") for part in parts):
                continue
            if file.suffix.lower() in allowed:
                bundle.write(file, file.relative_to(ROOT).as_posix())

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="", help="Git commit SHA used to select affected pages")
    parser.add_argument("--output", type=Path, default=ROOT / "publication-preview")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    paths = changed_pages(args.base)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", port), lambda *a, **kw: QuietHandler(*a, directory=str(ROOT), **kw))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    captures, failures = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, **(
                {"executable_path": os.environ["CHROMIUM_PATH"]} if os.getenv("CHROMIUM_PATH") else {}))
            for path in paths:
                pairs = []
                for device, (width, height) in VIEWPORTS.items():
                    page = browser.new_page(viewport={"width": width, "height": height})
                    js_errors = []
                    page.on("pageerror", lambda e, errors=js_errors: errors.append(str(e)))
                    try:
                        response = page.goto(f"http://127.0.0.1:{port}{site_url(path)}",
                                             wait_until="domcontentloaded", timeout=60000)
                        if response is None or response.status >= 400:
                            failures.append(f"{path} {device}: HTTP {response.status if response else 'no response'}")
                            continue
                        page.evaluate("document.fonts.ready")
                        page.wait_for_timeout(700)
                        metrics = page.evaluate("""() => ({
                          width: document.documentElement.clientWidth,
                          scroll: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
                          h1: document.querySelectorAll('h1').length,
                          height: document.documentElement.scrollHeight
                        })""")
                        if metrics["scroll"] > metrics["width"] + 4:
                            failures.append(f"{path} {device}: horizontal overflow")
                        if metrics["h1"] != 1:
                            failures.append(f"{path} {device}: expected 1 h1, found {metrics['h1']}")
                        if js_errors:
                            failures.append(f"{path} {device}: JS errors: {js_errors[:2]}")
                        full = metrics["height"] < 16000 and path != "notes/index.html"
                        png = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-") + f"-{device}.png"
                        page.screenshot(path=str(output / png), full_page=full, animations="disabled")
                        pairs.append((device, png, full))
                        # The Notes archive initially shows only its header; also
                        # capture its actual first cards so new Notes can be reviewed.
                        if path == "notes/index.html":
                            page.evaluate("document.getElementById('grid')?.scrollIntoView({block:'start',behavior:'instant'})")
                            page.wait_for_timeout(200)
                            cards_png = png.replace(".png", "-cards.png")
                            page.screenshot(path=str(output / cards_png), full_page=False, animations="disabled")
                            pairs.append((device + " — Notes cards", cards_png, False))
                        elif not full:
                            # Very long articles remain browsable in the ZIP, but
                            # screenshots also show their interior and conclusion.
                            for position, fraction in (("middle", 0.5), ("ending", 1.0)):
                                page.evaluate("(n) => window.scrollTo(0, n)", metrics["height"] * fraction)
                                page.wait_for_timeout(150)
                                extra = png.replace(".png", f"-{position}.png")
                                page.screenshot(path=str(output / extra), full_page=False, animations="disabled")
                                pairs.append((device + " — " + position, extra, False))
                    finally:
                        page.close()
                captures.append((path, pairs))
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    parts = ["""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Unpublished site preview</title>
<style>body{font:16px/1.5 system-ui,sans-serif;background:#f5f4ef;color:#16161d;padding:24px}
main{max-width:1200px;margin:auto}.pair{display:grid;grid-template-columns:2fr 1fr;gap:20px;align-items:start}
img{width:100%;border:1px solid #999}section{margin:40px 0}code{overflow-wrap:anywhere}
@media(max-width:700px){.pair{grid-template-columns:1fr}body{padding:12px}}</style>
</head><body><main><h1>Unpublished site preview</h1>
<p>Actual draft HTML rendered in Chromium at desktop (1440px) and phone (390px) widths.
To interact with every full page, extract <code>site-preview.zip</code>, serve its root with
<code>python -m http.server 8000</code>, then visit <code>http://localhost:8000/</code>.
Screenshots of very tall pages capture the viewport; review the full HTML by scrolling.</p>"""]
    for path, screenshots in captures:
        parts.extend([f"<section><h2>{html.escape(site_url(path))}</h2><div class='pair'>"])
        for device, png, full in screenshots:
            parts.append(f"<div><strong>{html.escape(device.capitalize())}</strong>"
                         f"<small> — {'whole page' if full else 'viewport; scroll HTML to review the rest'}</small>"
                         f"<a href='{html.escape(png)}'><img src='{html.escape(png)}' "
                         f"alt='{html.escape(device)} preview of {html.escape(path)}'></a></div>")
        parts.append("</div></section>")
    if failures:
        parts.append("<h2>Must fix before publishing</h2><ul>")
        parts.extend(f"<li>{html.escape(problem)}</li>" for problem in failures)
        parts.append("</ul>")
    parts.append("</main></body></html>")
    (output / "index.html").write_text("\n".join(parts), encoding="utf-8")
    site_zip(output / "site-preview.zip", output)
    print(f"Previewed {len(captures)} candidate page(s); report: {output / 'index.html'}")
    for path, _ in captures:
        print(" -", path)
    for issue in failures:
        print("ERROR:", issue)
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
