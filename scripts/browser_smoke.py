#!/usr/bin/env python3
"""Real-browser smoke checks for the static site at desktop and phone widths."""
from __future__ import annotations
import contextlib
import http.server
import json
import re
import socket
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[1]
DIRECT_NOTES = ROOT / "notes" / "direct-notes.json"
REMOVED_NOTES = ROOT / "notes" / "removed-note-ids.json"
DIRECT_TEST_ID = "ci-direct-sync-test"
PAGES = [
    ("/", "home"),
    ("/about/", "about"),
    ("/codeai/", "codeai"),
    ("/fit-check/", "fit-check"),
    ("/notes/", "notes"),
    ("/nyshex/", "nyshex"),
    ("/planning-tools/", "planning-tools"),
    ("/splice/", "splice"),
    ("/404.html", "404"),
]
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "phone": {"width": 390, "height": 844},
}

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    notes_html = (ROOT / "notes" / "index.html").read_text(encoding="utf-8")
    match = re.search(r"let NOTES=(\[.*?\]);const CATS=", notes_html, re.S)
    if not match:
        print("ERROR: notes/index.html: could not locate embedded Notes archive")
        return 1
    removed_ids = {str(x) for x in json.loads(REMOVED_NOTES.read_text(encoding="utf-8"))}
    archive_ids = {str(n["id"]) for n in json.loads(match.group(1)) if str(n["id"]) not in removed_ids}

    original_direct = DIRECT_NOTES.read_text(encoding="utf-8")
    direct_notes = json.loads(original_direct)
    if not isinstance(direct_notes, list):
        print("ERROR: notes/direct-notes.json must contain a JSON array")
        return 1

    # The committed HTML must contain every real note before JavaScript runs.
    expected_static_ids = set(archive_ids)
    for i, note in enumerate(direct_notes):
        if not isinstance(note, dict) or not note.get("title") or not note.get("date"):
            continue
        ident = str(note.get("id") or f"{note['date']}-{note['title']}-{i}").lower()
        ident = re.sub(r"[^a-z0-9_-]+", "-", ident).strip("-") or f"direct-{i}"
        if ident not in removed_ids:
            expected_static_ids.add(ident)
    expected_static_total = len(expected_static_ids)

    direct_notes.append({
        "id": DIRECT_TEST_ID,
        "date": "9999-12-31",
        "title": "CI direct note sync test",
        "body": "This temporary note verifies direct Notes loading.",
        "category": "Writing & craft",
    })
    DIRECT_NOTES.write_text(json.dumps(direct_notes, ensure_ascii=False), encoding="utf-8")
    # A direct note replaces the archive entry with the same ID; it is not
    # an additional note. Count valid, normalized IDs across both sources.
    expected_ids = set(expected_static_ids)
    for i, note in enumerate(direct_notes):
        if not isinstance(note, dict) or not note.get("title") or not note.get("date"):
            continue
        ident = str(note.get("id") or f"{note['date']}-{note['title']}-{i}").lower()
        ident = re.sub(r"[^a-z0-9_-]+", "-", ident).strip("-") or f"direct-{i}"
        if ident not in removed_ids:
            expected_ids.add(ident)
    expected_notes_total = len(expected_ids)

    port = free_port()
    handler = lambda *a, **kw: QuietHandler(*a, directory=str(ROOT), **kw)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # Progressive enhancement guarantee: the full Notes archive and
            # real crawlable links must exist with JavaScript completely off.
            nojs_context = browser.new_context(java_script_enabled=False)
            nojs_page = nojs_context.new_page()
            try:
                response = nojs_page.goto(base + "/notes/", wait_until="domcontentloaded", timeout=60_000)
                if response is None or response.status >= 400:
                    failures.append(f"no-js /notes/: HTTP {getattr(response, 'status', None)}")
                else:
                    static_links = nojs_page.locator("#grid a.note[data-id]")
                    if static_links.count() != expected_static_total:
                        failures.append(
                            f"no-js /notes/: expected {expected_static_total} static Note links, "
                            f"found {static_links.count()}"
                        )
                    static_ids = set(static_links.evaluate_all(
                        "els => els.map(el => el.getAttribute('data-id'))"
                    ))
                    missing_static = sorted(expected_static_ids - static_ids)
                    if missing_static:
                        failures.append(
                            f"no-js /notes/: missing static Note IDs: {missing_static[:5]}"
                        )
                    leaked_static = sorted(removed_ids & static_ids)
                    if leaked_static:
                        failures.append(
                            f"no-js /notes/: removed Note IDs leaked into static HTML: {leaked_static}"
                        )
                    bad_hrefs = static_links.evaluate_all(
                        """els => els.filter(el => {
                            const href = el.getAttribute('href') || '';
                            return !/^\.\/n\/.+\/$/.test(href);
                        }).slice(0, 5).map(el => el.getAttribute('href'))"""
                    )
                    if bad_hrefs:
                        failures.append(
                            f"no-js /notes/: non-crawlable static Note href(s): {bad_hrefs}"
                        )
            finally:
                nojs_page.close()
                nojs_context.close()

            for viewport_name, viewport in VIEWPORTS.items():
                for path, name in PAGES:
                    page = browser.new_page(viewport=viewport)
                    page_errors: list[str] = []
                    page.on("pageerror", lambda exc, bag=page_errors: bag.append(str(exc)))
                    try:
                        response = page.goto(base + path, wait_until="domcontentloaded", timeout=60_000)
                        if response is None or response.status >= 400:
                            failures.append(f"{viewport_name} {path}: HTTP {getattr(response, 'status', None)}")
                            continue

                        # Let deferred JS/layout settle without waiting for third-party network idleness.
                        page.wait_for_timeout(1500 if name != "planning-tools" else 3000)

                        # Refresh is intentionally a reset: every standard content page starts at the top.
                        # planning-tools is a separately bundled interactive artifact and is tested for runtime readiness below.
                        if name not in ("planning-tools", "404"):
                            page.evaluate("window.scrollTo(0, Math.min(700, Math.max(0, document.documentElement.scrollHeight - innerHeight)))")
                            page.wait_for_timeout(100)
                            page.reload(wait_until="domcontentloaded", timeout=60_000)
                            page.wait_for_timeout(800)
                            if page.evaluate("window.scrollY") > 3:
                                failures.append(f"{viewport_name} {path}: refresh did not reset scroll to top")

                        metrics = page.evaluate("""() => ({
                            htmlScroll: document.documentElement.scrollWidth,
                            htmlClient: document.documentElement.clientWidth,
                            bodyScroll: document.body ? document.body.scrollWidth : 0,
                            h1VisibleOrSemantic: document.querySelectorAll('h1').length,
                            missingAlt: [...document.images].filter(img => !img.hasAttribute('alt')).length
                        })""")
                        widest = max(metrics["htmlScroll"], metrics["bodyScroll"])
                        if widest > metrics["htmlClient"] + 4:
                            failures.append(
                                f"{viewport_name} {path}: page-level horizontal overflow "
                                f"{widest}px > {metrics['htmlClient']}px"
                            )
                        if metrics["h1VisibleOrSemantic"] != 1:
                            failures.append(
                                f"{viewport_name} {path}: expected one live h1, "
                                f"found {metrics['h1VisibleOrSemantic']}"
                            )
                        if metrics["missingAlt"]:
                            warnings.append(f"{viewport_name} {path}: {metrics['missingAlt']} image(s) without alt")

                        if page_errors:
                            failures.append(f"{viewport_name} {path}: JS error(s): {page_errors[:3]}")

                        # Core interactive smoke checks.
                        if name == "home":
                            # Featured previews are static images, never embedded scrollable documents.
                            if page.locator(".browser iframe, .fitpreview iframe").count():
                                failures.append(f"{viewport_name} /: static tile previews regressed to iframes")
                            if page.locator('.browser img[src*="splice-case-preview"], .fitpreview img[src*="fit-check-preview"]').count() != 2:
                                failures.append(f"{viewport_name} /: expected both static tile preview images")

                            # Top navigation must land correctly on the first click, including
                            # when the URL already has that hash and after returning from a subpage.
                            def nav_is_aligned(hash_value: str) -> bool:
                                try:
                                    page.wait_for_function(
                                        """hash => {
                                            const target = document.querySelector(hash);
                                            const header = document.querySelector('.top');
                                            if (!target || !header) return false;
                                            const expected = header.getBoundingClientRect().height;
                                            return location.hash === hash &&
                                                Math.abs(target.getBoundingClientRect().top - expected) <= 3;
                                        }""",
                                        arg=hash_value,
                                        timeout=3_000,
                                    )
                                    return True
                                except PlaywrightTimeoutError:
                                    return False

                            for href in ["#cases", "#projects", "#tools", "#writing"]:
                                link = page.locator(f'.nav a[href="{href}"]')
                                if link.count() != 1:
                                    failures.append(f"{viewport_name} /: missing nav link {href}")
                                    continue
                                link.click()
                                if not nav_is_aligned(href):
                                    failures.append(
                                        f"{viewport_name} /: first click on {href} did not align target below sticky header"
                                    )

                            # Re-clicking the current hash after scrolling away must realign it.
                            projects_link = page.locator('.nav a[href="#projects"]')
                            projects_link.click()
                            nav_is_aligned("#projects")
                            page.evaluate("window.scrollBy(0, 240)")
                            page.wait_for_timeout(100)
                            projects_link.click()
                            if not nav_is_aligned("#projects"):
                                failures.append(
                                    f"{viewport_name} /: repeated #projects click did not realign existing hash"
                                )

                            # Direct section URLs must align on initial load.
                            page.goto(base + "/#writing", wait_until="domcontentloaded", timeout=60_000)
                            if not nav_is_aligned("#writing"):
                                failures.append(
                                    f"{viewport_name} /#writing: direct hash load did not align target"
                                )
                            page.reload(wait_until="domcontentloaded", timeout=60_000)
                            page.wait_for_timeout(800)
                            reload_y = page.evaluate("window.scrollY")
                            reload_hash = page.evaluate("location.hash")
                            if reload_y > 3 or reload_hash:
                                failures.append(
                                    f"{viewport_name} /#writing: refresh did not reset homepage to top "
                                    f"(scrollY={reload_y}, hash={reload_hash!r})"
                                )

                            # Browser-history return must restore the previously selected section.
                            page.goto(base + "/", wait_until="domcontentloaded", timeout=60_000)
                            page.locator('.nav a[href="#projects"]').click()
                            if not nav_is_aligned("#projects"):
                                failures.append(
                                    f"{viewport_name} /: could not establish #projects before history test"
                                )
                            page.goto(base + "/about/", wait_until="domcontentloaded", timeout=60_000)
                            page.go_back(wait_until="domcontentloaded")
                            if not nav_is_aligned("#projects"):
                                failures.append(
                                    f"{viewport_name} /: browser Back from /about/ did not restore #projects"
                                )

                            # The About page's own return links intentionally go to the homepage top.
                            page.goto(base + "/about/", wait_until="domcontentloaded", timeout=60_000)
                            back = page.locator('a.back[href="../#top"]').first
                            if back.count():
                                back.click()
                                page.wait_for_url(base + "/#top", timeout=10_000)
                                try:
                                    page.wait_for_function("window.scrollY <= 3", timeout=3_000)
                                except PlaywrightTimeoutError:
                                    failures.append(
                                        f"{viewport_name} /about/: Back to work did not return to homepage top"
                                    )
                                page.locator('.nav a[href="#tools"]').click()
                                if not nav_is_aligned("#tools"):
                                    failures.append(
                                        f"{viewport_name} /: nav failed after About returned to top"
                                    )
                            else:
                                failures.append(f"{viewport_name} /about/: missing #top back-to-home link")

                            for opener, modal, closer in [
                                ("#paypal-open", "#paypal-modal", "#paypal-close"),
                                ("#simplebet-open", "#simplebet-modal", "#simplebet-close"),
                            ]:
                                if page.locator(opener).count():
                                    page.locator(opener).click()
                                    if "open" not in (page.locator(modal).get_attribute("class") or ""):
                                        failures.append(f"{viewport_name} /: {modal} did not open")
                                    page.locator(closer).click()
                        elif name == "notes":
                            try:
                                page.wait_for_function(
                                    f'document.documentElement.dataset.notesTotal === "{expected_notes_total}"',
                                    timeout=10_000,
                                )
                            except PlaywrightTimeoutError:
                                failures.append(
                                    f"{viewport_name} /notes/: expected total {expected_notes_total} "
                                    "after direct-note load"
                                )
                            if page.locator(f'[data-id="{DIRECT_TEST_ID}"]').count() != 1:
                                failures.append(
                                    f"{viewport_name} /notes/: directly added test note did not render"
                                )
                            leaked_removed = page.evaluate(
                                "(ids) => NOTES.filter(n => ids.includes(String(n.id))).map(n => String(n.id))",
                                sorted(removed_ids),
                            )
                            if leaked_removed:
                                failures.append(
                                    f"{viewport_name} /notes/: removed note IDs leaked into runtime: "
                                    f"{leaked_removed}"
                                )
                            for removed_id in sorted(removed_ids):
                                probe = browser.new_page(viewport=viewport)
                                try:
                                    probe.goto(
                                        base + f"/notes/#note-{removed_id}",
                                        wait_until="domcontentloaded",
                                        timeout=60_000,
                                    )
                                    probe.wait_for_timeout(1200)
                                    if probe.evaluate("location.hash"):
                                        failures.append(
                                            f"{viewport_name} /notes/#note-{removed_id}: "
                                            "removed-note hash was not cleared"
                                        )
                                    if probe.locator("#dialog[open]").count():
                                        failures.append(
                                            f"{viewport_name} /notes/#note-{removed_id}: "
                                            "removed note dialog opened"
                                        )
                                finally:
                                    probe.close()
                            if page.locator("#resultCount b").count():
                                shown = page.locator("#resultCount b").inner_text()
                                if shown != str(expected_notes_total):
                                    failures.append(
                                        f"{viewport_name} /notes/: displayed total {shown}, "
                                        f"expected {expected_notes_total}"
                                    )
                            noisy_feed = page.evaluate("""() => NOTES.map(n => ({
                                id: String(n.id),
                                title: feedTitle(n),
                                excerpt: feedExcerpt(n, feedTitle(n))
                            })).filter(x => /https?:\\/\\//i.test(x.title + " " + x.excerpt) || /\\bAttachments?\\b/i.test(x.title + " " + x.excerpt)).slice(0, 5)""")
                            if noisy_feed:
                                failures.append(
                                    f"{viewport_name} /notes/: raw link/attachment noise leaked into feed: "
                                    f"{noisy_feed}"
                                )
                        elif name == "planning-tools":
                            try:
                                page.wait_for_function("window.__PLANNING_PORTAL_READY__ === true", timeout=20_000)
                            except PlaywrightTimeoutError:
                                failures.append(f"{viewport_name} /planning-tools/: runtime did not become ready")
                        elif name == "splice":
                            if page.locator("#next-button").count() and page.locator("#next-button").is_visible():
                                before = page.locator("#counter").inner_text() if page.locator("#counter").count() else ""
                                page.locator("#next-button").click()
                                page.wait_for_timeout(200)
                                after = page.locator("#counter").inner_text() if page.locator("#counter").count() else ""
                                if before == after:
                                    failures.append(f"{viewport_name} /splice/: next control did not advance")
                    except Exception as exc:
                        failures.append(f"{viewport_name} {path}: {type(exc).__name__}: {exc}")
                    finally:
                        page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        DIRECT_NOTES.write_text(original_direct, encoding="utf-8")

    for w in sorted(set(warnings)):
        print("WARNING:", w)
    for f in failures:
        print("ERROR:", f)

    checks = len(PAGES) * len(VIEWPORTS)
    if failures:
        print(f"FAILED: {len(failures)} error(s) across {checks} browser/page combinations.")
        return 1
    print(f"PASS: {checks} browser/page combinations; no page-level overflow or runtime failures.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
