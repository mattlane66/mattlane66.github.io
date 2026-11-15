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
