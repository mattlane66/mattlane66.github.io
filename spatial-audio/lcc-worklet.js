/*
 * LCC (Localization Cue Correction) browser DSP, based on the original
 * lcc_rtaudio.cpp by Robert LiKamWa and Matthew Lane.
 * https://github.com/mattlane66/lcc/blob/master/lcc_rtaudio.cpp
 *
 * One fixed loudspeaker core uses the original algorithm parameters.
 * Bypass and LCC use the same latency and output gain; switching neither
 * reloads nor restarts playback.
 *
 * AudioWorklet input/output samples are Float32; recurrence state, the
 * fractional delay and output alignment use Float64.
 */

const LCC_PRESET = Object.freeze({ delayUs: 32, decayGain: 0.74989420933 });

class LCCCore {
  constructor(preset) {
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
    this.reset();
  }

  reset() {
    for (const key of ['inL','inR','preL','preR','prevL','prevR','wetL','wetR']) {
      this[key].fill(0);
    }
    this.fill = 0;
    this.read = this.frames;
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
    this.outputL = wetL;
    this.outputR = wetR;
  }
}

class LCCProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.core = new LCCCore(LCC_PRESET);
    const frames = this.core.frames;
    this.dryL = new Float64Array(frames);
    this.dryR = new Float64Array(frames);
    this.latencySamples = frames;
    this.dryIndex = 0;
    this.enabled = false;
    this.mix = 0;
    this.rampPerSample = 1 / Math.max(1, sampleRate * 0.008); // 8 ms A/B fade

    // Fixed, common gain (~-6.4 dB), retained from the prior tested build.
    // Both bypass and LCC share the SAME gain. Current lossless source
    // tracks are checked for peaks at common browser rates before publication.
    this.safetyGain = 0.48;
    this.port.onmessage = ({data}) => {
      if (!data) return;
      if (data.type === 'enable') this.enabled = Boolean(data.value);
      if (data.type === 'reset') this.reset();
    };
  }

  reset() {
    this.core.reset();
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
    const speakers = this.core;
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
      const modeTarget = this.enabled ? 1 : 0;
      if (this.mix < modeTarget) this.mix = Math.min(modeTarget, this.mix + this.rampPerSample);
      else if (this.mix > modeTarget) this.mix = Math.max(modeTarget, this.mix - this.rampPerSample);
      const wetL = speakers.outputL;
      const wetR = speakers.outputR;
      const a = this.mix;
      outL[i] = this.peakGuard(this.safetyGain * (dryL * (1 - a) + wetL * a));
      if (outR) outR[i] = this.peakGuard(this.safetyGain * (dryR * (1 - a) + wetR * a));
    }
    return true;
  }
}
registerProcessor('lcc-processor', LCCProcessor);
