<template>
  <div
    class="three-wrapper"
    :data-avatar-preset="props.preset"
    :data-avatar-status="avatarStatus"
    :data-avatar-state="props.avatarState"
    :data-avatar-action="activeActionName"
  >
    <div v-if="loading" class="three-loading" role="status" aria-live="polite">数字人准备中...</div>
    <div v-if="error" class="three-error" role="alert">{{ error }}</div>
    <canvas ref="canvasRef" class="three-canvas" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";

import {
  buildAvatarByPreset,
  getAvatarModelUrl,
  getAvatarMouthProfile,
} from "./avatar-presets/index.js";
import { getAvatarMotionProfile, getAvatarStateMotion } from "./avatar-motion.js";
import {
  ACTION_BONE_MAP,
  MIXAMO_TO_VRM_BONES,
  getAvatarAction,
  getStateAction,
} from "./avatar-actions.js";
import {
  getAvatarActionExpressionTargets,
  getAvatarExpressionProfile,
  getAvatarExpressionTargets,
} from "./avatar-expression.js";
import { useAudioPlayer } from "../composables/useAudioPlayer";

const props = defineProps({
  preset: { type: String, default: "monk" },
  emotion: { type: String, default: "neutral" },
  isSpeaking: { type: Boolean, default: false },
  visemeTimeline: { type: Array, default: null },
  speechProgress: { type: Number, default: 0 },
  speechElapsedMs: { type: Number, default: 0 },
  speechDurationMs: { type: Number, default: 0 },
  speechSyncActive: { type: Boolean, default: false },
  waving: { type: Boolean, default: false },
  gesture: { type: String, default: "" },
  gestureKey: { type: Number, default: 0 },
  action: { type: String, default: "" },
  actionKey: { type: Number, default: 0 },
  cameraOffsetY: { type: Number, default: 0 },
  avatarState: { type: String, default: "idle" },
});
const emit = defineEmits(["loaded", "error", "action-start", "action-end", "action-error"]);

const audioPlayer = useAudioPlayer();

const canvasRef = ref(null);
const loading = ref(true);
const error = ref("");
const avatarStatus = ref("initializing");
const activeActionName = ref("");

let renderer, scene, camera;
let avatarParts = null;
let particles;
let lookAtTarget;
let animId;
let timer = new THREE.Timer();
let blinkTimer = 0;
let nextBlink = 2;
let blinkPhase = -1;
let avatarLoadToken = 0;
let resizeObserver;
let intersectionObserver;
let idleLoadHandle = null;
let pageVisible = true;
let avatarVisible = true;
let gestureWaveUntil = 0;
let activeAvatarAction = null;
let pendingAvatarActionTimer = null;
let pendingAvatarAction = null;
let avatarActionRequestToken = 0;
let queuedExplicitAction = "";
let naturalMotionResumeTime = 0;
const avatarActionCooldowns = new Map();
const avatarActionClipPromises = new Map();
const lastStateAvatarActions = new Map();

const MAX_PIXEL_RATIO = 1.5;

const VRM_EMOTION_EXPRESSIONS = [
  "happy",
  "angry",
  "sad",
  "relaxed",
  "surprised",
  "neutral",
];


function normalizeLoadedAvatar(modelRoot) {
  const initialBox = new THREE.Box3().setFromObject(modelRoot);
  if (initialBox.isEmpty()) return;

  const size = new THREE.Vector3();
  initialBox.getSize(size);
  const safeHeight = Math.max(size.y, 0.001);
  const targetHeight = 3.9;
  const scale = targetHeight / safeHeight;
  modelRoot.scale.setScalar(scale);

  const scaledBox = new THREE.Box3().setFromObject(modelRoot);
  const center = new THREE.Vector3();
  scaledBox.getCenter(center);

  modelRoot.position.x -= center.x;
  modelRoot.position.z -= center.z;
  modelRoot.position.y += -scaledBox.min.y - 1.9;
}

function applyNaturalVrmPose(vrm) {
  const humanoid = vrm.humanoid;
  if (!humanoid) return;

  const leftUpperArm = humanoid.getNormalizedBoneNode("leftUpperArm");
  const rightUpperArm = humanoid.getNormalizedBoneNode("rightUpperArm");
  const leftLowerArm = humanoid.getNormalizedBoneNode("leftLowerArm");
  const rightLowerArm = humanoid.getNormalizedBoneNode("rightLowerArm");

  if (leftUpperArm) leftUpperArm.rotation.z = -1.18;
  if (rightUpperArm) rightUpperArm.rotation.z = 1.18;
  if (leftLowerArm) leftLowerArm.rotation.y = -0.08;
  if (rightLowerArm) rightLowerArm.rotation.y = 0.08;
}

function createVrmAvatarParts(vrm) {
  const group = new THREE.Group();
  const head = vrm.humanoid?.getNormalizedBoneNode("head") || null;

  normalizeLoadedAvatar(vrm.scene);
  applyNaturalVrmPose(vrm);
  group.add(vrm.scene);
  const motionBones = {
    rightUpperArm: vrm.humanoid?.getNormalizedBoneNode("rightUpperArm") || null,
    rightLowerArm: vrm.humanoid?.getNormalizedBoneNode("rightLowerArm") || null,
    rightHand: vrm.humanoid?.getNormalizedBoneNode("rightHand") || null,
  };

  if (vrm.lookAt && lookAtTarget) {
    vrm.lookAt.target = lookAtTarget;
  }

  return {
    group,
    head,
    motionBones,
    __avatarKind: "vrm",
    __vrm: vrm,
  };
}

function buildFallbackAvatar(preset) {
  const parts = buildAvatarByPreset(preset);
  parts.__avatarKind = "procedural";
  return parts;
}

function setVrmExpression(parts, name, value) {
  parts?.__vrm?.expressionManager?.setValue(name, THREE.MathUtils.clamp(value, 0, 1));
}

function smoothstep(min, max, value) {
  const t = THREE.MathUtils.clamp((value - min) / (max - min || 1), 0, 1);
  return t * t * (3 - 2 * t);
}

