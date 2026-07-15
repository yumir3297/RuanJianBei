import { ref } from "vue";

function getSpeechRecognitionConstructor() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

const IS_CHROME = typeof navigator !== "undefined" && /Chrome/.test(navigator.userAgent) && !/Edge|Edg/.test(navigator.userAgent);

export function useSpeechRecognition() {
  const SpeechRecognition = getSpeechRecognitionConstructor();
  const isListening = ref(false);
  const interimText = ref("");
  const finalText = ref("");
  const isSupported = ref(Boolean(SpeechRecognition));
  const error = ref("");
  const showBrowserHint = ref(!IS_CHROME);

  let recognition = null;
  let finalSegments = [];

  function resetTranscript() {
    interimText.value = "";
    finalText.value = "";
    finalSegments = [];
  }

  function start() {
    if (!SpeechRecognition) {
      error.value = "not-supported";
      return false;
    }
    if (isListening.value || recognition) {
      return false;
    }

    error.value = "";
    resetTranscript();

    let instance;
    try {
      instance = new SpeechRecognition();
    } catch {
      error.value = "not-supported";
      return false;
    }
    recognition = instance;
    try {
      instance.lang = "zh-CN";
    } catch {
      // Some browser implementations may not expose the `lang` property.
      // The default language is already acceptable for the first version.
    }
    instance.interimResults = true;
    instance.continuous = false;
    instance.maxAlternatives = 1;

    instance.onstart = () => {
      isListening.value = true;
    };

    instance.onresult = (event) => {
      let interim = "";

      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const transcript = result[0]?.transcript?.trim() || "";
        if (!transcript) {
          continue;
        }
        if (result.isFinal) {
          finalSegments[index] = transcript;
        } else {
          interim += transcript;
        }
      }

      finalText.value = finalSegments.filter(Boolean).join("");
      interimText.value = interim;
    };

    instance.onerror = (event) => {
      error.value = event.error || "unknown";
      interimText.value = "";
      isListening.value = false;
    };

    instance.onend = () => {
      if (recognition === instance) {
        recognition = null;
      }
      interimText.value = "";
      isListening.value = false;
    };

    try {
      instance.start();
      isListening.value = true;
      return true;
    } catch (startError) {
      recognition = null;
      isListening.value = false;
      error.value = startError?.name || "start-failed";
      return false;
    }
  }

  function stop() {
    if (!recognition) {
      isListening.value = false;
      interimText.value = "";
      return;
    }

    try {
      recognition.stop();
    } catch {
      recognition = null;
      isListening.value = false;
      interimText.value = "";
    }
  }

  function abort() {
    const instance = recognition;
    recognition = null;
    if (instance) {
      instance.onstart = null;
      instance.onresult = null;
      instance.onerror = null;
      instance.onend = null;
      try {
        instance.abort();
      } catch {
        // The browser may already have ended the recognition session.
      }
    }
    interimText.value = "";
    isListening.value = false;
  }

  function dismissHint() {
    showBrowserHint.value = false;
  }

  return {
    isListening,
    interimText,
    finalText,
    isSupported,
    error,
    showBrowserHint,
    start,
    stop,
    abort,
    dismissHint,
  };
}
