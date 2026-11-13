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


def check_live_media(browser, base_url):
    """Best-effort external fetch check; network blocking does not invalidate local DSP."""
    page = browser.new_page()
    try:
        page.goto(base_url, wait_until="domcontentloaded")
        for kind, url in [
            ("engine", "https://raw.githubusercontent.com/facebookincubator/Meta-open-sound/main/corpora/oculus-audio-pack/ogg/VEHCar_CarEngineHigh_LOOP_01.ogg")
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
                        const x=audio.getChannelData(0);
                        let peak=0,energy=0;
                        for(let n=0;n<x.length;n++){
                            peak=Math.max(peak,Math.abs(x[n]));
                            energy+=x[n]*x[n];
                        }
                        const rms=Math.sqrt(energy/Math.max(1,x.length));
                        return {channels:audio.numberOfChannels,duration:audio.duration,bytes:size,peak,rms};
                      }finally{await ac.close();}
                    }finally{clearTimeout(timeout);}
                }""",url)
                expected=1
                if check["channels"]==expected and check["duration"]>0.35 and check["peak"]>=.01 and check["rms"]>=.001:
                    print(f"LIVE MEDIA VERIFIED: {kind} channels={check['channels']} duration={check['duration']:.1f}s bytes={check['bytes']} peak={check['peak']:.4f} rms={check['rms']:.4f}")
                else:
                    raise ValueError(f"Engine source missing, silent or very low level: {check}")
            except Exception as exc:
                # Avoid claiming success for a source that merely decodes.
                raise RuntimeError(f"Live engine audio source/level check failed: {exc}") from exc
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
                    window.__lccAudit={panners:0,captureCalls:0,captureOptions:null,captureGesture:false};
                    const original=AudioContext.prototype.createPanner;
                    AudioContext.prototype.createPanner=function(...args){
                        window.__lccAudit.panners++;
                        return original.apply(this,args);
                    };
                    // Stub permission-gated tab sharing with a genuine audio MediaStream.
                    // It models capture routing but does NOT imply Dolby/THX permit capture.
                    Object.defineProperty(navigator.mediaDevices,'getDisplayMedia',{
                        configurable:true,
                        value:function(options){
                            window.__lccAudit.captureCalls++;
                            window.__lccAudit.captureOptions=options;
                            window.__lccAudit.captureGesture=!!navigator.userActivation?.isActive;
                            const sourceCtx=new AudioContext();
                            const oscillator=sourceCtx.createOscillator();
                            const gain=sourceCtx.createGain();
                            gain.gain.value=.20;oscillator.frequency.value=320;
                            const dest=sourceCtx.createMediaStreamDestination();
                            oscillator.connect(gain);gain.connect(dest);oscillator.start();
                            const audioTrack=dest.stream.getAudioTracks()[0];
                            Object.defineProperty(audioTrack,'getSettings',{
                                configurable:true,value:()=>({suppressLocalAudioPlayback:true})
                            });
                            const canvas=document.createElement('canvas');
                            canvas.width=16;canvas.height=16;
                            const videoTrack=canvas.captureStream(10).getVideoTracks()[0];
                            Object.defineProperty(videoTrack,'getSettings',{
                                configurable:true,value:()=>({displaySurface:'browser'})
                            });
                            const stream=new MediaStream([audioTrack,videoTrack]);
                            return Promise.resolve(stream);
                        }
                    });
                })();""")
                def audio_route(route):
                    route.fulfill(status=200,content_type="audio/wav",body=fixture,
                        headers={"Access-Control-Allow-Origin":"*","Cache-Control":"no-store"})
                def mono_route(route):
                    route.fulfill(status=200,content_type="audio/wav",body=mono_fixture,
                        headers={"Access-Control-Allow-Origin":"*","Cache-Control":"no-store"})
                page.route("https://raw.githubusercontent.com/facebookincubator/Meta-open-sound/**",mono_route)
                errors=[]
                page.on("pageerror",lambda err:errors.append(str(err)))
                page.goto(f"http://127.0.0.1:{port}/spatial-audio/",wait_until="domcontentloaded")
                if page.locator("h1").count()!=1:failures.append("Expected exactly one h1")
                if page.locator(".sample").count()!=0:failures.append("Unexpected redundant scene picker in one-scene demo")
                if page.locator(".audition-grid a").count()!=8:
                    failures.append("Expected eight Dolby/THX external reference links")
                if not page.locator("#route-tab").is_visible():
                    failures.append("Missing live trailer-audio LCC connection button")
                if page.locator("#stop-tab").is_enabled():
                    failures.append("Disconnect button should be disabled before sharing")
                if "Share tab audio" not in page.locator(".demo-auditions").inner_text():
                    failures.append("Trailer tab capture instructions are not visible")
                if not page.locator("#stereo-file").is_visible():
                    failures.append("Local stereo audition control missing")
                if page.locator("#sample-title").inner_text().strip().lower()!="engine orbit":
                    failures.append("Engine Orbit is not the only active scene")
                if "Saw orbit" in page.locator("body").inner_text() or "Rotor overhead" in page.locator("body").inner_text():
                    failures.append("Removed low-quality scenes remain visible")
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
                    # Only Engine Orbit remains. No deleted sample-picker controls.
                    if page.locator(".sample").count():
                        failures.append("Deleted samples remain available")
                    if page.locator("#source-link").count()!=1 or "Recorded source and license" not in page.locator("#source-link").inner_text():
                        failures.append("Engine source/attribution link missing")
                    if "HRTF" not in page.locator("#stage-explanation").inner_text():
                        failures.append("Engine HRTF explanation missing")
                    before=page.evaluate("window.__lccAudit.panners")
                    page.locator("#play").click()
                    page.wait_for_function("document.getElementById('play').textContent.includes('Pause')",timeout=15000)
                    if page.evaluate("window.__lccAudit.panners")<=before:
                        failures.append("Engine source did not connect to spatial HRTF panner")
                    first=page.locator("#source-dot").get_attribute("style")
                    page.wait_for_timeout(330)
                    if first==page.locator("#source-dot").get_attribute("style"):
                        failures.append("Engine source does not visibly move")
                    page.locator("#lcc-switch").click()
                    page.locator("#lcc-switch").click()
                    page.locator("#play").click()
                    if "Play" not in page.locator("#play").inner_text():
                        failures.append("Engine did not pause")
                    # Resume still works, including cached audio.
                    page.locator("#play").click()
                    page.wait_for_function("document.getElementById('play').textContent.includes('Pause')",timeout=10000)
                    page.locator("#play").click()
                    # User-provided binaural stereo must enter the LCC bus directly:
                    # never downmix it and never run a second positional HRTF.
                    page.locator("#stereo-file").set_input_files({
                        "name":"test-binaural-stereo.wav",
                        "mimeType":"audio/wav",
                        "buffer":fixture
                    })
                    page.wait_for_function(
                        "document.getElementById('file-status').textContent.startsWith('Ready:')",
                        timeout=15000
                    )
                    if "test-binaural-stereo.wav" not in page.locator("#sample-title").inner_text():
                        failures.append("Local file did not become active audio source")
                    if page.locator("#source-dot").is_visible():
                        failures.append("Locally loaded binaural stereo has a fake HRTF position dot")
                    if not page.locator("#reset-file").is_enabled():
                        failures.append("Return-to-engine control unavailable after local file selection")
                    if page.locator("#source-link").is_visible():
                        failures.append("Engine license link remained visible for private local audio")
                    count_before=page.evaluate("window.__lccAudit.panners")
                    page.locator("#play").click()
                    page.wait_for_function(
                        "document.getElementById('play').textContent.includes('Pause')",
                        timeout=12000
                    )
                    if page.evaluate("window.__lccAudit.panners")!=count_before:
                        failures.append("Local binaural audio was incorrectly given a second HRTF")
                    page.locator("#lcc-switch").click()
                    page.locator('[data-preset="laptop"]').click()
                    if page.locator("#preset-active").inner_text()!="Laptop · 113 µs":
                        failures.append("Local stereo did not preserve laptop preset switching")
                    if "Pause" not in page.locator("#play").inner_text():
                        failures.append("Local stereo stopped during preset switch")
                    page.locator("#lcc-switch").click()
                    page.locator('[data-preset="loudspeakers"]').click()
                    page.locator("#reset-file").click()
                    if page.locator("#sample-title").inner_text().lower()!="engine orbit":
                        failures.append("Could not return to Engine Orbit")
                    if not page.locator("#source-dot").is_visible():
                        failures.append("Engine dot did not return after leaving binaural file")
                    if page.locator("#reset-file").is_enabled():
                        failures.append("Reset action remains active without a local file")
                    # A mono file is not silently accepted as a binaural stereo file.
                    page.locator("#stereo-file").set_input_files({
                        "name":"mono-not-binaural.wav",
                        "mimeType":"audio/wav",
                        "buffer":mono_fixture
                    })
                    page.wait_for_function(
                        "document.getElementById('file-status').textContent.startsWith('Could not use file:')",
                        timeout=12000
                    )
                    if page.locator("#sample-title").inner_text().lower()!="engine orbit":
                        failures.append("Rejected mono file changed the active source")
                    # Request tab capture from a click event and route synthetic
                    # stereo MediaStream into the SAME LCC worklet, no HRTF.
                    panners_before=page.evaluate("window.__lccAudit.panners")
                    page.locator("#route-tab").click()
                    page.wait_for_function(
                        "document.getElementById('sample-title').textContent==='Live trailer audio'",
                        timeout=15000
                    )
                    if page.evaluate("window.__lccAudit.captureCalls")!=1:
                        failures.append("Tab audio share picker was not invoked")
                    opts=page.evaluate("window.__lccAudit.captureOptions")
                    if opts.get("audio",{}).get("suppressLocalAudioPlayback") is not True:
                        failures.append("Original trailer audio was not requested to be suppressed")
                    if not page.evaluate("window.__lccAudit.captureGesture"):
                        failures.append("Tab-audio sharing was not requested inside an active click")
                    if page.evaluate("window.__lccAudit.panners")!=panners_before:
                        failures.append("Captured trailer stereo was incorrectly spatialized with HRTF")
                    if page.locator("#source-dot").is_visible():
                        failures.append("Captured trailer stereo incorrectly shows HRTF source dot")
                    if not page.locator("#stop-tab").is_enabled():
                        failures.append("User cannot disconnect the shared trailer")
                    if "Pause" not in page.locator("#play").inner_text():
                        failures.append("Live tab audio did not enter the playing state")
                    # Capture-audio monitor must recognize incoming non-silent PCM.
                    page.wait_for_function(
                        "document.getElementById('capture-status').textContent.includes('Tab audio received')",
                        timeout=7000
                    )
                    page.locator("#lcc-switch").click()
                    page.locator('[data-preset="laptop"]').click()
                    if "Pause" not in page.locator("#play").inner_text():
                        failures.append("Tab audio stopped when changing LCC preset")
                    page.locator("#play").click()
                    if "Play" not in page.locator("#play").inner_text():
                        failures.append("Captured tab audio could not be locally muted")
                    page.locator("#play").click()
                    page.wait_for_function(
                        "document.getElementById('play').textContent.includes('Pause')",
                        timeout=4000
                    )
                    page.locator("#stop-tab").click()
                    if page.locator("#sample-title").inner_text().lower()!="engine orbit":
                        failures.append("Disconnect failed to restore Engine Orbit")
                    if page.locator("#stop-tab").is_enabled():
                        failures.append("Disconnect remained active after capture ended")
                    if page.locator("#source-dot").is_visible() is False:
                        failures.append("Engine orbit visualization did not return after disconnect")
                    page.locator('[data-preset="loudspeakers"]').click()
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
    print("LCC audition passed: live captured tab stereo routed through worklet without HRTF, user gesture, audio monitoring, suppression request, eight reference links, local stereo and both presets.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
