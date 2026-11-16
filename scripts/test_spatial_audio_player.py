#!/usr/bin/env python3
"""Browser interaction regression for the LCC listening lab (real FLACs, Chromium)."""
from __future__ import annotations
import contextlib
import http.server
import socket
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):
        pass

def main():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0))
        port=s.getsockname()[1]
    server=http.server.ThreadingHTTPServer(('127.0.0.1',port),lambda *a,**k:Handler(*a,directory=str(ROOT),**k))
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            for viewport in [{'width':1440,'height':900},{'width':390,'height':844}]:
                page=browser.new_page(viewport=viewport)
                errors=[]
                page.on('pageerror',lambda exc:errors.append(str(exc)))
                page.goto(f'http://127.0.0.1:{port}/spatial-audio/',wait_until='domcontentloaded',timeout=60_000)
                assert page.locator('#loudspeakers, #laptop, .preset').count()==0
                assert page.locator('#tracks button').count()==3
                assert page.locator('#play').count()==1
                page.wait_for_function('window.__lccTest && window.__lccTest.bufferReady',timeout=40_000)
                page.locator('#play').click()
                page.wait_for_function('window.__lccTest.playing',timeout=12_000)
                page.wait_for_timeout(300)
                assert 0.1 < page.evaluate('window.__lccTest.position') < 3
                assert page.evaluate('window.__lccTest.selected')=='battlefield-binaural'
                page.locator('#seek').evaluate("e=>{e.value='750';e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));}")
                page.wait_for_timeout(250)
                assert 25 < page.evaluate('window.__lccTest.position') < 28
                page.locator('#seek').evaluate("e=>{e.value='150';e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));}")
                page.wait_for_timeout(250)
                assert 4 < page.evaluate('window.__lccTest.position') < 7
                page.locator('#play').click()
                paused=page.evaluate('window.__lccTest.position')
                page.wait_for_timeout(350)
                assert abs(page.evaluate('window.__lccTest.position')-paused)<0.06
                page.locator('#play').click()
                page.wait_for_function('window.__lccTest.playing',timeout=6000)
                page.wait_for_timeout(200)
                assert page.evaluate('window.__lccTest.position')>paused+0.10
                page.locator('#on').click()
                assert page.evaluate('window.__lccTest.mode')
                page.locator('#off').click()
                assert not page.evaluate('window.__lccTest.mode')
                page.locator('#tracks button[data-index="2"]').click()
                page.wait_for_function('window.__lccTest.selected==="gravity" && window.__lccTest.playing',timeout=15_000)
                page.locator('#tracks button[data-index="1"]').click()
                page.locator('#play').click()
                page.wait_for_timeout(250)
                assert not page.evaluate('window.__lccTest.playing || window.__lccTest.wantsPlayback')
                page.locator('#play').click()
                page.wait_for_function('window.__lccTest.selected==="patch" && window.__lccTest.playing',timeout=15_000)
                assert not errors,errors
                page.close()
                print(f"PASS LCC playback browser regression {viewport['width']} px")
            browser.close()
    finally:
        server.shutdown()

if __name__=='__main__':main()