function enhanceVrmMouthMaterial(vrm, preset) {
  const profile = getAvatarMouthProfile(preset);
  const tint = new THREE.Color(profile.materialTint);
  const maxAnisotropy = renderer?.capabilities?.getMaxAnisotropy?.() || 1;

  vrm.scene.traverse((node) => {
    if (!node.isMesh) return;
    const materials = Array.isArray(node.material) ? node.material : [node.material];

    materials.filter(Boolean).forEach((material) => {
      if (!/face.?mouth|mouth|lip/i.test(material.name || "")) return;
      if (material.userData.avatarMouthEnhanced) return;

      material.userData.avatarMouthEnhanced = true;
      material.color?.multiply(tint);
      material.shadeColorFactor?.multiplyScalar(profile.shadeStrength);
      material.normalScale?.multiplyScalar(profile.normalStrength);
      material.alphaTest = Math.min(material.alphaTest || 0.5, profile.alphaCutoff);

      [material.map, material.normalMap, material.emissiveMap]
        .filter(Boolean)
        .forEach((texture) => {
          texture.anisotropy = Math.min(8, maxAnisotropy);
          texture.needsUpdate = true;
        });

      material.needsUpdate = true;
    });
  });
}

function applyVrmMouth(parts, open, form, deltaSeconds) {
  const profile = getAvatarMouthProfile(props.preset);
  const sourceOpen = THREE.MathUtils.clamp(
    (open - profile.deadZone) / (1 - profile.deadZone),
    0,
    1,
  );
  const targetOpen = Math.pow(sourceOpen, profile.openCurve) * profile.maxOpen;
  const targetForm = THREE.MathUtils.clamp(form, 0, 1);
  const response = 1 - Math.exp(-profile.response * Math.min(deltaSeconds, 0.1));
  const state = parts.__mouthState || { open: 0, sourceOpen: 0, form: targetForm };

  state.open = THREE.MathUtils.lerp(state.open, targetOpen, response);
  state.sourceOpen = THREE.MathUtils.lerp(state.sourceOpen, sourceOpen, response);
  state.form = THREE.MathUtils.lerp(state.form, targetForm, response);
  parts.__mouthState = state;

  // Separate Chinese vowels by lip roundness, then select a dominant aperture shape.
  const rounded = smoothstep(0.42, 0.62, state.form);
  const wide = 1 - rounded;
  const aa = smoothstep(0.45, 0.72, state.sourceOpen);
  const ee = 1 - smoothstep(0.16, 0.32, state.sourceOpen);
  const ih = Math.max(0, 1 - aa - ee);
  const oh = smoothstep(0.32, 0.62, state.sourceOpen);
  const ou = 1 - oh;
  const scale = profile.expressionScale;

  setVrmExpression(parts, "aa", state.open * wide * aa * scale.aa);
  setVrmExpression(parts, "ih", state.open * wide * ih * scale.ih);
  setVrmExpression(parts, "ee", state.open * wide * ee * scale.ee);
  setVrmExpression(parts, "oh", state.open * rounded * oh * scale.oh);
  setVrmExpression(parts, "ou", state.open * rounded * ou * scale.ou);
}

function setBlinkState(parts, value) {
  setVrmExpression(parts, "blink", value);
}

async function tryUpgradeAvatarToVrm(preset) {
  const currentToken = ++avatarLoadToken;
  const vrmUrl = getAvatarModelUrl(preset);
  if (!vrmUrl) {
    avatarStatus.value = "fallback";
    loading.value = false;
    return false;
  }

  avatarStatus.value = "loading-vrm";
  loading.value = true;
  error.value = "";

  try {
    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));
    const gltf = await loader.loadAsync(vrmUrl);
    const vrm = gltf.userData.vrm;
    if (!vrm) {
      throw new Error("文件中没有可用的 VRM 数据");
    }

    VRMUtils.rotateVRM0(vrm);
    VRMUtils.removeUnnecessaryVertices(vrm.scene);
    enhanceVrmMouthMaterial(vrm, preset);

    if (!scene || currentToken !== avatarLoadToken) {
      disposeObject(vrm.scene);
      return false;
    }

    const vrmParts = createVrmAvatarParts(vrm);
    cacheAvatarDefaults(vrmParts);

    if (avatarParts?.group) {
      scene.remove(avatarParts.group);
      disposeAvatarParts(avatarParts);
    }

    avatarParts = vrmParts;
    resetNaturalMotion();
    scene.add(avatarParts.group);
    vrm.scene.updateMatrixWorld(true);
    vrm.springBoneManager?.reset();
    updateEmotionExpressions(avatarParts, 1);
    vrm.update(0);
    avatarStatus.value = "vrm";
    loading.value = false;
    const queuedAction = queuedExplicitAction;
    queuedExplicitAction = "";
    if (queuedAction) requestAvatarAction(queuedAction, { explicit: true });
    else scheduleStateAvatarAction();
    emit("loaded", {
      preset,
      url: vrmUrl,
      kind: "vrm",
      expressions: Object.keys(vrm.expressionManager?.expressionMap || {}),
    });
    return true;
  } catch (loadError) {
    if (currentToken !== avatarLoadToken) return false;
    avatarStatus.value = "fallback";
    loading.value = false;
    error.value = "VRM 模型加载失败，已显示备用形象";
    emit("error", loadError);
    return false;
  }
}

function cancelScheduledVrmUpgrade() {
  if (idleLoadHandle === null) return;
  if ("cancelIdleCallback" in window) {
    window.cancelIdleCallback(idleLoadHandle);
  } else {
    window.clearTimeout(idleLoadHandle);
  }
  idleLoadHandle = null;
}

function scheduleVrmUpgrade(preset) {
  cancelScheduledVrmUpgrade();
  const load = () => {
    idleLoadHandle = null;
    void tryUpgradeAvatarToVrm(preset);
  };

  if ("requestIdleCallback" in window) {
    idleLoadHandle = window.requestIdleCallback(load, { timeout: 800 });
  } else {
    idleLoadHandle = window.setTimeout(load, 180);
  }
}

function disposeObject(root) {
  root?.traverse((node) => {
    if (!node.isMesh) return;
    node.geometry?.dispose?.();
    const materials = Array.isArray(node.material) ? node.material : [node.material];
    materials.filter(Boolean).forEach((material) => {
      Object.values(material).forEach((value) => {
        if (value?.isTexture) value.dispose();
      });
      material.dispose?.();
    });
  });
}

