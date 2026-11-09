export const SPEECH_RATE_STORAGE_KEY = 'a5-tourist-speech-rate-v1';
export const DEFAULT_SPEECH_RATE = 1;
export const SPEECH_RATE_OPTIONS = Object.freeze([0.8, 1, 1.2, 1.5]);

export function normalizeSpeechRate(value) {
  const rate = Number(value);
  return SPEECH_RATE_OPTIONS.includes(rate) ? rate : DEFAULT_SPEECH_RATE;
}

export function readSpeechRate(storage) {
  try {
    const target = storage ?? globalThis.localStorage;
    const stored = target?.getItem(SPEECH_RATE_STORAGE_KEY);
    return stored == null ? DEFAULT_SPEECH_RATE : normalizeSpeechRate(JSON.parse(stored));
  } catch {
    return DEFAULT_SPEECH_RATE;
  }
}

export function writeSpeechRate(value, storage) {
  const rate = normalizeSpeechRate(value);
  try {
    const target = storage ?? globalThis.localStorage;
    target?.setItem(SPEECH_RATE_STORAGE_KEY, JSON.stringify(rate));
  } catch {
    // Playback remains available when storage is disabled or full.
  }
  return rate;
}
