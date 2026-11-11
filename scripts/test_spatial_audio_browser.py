#!/usr/bin/env python3
"""Browser audit for the LCC demo: real DSP, two presets, generated and binaural recordings.

Mocked stereo WAV responses make deterministic browser checks independent of third-party
hosts. An additional non-blocking real-source check attempts actual external CORS+decode
to report whether public binaural recordings are reachable from Chromium in CI.
"""
from __future__ import annotations

import http.server
import io
import math
import socket
import struct
import threading
import wave
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


def stereo_wav():
    """Create truly distinct left/right audio so stereo downmix bugs are detectable."""
    sample_rate = 24000
    samples = int(sample_rate * 1.75)
    raw = io.BytesIO()
    with wave.open(raw, "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(b"".join(
            struct.pack(
                "<hh",
                int(10000 * math.sin(2 * math.pi * 460 * i / sample_rate)),
                int(10000 * math.sin(2 * math.pi * 670 * i / sample_rate))
            )
            for i in range(samples)
        ))
    return raw.getvalue()


def mono_wav():
    rate=24000
    raw=io.BytesIO()
    with wave.open(raw,"wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(b"".join(struct.pack("<h",int(9000*math.sin(2*math.pi*360*i/rate))) for i in range(rate)))
    return raw.getvalue()


def probe_worklet(page):
    return page.evaluate("""async () => {
      const src = await (await fetch('./lcc-worklet.js')).text();
      let Processor;
      class FakeWorklet { constructor(){ this.port={onmessage:null}; } }
      new Function('AudioWorkletProcessor','registerProcessor','sampleRate',src)(
        FakeWorklet,(name,constructor)=>{Processor=constructor;},48000);
      if(!Processor) throw new Error('LCC worklet not registered');
      const processor=new Processor();
      const left=Float32Array.from({length:128},(_,i)=>.15*Math.sin(i*.17));
      const right=Float32Array.from({length:128},(_,i)=>.09*Math.cos(i*.13));
      function advance(rounds){
        let last=null,peak=0,nonFinite=0;
        for(let r=0;r<rounds;r++){
          last=[new Float32Array(128),new Float32Array(128)];
          processor.process([[left,right]],[last]);
          for(let k=0;k<2;k++) for(let i=0;i<128;i++){
            const value=last[k][i];
            if(!Number.isFinite(value))nonFinite++;
            peak=Math.max(peak,Math.abs(value));
          }
        }
        return {left:Array.from(last[0]),right:Array.from(last[1]),peak,nonFinite};
      }
      const bypass=advance(1),orig={delay:processor.delayUs,decay:processor.decaygain,frames:processor.framesPerBlock};
      let bypassError=0;
      for(let i=0;i<128;i++)bypassError=Math.max(bypassError,
        Math.abs(bypass.left[i]-left[i]),Math.abs(bypass.right[i]-right[i]));
      processor.port.onmessage({data:{type:'enable',value:true}});
      const originalWet=advance(60);
      processor.port.onmessage({data:{type:'preset',value:'laptop'}});
      const laptopWet=advance(60);
      const laptop={delay:processor.delayUs,decay:processor.decaygain,frames:processor.framesPerBlock,preset:processor.currentPreset};
      processor.port.onmessage({data:{type:'preset',value:'loudspeakers'}});
      const restoredWet=advance(60);
      const restored={delay:processor.delayUs,decay:processor.decaygain,frames:processor.framesPerBlock,preset:processor.currentPreset};
      let wetDifference=0,presetDifference=0,restoredDifference=0;
      for(let i=0;i<128;i++){
        wetDifference=Math.max(wetDifference,Math.abs(originalWet.left[i]-left[i]));
        presetDifference=Math.max(presetDifference,Math.abs(originalWet.left[i]-laptopWet.left[i]));
        restoredDifference=Math.max(restoredDifference,Math.abs(originalWet.left[i]-restoredWet.left[i]));
      }
      return {orig,bypassError,originalWetPeak:originalWet.peak,wetDifference,
        presetDifference,restoredDifference,laptop,restored,
        finite:[bypass.nonFinite,originalWet.nonFinite,laptopWet.nonFinite,restoredWet.nonFinite]};
    }""")


def check_live_media(browser, base_url):
    """Best-effort external fetch check; network blocking does not invalidate local DSP."""
    page = browser.new_page()
    try:
        page.goto(base_url, wait_until="domcontentloaded")
        for kind, url in [
            ("rumba", "https://upload.wikimedia.org/wikipedia/commons/3/35/One_Man_Rumba_binaural_audio_demonstration.ogg"),
            ("pool", "https://upload.wikimedia.org/wikipedia/commons/5/5d/Pool_Sounds.ogg"),
            ("skyball", "https://upload.wikimedia.org/wikipedia/commons/e/e9/Skyball.ogg"),
            ("fall", "https://raw.githubusercontent.com/facebookincubator/Meta-open-sound/main/corpora/oculus-audio-pack/ogg/METLImpt_CanDrop_OS_01.ogg"),
            ("train", "https://raw.githubusercontent.com/facebookincubator/Meta-open-sound/main/corpora/oculus-audio-pack/ogg/TRNElec_TrainPassby_OS_01.ogg"),
            ("carriage3d", "https://upload.wikimedia.org/wikipedia/commons/a/a8/2023-Mai-20_15h52min_Wien_Stephansplatz_Ecke_Schulerstra%C3%9Fe_Rotenturmgasse_Fiaker_anhalten_einparken.ogg"),
            ("carriage3d_mp3", "https://upload.wikimedia.org/wikipedia/commons/transcoded/a/a8/2023-Mai-20_15h52min_Wien_Stephansplatz_Ecke_Schulerstra%C3%9Fe_Rotenturmgasse_Fiaker_anhalten_einparken.ogg/2023-Mai-20_15h52min_Wien_Stephansplatz_Ecke_Schulerstra%C3%9Fe_Rotenturmgasse_Fiaker_anhalten_einparken.ogg.mp3")
        ]:
            try:
                check=page.evaluate("""async (url) => {
                    const controller=new AbortController();
                    const timeout=setTimeout(()=>controller.abort(),12000);
                    try{
                      const response=await fetch(url,{mode:'cors',signal:controller.signal});
                      if(!response.ok)throw new Error('HTTP '+response.status);
                      const bytes=await response.arrayBuffer();
                      const size=bytes.byteLength;
                      const ac=new AudioContext();
                      try{
                        const audio=await ac.decodeAudioData(bytes);
                        return {channels:audio.numberOfChannels,duration:audio.duration,bytes:size};
                      }finally{await ac.close();}
                    }finally{clearTimeout(timeout);}
                }""",url)
                expected=1 if kind in ("fall","train") else 2
                if check["channels"]==expected and check["duration"]>0.5:
                    print(f"LIVE MEDIA VERIFIED: {kind} channels={check['channels']} duration={check['duration']:.1f}s bytes={check['bytes']}")
                else:
                    print(f"WARNING: live media {kind} has unexpected channels/length: {check}")
            except Exception as exc:
                print(f"WARNING: live binaural media {kind} unavailable in CI browser: {str(exc)[:250]}")
    finally:
        page.close()


def main():
    port=free_port()
    handler=lambda *args,**kwargs:QuietHandler(*args,directory=str(ROOT),**kwargs)
    server=http.server.ThreadingHTTPServer(("127.0.0.1",port),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    failures=[]
    fixture=stereo_wav()
    mono_fixture=mono_wav()
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True,args=["--autoplay-policy=no-user-gesture-required"])
            for viewport in [{"width":1440,"height":900},{"width":390,"height":844}]:
                page=browser.new_page(viewport=viewport)
                page.add_init_script("""(() => {
                    window.__lccAudit={panners:0};
                    const original=AudioContext.prototype.createPanner;
                    AudioContext.prototype.createPanner=function(...args){
                        window.__lccAudit.panners++;
                        return original.apply(this,args);
                    };
                })();""")
                def audio_route(route):
                    route.fulfill(status=200,content_type="audio/wav",body=fixture,
                        headers={"Access-Control-Allow-Origin":"*","Cache-Control":"no-store"})
                page.route("https://upload.wikimedia.org/**",audio_route)
                def mono_route(route):
                    route.fulfill(status=200,content_type="audio/wav",body=mono_fixture,
                        headers={"Access-Control-Allow-Origin":"*","Cache-Control":"no-store"})
                page.route("https://raw.githubusercontent.com/facebookincubator/Meta-open-sound/**",mono_route)
                errors=[]
                page.on("pageerror",lambda err:errors.append(str(err)))
                page.goto(f"http://127.0.0.1:{port}/spatial-audio/",wait_until="domcontentloaded")
                if page.locator("h1").count()!=1:failures.append("Expected exactly one h1")
                if page.locator(".sample").count()!=12:failures.append("Expected 12 sound selections")
                if page.locator('[data-preset="loudspeakers"]').get_attribute("aria-pressed")!="true":
                    failures.append("Original preset is not selected on load")
                if page.locator("#lcc-switch").get_attribute("aria-checked")!="false":
                    failures.append("LCC must begin Off")
                if page.locator("iframe").count():failures.append("Unexpected obsolete player embed")
                if page.locator("body").inner_text().find("Hear something real.")>=0:
                    failures.append("Removed promotional binaural references are still present")
                if page.locator("body").inner_text().find("All five scenes use original synthesized")>=0:
                    failures.append("Removed verbose explanation is still present")
                if page.locator(".signal").count():failures.append("Removed HDMI signal diagram is still present")
                if not page.locator(".brand").get_attribute("href").startswith("https://mattlane66.github.io"):
                    failures.append("Preview brand navigation does not return to portfolio")
                width=page.evaluate("({doc:document.documentElement.scrollWidth,view:document.documentElement.clientWidth})")
                if width["doc"]>width["view"]+4:
                    failures.append(f"{viewport['width']}px page overflow: {width}")
                try:
                    probe=probe_worklet(page)
                    if probe["bypassError"]>1e-5:failures.append(f"Stereo bypass altered signal: {probe}")
                    if probe["orig"]["delay"]!=32 or abs(probe["orig"]["decay"]-.74989420933)>1e-9:
                        failures.append(f"Original LCC default changed: {probe}")
                    if probe["wetDifference"]<.001 or probe["presetDifference"]<.001:
                        failures.append(f"LCC On or laptop preset made no DSP output difference: {probe}")
                    if probe["laptop"]["preset"]!="laptop" or probe["laptop"]["delay"]!=113 or abs(probe["laptop"]["decay"]-.68)>1e-9 or probe["laptop"]["frames"]!=6:
                        failures.append(f"Laptop preset failed to change delay and attenuation: {probe}")
                    if probe["restored"]["preset"]!="loudspeakers" or probe["restored"]["delay"]!=32 or abs(probe["restored"]["decay"]-.74989420933)>1e-9 or probe["restored"]["frames"]!=2:
                        failures.append(f"Original DSP preset could not be restored: {probe}")
                    if any(probe["finite"]):failures.append(f"Non-finite audio samples: {probe}")
                    page.locator("#play").click()
                    page.wait_for_function("document.getElementById('play').textContent.includes('Pause')",timeout=15000)
                    first=page.locator("#source-dot").get_attribute("style")
                    page.wait_for_timeout(400)
                    if first==page.locator("#source-dot").get_attribute("style"):
                        failures.append("3D source indicator did not move")
                    page.locator("#lcc-switch").click()
                    page.locator('[data-preset="laptop"]').click()
                    if page.locator("#preset-active").inner_text()!="Laptop · 113 µs":
                        failures.append("Laptop UI selection failed")
                    page.wait_for_timeout(170)
                    if not page.locator("#play").inner_text().find("Pause")>=0:
                        failures.append("Audio stopped when changing to laptop preset")
                    page.locator('[data-preset="loudspeakers"]').click()
                    if page.locator("#preset-active").inner_text()!="Original LCC · 32 µs":
                        failures.append("Restoring original UI selection failed")
                    if page.locator("#lcc-switch").get_attribute("aria-checked")!="true":
                        failures.append("LCC switch reset when changing presets")
                    page.locator("#play").click()
                    for kind in ["dinosaur","flyby","helicopter","barber","clock360"]:
                        page.locator(f'[data-sound="{kind}"]').click()
                        page.locator("#play").click()
                        page.wait_for_function("document.getElementById('play').textContent.includes('Pause')",timeout=15000)
                        page.locator("#play").click()
                    for kind in ["fall","train"]:
                        page.locator(f'[data-sound="{kind}"]').click()
                        before=page.evaluate("window.__lccAudit.panners")
                        if not page.locator("#source-dot").is_visible():
                            failures.append(f"Recorded object {kind} lacks moving source indicator")
                        page.locator("#play").click()
                        page.wait_for_function("document.getElementById('play').textContent.includes('Pause')",timeout=15000)
                        if page.evaluate("window.__lccAudit.panners")<=before:
                            failures.append(f"Recorded mono object {kind} did not use PannerNode/HRTF")
                        page.locator("#play").click()
                    for kind in ["rumba","pool","skyball","carriage3d"]:
                        page.locator(f'[data-sound="{kind}"]').click()
                        before=page.evaluate("window.__lccAudit.panners")
                        if page.locator("#source-dot").is_visible():
                            failures.append(f"Recording {kind} wrongly displays simulated direction dot")
                        if "without a second HRTF" not in page.locator("#stage-explanation").inner_text():
                            failures.append(f"Recording {kind} missing stereo routing explanation")
                        page.locator("#play").click()
                        page.wait_for_function("document.getElementById('play').textContent.includes('Pause')",timeout=15000)
                        after=page.evaluate("window.__lccAudit.panners")
                        if before!=after:
                            failures.append(f"Recording {kind} was incorrectly reprocessed by a PannerNode")
                        if "Recording and license" not in page.locator("#source-link").inner_text():
                            failures.append(f"Recording {kind} missing license link")
                        page.locator("#lcc-switch").click()
                        page.locator("#lcc-switch").click()
                        page.locator("#play").click()
                    # The recorded source remains paused and can restart without downloading again.
                    page.locator("#play").click()
                    page.wait_for_function("document.getElementById('play').textContent.includes('Pause')",timeout=10000)
                    page.locator("#play").click()
                except Exception as exc:
                    failures.append(f"{viewport['width']}px browser interaction failure: {exc}")
                if errors:failures.append(f"{viewport['width']}px runtime errors: {errors[:3]}")
                page.close()
            # An external probe is diagnostic, not the deterministic test.
            check_live_media(browser,f"http://127.0.0.1:{port}/spatial-audio/")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    for failure in failures:print("ERROR:",failure)
    if failures:return 1
    print("LCC audit passed: 12 samples, stereo recordings bypass HRTF, mono recorded objects use HRTF, moving clock/drop/train, DSP presets, desktop/mobile.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