function disposeAvatarParts(parts) {
  disposeObject(parts?.group);
}

function cachePartTransform(part) {
  if (!part) return;
  if (!part.userData.basePosition) part.userData.basePosition = part.position.clone();
  if (!part.userData.baseRotation) part.userData.baseRotation = part.rotation.clone();
  if (!part.userData.baseScale) part.userData.baseScale = part.scale.clone();
}

function cacheAvatarDefaults(parts) {
  if (!parts) return;
  [
    parts.head,
    parts.mouth,
    parts.leftEye,
    parts.rightEye,
    parts.leftPupil,
    parts.rightPupil,
    parts.leftBrow,
    parts.rightBrow,
    ...Object.values(parts.motionBones || {}),
  ].forEach(cachePartTransform);
}

function interpolateActionKeys(keyframes, progress) {
  if (!keyframes?.length) return {};
  if (progress <= keyframes[0].t) return { ...keyframes[0] };
  for (let index = keyframes.length - 1; index >= 0; index -= 1) {
    if (progress < keyframes[index].t) continue;
    if (index === keyframes.length - 1) return { ...keyframes[index] };
    const previous = keyframes[index];
    const next = keyframes[index + 1];
    const local = THREE.MathUtils.clamp(
      (progress - previous.t) / (next.t - previous.t || 1),
      0,
      1,
    );
    const eased = local < 0.5
      ? 2 * local * local
      : 1 - Math.pow(-2 * local + 2, 2) / 2;
    const values = {};
    Object.keys(previous).forEach((key) => {
      if (key === "t") return;
      values[key] = THREE.MathUtils.lerp(previous[key] || 0, next[key] || 0, eased);
    });
    return values;
  }
  return { ...keyframes[0] };
}

function normalizeMixamoBoneName(trackName) {
  const objectName = String(trackName || "")
    .replace(/^.*\[/, "")
    .replace(/\].*$/, "")
    .split(/[|:/]/)
    .pop();
  return objectName?.replace(/^mixamorig/i, "") || "";
}

function getActionBone(parts, name) {
  return parts?.__vrm?.humanoid?.getNormalizedBoneNode(name) || null;
}

async function loadAvatarActionClip(definition) {
  if (avatarActionClipPromises.has(definition.name)) {
    return avatarActionClipPromises.get(definition.name);
  }

  const promise = new GLTFLoader()
    .loadAsync(encodeURI(`/motions/${definition.file}`))
    .then((gltf) => {
      const clip = gltf.animations?.[0];
      if (!clip) throw new Error(`动作文件没有动画轨道：${definition.file}`);
      disposeObject(gltf.scene);
      return clip;
    })
    .catch((loadError) => {
      avatarActionClipPromises.delete(definition.name);
      throw loadError;
    });

  avatarActionClipPromises.set(definition.name, promise);
  return promise;
}

function createMixamoSamples(parts, clip) {
  const samples = [];
  clip.tracks.forEach((track) => {
    const trackParts = track.name.split(".");
    const property = trackParts.pop();
    const mixamoName = normalizeMixamoBoneName(trackParts.join("."));
    const vrmName = MIXAMO_TO_VRM_BONES[mixamoName];
    const bone = vrmName ? getActionBone(parts, vrmName) : null;
    if (!bone) return;

    if (property === "quaternion") {
      samples.push({ bone, times: track.times, values: track.values });
      return;
    }
    if (property !== "rotation") return;

    const quaternionValues = new Float32Array(track.times.length * 4);
    const euler = new THREE.Euler();
    const quaternion = new THREE.Quaternion();
    for (let index = 0; index < track.times.length; index += 1) {
      const values = [
        track.values[index * 3],
        track.values[index * 3 + 1],
        track.values[index * 3 + 2],
      ];
      const usesDegrees = values.some((value) => Math.abs(value) > Math.PI * 2);
      euler.set(...values.map((value) => usesDegrees ? THREE.MathUtils.degToRad(value) : value));
      quaternion.setFromEuler(euler);
      quaternion.toArray(quaternionValues, index * 4);
    }
    samples.push({ bone, times: track.times, values: quaternionValues });
  });
  return samples;
}

function restoreAvatarActionPose(action = activeAvatarAction) {
  if (!action) return;
  action.restBones.forEach((rest, bone) => bone.quaternion.copy(rest.quaternion));
  if (action.parts?.group) action.parts.group.rotation.y = action.groupRotationY;
}

function stopAvatarAction(reason = "completed") {
  const action = activeAvatarAction;
  if (!action) return;
  restoreAvatarActionPose(action);
  activeAvatarAction = null;
  activeActionName.value = "";
  naturalMotionResumeTime = performance.now() + 350;
  emit("action-end", { action: action.definition.name, reason });
  // 高优先级动作可能覆盖了状态动作；自然结束后按最新状态重新评估一次。
  if (reason === "completed") scheduleStateAvatarAction();
}

function clearPendingAvatarAction() {
  avatarActionRequestToken += 1;
  if (pendingAvatarActionTimer !== null) {
    window.clearTimeout(pendingAvatarActionTimer);
    pendingAvatarActionTimer = null;
  }
  pendingAvatarAction = null;
}

function cancelAvatarActions({ clearQueue = true } = {}) {
  clearPendingAvatarAction();
  stopAvatarAction("cancelled");
  if (clearQueue) queuedExplicitAction = "";
}

