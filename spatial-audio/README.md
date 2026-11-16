# LCC — Three Recording Listening Lab

Static GitHub Pages page at https://mattlane66.github.io/spatial-audio/.

## Recordings

- **Battlefield** — source: battlefieldBinaural.wav
- **Patch** — source: patch(1).wav
- **Gravity** — source: gravity(1).wav

The audio files in `audio/` are 224 kb/s stereo AAC versions of user-supplied WAV files. This site intentionally avoids a backend.

## Player

The player uses one stereo HTMLAudioElement routed through the Web Audio API. The AudioWorklet runs the browser adaptation of LCC; the Off/On controls fade between the dry and LCC-processed signal without restarting playback.

For local development, run `python3 -m http.server 8000` from this folder, then open http://localhost:8000/ (AudioWorklet requires a secure context such as localhost or HTTPS).

The open-source research implementation is at https://github.com/mattlane66/lcc.

Ensure you have rights to redistribute the source audio recordings before public use.

## Output-level calibration (November 2026)

The earlier worst-case fixed attenuation was approximately -13.8 dB, which made these three recordings unnecessarily quiet. The listening-lab output gain is now **0.48** (approximately -6.4 dB), a **+7.4 dB** increase. That shared gain is applied to both unprocessed and LCC-processed audio.

We decoded each published AAC file and ran the actual browser LCC worklet at 44.1, 48, and 96 kHz. The highest processed sample peak was 0.887 (Battlefield at 96 kHz), below the 0.92 level where the protective peak guard begins. Thus the current three recordings are not affected by peak limiting. Unexpected full-scale material is smoothly constrained below 1.0 to avoid digital overflows. The gain has been calibrated for these **specific** recordings, not arbitrary future audio files; repeat the test before adding tracks.
