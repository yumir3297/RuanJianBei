/**
 * 数字人离散动作目录。
 *
 * 触发分为两层：
 * 1. stateTrigger：由 listening / thinking / speaking 等页面状态自动触发；
 * 2. explicit：由具体业务场景通过 action 字段触发，优先级高于自动动作。
 *
 * cooldownMs 用来防止连续回答时反复做同一个动作；priority 用来解决动作冲突。
 */
const KEYFRAME_ACTIONS = {
  lean_in: {
    label: "侧耳倾听",
    kind: "keyframes",
    durationMs: 3000,
    blendInMs: 350,
    blendOutMs: 400,
    priority: 30,
    cooldownMs: 6500,
    keyframes: [
      { t: 0, head_x: 0, head_z: 0 },
      { t: 0.25, head_x: -0.04, head_z: 0.1 },
      { t: 0.35, head_x: -0.05, head_z: 0.12 },
      { t: 0.45, head_x: -0.03, head_z: 0.08 },
      { t: 0.55, head_x: -0.05, head_z: 0.11 },
      { t: 0.65, head_x: -0.03, head_z: 0.09 },
      { t: 1, head_x: 0, head_z: 0 },
    ],
  },
  guide_narrate: {
    label: "导览讲解",
    kind: "keyframes",
    durationMs: 3000,
    blendInMs: 250,
    blendOutMs: 450,
    priority: 35,
    cooldownMs: 12000,
    keyframes: [
      { t: 0, rua_y: 0, rua_z: 0.35, rla_y: 0, rla_z: 0, rh_z: 0, head_y: 0 },
      { t: 0.35, rua_y: 0.4, rua_z: -0.2, rla_y: 0.2, rla_z: 0.05, rh_z: -0.1, head_y: 0.04 },
      { t: 0.55, rua_y: 0.3, rua_z: -0.15, rla_y: 0.22, rla_z: -0.08, rh_z: -0.08, head_y: 0.02 },
      { t: 0.7, rua_y: 0.32, rua_z: -0.18, rla_y: 0.2, rla_z: -0.12, rh_z: -0.1, head_y: -0.01 },
      { t: 1, rua_y: 0, rua_z: 0.35, rla_y: 0, rla_z: 0, rh_z: 0, head_y: 0 },
    ],
  },
  welcome_invite: {
    label: "侧身请进",
    kind: "keyframes",
    durationMs: 3200,
    blendInMs: 250,
    blendOutMs: 450,
    priority: 82,
    cooldownMs: 20000,
    keyframes: [
      { t: 0, head_y: 0, rua_y: 0, rua_z: 0.35, rla_y: 0, rla_z: 0, rh_z: 0, lua_z: -0.35, group_y: 0 },
      { t: 0.2, head_y: -0.05, rua_y: -0.13, rua_z: -0.1, rla_y: -0.08, rla_z: 0, rh_z: 0, lua_z: -0.42, group_y: -0.035 },
      { t: 0.55, head_y: -0.05, rua_y: -0.21, rua_z: -0.07, rla_y: -0.18, rla_z: 0, rh_z: -0.07, lua_z: -0.46, group_y: -0.035 },
      { t: 0.75, head_y: -0.05, rua_y: -0.21, rua_z: -0.07, rla_y: -0.18, rla_z: 0, rh_z: -0.07, lua_z: -0.46, group_y: -0.035 },
      { t: 1, head_y: 0, rua_y: 0, rua_z: 0.35, rla_y: 0, rla_z: 0, rh_z: 0, lua_z: -0.35, group_y: 0 },
    ],
  },
  departure_pose: {
    label: "准备出发",
    kind: "keyframes",
    durationMs: 3000,
    blendInMs: 300,
    blendOutMs: 500,
    priority: 85,
    cooldownMs: 10000,
    keyframes: [
      { t: 0, rua_y: 0, rua_z: 0.35, rla_x: 0, lua_y: 0, lua_z: -0.35, lla_x: 0, head_x: 0, head_y: 0 },
      { t: 0.25, rua_y: 0.6, rua_z: -0.3, rla_x: -0.5, lua_y: 0, lua_z: -0.55, lla_x: -0.5, head_x: -0.04, head_y: 0.03 },
      { t: 0.5, rua_y: 1, rua_z: -0.55, rla_x: -1.4, lua_y: 0, lua_z: -0.7, lla_x: -1, head_x: -0.06, head_y: 0.05 },
      { t: 0.65, rua_y: 1, rua_z: -0.55, rla_x: -1.4, lua_y: 0, lua_z: -0.7, lla_x: -1, head_x: -0.06, head_y: 0.05 },
      { t: 1, rua_y: 0, rua_z: 0.35, rla_x: 0, lua_y: 0, lua_z: -0.35, lla_x: 0, head_x: 0, head_y: 0 },
    ],
  },
};

