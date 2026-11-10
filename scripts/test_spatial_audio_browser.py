#!/usr/bin/env python3
"""Targeted browser regression for the spatial audio capture demonstration.

Uses an in-memory generated stereo audio stream, not Spotify or copyrighted audio.
Browsers cannot auto-accept the native screen-sharing picker in CI; capture is
mocked so the end-to-end WebAudio worklet, switch and disconnect can be tested.
"""
from __future__ import annotations

import http.server
import socket
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


MOCK_CAPTURE = """
(() => {
  const media = navigator.mediaDevices || {};
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: media });
  media.getDisplayMedia = async () => {
    const ctx = new AudioContext();
    const left = ctx.createOscillator();
    const right = ctx.createOscillator();
    const merger = ctx.createChannelMerger(2);
    left.frequency.value = 270;
    right.frequency.value = 430;
    left.connect(merger, 0, 0);
    right.connect(merger, 0, 1);
    const destination = ctx.createMediaStreamDestination();
    merger.connect(destination);
    left.start();
    right.start();
    const canvas = document.createElement('canvas');
    canvas.width = 2;
    canvas.height = 2;
    const video = canvas.captureStream(1).getVideoTracks()[0];
    return new MediaStream([...destination.stream.getAudioTracks(), video]);
  };
})();
"""


def main():
    port = free_port()
    handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(ROOT), **kwargs)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    failures = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
            for viewport in [{"width": 1440, "height": 900}, {"width": 390, "height": 844}]:
                page = browser.new_page(viewport=viewport)
                page.route("https://open.spotify.com/**", lambda route: route.abort())
                page.add_init_script(MOCK_CAPTURE)
                errors = []
                page.on("pageerror", lambda exc: errors.append(str(exc)))
                page.goto(f"http://127.0.0.1:{port}/spatial-audio/", wait_until="domcontentloaded")
                if page.locator("h1").count() != 1:
                    failures.append("Expected one semantic h1.")
                if page.locator("#lcc-switch").get_attribute("aria-checked") != "false":
                    failures.append("LCC not Off on initial load.")
                if not page.locator("#lcc-switch").is_disabled():
                    failures.append("LCC must remain disabled before audio connection.")
                if "0XrqQ8tIVGMKuVIC5mIrNN" not in page.locator("iframe").get_attribute("src"):
                    failures.append("Spotify playlist ID does not match requested embed.")
                widths = page.evaluate("({doc:document.documentElement.scrollWidth, viewport:document.documentElement.clientWidth})")
                if widths["doc"] > widths["viewport"] + 4:
                    failures.append(f"{viewport['width']}px: document overflows by {widths['doc']-widths['viewport']}px.")
                page.locator("#play-demo").click()
                try:
                    page.wait_for_function("!document.getElementById('lcc-switch').disabled", timeout=10000)
                    if "Demo audio is playing" not in page.locator("#status").inner_text():
                        failures.append("Built-in demo did not connect and start.")
                    page.locator("#lcc-switch").click()
                    if page.locator("#lcc-switch").get_attribute("aria-checked") != "true":
                        failures.append("Demo On switch failed.")
                    page.locator("#lcc-switch").click()
                    if page.locator("#lcc-switch").get_attribute("aria-checked") != "false":
                        failures.append("Demo Off switch failed.")
                    page.locator("#stop").click()
                    page.wait_for_function("document.getElementById('lcc-switch').disabled", timeout=10000)
                except Exception as exc:
                    failures.append(f"{viewport['width']}px: built-in demo check failed: {exc}")
                page.locator("#capture-tab").click()
                try:
                    page.locator("#lcc-switch").wait_for(state="visible")
                    page.wait_for_function("!document.getElementById('lcc-switch').disabled", timeout=10000)
                    page.locator("#lcc-switch").click()
                    if page.locator("#lcc-switch").get_attribute("aria-checked") != "true":
                        failures.append("Switch failed to enable on connected stereo stream.")
                    page.locator("#lcc-switch").click()
                    if page.locator("#lcc-switch").get_attribute("aria-checked") != "false":
                        failures.append("Switch failed to disable on connected stereo stream.")
                    page.locator("#stop").click()
                    page.wait_for_function("document.getElementById('lcc-switch').disabled", timeout=10000)
                    if page.locator("#lcc-switch").get_attribute("aria-checked") != "false":
                        failures.append("Disconnect failed to restore Off state.")
                except Exception as exc:
                    failures.append(f"{viewport['width']}px: functional capture check failed: {exc}")
                if errors:
                    failures.append(f"{viewport['width']}px: page JS errors: {errors[:3]}")
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    for failure in failures:
        print("ERROR:", failure)
    if failures:
        return 1
    print("Spatial audio browser smoke passed: desktop/mobile, Spotify embed ID, built-in stereo demo, capture mock, real worklet, LCC switching and disconnect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
