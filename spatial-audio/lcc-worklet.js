/*
 * Browser AudioWorklet adaptation of the open-source LCC (Localization Cue
 * Correction) stereo crosstalk-cancellation algorithm by Robert LiKamWa
 * and Matthew Lane, with guidance from Ralph Glasgal.
 * Reference: https://github.com/mattlane66/lcc/blob/master/lcc_rtaudio.cpp
 *
 * This implementation follows the C++ sample-by-sample two-pass block
 * equations and default parameters. Both enabled and bypass audio are
 * rendered from the same input samples, with identical latency and a shared
 * output gain. Enable/disable ramps the wet mix without restarting playback.
 */
class LCCProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.inputGain = 0.70;
    this.decayGain = 0.74989420933;
    this.centerGain = 0.70;
    this.endGain = 1.4285;
    this.delayUs = 32;
    this.delaySamples = this.delayUs * 1e-6 * sampleRate;
    this.frames = Math.max(1, Math.ceil(this.delaySamples));
    this.delayMod = this.frames - this.delaySamples;
    this.delayModInv = 1 - this.delayMod;
    this.inL = new Float64Array(this.frames);
    this.inR = new Float64Array(this.frames);
    this.preL = new Float64Array(this.frames);
    this.preR = new Float64Array(this.frames);
    this.prevL = new Float64Array(this.frames);
    this.prevR = new Float64Array(this.frames);
    this.dryL = new Float32Array(this.frames);
    this.dryR = new Float32Array(this.frames);
    this.wetL = new Float32Array(this.frames);
    this.wetR = new Float32Array(this.frames);
    this.fill = 0;
    this.read = this.frames;
    this.mix = 0;
    this.enabled = false;
    this.rampPerSample = 1 / Math.max(1, sampleRate * 0.03);
    // Conservative shared headroom protects against peaks of the LCC matrix.
    // The same gain is applied to ON and OFF to preserve their A/B level basis.
    this.safetyGain = 0.55;
    this.port.onmessage = ({data}) => {
      if (data && data.type === 'enable') this.enabled = !!data.value;
      if (data && data.type === 'reset') this.reset();
    };
  }

  reset() {
    this.prevL.fill(0);
    this.prevR.fill(0);
    this.inL.fill(0);
    this.inR.fill(0);
    this.dryL.fill(0);
    this.dryR.fill(0);
    this.wetL.fill(0);
    this.wetR.fill(0);
    this.fill = 0;
    this.read = this.frames;
  }

  renderBlock() {
    const n = this.frames;
    const a = this.inputGain;
    const c = this.centerGain * a / 2;
    for (let i = 0; i < n; i++) {
      const l = this.inL[i] * a;
      const r = this.inR[i] * a;
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
      const center = (this.inL[i] + this.inR[i]) * c;
      this.wetL[i] = this.endGain * (this.preL[i] + center);
      this.wetR[i] = this.endGain * (this.preR[i] + center);
    }
  }

  process(inputs, outputs) {
    const input = inputs[0] || [];
    const output = outputs[0] || [];
    if (!output[0]) return true;
    const sourceL = input[0];
    const sourceR = input[1] || input[0];
    const outL = output[0];
    const outR = output[1];
    const n = outL.length;
    for (let i = 0; i < n; i++) {
      let dryL = 0, dryR = 0, wetL = 0, wetR = 0;
      if (this.read < this.frames) {
        const j = this.read++;
        dryL = this.dryL[j]; dryR = this.dryR[j];
        wetL = this.wetL[j]; wetR = this.wetR[j];
      }
      const target = this.enabled ? 1 : 0;
      if (this.mix < target) this.mix = Math.min(target, this.mix + this.rampPerSample);
      else if (this.mix > target) this.mix = Math.max(target, this.mix - this.rampPerSample);
      outL[i] = this.safetyGain * (dryL * (1 - this.mix) + wetL * this.mix);
      if (outR) outR[i] = this.safetyGain * (dryR * (1 - this.mix) + wetR * this.mix);

      const j = this.fill++;
      const l = sourceL ? sourceL[i] : 0;
      const r = sourceR ? sourceR[i] : 0;
      this.inL[j] = l; this.inR[j] = r;
      this.dryL[j] = l; this.dryR[j] = r;
      if (this.fill === this.frames) {
        this.renderBlock();
        this.fill = 0;
        this.read = 0;
      }
    }
    return true;
  }
}
registerProcessor('lcc-processor', LCCProcessor);