const GLB_ACTIONS = {
  two_hand_wave: { label: "双手挥手欢迎", file: "双手挥手欢迎.glb", priority: 88, cooldownMs: 1200 },
  wave: { label: "热烈挥手欢迎", file: "热烈挥手欢迎.glb", durationMs: 1800, priority: 80, cooldownMs: 15000 },
  farewell: { label: "挥手告别", file: "挥手告别.glb", priority: 80, cooldownMs: 12000 },
  agree: { label: "点头同意", file: "同意.glb", priority: 70, cooldownMs: 5000 },
  disagree: { label: "摇头否定", file: "摇头摆手不.glb", priority: 72, cooldownMs: 6000 },
  point_back: { label: "指向身后", file: "指向身后.glb", priority: 74, cooldownMs: 7000 },
  think: { label: "思考", file: "思考.glb", priority: 25, cooldownMs: 7000 },
  encourage: { label: "握拳加油", file: "握拳加油.glb", priority: 76, cooldownMs: 8000 },
  praise: { label: "大拇指称赞", file: "站在大拇指你真棒.glb", priority: 78, cooldownMs: 8000 },
  applaud: { label: "热烈鼓掌", file: "站起来热烈鼓掌.glb", priority: 84, cooldownMs: 12000 },
  celebrate: { label: "庆祝", file: "庆祝.glb", priority: 86, cooldownMs: 15000 },
  look_around: { label: "抬手观察风景", file: "抬手挡光看（风景）.glb", priority: 75, cooldownMs: 9000 },
  // 自动状态动作使用独立别名，避免消耗拍照识景等显式业务动作的冷却时间。
  think_observe: {
    label: "思考时观察环境",
    file: "抬手挡光看（风景）.glb",
    durationMs: 5200,
    priority: 26,
    cooldownMs: 15000,
  },
  speaking_nod: {
    label: "讲解时轻点头",
    file: "同意.glb",
    durationMs: 2800,
    priority: 34,
    cooldownMs: 10000,
  },
  speaking_point: {
    label: "讲解时指引方向",
    file: "指向身后.glb",
    durationMs: 3000,
    priority: 36,
    cooldownMs: 12000,
  },
  speaking_disagree: {
    label: "讲解时提示否定",
    file: "摇头摆手不.glb",
    durationMs: 3600,
    priority: 36,
    cooldownMs: 12000,
  },
  speaking_observe: {
    label: "讲解时观察景点",
    file: "抬手挡光看（风景）.glb",
    durationMs: 5000,
    priority: 35,
    cooldownMs: 15000,
  },
};

export const AVATAR_ACTIONS = Object.freeze({
  ...Object.fromEntries(Object.entries(KEYFRAME_ACTIONS).map(([name, item]) => [name, Object.freeze({ name, ...item })])),
  ...Object.fromEntries(Object.entries(GLB_ACTIONS).map(([name, item]) => [name, Object.freeze({
    name,
    kind: "mixamo",
    blendInMs: 220,
    blendOutMs: 320,
    maxDurationMs: 6500,
    ...item,
  })])),
});

export const AVATAR_STATE_ACTIONS = Object.freeze({
  listening: Object.freeze({ action: "lean_in", delayMs: 120 }),
  thinking: Object.freeze({
    actions: Object.freeze([
      Object.freeze({ action: "think", weight: 70 }),
      Object.freeze({ action: "think_observe", weight: 30 }),
    ]),
    delayMs: 800,
  }),
});

