export const DEFAULT_AVATAR_PRESET = "hanfu";
export const DEFAULT_AVATAR_VOICE = "gentle-female";

const SUPPORTED_PRESETS = new Set(["monk", "hanfu", "modern"]);
const SUPPORTED_VOICES = new Set([
  "gentle-female",
  "calm-female",
  "deep-male",
  "lively-female",
]);

const LEGACY_VOICE_MAP = {
  female_warm: "gentle-female",
  female_calm: "calm-female",
  male_calm: "deep-male",
  male_enthusiastic: "deep-male",
};

export function normalizeAvatarPreset(value, fallback = DEFAULT_AVATAR_PRESET) {
  if (typeof value !== "string") {
    return fallback;
  }
  return SUPPORTED_PRESETS.has(value) ? value : fallback;
}

export function normalizeAvatarPresetFromModelPath(modelPath, fallback = DEFAULT_AVATAR_PRESET) {
  if (typeof modelPath !== "string" || !modelPath.trim()) {
    return fallback;
  }
  if (modelPath.includes("monk")) return "monk";
  if (modelPath.includes("hanfu")) return "hanfu";
  if (modelPath.includes("modern")) return "modern";
  return fallback;
}

export function normalizeAvatarVoiceType(value, fallback = DEFAULT_AVATAR_VOICE) {
  if (typeof value !== "string" || !value.trim()) {
    return fallback;
  }
  const normalized = LEGACY_VOICE_MAP[value] || value;
  return SUPPORTED_VOICES.has(normalized) ? normalized : fallback;
}
