from pathlib import Path
import http.server
import socket
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "preview-captures"

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def main():
    OUT.mkdir(exist_ok=True)
    port = free_port()
    handler = lambda *a, **kw: QuietHandler(*a, directory=str(ROOT), **kw)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for name, path in [
                ("splice-case-preview", "/splice/#opening"),
                ("fit-check-preview", "/fit-check/"),
            ]:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.goto(base + path, wait_until="domcontentloaded", timeout=60_000)
                page.wait_for_timeout(1800)
                page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    main()