function startAvatarAction(definition, clip = null, stateKey = "") {
  const parts = avatarParts;
  if (parts?.__avatarKind !== "vrm" || !parts.__vrm?.humanoid) return false;

  let samples = [];
  const actionBones = new Set();
  if (definition.kind === "mixamo") {
    samples = createMixamoSamples(parts, clip);
    samples.forEach((sample) => actionBones.add(sample.bone));
    if (!samples.length) throw new Error(`动作没有匹配当前 VRM 的骨骼：${definition.file}`);
  } else {
    definition.keyframes.forEach((frame) => {
      Object.keys(frame).forEach((key) => {
        const boneName = ACTION_BONE_MAP[key];
        if (!boneName || boneName === "__group_y") return;
        const bone = getActionBone(parts, boneName);
        if (bone) actionBones.add(bone);
      });
    });
  }

  if (activeAvatarAction) stopAvatarAction("interrupted");
  const restBones = new Map();
  actionBones.forEach((bone) => {
    restBones.set(bone, {
      quaternion: bone.quaternion.clone(),
      euler: bone.rotation.clone(),
    });
  });

  const clipDurationMs = clip ? clip.duration * 1000 : definition.durationMs;
  const requestedDurationMs = definition.durationMs || clipDurationMs;
  const durationMs = definition.maxDurationMs
    ? Math.min(requestedDurationMs, definition.maxDurationMs)
    : requestedDurationMs;
  activeAvatarAction = {
    definition,
    parts,
    samples,
    restBones,
    groupRotationY: parts.group.rotation.y,
    startedAt: performance.now(),
    durationMs: Math.max(durationMs, 500),
    clipDurationSeconds: clip?.duration || 0,
    stateKey,
  };
  activeActionName.value = definition.name;
  avatarActionCooldowns.set(definition.name, performance.now());
  emit("action-start", { action: definition.name, label: definition.label });
  return true;
}

function getAvatarActionBlend(action, elapsedMs) {
  const remainingMs = action.durationMs - elapsedMs;
  const blendIn = action.definition.blendInMs || 200;
  const blendOut = action.definition.blendOutMs || 300;
  const inWeight = smoothstep(0, blendIn, elapsedMs);
  const outWeight = smoothstep(0, blendOut, remainingMs);
  return Math.min(inWeight, outWeight);
}

function applyKeyframeAvatarAction(action, elapsedMs, blend) {
  const progress = THREE.MathUtils.clamp(elapsedMs / action.durationMs, 0, 1);
  const values = interpolateActionKeys(action.definition.keyframes, progress);
  const rotations = new Map();

  Object.entries(values).forEach(([key, value]) => {
    const boneName = ACTION_BONE_MAP[key];
    if (!boneName) return;
    if (boneName === "__group_y") {
      action.parts.group.rotation.y = THREE.MathUtils.lerp(action.groupRotationY, value, blend);
      return;
    }
    const axis = key.split("_")[1];
    const bone = getActionBone(action.parts, boneName);
    const rest = action.restBones.get(bone);
    if (!bone || !rest || !axis) return;
    if (!rotations.has(bone)) rotations.set(bone, rest.euler.clone());
    rotations.get(bone)[axis] = value;
  });

  const targetQuaternion = new THREE.Quaternion();
  rotations.forEach((targetEuler, bone) => {
    const rest = action.restBones.get(bone);
    targetQuaternion.setFromEuler(targetEuler);
    bone.quaternion.slerpQuaternions(rest.quaternion, targetQuaternion, blend);
  });
}

function findTrackFrame(times, timeSeconds) {
  let low = 0;
  let high = times.length - 1;
  while (low < high) {
    const middle = (low + high + 1) >>> 1;
    if (times[middle] <= timeSeconds) low = middle;
    else high = middle - 1;
  }
  return low;
}

function applyMixamoAvatarAction(action, elapsedMs, blend) {
  // 将源动画完整重映射到配置时长：短动作可放慢，过长动作可压缩但不会被截断。
  const timeSeconds = THREE.MathUtils.clamp(
    (elapsedMs / action.durationMs) * action.clipDurationSeconds,
    0,
    action.clipDurationSeconds,
  );
  const fromQuaternion = new THREE.Quaternion();
  const toQuaternion = new THREE.Quaternion();
  const targetQuaternion = new THREE.Quaternion();

  action.samples.forEach((sample) => {
    const frame = findTrackFrame(sample.times, timeSeconds);
    const nextFrame = Math.min(frame + 1, sample.times.length - 1);
    fromQuaternion.fromArray(sample.values, frame * 4).normalize();
    toQuaternion.fromArray(sample.values, nextFrame * 4).normalize();
    const segmentDuration = sample.times[nextFrame] - sample.times[frame];
    const local = frame === nextFrame
      ? 0
      : THREE.MathUtils.clamp((timeSeconds - sample.times[frame]) / (segmentDuration || 1), 0, 1);
    targetQuaternion.slerpQuaternions(fromQuaternion, toQuaternion, local);
    sample.bone.quaternion.slerpQuaternions(
      action.restBones.get(sample.bone).quaternion,
      targetQuaternion,
      blend,
    );
  });
}

function updateActiveAvatarAction(nowMs) {
  const action = activeAvatarAction;
  if (!action) return false;
  if (action.parts !== avatarParts) {
    stopAvatarAction("avatar-changed");
    return false;
  }

  const elapsedMs = nowMs - action.startedAt;
  if (elapsedMs >= action.durationMs) {
    stopAvatarAction("completed");
    return false;
  }

  const blend = getAvatarActionBlend(action, elapsedMs);
  if (action.definition.kind === "mixamo") {
    applyMixamoAvatarAction(action, elapsedMs, blend);
  } else {
    applyKeyframeAvatarAction(action, elapsedMs, blend);
  }
  return true;
}

async function executeAvatarActionRequest(request) {
  if (request.token !== avatarActionRequestToken) return;
  pendingAvatarActionTimer = null;
  if (request.expectedState && resolveMotionState() !== request.expectedState) {
    pendingAvatarAction = null;
    return;
  }
  if (avatarParts?.__avatarKind !== "vrm") {
    if (request.explicit) queuedExplicitAction = request.definition.name;
    pendingAvatarAction = null;
    return;
  }

  const lastStartedAt = avatarActionCooldowns.get(request.definition.name);
  if (lastStartedAt !== undefined && performance.now() - lastStartedAt < request.definition.cooldownMs) {
    pendingAvatarAction = null;
    return;
  }
  if (activeAvatarAction && request.definition.priority <= activeAvatarAction.definition.priority) {
    pendingAvatarAction = null;
    return;
  }

  try {
    const clip = request.definition.kind === "mixamo"
      ? await loadAvatarActionClip(request.definition)
      : null;
    if (request.token !== avatarActionRequestToken) return;
    if (request.expectedState && resolveMotionState() !== request.expectedState) return;
    if (activeAvatarAction && request.definition.priority <= activeAvatarAction.definition.priority) return;
    const started = startAvatarAction(request.definition, clip, request.stateKey);
    if (started && request.stateKey) {
      lastStateAvatarActions.set(request.stateKey, request.definition.name);
    }
  } catch (actionError) {
    console.warn(`[avatar-action] ${request.definition.name} 加载或播放失败`, actionError);
    emit("action-error", { action: request.definition.name, error: actionError });
  } finally {
    if (pendingAvatarAction?.token === request.token) pendingAvatarAction = null;
  }
}

