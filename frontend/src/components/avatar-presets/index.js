import { buildMonk } from "./monk.js";
import { buildHanfu } from "./hanfu.js";
import { buildModern } from "./modern.js";

/** 三套预设配置表，供模型管理器与页面读取 */
export const AVATAR_PRESETS = {
  monk: {
    key: "monk",
    label: "明彻法师",
    description: "智慧庄严 · 佛教文化讲解",
    presetType: "monk",
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
  },
};

export const DEFAULT_PRESET_KEY = "hanfu";

const builders = { monk: buildMonk, hanfu: buildHanfu, modern: buildModern };

export function buildAvatarByPreset(preset) {
  const builder = builders[preset] || builders.monk;
  return builder();
}

export function getAvatarModelUrl(preset) {
  return AVATAR_PRESETS[preset]?.modelUrl || null;
}
