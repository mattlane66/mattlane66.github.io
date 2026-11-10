#!/usr/bin/env python3
"""Targeted browser regression for the four-scene HRTF spatial audio demonstration.

Exercises the actual WebAudio graph and browser AudioWorklet, with no mic capture,
external service authorization, or copyrighted inputs. The optional public-domain
growl is blocked to confirm the dinosaur synthesis remains independent.
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


def worklet_probe(page):
    return page.evaluate("""async () => {
      const src = await (await fetch('./lcc-worklet.js')).text();
      let Processor;
      class WorkletBase { constructor() { this.port = { onmessage: null }; } }
      new Function('AudioWorkletProcessor','registerProcessor','sampleRate',src)(
        WorkletBase, (name,Ctor) => { Processor = Ctor; }, 48000
      );
      if (!Processor) throw new Error('Worklet could not register');
      const instance = new Processor();
      const raw = new Float32Array(128);
      for (let i=0;i<128;i++) raw[i]=Math.sin(i * 0.17) * 0.17;
      const silent = new Float32Array(128);
      const baseline = [new Float32Array(128),new Float32Array(128)];
      instance.process([[raw,silent]],[baseline]);
      let bypassError=0;
      for (let i=0;i<128;i++) {
        bypassError=Math.max(bypassError,Math.abs(baseline[0][i]-raw[i]),Math.abs(baseline[1][i]));
      }
      instance.port.onmessage({ data: {type:'enable',value:true} });
      let processedDifference=0;
      for(let round=0;round<4;round++){
        const changed=[new Float32Array(128),new Float32Array(128)];
        instance.process([[raw,silent]],[changed]);
        for (let i=0;i<128;i++) processedDifference=Math.max(
          processedDifference,Math.abs(changed[0][i]-raw[i]),Math.abs(changed[1][i])
        );
      }
      return {bypassError,processedDifference};
    }""")


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
                page.route("https://upload.wikimedia.org/**", lambda route: route.abort())
                errors = []
                page.on("pageerror", lambda exc: errors.append(str(exc)))
                page.goto(f"http://127.0.0.1:{port}/spatial-audio/", wait_until="domcontentloaded")
                if page.locator("h1").count() != 1:
                    failures.append("Expected exactly one h1.")
                if page.locator(".sample").count() != 4:
                    failures.append("Expected four spatial scenes.")
                if page.locator("#lcc-switch").get_attribute("aria-checked") != "false":
                    failures.append("LCC did not begin Off.")
                if page.locator("#lcc-switch").is_disabled():
                    failures.append("LCC must be clickable before playback.")
                if page.locator("iframe").count() or page.locator("#capture-tab").count():
                    failures.append("Legacy embed/capture UI was not removed.")
                width = page.evaluate("({doc:document.documentElement.scrollWidth,viewport:document.documentElement.clientWidth})")
                if width["doc"] > width["viewport"] + 4:
                    failures.append(f"{viewport['width']}px overflow: {width}")
                try:
                    # A real bypass-vs-processed signal test independent of UI state.
                    probe=worklet_probe(page)
                    if probe["bypassError"] > 0.00001:
                        failures.append(f"Worklet bypass changed original signal: {probe}")
                    if probe["processedDifference"] < 0.001:
                        failures.append(f"Worklet On mode made no audible-sample change: {probe}")
                    page.locator("#lcc-switch").click()
                    if page.locator("#lcc-switch").get_attribute("aria-checked") != "true":
                        failures.append("LCC could not be enabled before sound played.")
                    page.locator("#play").click()
                    page.wait_for_function("document.getElementById('play').textContent.includes('Pause')", timeout=15000)
                    first_position = page.locator("#source-dot").get_attribute("style")
                    page.wait_for_timeout(450)
                    moved_position = page.locator("#source-dot").get_attribute("style")
                    if first_position == moved_position:
                        failures.append("Spatial source marker does not follow the moving scene.")
                    page.locator("#lcc-switch").click()
                    if page.locator("#lcc-switch").get_attribute("aria-checked") != "false":
                        failures.append("LCC Off did not follow active On.")
                    page.locator("#lcc-switch").click()
                    if page.locator("#lcc-switch").get_attribute("aria-checked") != "true":
                        failures.append("LCC did not toggle back On.")
                    page.locator("#play").click()
                    if "Play" not in page.locator("#play").inner_text():
                        failures.append("Pause button did not return to Play.")
                    for kind in ["dinosaur","flyby","helicopter","orbit"]:
                        page.locator(f'[data-sound="{kind}"]').click()
                        if page.locator(f'[data-sound="{kind}"]').get_attribute("aria-pressed") != "true":
                            failures.append(f"Selecting {kind} did not update selection.")
                        page.locator("#play").click()
                        page.wait_for_function("document.getElementById('play').textContent.includes('Pause')", timeout=15000)
                        if kind == "dinosaur":
                            page.wait_for_function("document.getElementById('status').textContent.includes('Dinosaur: synthesized') || document.getElementById('status').textContent.includes('Creature approaching')", timeout=10000)
                            text=page.locator("#status").inner_text()
                            if "synthesized" not in text and "Creature approaching" not in text:
                                failures.append(f"Dinosaur does not identify synthesized layers: {text}")
                        page.locator("#play").click()
                except Exception as exc:
                    failures.append(f"{viewport['width']}px: playback or switch check failed: {exc}")
                if errors:
                    failures.append(f"{viewport['width']}px: JS errors: {errors[:3]}")
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()

    for failure in failures:
        print("ERROR:", failure)
    if failures:
        return 1
    print("Spatial audio browser smoke passed: four HRTF scenes, DSP bypass-versus-LCC, moving source marker, switching during playback, desktop and mobile.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
