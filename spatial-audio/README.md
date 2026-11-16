# Spatial audio — LCC listening lab

Source algorithm: https://github.com/mattlane66/lcc
Website: https://mattlane66.github.io/spatial-audio/

## Playback

The page uses the original **loudspeaker** LCC defaults exclusively. There are no speaker setup selectors. The three recordings are lossless stereo FLAC copies of the original 16-bit, 44.1 kHz WAV audio. Their sample data is unchanged; only the **playback cue-in** moves the start point past the recording's silent/very faint lead-in:

| Track | Source duration | Player starts at | Effective duration |
| --- | ---: | ---: | ---: |
| Battlefield | 54.985 s | 19.50 s | 35.485 s |
| Patch | 35.341 s | 0 s | 35.341 s |
| Gravity | 40.585 s | 2.0739 s | 38.511 s |

The original Battlefield contains ~15.07 s of absolute silence followed by a very quiet swell. Starting playback at 19.50 s leaves a short lead-in before the first strong audible event. The full lossless file is preserved in the repository; the cue is reversible via the `cueIn` value in the embedded track metadata and `tracks.json`.

Short clips are fetched and decoded once into Web Audio `AudioBuffer` objects. `AudioBufferSourceNode` supports precise start/seek offsets. The player maintains explicit transport state so Play, Pause, seek, and track selection cannot race with pending loading operations. Seeking starts a new source from the selected audio sample rather than waiting for the browser media element's asynchronous `seeked` event. A six-millisecond input gain crossfade prevents clicks during discontinuities. The LCC core remains alive through playback and mode transitions.

## Processing parameters

| Parameter | Value |
| --- | ---: |
| Input gain | 0.70 |
| Center gain | 0.70 |
| End gain | 1.4285 |
| Crosstalk decay | 0.74989420933 |
| Algorithm delay | 32 microseconds |

These are the defaults from `lcc_rtaudio.cpp`. LCC On/Off uses an 8 ms fade. The shared output gain remains 0.48 (approximately −6.4 dB), unchanged. Web Audio input/output uses Float32 samples, while the feedback, interpolation, buffer state, and calculations in the worklet use Float64. The emergency output peak guard is transparent below 0.98; the earlier published recordings passed peak testing. Browser sample-rate conversion and final speaker acoustics are device-dependent; the playback is not guaranteed bit-perfect at the speaker outputs.

## Regression checks

- `node --check spatial-audio/player.js` and `node --check spatial-audio/lcc-worklet.js`
- `python scripts/test_spatial_audio_player.py` runs real headless Chromium on GitHub Actions, testing start, seeks, pause/resume, track changes, and LCC toggles on both desktop and mobile. 

Audio distribution rights have not been independently verified. Headphones are not the intended loudspeaker configuration.