function requestAvatarAction(name, options = {}) {
  const definition = getAvatarAction(name);
  if (!definition) {
    console.warn(`[avatar-action] 未注册的动作：${name}`);
    return false;
  }

  const explicit = Boolean(options.explicit);
  if (!explicit && pendingAvatarAction?.explicit) return false;
  if (activeAvatarAction && definition.priority <= activeAvatarAction.definition.priority) return false;
  clearPendingAvatarAction();
  const request = {
    definition,
    explicit,
    expectedState: options.expectedState || "",
    stateKey: options.stateKey || "",
    token: avatarActionRequestToken,
  };
  pendingAvatarAction = request;
  const delayMs = Math.max(options.delayMs || 0, 0);
  if (delayMs > 0) {
    pendingAvatarActionTimer = window.setTimeout(() => {
      void executeAvatarActionRequest(request);
    }, delayMs);
  } else {
    void executeAvatarActionRequest(request);
  }
  return true;
}

function scheduleStateAvatarAction(state = resolveMotionState()) {
  if (pendingAvatarAction?.explicit) return;
  if (activeAvatarAction?.stateKey && activeAvatarAction.stateKey !== state) {
    stopAvatarAction("state-changed");
  }
  const trigger = getStateAction(state);
  if (!trigger) {
    if (pendingAvatarAction && !pendingAvatarAction.explicit) clearPendingAvatarAction();
    return;
  }
  const action = selectStateAvatarAction(state, trigger);
  if (!action) return;
  requestAvatarAction(action, {
    delayMs: trigger.delayMs,
    expectedState: state,
    stateKey: state,
  });
}

function selectStateAvatarAction(state, trigger) {
  if (trigger.action) return trigger.action;
  if (!Array.isArray(trigger.actions) || !trigger.actions.length) return "";

  const now = performance.now();
  const lastAction = lastStateAvatarActions.get(state);
  let candidates = trigger.actions.filter((candidate) => {
    const definition = getAvatarAction(candidate.action);
    if (!definition) return false;
    const lastStartedAt = avatarActionCooldowns.get(definition.name);
    return lastStartedAt === undefined || now - lastStartedAt >= definition.cooldownMs;
  });
  if (!candidates.length) return "";

  // 观察动作表现较强，不允许连续两次出现；普通思考动作可以连续，才能维持 70/30 权重。
  if (lastAction === "think_observe") {
    const alternatives = candidates.filter((candidate) => candidate.action !== lastAction);
    if (alternatives.length) candidates = alternatives;
  }

  const totalWeight = candidates.reduce((total, candidate) => total + Math.max(candidate.weight || 0, 0), 0);
  if (totalWeight <= 0) return candidates[0].action;
  let cursor = Math.random() * totalWeight;
  for (const candidate of candidates) {
    cursor -= Math.max(candidate.weight || 0, 0);
    if (cursor <= 0) return candidate.action;
  }
  return candidates[candidates.length - 1].action;
}

function buildScene() {
  scene = new THREE.Scene();
  scene.background = null;
  scene.fog = new THREE.FogExp2(0x0f172a, 0.00015);

  // Lighting
  scene.add(new THREE.AmbientLight(0x404060, 0.6));
  const key = new THREE.DirectionalLight(0xffeedd, 2.0);
  key.position.set(3, 2, 5);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x8899cc, 0.7);
  fill.position.set(-2, 0.5, 2);
  scene.add(fill);
  const rim = new THREE.PointLight(0xff9966, 1.5, 8);
  rim.position.set(0, 2.5, -2);
  scene.add(rim);

  lookAtTarget = new THREE.Object3D();
  lookAtTarget.position.set(0, 0.9, 5.5);
  scene.add(lookAtTarget);

  // Build avatar by preset
  avatarParts = buildFallbackAvatar(props.preset);
  cacheAvatarDefaults(avatarParts);
  resetNaturalMotion();
  scene.add(avatarParts.group);
  scheduleVrmUpgrade(props.preset);

  // Particles
  const particleCount = 100;
  const particleGeo = new THREE.BufferGeometry();
  const positions = new Float32Array(particleCount * 3);
  const colors = new Float32Array(particleCount * 3);
  for (let i = 0; i < particleCount; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 5;
    positions[i * 3 + 1] = Math.random() * 4 - 0.5;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 4;
    colors[i * 3] = 0.2 + Math.random() * 0.3;
    colors[i * 3 + 1] = 0.4 + Math.random() * 0.4;
    colors[i * 3 + 2] = 0.5 + Math.random() * 0.5;
  }
  particleGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  particleGeo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  const particleMat = new THREE.PointsMaterial({
    size: 0.025,
    vertexColors: true,
    transparent: true,
    opacity: 0.6,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  particles = new THREE.Points(particleGeo, particleMat);
  scene.add(particles);
}

function blendTimelineWithAudio(timelineOpen, form, audioEnergy, analysisActive) {
  if (!analysisActive) return { open: timelineOpen, form };
  if (audioEnergy <= 0.012) return { open: 0, form };

  return {
    open: THREE.MathUtils.clamp(audioEnergy * 0.72 + timelineOpen * 0.28, 0, 1),
    form,
  };
}

function getMouthState() {
  const audioEnergy = THREE.MathUtils.clamp(audioPlayer.mouthEnergy?.value || 0, 0, 1);
  const analysisActive = Boolean(audioPlayer.mouthAnalysisActive?.value);

  if (!props.isSpeaking || !props.speechSyncActive || !props.visemeTimeline?.length) {
    if (!props.isSpeaking) return { open: 0, form: 0 };
    if (analysisActive) {
      return {
        open: audioEnergy,
        form: 0.12 + (Math.sin(performance.now() * 0.007) + 1) * 0.18,
      };
    }

    const previewPulse = props.isSpeaking
      ? 0.18 + (Math.sin(performance.now() * 0.013) + 1) * 0.16
      : 0;
    return {
      open: previewPulse,
      form: props.isSpeaking ? (Math.sin(performance.now() * 0.007) + 1) * 0.25 : 0,
    };
  }

  const timeline = props.visemeTimeline;
  const totalDuration = timeline[timeline.length - 1].end;
  const playbackDuration = props.speechDurationMs > 0
    ? props.speechDurationMs
    : totalDuration;
  const playbackElapsed = props.speechElapsedMs > 0
    ? props.speechElapsedMs
    : props.speechProgress * playbackDuration;
  const elapsedMs = THREE.MathUtils.clamp(
    (playbackElapsed / playbackDuration) * totalDuration,
    0,
    totalDuration,
  );

  let lo = 0;
  let hi = timeline.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >>> 1;
    if (timeline[mid].start <= elapsedMs) lo = mid;
    else hi = mid - 1;
  }

  const frame = timeline[lo];
  const next = timeline[lo + 1];
  if (elapsedMs >= frame.start && elapsedMs <= frame.end) {
    const t = (elapsedMs - frame.start) / (frame.end - frame.start || 1);
    const eased = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    const open = (frame.value || 0) + ((next?.value || frame.value || 0) - (frame.value || 0)) * eased;
    const form = (frame.form || 0) + ((next?.form || frame.form || 0) - (frame.form || 0)) * eased;
    return blendTimelineWithAudio(open, form, audioEnergy, analysisActive);
  }

  return blendTimelineWithAudio(
    frame.value || 0,
    frame.form || 0,
    audioEnergy,
    analysisActive,
  );
}

