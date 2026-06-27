import { ref } from "vue";

export function useRecorder() {
  const isRecording = ref(false);
  const isSupported = ref(false);
  const durationSeconds = ref(0);

  let mediaRecorder = null;
  let stream = null;
  let chunks = [];
  let durationTimer = null;

  const isSupportedCheck =
    typeof navigator !== "undefined" &&
    typeof navigator.mediaDevices !== "undefined" &&
    typeof navigator.mediaDevices.getUserMedia === "function" &&
    typeof window.MediaRecorder !== "undefined";

  isSupported.value = isSupportedCheck;

  async function start() {
    if (!isSupported.value) {
      return null;
    }

    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      isSupported.value = false;
      return null;
    }

    chunks = [];
    durationSeconds.value = 0;

    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

    mediaRecorder = new MediaRecorder(stream, { mimeType });

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    };

    mediaRecorder.start(100);

    durationTimer = setInterval(() => {
      durationSeconds.value += 1;
    }, 1000);

    isRecording.value = true;
    return null;
  }

  function stop() {
    return new Promise((resolve) => {
      if (!mediaRecorder || mediaRecorder.state === "inactive") {
        cleanup();
        isRecording.value = false;
        resolve(null);
        return;
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: mediaRecorder.mimeType || "audio/webm" });
        cleanup();
        isRecording.value = false;
        resolve(blob);
      };

      mediaRecorder.stop();
    });
  }

  function cleanup() {
    if (durationTimer) {
      clearInterval(durationTimer);
      durationTimer = null;
    }
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      stream = null;
    }
    mediaRecorder = null;
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
