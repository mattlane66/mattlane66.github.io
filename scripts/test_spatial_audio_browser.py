#!/usr/bin/env python3
"""Browser audit for the single retained Engine Orbit scene and two LCC presets.

Mocked mono audio checks the actual HRTF and DSP paths; a separate browser
probe checks the live recording's duration, channel count, peak and RMS level.
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


def check_engine_asset(page):
    """Decode the actual bundled sound (not a mocked stereo fixture)."""
    return page.evaluate("""async () => {
      const response=await fetch('./engine-orbit.ogg',{cache:'no-cache'});
      if(!response.ok)throw new Error('Bundled engine HTTP '+response.status);
      const bytes=await response.arrayBuffer();
      const ctx=new (window.AudioContext||window.webkitAudioContext)();
      try{
        const decoded=await ctx.decodeAudioData(bytes);
        const ch=decoded.getChannelData(0);
        let peak=0,energy=0;
        for(let i=0;i<ch.length;i++){peak=Math.max(peak,Math.abs(ch[i]));energy+=ch[i]*ch[i];}
        return {bytes:bytes.byteLength,channels:decoded.numberOfChannels,
          duration:decoded.duration,peak,rms:Math.sqrt(energy/ch.length)};
      }finally{await ctx.close();}
    }""")


def wait_for_audible_output(page):
    """Ensure samples actually flow through Web Audio output, not just UI state."""
    page.wait_for_function("""() => {
      const analyser=window.__lccOutputAnalyser;
      if(!analyser)return false;
      const data=new Float32Array(analyser.fftSize);
      analyser.getFloatTimeDomainData(data);
      let peak=0;
      for(let i=0;i<data.length;i++)peak=Math.max(peak,Math.abs(data[i]));
      return peak>.001;
    }""",timeout=12000)


def main():
    import sys
    engines=["webkit"] if "--webkit" in sys.argv else ["chromium"]
    port=free_port()
    handler=lambda *args,**kwargs:QuietHandler(*args,directory=str(ROOT),**kwargs)
    server=http.server.ThreadingHTTPServer(("127.0.0.1",port),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    failures=[]
    fixture=stereo_wav()
    mono_fixture=mono_wav()
    try:
        with sync_playwright() as playwright:
            for engine in engines:
                try:
                    browser_type=getattr(playwright,engine)
                    args={"headless":True}
                    if engine=="chromium":
                        args["args"]=["--autoplay-policy=no-user-gesture-required"]
                    browser=browser_type.launch(**args)
                except Exception as exc:
                    failures.append(f"{engine} browser failed to launch: {exc}")
                    continue
                for viewport in [{"width":1440,"height":900},{"width":390,"height":844}]:
                    page=browser.new_page(viewport=viewport)
                    page.add_init_script("""(() => {
                      window.__lccAudit={panners:0};
                      const original=AudioContext.prototype.createPanner;
                      AudioContext.prototype.createPanner=function(...args){
                        window.__lccAudit.panners++;
                        return original.apply(this,args);
                      };
                      if(navigator.mediaDevices){
                        try{Object.defineProperty(navigator.mediaDevices,'getDisplayMedia',{
                          configurable:true,
                          value:()=>{throw Error('Forbidden tab capture was invoked')}
                        });}catch(_){}
                      }
                    })();""")
                    errors=[]
                    remote=[]
                    page.on("pageerror",lambda err:errors.append(str(err)))
                    page.on("request",lambda req:remote.append(req.url) if req.url.startswith("https://") else None)
                    try:
                        page.goto(f"http://127.0.0.1:{port}/spatial-audio/",wait_until="domcontentloaded")
                        if page.locator("h1").count()!=1:failures.append("Expected exactly one h1")
                        if page.locator(".sample").count()!=0:failures.append("Sound picker should not clutter one-source demo")
                        if page.locator("#route-tab").count() or page.locator(".demo-auditions").count():
                            failures.append("Obsolete trailer tab-sharing feature remains")
                        if page.locator("#play").count()!=1 or page.locator("#lcc-switch").count()!=1:
                            failures.append("Simple Play and LCC controls missing")
                        if page.locator(".own-audio").get_attribute("open") is not None:
                            failures.append("Optional stereo-file controls should start collapsed")
                        if page.locator('[data-preset="loudspeakers"]').get_attribute("aria-pressed")!="true":
                            failures.append("Original preset must be default")
                        if page.locator("#lcc-switch").get_attribute("aria-checked")!="false":
                            failures.append("LCC should start Off")
                        width=page.evaluate("({doc:document.documentElement.scrollWidth,view:document.documentElement.clientWidth})")
                        if width["doc"]>width["view"]+4:
                            failures.append(f"{engine} {viewport['width']}px overflow: {width}")
                        asset=check_engine_asset(page)
                        if asset["channels"]!=1 or asset["duration"]<3 or asset["peak"]<.05 or asset["rms"]<.01:
                            failures.append(f"Bundled engine asset is wrong or too quiet: {asset}")
                        print(f"BUNDLED AUDIO VERIFIED: {engine} mono duration={asset['duration']:.2f}s bytes={asset['bytes']} peak={asset['peak']:.4f} rms={asset['rms']:.4f}")
                        probe=probe_worklet(page)
                        if probe["bypassError"]>1e-5 or probe["wetDifference"]<.001 or probe["presetDifference"]<.001:
                            failures.append(f"{engine}: original/laptop LCC DSP missing real signal difference: {probe}")
                        if probe["orig"]["delay"]!=32 or abs(probe["orig"]["decay"]-.74989420933)>1e-9:
                            failures.append(f"{engine}: original LCC default altered: {probe}")
                        if probe["laptop"]["delay"]!=113 or abs(probe["laptop"]["decay"]-.68)>1e-9:
                            failures.append(f"{engine}: laptop DSP model altered: {probe}")
                        if probe["restored"]["delay"]!=32 or abs(probe["restored"]["decay"]-.74989420933)>1e-9:
                            failures.append(f"{engine}: LCC default did not restore: {probe}")
                        if any(probe["finite"]):failures.append(f"{engine}: non-finite DSP output: {probe}")
                        # One click on Play, then an actual non-silent output signal.
                        page.locator("#play").click()
                        page.wait_for_function("document.getElementById('play').textContent.includes('Pause')",timeout=15000)
                        wait_for_audible_output(page)
                        before=page.locator("#source-dot").get_attribute("style")
                        page.wait_for_timeout(300)
                        if before==page.locator("#source-dot").get_attribute("style"):
                            failures.append(f"{engine}: 360-degree source did not move")
                        if page.evaluate("window.__lccAudit.panners")<1:
                            failures.append(f"{engine}: engine never passed through HRTF")
                        page.locator("#lcc-switch").click()
                        if page.locator("#lcc-switch").get_attribute("aria-checked")!="true":
                            failures.append(f"{engine}: LCC On control failed")
                        wait_for_audible_output(page)
                        page.locator('[data-preset="laptop"]').click()
                        if page.locator("#preset-active").inner_text()!="Laptop · 113 µs":
                            failures.append(f"{engine}: laptop preset UI failed")
                        if "Pause" not in page.locator("#play").inner_text():
                            failures.append(f"{engine}: playback stopped on preset switch")
                        wait_for_audible_output(page)
                        page.locator('[data-preset="loudspeakers"]').click()
                        page.locator("#lcc-switch").click()
                        if page.locator("#lcc-switch").get_attribute("aria-checked")!="false":
                            failures.append(f"{engine}: LCC Off control failed")
                        wait_for_audible_output(page)
                        page.locator("#play").click()
                        if "Play" not in page.locator("#play").inner_text():
                            failures.append(f"{engine}: pause control failed")
                        # Optional local stereo is routed directly, without adding HRTF.
                        page.locator(".own-audio summary").click()
                        page.locator("#stereo-file").set_input_files({
                            "name":"two-channel.wav","mimeType":"audio/wav","buffer":fixture
                        })
                        page.wait_for_function("document.getElementById('file-status').textContent.startsWith('Ready:')",timeout=15000)
                        count=page.evaluate("window.__lccAudit.panners")
                        if page.locator("#source-dot").is_visible():
                            failures.append(f"{engine}: local binaural audio has false HRTF source")
                        page.locator("#play").click()
                        page.wait_for_function("document.getElementById('play').textContent.includes('Pause')",timeout=15000)
                        wait_for_audible_output(page)
                        if page.evaluate("window.__lccAudit.panners")!=count:
                            failures.append(f"{engine}: local stereo was re-HRTF processed")
                        page.locator("#lcc-switch").click()
                        page.locator('[data-preset="laptop"]').click()
                        if "Pause" not in page.locator("#play").inner_text():
                            failures.append(f"{engine}: local stereo stopped when LCC preset changed")
                        page.locator("#reset-file").click()
                        if page.locator("#sample-title").inner_text().lower()!="engine orbit":
                            failures.append(f"{engine}: failed to restore built-in engine")
                        page.locator("#stereo-file").set_input_files({
                            "name":"mono.wav","mimeType":"audio/wav","buffer":mono_fixture
                        })
                        page.wait_for_function("document.getElementById('file-status').textContent.startsWith('Could not use file:')",timeout=15000)
                        if page.locator("#sample-title").inner_text().lower()!="engine orbit":
                            failures.append(f"{engine}: rejected mono file altered source")
                    except Exception as exc:
                        failures.append(f"{engine} {viewport['width']}px browser failure: {exc}")
                    if remote:failures.append(f"{engine}: bundled playback unexpectedly requires external hosts: {remote[:2]}")
                    if errors:failures.append(f"{engine}: JS errors: {errors[:3]}")
                    page.close()
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    for failure in failures:print("ERROR:",failure)
    if failures:return 1
    print("LCC ONE-CLICK AUDIT PASSED: real bundled engine PCM, non-silent output, On/Off A-B without restart, both DSP presets, local stereo HRTF bypass, mono rejection, responsive layout.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