function resolveExpressionState() {
  const explicitEmotions = ["happy", "apology", "angry", "sad", "relaxed", "surprised"];
  if (explicitEmotions.includes(props.emotion)) return props.emotion;
  return resolveMotionState();
}

function getCompatibleVrmExpressionWeight(parts, name, value) {
  const expression = parts.__vrm?.expressionManager?.getExpression?.(name);
  if (!expression || value <= 0) return value;

  // A body gesture must not freeze natural blinking or block live lip-sync.
  if (expression.overrideBlink === "block") return 0;
  let safeValue = expression.overrideBlink === "blend" ? Math.min(value, 0.55) : value;
  if (props.isSpeaking && expression.overrideMouth === "block") return 0;
  if (props.isSpeaking && expression.overrideMouth === "blend") {
    safeValue = Math.min(safeValue, 0.32);
  }
  return safeValue;
}

function updateEmotionExpressions(parts, deltaSeconds) {
  if (!parts) return;
  cacheAvatarDefaults(parts);

  const expressionState = resolveExpressionState();
  const targets = getAvatarExpressionTargets(expressionState);
  const profile = getAvatarExpressionProfile(props.preset);
  const speakingScale = props.isSpeaking ? profile.speakingScale : 1;
  const actionElapsedMs = activeAvatarAction
    ? performance.now() - activeAvatarAction.startedAt
    : 0;
  const actionProgress = activeAvatarAction
    ? THREE.MathUtils.clamp(actionElapsedMs / activeAvatarAction.durationMs, 0, 1)
    : 0;
  const actionTargets = activeAvatarAction
    ? getAvatarActionExpressionTargets(activeAvatarAction.definition.name, actionProgress)
    : null;
  const actionInfluence = actionTargets?.influence || 0;
  const response = actionTargets ? profile.actionResponse : profile.transitionSpeed;
  const state = parts.__expressionState || Object.fromEntries(
    VRM_EMOTION_EXPRESSIONS.map((name) => [name, 0]),
  );

  VRM_EMOTION_EXPRESSIONS.forEach((name) => {
    const stateTarget = (targets[name] || 0) * profile.expressionScale * speakingScale;
    const actionTarget = (actionTargets?.[name] || 0) * profile.actionScale;
    const target = THREE.MathUtils.lerp(stateTarget, actionTarget, actionInfluence);
    state[name] = dampValue(state[name] || 0, target, response, deltaSeconds);
    if (parts.__avatarKind === "vrm") {
      setVrmExpression(parts, name, getCompatibleVrmExpressionWeight(parts, name, state[name]));
    }
  });
  parts.__expressionState = state;

  const head = parts.head;
  const headBase = head?.userData.baseRotation;
  if (head && headBase && !activeAvatarAction?.restBones?.has(head)) {
    const targetPitch = headBase.x + (targets.headPitch || 0) * profile.expressionScale;
    head.rotation.x = dampValue(head.rotation.x, targetPitch, profile.headResponse, deltaSeconds);
  }

  if (parts.__avatarKind === "vrm") return;

  const happy = THREE.MathUtils.clamp(state.happy / 0.52, 0, 1);
  const sad = THREE.MathUtils.clamp((state.sad + state.angry * 0.35) / 0.42, 0, 1);
  const surprised = THREE.MathUtils.clamp(state.surprised / 0.48, 0, 1);
  const { mouth, leftPupil, rightPupil, leftBrow, rightBrow } = parts;
  const mouthBase = mouth?.userData.basePosition;
  const leftPupilBase = leftPupil?.userData.baseScale;
  const rightPupilBase = rightPupil?.userData.baseScale;
  const leftBrowBase = leftBrow?.userData.basePosition;
  const rightBrowBase = rightBrow?.userData.basePosition;
  const leftBrowRotation = leftBrow?.userData.baseRotation;
  const rightBrowRotation = rightBrow?.userData.baseRotation;

  if (mouth && mouthBase) mouth.position.y = mouthBase.y + happy * 0.025 - sad * 0.018;
  if (leftPupil && leftPupilBase) {
    leftPupil.scale.y = leftPupilBase.y * (1 - happy * 0.08 + surprised * 0.08);
  }
  if (rightPupil && rightPupilBase) {
    rightPupil.scale.y = rightPupilBase.y * (1 - happy * 0.08 + surprised * 0.08);
  }

  const browLift = happy * 0.018 - sad * 0.02 + surprised * 0.026;
  if (leftBrow && leftBrowBase && leftBrowRotation) {
    leftBrow.position.y = leftBrowBase.y + browLift;
    leftBrow.rotation.z = leftBrowRotation.z - happy * 0.12 + sad * 0.12;
  }
  if (rightBrow && rightBrowBase && rightBrowRotation) {
    rightBrow.position.y = rightBrowBase.y + browLift;
    rightBrow.rotation.z = rightBrowRotation.z + happy * 0.12 - sad * 0.12;
  }
}