const DIRECTION_SPEECH_PATTERN = /路线|方向|前方|后方|左侧|右侧|向左|向右|入口|出口|沿着|到达|前往|步行|乘坐|接驳/;
const NEGATIVE_SPEECH_PATTERN = /不能|不可以|禁止|不允许|无法|没有检索到|证据不足|暂不|请勿|不要|抱歉/;
const SCENIC_SPEECH_PATTERN = /景点|风景|景色|大佛|梵宫|坛城|花海|太湖|建筑|雕塑|广场|寺|湖|山/;

/**
 * 在句子开始时选择一次低频讲解手势。
 * 方向与否定语义优先；普通讲解大多数时候不触发离散动作，继续使用自然身体运动。
 */
export function selectSpeakingAction(text, randomValue = Math.random()) {
  const sentence = typeof text === "string" ? text.trim() : "";
  if (!sentence) return "";
  if (NEGATIVE_SPEECH_PATTERN.test(sentence)) return "speaking_disagree";
  if (DIRECTION_SPEECH_PATTERN.test(sentence)) return "speaking_point";
  if (SCENIC_SPEECH_PATTERN.test(sentence) && randomValue < 0.28) return "speaking_observe";
  if (randomValue < 0.2) return "speaking_nod";
  return "";
}

export const ACTION_BONE_MAP = Object.freeze({
  rua_x: "rightUpperArm", rua_y: "rightUpperArm", rua_z: "rightUpperArm",
  lua_x: "leftUpperArm", lua_y: "leftUpperArm", lua_z: "leftUpperArm",
  rla_x: "rightLowerArm", rla_y: "rightLowerArm", rla_z: "rightLowerArm",
  lla_x: "leftLowerArm", lla_y: "leftLowerArm", lla_z: "leftLowerArm",
  rh_x: "rightHand", rh_y: "rightHand", rh_z: "rightHand",
  lh_x: "leftHand", lh_y: "leftHand", lh_z: "leftHand",
  head_x: "head", head_y: "head", head_z: "head",
  spine_x: "spine", spine_y: "spine", spine_z: "spine",
  group_y: "__group_y",
});

export const MIXAMO_TO_VRM_BONES = Object.freeze({
  Spine: "spine", Spine1: "chest", Spine2: "upperChest",
  LeftArm: "leftUpperArm", LeftForeArm: "leftLowerArm", LeftHand: "leftHand",
  RightArm: "rightUpperArm", RightForeArm: "rightLowerArm", RightHand: "rightHand",
  Head: "head", Neck: "neck", LeftShoulder: "leftShoulder", RightShoulder: "rightShoulder",
  LeftHandThumb1: "leftThumbMetacarpal", LeftHandThumb2: "leftThumbProximal", LeftHandThumb3: "leftThumbDistal",
  LeftHandIndex1: "leftIndexProximal", LeftHandIndex2: "leftIndexIntermediate", LeftHandIndex3: "leftIndexDistal",
  LeftHandMiddle1: "leftMiddleProximal", LeftHandMiddle2: "leftMiddleIntermediate", LeftHandMiddle3: "leftMiddleDistal",
  LeftHandRing1: "leftRingProximal", LeftHandRing2: "leftRingIntermediate", LeftHandRing3: "leftRingDistal",
  LeftHandPinky1: "leftLittleProximal", LeftHandPinky2: "leftLittleIntermediate", LeftHandPinky3: "leftLittleDistal",
  RightHandThumb1: "rightThumbMetacarpal", RightHandThumb2: "rightThumbProximal", RightHandThumb3: "rightThumbDistal",
  RightHandIndex1: "rightIndexProximal", RightHandIndex2: "rightIndexIntermediate", RightHandIndex3: "rightIndexDistal",
  RightHandMiddle1: "rightMiddleProximal", RightHandMiddle2: "rightMiddleIntermediate", RightHandMiddle3: "rightMiddleDistal",
  RightHandRing1: "rightRingProximal", RightHandRing2: "rightRingIntermediate", RightHandRing3: "rightRingDistal",
  RightHandPinky1: "rightLittleProximal", RightHandPinky2: "rightLittleIntermediate", RightHandPinky3: "rightLittleDistal",
});

export function getAvatarAction(name) {
  return AVATAR_ACTIONS[name] || null;
}

export function getStateAction(state) {
  return AVATAR_STATE_ACTIONS[state] || null;
}
