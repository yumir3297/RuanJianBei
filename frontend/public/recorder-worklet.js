// pcm-recorder: 在音频渲染线程采集单声道 PCM，缓冲后整块回传主线程。
// 与 ScriptProcessorNode 不同，AudioWorklet 不占用主线程，
// 页面即使被 Three.js/WebGL 重负载阻塞也不会静默丢帧。
class PcmRecorderProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._recording = false;
    this._buffer = new Float32Array(4096);
    this._offset = 0;
    this.port.onmessage = (event) => {
      if (event.data === "start") {
        this._recording = true;
        this._offset = 0;
      } else if (event.data === "stop") {
        // 收到停止指令时把未满一缓冲区的尾部采样也发回去，避免丢最后一个字的尾巴
        if (this._recording && this._offset > 0) {
          this._flush(this._buffer.subarray(0, this._offset));
        }
        this._recording = false;
      }
    };
  }

  _flush(samples) {
    const copy = new Float32Array(samples.length);
    copy.set(samples);
    this.port.postMessage(copy, [copy.buffer]);
  }

  process(inputs) {
    const input = inputs[0];
    if (this._recording && input && input.length > 0 && input[0] && input[0].length > 0) {
      const channelCount = input.length;
      const length = input[0].length;
      for (let index = 0; index < length; index += 1) {
        let sample = 0;
        for (let channel = 0; channel < channelCount; channel += 1) {
          sample += input[channel][index] / channelCount;
        }
        this._buffer[this._offset] = sample;
        this._offset += 1;
        if (this._offset === this._buffer.length) {
          this._flush(this._buffer);
          this._offset = 0;
        }
      }
    }
    return true;
  }
}

registerProcessor("pcm-recorder", PcmRecorderProcessor);