function dampValue(current, target, response, deltaSeconds) {
  const amount = 1 - Math.exp(-response * Math.min(deltaSeconds, 0.1));
  return THREE.MathUtils.lerp(current, target, amount);
}

function resolveMotionState() {
  const supportedStates = ["idle", "listening", "thinking", "speaking", "happy", "apology", "guide"];
  if (props.isSpeaking) {
    if (["happy", "apology", "guide"].includes(props.avatarState)) return props.avatarState;
    return "speaking";
  }
  if (props.avatarState !== "idle" && supportedStates.includes(props.avatarState)) return props.avatarState;
  if (props.emotion === "happy" || props.emotion === "apology") return props.emotion;
  return "idle";
}

function resetNaturalMotion() {
  blinkTimer = 0;
  nextBlink = 2 + Math.random() * 2;
  blinkPhase = -1;
}

function updateNaturalBodyMotion(parts, time, deltaSeconds, mouthOpen) {
  const state = resolveMotionState();
  const target = getAvatarStateMotion(state);
  const profile = getAvatarMotionProfile(props.preset);
  const blend = parts.__motionBlend || { ...target };

  Object.entries(target).forEach(([key, value]) => {
    blend[key] = dampValue(blend[key] ?? value, value, profile.transitionSpeed, deltaSeconds);
  });
  parts.__motionBlend = blend;

  const scale = profile.motionScale;
  const speakingNod = (state === "speaking" || state === "happy")
    ? Math.sin(time * 2.15) * blend.nod * (0.35 + mouthOpen * 0.65)
    : Math.sin(time * 0.82) * blend.nod;
  const postureRoll = state === "thinking" ? 0.032 : state === "apology" ? -0.012 : 0;

  parts.group.rotation.x = (
    Math.sin(time * blend.bodySpeed * 1.07) * blend.pitch + speakingNod
  ) * scale;
  parts.group.rotation.y = Math.sin(time * blend.bodySpeed * 0.83) * blend.yaw * scale;
  parts.group.rotation.z = (
    postureRoll + Math.sin(time * blend.bodySpeed * 0.71) * blend.roll
  ) * scale;
  parts.group.position.y = Math.sin(time * blend.breathSpeed) * blend.breath * scale;

  if (lookAtTarget) {
    lookAtTarget.position.x = blend.gazeOffsetX
      + Math.sin(time * blend.gazeSpeed) * blend.gazeX * scale;
    lookAtTarget.position.y = 0.92 + blend.gazeOffsetY
      + Math.sin(time * blend.gazeSpeed * 0.73) * blend.gazeY * scale;
  }

  if (parts.__avatarKind !== "vrm") {
    const pupilOffset = Math.sin(time * blend.gazeSpeed) * 0.012 * scale;
    const leftBase = parts.leftPupil?.userData.basePosition;
    const rightBase = parts.rightPupil?.userData.basePosition;
    if (parts.leftPupil && leftBase) parts.leftPupil.position.z = leftBase.z + pupilOffset;
    if (parts.rightPupil && rightBase) parts.rightPupil.position.z = rightBase.z + pupilOffset;
  }
}

function dampBoneRotation(bone, target, response, deltaSeconds) {
  if (!bone || !target) return;
  bone.rotation.x = dampValue(bone.rotation.x, target.x, response, deltaSeconds);
  bone.rotation.y = dampValue(bone.rotation.y, target.y, response, deltaSeconds);
  bone.rotation.z = dampValue(bone.rotation.z, target.z, response, deltaSeconds);
}

function updateVrmArmMotion(parts, time, deltaSeconds) {
  if (parts.__avatarKind !== "vrm") return;
  const profile = getAvatarMotionProfile(props.preset);
  const bones = parts.motionBones || {};
  const upperBase = bones.rightUpperArm?.userData.baseRotation;
  const lowerBase = bones.rightLowerArm?.userData.baseRotation;
  const handBase = bones.rightHand?.userData.baseRotation;
  if (!upperBase || !lowerBase || !handBase) return;

  const waving = props.waving || (props.gesture === "wave" && time < gestureWaveUntil);
  const waveAngle = Math.sin(time * profile.waveSpeed) * 0.55 * profile.gestureScale;
  const upperTarget = waving
    ? { x: -1.55, y: 0, z: 0.08 }
    : upperBase;
  const lowerTarget = waving
    ? { x: 1.55, y: 0, z: waveAngle }
    : lowerBase;
  const handTarget = waving
    ? { x: handBase.x, y: 0, z: waveAngle * 0.7 }
    : handBase;

  dampBoneRotation(bones.rightUpperArm, upperTarget, profile.armResponse, deltaSeconds);
  dampBoneRotation(bones.rightLowerArm, lowerTarget, profile.armResponse, deltaSeconds);
  dampBoneRotation(bones.rightHand, handTarget, profile.armResponse, deltaSeconds);
}

function updateNaturalBlink(parts, deltaSeconds) {
  const motion = getAvatarStateMotion(resolveMotionState());
  blinkTimer += deltaSeconds;

  if (blinkPhase < 0 && blinkTimer >= nextBlink) blinkPhase = 0;

  let blinkValue = 0;
  if (blinkPhase >= 0) {
    blinkPhase += deltaSeconds / Math.max(motion.blinkDuration, 0.08);
    if (blinkPhase < 0.38) {
      blinkValue = smoothstep(0, 0.38, blinkPhase);
    } else if (blinkPhase < 1) {
      blinkValue = 1 - smoothstep(0.38, 1, blinkPhase);
    } else {
      blinkPhase = -1;
      blinkTimer = 0;
      nextBlink = motion.blinkMin + Math.random() * (motion.blinkMax - motion.blinkMin);
    }
  }

  if (parts.__avatarKind === "vrm") {
    setBlinkState(parts, blinkValue);
    return;
  }

  const eyeScale = Math.max(1 - blinkValue * 0.95, 0.05);
  const leftBase = parts.leftEye?.userData.baseScale;
  const rightBase = parts.rightEye?.userData.baseScale;
  if (parts.leftEye && leftBase) parts.leftEye.scale.y = leftBase.y * eyeScale;
  if (parts.rightEye && rightBase) parts.rightEye.scale.y = rightBase.y * eyeScale;
}

