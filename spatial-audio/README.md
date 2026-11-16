# Spatial audio — LCC listening lab

Source repository: https://github.com/mattlane66/lcc  
Website: https://mattlane66.github.io/spatial-audio/

## Fidelity

The three files are **lossless FLAC** encodings of the exact 16-bit, 44,100 Hz,
two-channel PCM samples supplied as WAV files by the author. We compared
the integer PCM samples after encoding and decoding against the original WAVs;
all three were sample-for-sample identical. No AAC or other lossy recording is
used by the published player.

HTMLAudioElement decodes the source; AudioWorklet receives Float32 arrays
from Web Audio, with the LCC recurrence, feedback, delay state and core
alignment computed in Float64 arrays/JavaScript Number, and emits Float32
samples. The browser or OS may resample audio if the device runs at a
different rate. The sound heard at the speakers cannot be guaranteed bit-perfect
relative to the digital source; LCC On intentionally changes the signal.

All three lossless clips were evaluated at 44.1, 48 and 96 kHz, Off,
Loudspeakers and Laptop. Max processed peak was 0.914141 (Battlefield,
96 kHz, loudspeakers), below the 0.98 threshold of the emergency
peak guard; it was inactive throughout the tested signals. No NaN or
Infinity occurred, and the Off stream matched the original decoded samples
(after shared gain of 0.48 and known delay) within Float32 rounding error.

The two LCC cores were checked against an independent translation of the
original C++ recurrence at those three rates; max absolute error was under
1.5e-8 after the common output gain and latency.

## Parameters

| Parameter | Loudspeakers | Laptop |
| --- | ---: | ---: |
| Input gain | 0.70 | 0.70 |
| Center gain | 0.70 | 0.70 |
| End gain | 1.4285 | 1.4285 |
| Crosstalk decay | 0.74989420933 | 0.68 |
| Algorithm delay | 32 microseconds | 113 microseconds |

**Loudspeakers** corresponds to the original C++ defaults. **Laptop** is
a previously modeled starting point (approximately 25 cm speaker spacing,
55 cm listener distance), **not** individually calibrated or validated for
every laptop. Both processing states run continuously, and selecting a preset
crossfades their time-aligned results over 50 ms without restarting the track.
LCC On/Off crossfades over 30 ms, with shared -6.4 dB digital headroom
(0.48) for both processed and unprocessed signals.

Playback is intended for two closely spaced, symmetrically positioned
loudspeakers with a centered listener, not headphones.

## Recordings

- Battlefield: source `battlefieldBinaural.wav`
- Patch: source `patch(1).wav`
- Gravity: source `gravity(1).wav`

The recording provenance and public redistribution rights have not been
independently verified.

To test locally, run `python3 -m http.server 8000` from this folder,
then open `http://localhost:8000`. An AudioWorklet requires a secure
context (HTTPS or localhost).
