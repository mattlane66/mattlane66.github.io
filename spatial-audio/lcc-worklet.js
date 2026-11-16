/*
 * LCC (Localization Cue Correction) browser DSP, based on the original
 * lcc_rtaudio.cpp by Robert LiKamWa and Matthew Lane.
 * https://github.com/mattlane66/lcc/blob/master/lcc_rtaudio.cpp
 *
 * The loudspeaker preset uses the exact original numerical parameters.
 * The laptop preset is a previously modeled, uncalibrated nearfield geometry.
 * Both cores run continuously. Their outputs are aligned to the same sample
 * before a smooth preset crossfade. Bypass and LCC share that same latency
 * and fixed output gain, so A/B does not seek, decode twice, or restart.
 *
 * AudioWorklet input/output samples are Float32; recurrence state, the
 * fractional delay, preset blend, and output alignment use Float64.
 */

const LCC_PRESETS = Object.freeze({
  loudspeakers: { delayUs: 32, decayGain: 0.74989420933 },
  laptop: { delayUs: 113, decayGain: 0.68 },
});

class LCCCore {
  constructor(preset, sharedFrames) {
    this.inputGain = 0.70;
    this.centerGain = 0.70;
    this.endGain = 1.4285;
    this.decayGain = preset.decayGain;
    const delaySamples = preset.delayUs * 1e-6 * sampleRate;
    this.frames = Math.max(1, Math.ceil(delaySamples));
    this.delayMod = this.frames - delaySamples;
    this.delayModInv = 1 - this.delayMod;
    const n = this.frames;
    this.inL = new Float64Array(n);
    this.inR = new Float64Array(n);
    this.preL = new Float64Array(n);
    this.preR = new Float64Array(n);
    this.prevL = new Float64Array(n);
    this.prevR = new Float64Array(n);
    this.wetL = new Float64Array(n);
    this.wetR = new Float64Array(n);
    this.padFrames = sharedFrames - n;
    this.padL = new Float64Array(this.padFrames);
    this.padR = new Float64Array(this.padFrames);
    this.reset();
  }

  reset() {
    for (const key of ['inL','inR','preL','preR','prevL','prevR','wetL','wetR','padL','padR']) {
      this[key].fill(0);
    }
    this.fill = 0;
    this.read = this.frames;
    this.padIndex = 0;
    this.outputL = 0;
    this.outputR = 0;
  }

  renderBlock() {
    // The two-pass recurrence and fractional-delay interpolation match
    // the C++ lcc() function, including the cross-block sample carry.
    const n = this.frames;
    const inputGain = this.inputGain;
    const centerFactor = this.centerGain * inputGain / 2;
    for (let i = 0; i < n; i++) {
      const l = this.inL[i] * inputGain;
      const r = this.inR[i] * inputGain;
      this.inL[i] = l;
      this.inR[i] = r;
      this.preL[i] = l - this.decayGain * this.prevR[i];
      this.preR[i] = r - this.decayGain * this.prevL[i];
      if (i === 0) {
        this.prevL[n - 1] += this.preL[0] * this.delayMod;
        this.prevR[n - 1] += this.preR[0] * this.delayMod;
      }
    }
    for (let i = 0; i < n; i++) {
      this.prevL[i] = this.preL[i] * this.delayModInv +
        (i + 1 < n ? this.preL[i + 1] * this.delayMod : 0);
      this.prevR[i] = this.preR[i] * this.delayModInv +
        (i + 1 < n ? this.preR[i + 1] * this.delayMod : 0);
      const center = (this.inL[i] + this.inR[i]) * centerFactor;
      this.wetL[i] = this.endGain * (this.preL[i] + center);
      this.wetR[i] = this.endGain * (this.preR[i] + center);
    }
  }

  processSample(left, right) {
    let wetL = 0, wetR = 0;
    if (this.read < this.frames) {
      wetL = this.wetL[this.read];
      wetR = this.wetR[this.read];
      this.read++;
    }
    const i = this.fill++;
    this.inL[i] = left;
    this.inR[i] = right;
    if (this.fill === this.frames) {
      this.renderBlock();
      this.fill = 0;
      this.read = 0;
    }
    // Align cores with different filter-block lengths before blending.
    // Always pad the shorter core; do not phase-shift one preset against dry.
    if (this.padFrames > 0) {
      const p = this.padIndex;
      this.outputL = this.padL[p];
      this.outputR = this.padR[p];
      this.padL[p] = wetL;
      this.padR[p] = wetR;
      this.padIndex = (p + 1) % this.padFrames;
    } else {
      this.outputL = wetL;
      this.outputR = wetR;
    }
  }
}

class LCCProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    const maxFrames = Math.max(
      ...Object.values(LCC_PRESETS).map(p => Math.max(1, Math.ceil(p.delayUs * 1e-6 * sampleRate)))
    );
    this.cores = {
      loudspeakers: new LCCCore(LCC_PRESETS.loudspeakers, maxFrames),
      laptop: new LCCCore(LCC_PRESETS.laptop, maxFrames),
    };
    this.dryL = new Float64Array(maxFrames);
    this.dryR = new Float64Array(maxFrames);
    this.latencySamples = maxFrames;
    this.dryIndex = 0;
    this.enabled = false;
    this.mix = 0;
    this.preset = 'loudspeakers';
    this.presetMix = 0;
    this.rampPerSample = 1 / Math.max(1, sampleRate * 0.03);
    this.presetRampPerSample = 1 / Math.max(1, sampleRate * 0.05);

    // Fixed, common gain (~-6.4 dB), retained from the prior tested build.
    // Both presets and bypass share the SAME gain. Current lossless source
    // tracks are checked for peaks at common browser rates before publication.
    this.safetyGain = 0.48;
    this.port.onmessage = ({data}) => {
      if (!data) return;
      if (data.type === 'enable') this.enabled = Boolean(data.value);
      if (data.type === 'preset' && LCC_PRESETS[data.value]) this.preset = data.value;
      if (data.type === 'reset') this.reset();
    };
  }

  reset() {
    this.cores.loudspeakers.reset();
    this.cores.laptop.reset();
    this.dryL.fill(0);
    this.dryR.fill(0);
    this.dryIndex = 0;
  }

  // Transparent below |0.92|: no limiter action on validated tracks.
  // Exceptional input saturates smoothly without clipping the output device.
  peakGuard(value) {
    const threshold = 0.92;
    const range = 0.075;
    if (value > threshold) return threshold + range * Math.tanh((value - threshold) / range);
    if (value < -threshold) return -threshold - range * Math.tanh((-value - threshold) / range);
    return value;
  }

  process(inputs, outputs) {
    const input = inputs[0] || [];
    const output = outputs[0] || [];
    if (!output[0]) return true;
    const sourceL = input[0], sourceR = input[1] || input[0];
    const outL = output[0], outR = output[1];
    const speakers = this.cores.loudspeakers;
    const laptop = this.cores.laptop;
    const n = outL.length;

    for (let i = 0; i < n; i++) {
      const l = sourceL ? sourceL[i] : 0;
      const r = sourceR ? sourceR[i] : 0;
      const p = this.dryIndex;
      const dryL = this.dryL[p];
      const dryR = this.dryR[p];
      this.dryL[p] = l;
      this.dryR[p] = r;
      this.dryIndex = (p + 1) % this.latencySamples;

      speakers.processSample(l, r);
      laptop.processSample(l, r);
      const modeTarget = this.enabled ? 1 : 0;
      const presetTarget = this.preset === 'laptop' ? 1 : 0;
      if (this.mix < modeTarget) this.mix = Math.min(modeTarget, this.mix + this.rampPerSample);
      else if (this.mix > modeTarget) this.mix = Math.max(modeTarget, this.mix - this.rampPerSample);
      if (this.presetMix < presetTarget) this.presetMix = Math.min(presetTarget, this.presetMix + this.presetRampPerSample);
      else if (this.presetMix > presetTarget) this.presetMix = Math.max(presetTarget, this.presetMix - this.presetRampPerSample);

      const wetL = speakers.outputL * (1 - this.presetMix) + laptop.outputL * this.presetMix;
      const wetR = speakers.outputR * (1 - this.presetMix) + laptop.outputR * this.presetMix;
      const a = this.mix;
      outL[i] = this.peakGuard(this.safetyGain * (dryL * (1 - a) + wetL * a));
      if (outR) outR[i] = this.peakGuard(this.safetyGain * (dryR * (1 - a) + wetR * a));
    }
    return true;
  }
}
registerProcessor('lcc-processor', LCCProcessor);