function shouldAnimate() {
  return pageVisible && avatarVisible && Boolean(renderer && scene && camera);
}

function stopAnimation() {
  if (animId) cancelAnimationFrame(animId);
  animId = undefined;
}

function startAnimation() {
  if (animId || !shouldAnimate()) return;
  timer = new THREE.Timer();
  animate();
}

function handleVisibilityChange() {
  pageVisible = !document.hidden;
  if (pageVisible) startAnimation();
  else stopAnimation();
}

function animate() {
  if (!shouldAnimate()) {
    animId = undefined;
    return;
  }
  animId = requestAnimationFrame(animate);

  timer.update();
  const dt = Math.min(timer.getDelta(), 0.1);
  const t = performance.now() * 0.001;

  if (!avatarParts) return;

  // Mouth animation
  const mouthState = getMouthState();
  const mouthOpen = THREE.MathUtils.clamp(mouthState.open || 0, 0, 1);
  const mouthForm = THREE.MathUtils.clamp(mouthState.form || 0, 0, 1);
  if (avatarParts.__avatarKind === "vrm") {
    applyVrmMouth(avatarParts, mouthOpen, mouthForm, dt);
  } else {
    avatarParts.mouth.scale.y = 1 + mouthOpen * 0.72;
    avatarParts.mouth.scale.x = 1 + mouthOpen * 0.1 + mouthForm * 0.16;
    avatarParts.mouth.scale.z = 1 + mouthForm * 0.05;
  }

  const actionPlaying = updateActiveAvatarAction(performance.now());
  if (!actionPlaying && performance.now() >= naturalMotionResumeTime) {
    updateNaturalBodyMotion(avatarParts, t, dt, mouthOpen);
    updateVrmArmMotion(avatarParts, t, dt);
  }
  updateNaturalBlink(avatarParts, dt);

  // Particles
  if (particles) {
    const pos = particles.geometry.attributes.position.array;
    for (let i = 0; i < pos.length / 3; i++) {
      pos[i * 3 + 1] += (Math.sin(t * 2 + i) * 0.002) * dt * 10;
      if (pos[i * 3 + 1] > 3) pos[i * 3 + 1] = -1;
    }
    particles.geometry.attributes.position.needsUpdate = true;
    particles.rotation.y += dt * 0.03;
  }

  updateEmotionExpressions(avatarParts, dt);
  // Spring bone 物理步长上限，防止低帧率时过冲抖动
  avatarParts.__vrm?.update(Math.min(dt, 0.033));
  renderer.render(scene, camera);
}

function resizeRenderer() {
  const wrapper = canvasRef.value?.parentElement;
  if (!renderer || !camera || !wrapper) return;
  const width = Math.max(wrapper.clientWidth, 1);
  const height = Math.max(wrapper.clientHeight, 1);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO));
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

onMounted(() => {
  try {
    const width = canvasRef.value?.parentElement?.clientWidth || 480;
    const height = canvasRef.value?.parentElement?.clientHeight || 720;

    renderer = new THREE.WebGLRenderer({
      canvas: canvasRef.value,
      alpha: true,
      antialias: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO));
    renderer.setSize(width, height, false);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.shadowMap.enabled = true;

    camera = new THREE.PerspectiveCamera(28, width / height, 0.8, 20);
    camera.position.set(0, 1.0 + props.cameraOffsetY, 4.8);
    camera.lookAt(0, 1.0 + props.cameraOffsetY, 0);

    buildScene();
    pageVisible = !document.hidden;
    document.addEventListener("visibilitychange", handleVisibilityChange);
    if ("IntersectionObserver" in window) {
      intersectionObserver = new IntersectionObserver(([entry]) => {
        avatarVisible = entry.isIntersecting;
        if (avatarVisible) startAnimation();
        else stopAnimation();
      }, { threshold: 0.01 });
      intersectionObserver.observe(canvasRef.value.parentElement);
    }
    startAnimation();
    resizeObserver = new ResizeObserver(resizeRenderer);
    resizeObserver.observe(canvasRef.value.parentElement);
  } catch (err) {
    avatarStatus.value = "error";
    error.value = "无法初始化 3D 场景";
    loading.value = false;
    emit("error", err);
  }
});

onBeforeUnmount(() => {
  avatarLoadToken += 1;
  cancelAvatarActions();
  cancelScheduledVrmUpgrade();
  stopAnimation();
  document.removeEventListener("visibilitychange", handleVisibilityChange);
  resizeObserver?.disconnect();
  intersectionObserver?.disconnect();
  disposeAvatarParts(avatarParts);
  particles?.geometry?.dispose();
  particles?.material?.dispose();
  renderer?.dispose();
});

watch(() => props.preset, () => {
  avatarLoadToken += 1;
  cancelAvatarActions();
  cancelScheduledVrmUpgrade();
  if (scene && avatarParts) {
    scene.remove(avatarParts.group);
    disposeAvatarParts(avatarParts);
    avatarParts = buildFallbackAvatar(props.preset);
    cacheAvatarDefaults(avatarParts);
    resetNaturalMotion();
    scene.add(avatarParts.group);
    error.value = "";
    avatarStatus.value = "fallback";
    scheduleVrmUpgrade(props.preset);
  }
});

watch(() => props.gestureKey, () => {
  if (props.gesture === "wave") gestureWaveUntil = performance.now() * 0.001 + 2.2;
});

watch([() => props.action, () => props.actionKey], ([action]) => {
  if (action) requestAvatarAction(action, { explicit: true });
});

watch([() => props.avatarState, () => props.isSpeaking], () => {
  scheduleStateAvatarAction();
});
</script>

<style>
.three-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: transparent;
}
.three-canvas {
  display: block;
  width: 100% !important;
  height: 100% !important;
}
.three-loading, .three-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 10px 18px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.85);
  color: #94a3b8;
  font-size: 13px;
  z-index: 10;
}
.three-error { color: #fca5a5; }
</style>
