/*
 * Browser adaptation of LCC (Localization Cue Correction) by Robert LiKamWa
 * and Matthew Lane, with guidance from Ralph Glasgal.
 * https://github.com/mattlane66/lcc/blob/master/lcc_rtaudio.cpp
 * Follows the original lcc() calculation and default parameters. The worklet
 * buffers one short processing block to accommodate the original block method.
 */
class LCCProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.enabled = false;
    this.mix = 0;
    this.rampPerSample = 1 / Math.max(1, sampleRate * 0.025);
    this.inputgain = 0.70;
    this.decaygain = 0.74989420933;
    this.centergain = 0.70;
    this.endgain = 1.4285;
    this.delay = 32 * 1e-6 * sampleRate;
    this.framesPerBlock = Math.max(1, Math.ceil(this.delay));
    this.buflen = this.framesPerBlock * 2;
    this.delaymod = this.framesPerBlock - this.delay;
    this.delaymodinv = 1 - this.delaymod;
    this.prevOut = new Float64Array(this.buflen);
    this.inBlock = new Float64Array(this.buflen);
    this.outBlock = new Float64Array(this.buflen);
    this.rawBlock = new Float64Array(this.buflen);
    this.fill = 0;
    this.read = this.framesPerBlock;
    this.port.onmessage = event => {
      if (event.data && event.data.type === 'enable') {
        const next = Boolean(event.data.value);
        this.enabled = next;
      }
    };
  }
  runBlock() {
    const n = this.buflen;
    const input = this.inBlock;
    const raw = this.rawBlock;
    const previous = this.prevOut;
    for (let i = 0; i < n; i += 2) {
      input[i] *= this.inputgain;
      input[i + 1] *= this.inputgain;
      raw[i] = input[i] - this.decaygain * previous[i + 1];
      raw[i + 1] = input[i + 1] - this.decaygain * previous[i];
      if (i === 0) {
        previous[n - 2] += raw[0] * this.delaymod;
        previous[n - 1] += raw[1] * this.delaymod;
      }
    }
    for (let i = 0; i < n; i += 2) {
      if (i < n - 2) {
        previous[i] = raw[i] * this.delaymodinv + raw[i + 2] * this.delaymod;
        previous[i + 1] = raw[i + 1] * this.delaymodinv + raw[i + 3] * this.delaymod;
      } else {
        previous[i] = raw[i] * this.delaymodinv;
        previous[i + 1] = raw[i + 1] * this.delaymodinv;
      }
      const center = (input[i] + input[i + 1]) * this.centergain * this.inputgain / 2;
      this.outBlock[i] = this.endgain * (raw[i] + center);
      this.outBlock[i + 1] = this.endgain * (raw[i + 1] + center);
    }
    this.read = 0;
  }
  process(inputs, outputs) {
    const input = inputs[0] || [];
    const output = outputs[0];
    const leftIn = input[0];
    const rightIn = input[1] || leftIn;
    const leftOut = output[0];
    const rightOut = output[1];
    if (!leftOut || !rightOut) return true;
    for (let i = 0; i < leftOut.length; i++) {
      const l = leftIn ? leftIn[i] : 0;
      const r = rightIn ? rightIn[i] : l;
      const wetL = this.read < this.framesPerBlock ? this.outBlock[this.read * 2] : 0;
      const wetR = this.read < this.framesPerBlock ? this.outBlock[this.read * 2 + 1] : 0;
      if (this.read < this.framesPerBlock) this.read++;
      // Run the cancellation network continuously to keep its delay state
      // warm, even when bypassed. Crossfade over 25 ms so a comparison
      // does not click or restart the source's timeline.
      const target = this.enabled ? 1 : 0;
      if (this.mix !== target) {
        const step = this.rampPerSample;
        this.mix = Math.max(0, Math.min(1, this.mix + (target > this.mix ? step : -step)));
      }
      leftOut[i] = l * (1 - this.mix) + wetL * this.mix;
      rightOut[i] = r * (1 - this.mix) + wetR * this.mix;
      this.inBlock[this.fill * 2] = l;
      this.inBlock[this.fill * 2 + 1] = r;
      this.fill++;
      if (this.fill === this.framesPerBlock) {
        this.runBlock();
        this.fill = 0;
      }
    }
    return true;
  }
}
registerProcessor('lcc-processor', LCCProcessor);
