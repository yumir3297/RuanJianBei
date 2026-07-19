import { ref } from "vue";

function writeAscii(view, offset, value) {
  for (let index = 0; index < value.length; index += 1) {
    view.setUint8(offset + index, value.charCodeAt(index));
  }
}

function encodeMonoWav(chunks, sampleRate) {
  const sampleCount = chunks.reduce((total, chunk) => total + chunk.length, 0);
  const buffer = new ArrayBuffer(44 + sampleCount * 2);
  const view = new DataView(buffer);

  writeAscii(view, 0, "RIFF");
  view.setUint32(4, 36 + sampleCount * 2, true);
  writeAscii(view, 8, "WAVE");
  writeAscii(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeAscii(view, 36, "data");
  view.setUint32(40, sampleCount * 2, true);

  let offset = 44;
  for (const chunk of chunks) {
    for (let index = 0; index < chunk.length; index += 1) {
      const sample = Math.max(-1, Math.min(1, chunk[index]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
      offset += 2;
    }
  }
  return new Blob([buffer], { type: "audio/wav" });
}

export function useRecorder() {
  const isRecording = ref(false);
  const isSupported = ref(false);
  const durationSeconds = ref(0);

  let stream = null;
  let audioContext = null;
  let sourceNode = null;
  let processorNode = null;
  let silentGainNode = null;
  let chunks = [];
  let durationTimer = null;

  const AudioContextClass =
    typeof window !== "undefined" ? window.AudioContext || window.webkitAudioContext : null;
  isSupported.value = Boolean(
    typeof navigator !== "undefined"
      && navigator.mediaDevices?.getUserMedia
      && AudioContextClass,
  );

  async function start() {
    if (!isSupported.value || isRecording.value) {
      return null;
    }

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      audioContext = new AudioContextClass();
      if (audioContext.state === "suspended") {
        await audioContext.resume();
      }
    } catch {
      await cleanup();
      return null;
    }

    chunks = [];
    durationSeconds.value = 0;
    sourceNode = audioContext.createMediaStreamSource(stream);
    processorNode = audioContext.createScriptProcessor(4096, sourceNode.channelCount || 1, 1);
    silentGainNode = audioContext.createGain();
    silentGainNode.gain.value = 0;

    processorNode.onaudioprocess = (event) => {
      if (!isRecording.value) {
        return;
      }
      const input = event.inputBuffer;
      const channelCount = input.numberOfChannels;
      const mono = new Float32Array(input.length);
      for (let channel = 0; channel < channelCount; channel += 1) {
        const samples = input.getChannelData(channel);
        for (let index = 0; index < samples.length; index += 1) {
          mono[index] += samples[index] / channelCount;
        }
      }
      chunks.push(mono);
    };

    sourceNode.connect(processorNode);
    processorNode.connect(silentGainNode);
    silentGainNode.connect(audioContext.destination);
    isRecording.value = true;
    durationTimer = window.setInterval(() => {
      durationSeconds.value += 1;
    }, 1000);
    return null;
  }

  async function stop() {
    if (!isRecording.value || !audioContext) {
      await cleanup();
      return null;
    }

    isRecording.value = false;
    const recordedChunks = chunks;
    const sampleRate = audioContext.sampleRate;
    await cleanup();
    if (recordedChunks.length === 0) {
      return null;
    }
    return encodeMonoWav(recordedChunks, sampleRate);
  }

  async function cleanup() {
    isRecording.value = false;
    if (durationTimer) {
      window.clearInterval(durationTimer);
      durationTimer = null;
    }
    if (processorNode) {
      processorNode.onaudioprocess = null;
      processorNode.disconnect();
      processorNode = null;
    }
    sourceNode?.disconnect();
    silentGainNode?.disconnect();
    sourceNode = null;
    silentGainNode = null;
    stream?.getTracks().forEach((track) => track.stop());
    stream = null;
    if (audioContext && audioContext.state !== "closed") {
      await audioContext.close();
    }
    audioContext = null;
    chunks = [];
  }

  return {
    isRecording,
    isSupported,
    durationSeconds,
    start,
    stop,
  };
}
