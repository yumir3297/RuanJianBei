import { buildMonk } from "./monk.js";
import { buildHanfu } from "./hanfu.js";
import { buildModern } from "./modern.js";

export const AVATAR_PRESETS = {
  monk: {
    key: "monk",
    label: "宁灵",
    description: "智慧庄严 · 佛教文化讲解",
    presetType: "monk",
    modelUrl: "/models/林二女.vrm",
  },
  hanfu: {
    key: "hanfu",
    label: "清岚",
    description: "古典优雅 · 文化叙事导览",
    presetType: "hanfu",
    modelUrl: "/models/hanfu.vrm",
  },
  modern: {
    key: "modern",
    label: "景行",
    description: "专业活力 · 现代智能导览",
    presetType: "modern",
    modelUrl: "/models/male-guide.vrm",
  },
};

export const DEFAULT_PRESET_KEY = "hanfu";

const DEFAULT_MOUTH_PROFILE = Object.freeze({
  maxOpen: 0.78,
  response: 15,
  deadZone: 0.05,
  openCurve: 0.9,
  expressionScale: Object.freeze({ aa: 0.92, ih: 0.72, ee: 0.58, oh: 0.8, ou: 0.64 }),
  materialTint: 0xfff5f6,
  shadeStrength: 0.84,
  normalStrength: 1.1,
  alphaCutoff: 0.38,
});

export const AVATAR_MOUTH_PROFILES = Object.freeze({
  monk: Object.freeze({
    ...DEFAULT_MOUTH_PROFILE,
    maxOpen: 0.76,
    expressionScale: Object.freeze({ aa: 0.88, ih: 0.7, ee: 0.56, oh: 0.76, ou: 0.62 }),
    materialTint: 0xfff3f5,
  }),
  hanfu: Object.freeze({
    ...DEFAULT_MOUTH_PROFILE,
    maxOpen: 0.74,
    expressionScale: Object.freeze({ aa: 0.86, ih: 0.7, ee: 0.58, oh: 0.76, ou: 0.64 }),
    materialTint: 0xfff1f4,
    shadeStrength: 0.8,
  }),
  modern: Object.freeze({
    ...DEFAULT_MOUTH_PROFILE,
    maxOpen: 0.8,
    expressionScale: Object.freeze({ aa: 0.94, ih: 0.74, ee: 0.56, oh: 0.82, ou: 0.62 }),
    materialTint: 0xfff7f5,
    shadeStrength: 0.88,
  }),
});

const builders = { monk: buildMonk, hanfu: buildHanfu, modern: buildModern };

export function buildAvatarByPreset(preset) {
  const builder = builders[preset] || builders.monk;
  return builder();
}

export function getAvatarModelUrl(preset) {
  return AVATAR_PRESETS[preset]?.modelUrl || null;
}

export function getAvatarMouthProfile(preset) {
  return AVATAR_MOUTH_PROFILES[preset] || DEFAULT_MOUTH_PROFILE;
}
