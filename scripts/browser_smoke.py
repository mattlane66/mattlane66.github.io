#!/usr/bin/env python3
"""Real-browser smoke checks for the static site at desktop and phone widths."""
from __future__ import annotations
import contextlib
import http.server
import socket
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[1]
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
    port = free_port()
    handler = lambda *a, **kw: QuietHandler(*a, directory=str(ROOT), **kw)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    failures: list[str] = []
    warnings: list[str] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
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
                            for opener, modal, closer in [
                                ("#paypal-open", "#paypal-modal", "#paypal-close"),
                                ("#simplebet-open", "#simplebet-modal", "#simplebet-close"),
                            ]:
                                if page.locator(opener).count():
                                    page.locator(opener).click()
                                    if "open" not in (page.locator(modal).get_attribute("class") or ""):
                                        failures.append(f"{viewport_name} /: {modal} did not open")
                                    page.locator(closer).click()
                        elif name == "planning-tools":
                            try:
                                page.wait_for_function("window.__PLANNING_PORTAL_READY__ === true", timeout=20_000)
                            except PlaywrightTimeoutError:
                                failures.append(f"{viewport_name} /planning-tools/: runtime did not become ready")
                        elif name == "splice":
                            if page.locator("#next-button").count():
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
