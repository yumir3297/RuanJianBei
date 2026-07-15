<template>
  <div
    class="three-wrapper"
    :data-avatar-preset="props.preset"
    :data-avatar-status="avatarStatus"
  >
    <div v-if="loading" class="three-loading">模型加载中...</div>
    <div v-if="error" class="three-error">{{ error }}</div>
    <canvas ref="canvasRef" class="three-canvas" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";

import { buildAvatarByPreset, getAvatarModelUrl } from "./avatar-presets/index.js";
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
  cameraOffsetY: { type: Number, default: 0 },
  avatarState: { type: String, default: "idle" },
});
const emit = defineEmits(["loaded", "error"]);

const audioPlayer = useAudioPlayer();

const canvasRef = ref(null);
const loading = ref(true);
const error = ref("");
const avatarStatus = ref("initializing");

let renderer, scene, camera;
let avatarParts = null;
let particles;
let lookAtTarget;
let animId;
let timer = new THREE.Timer();
let blinkTimer = 0;
let nextBlink = 2;
let avatarLoadToken = 0;
let blinkTimeout;
let resizeObserver;

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

  if (vrm.lookAt && lookAtTarget) {
    vrm.lookAt.target = lookAtTarget;
  }

  return {
    group,
    head,
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

function applyVrmMouth(parts, open, form) {
  const rounded = THREE.MathUtils.clamp(form, 0, 1);
  const wide = 1 - rounded;
  setVrmExpression(parts, "aa", open * (1 - rounded * 0.25));
  setVrmExpression(parts, "oh", open * rounded * 0.55);
  setVrmExpression(parts, "ou", open * rounded * 0.35);
  setVrmExpression(parts, "ih", open * wide * 0.28);
  setVrmExpression(parts, "ee", open * wide * 0.15);
}

function clearEmotionMorphs(parts) {
  VRM_EMOTION_EXPRESSIONS.forEach((name) => setVrmExpression(parts, name, 0));
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
    scene.add(avatarParts.group);
    vrm.scene.updateMatrixWorld(true);
    vrm.springBoneManager?.reset();
    vrm.update(0);
    applyEmotion();
    avatarStatus.value = "vrm";
    loading.value = false;
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
  ].forEach(cachePartTransform);
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
  scene.add(avatarParts.group);
  void tryUpgradeAvatarToVrm(props.preset);

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

function getMouthState() {
  if (!props.isSpeaking || !props.speechSyncActive || !props.visemeTimeline?.length) {
    const audioEnergy = audioPlayer.mouthEnergy?.value || 0;
    const previewPulse = props.isSpeaking
      ? 0.18 + (Math.sin(performance.now() * 0.013) + 1) * 0.16
      : 0;
    return {
      open: Math.max(audioEnergy, previewPulse),
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
    return { open, form };
  }

  return { open: frame.value || 0, form: frame.form || 0 };
}

function applyEmotion() {
  if (!avatarParts) return;

  cacheAvatarDefaults(avatarParts);

  if (avatarParts.__avatarKind === "vrm") {
    const { head } = avatarParts;
    const headBaseRot = head?.userData.baseRotation;

    if (headBaseRot && head) head.rotation.copy(headBaseRot);
    clearEmotionMorphs(avatarParts);

    if (props.emotion === "happy") {
      setVrmExpression(avatarParts, "happy", 0.78);
    } else if (props.emotion === "apology") {
      setVrmExpression(avatarParts, "sad", 0.5);
      if (head && headBaseRot) head.rotation.x = headBaseRot.x + 0.08;
    } else if (VRM_EMOTION_EXPRESSIONS.includes(props.emotion)) {
      setVrmExpression(avatarParts, props.emotion, 0.72);
    }
    return;
  }

  const { head, leftPupil, rightPupil, mouth, leftBrow, rightBrow } = avatarParts;
  const mouthBase = mouth?.userData.basePosition;
  const headBaseRot = head?.userData.baseRotation;
  const leftPupilBaseScale = leftPupil?.userData.baseScale;
  const rightPupilBaseScale = rightPupil?.userData.baseScale;
  const leftBrowBase = leftBrow?.userData.basePosition;
  const rightBrowBase = rightBrow?.userData.basePosition;
  const leftBrowBaseRot = leftBrow?.userData.baseRotation;
  const rightBrowBaseRot = rightBrow?.userData.baseRotation;

  if (mouthBase) mouth.position.copy(mouthBase);
  if (headBaseRot && head) head.rotation.copy(headBaseRot);
  if (leftPupilBaseScale && leftPupil) leftPupil.scale.copy(leftPupilBaseScale);
  if (rightPupilBaseScale && rightPupil) rightPupil.scale.copy(rightPupilBaseScale);
  if (leftBrowBase && leftBrow) leftBrow.position.copy(leftBrowBase);
  if (rightBrowBase && rightBrow) rightBrow.position.copy(rightBrowBase);
  if (leftBrowBaseRot && leftBrow) leftBrow.rotation.copy(leftBrowBaseRot);
  if (rightBrowBaseRot && rightBrow) rightBrow.rotation.copy(rightBrowBaseRot);

  if (props.emotion === "happy") {
    if (mouthBase && mouth) mouth.position.y = mouthBase.y + 0.025;
    if (leftPupil && leftPupilBaseScale) leftPupil.scale.y = leftPupilBaseScale.y * 0.92;
    if (rightPupil && rightPupilBaseScale) rightPupil.scale.y = rightPupilBaseScale.y * 0.92;
    if (leftBrow && leftBrowBase && leftBrowBaseRot) {
      leftBrow.position.y = leftBrowBase.y + 0.018;
      leftBrow.rotation.z = leftBrowBaseRot.z - 0.12;
    }
    if (rightBrow && rightBrowBase && rightBrowBaseRot) {
      rightBrow.position.y = rightBrowBase.y + 0.018;
      rightBrow.rotation.z = rightBrowBaseRot.z + 0.12;
    }
  } else if (props.emotion === "apology") {
    if (mouthBase && mouth) mouth.position.y = mouthBase.y - 0.018;
    if (head && headBaseRot) head.rotation.x = headBaseRot.x + 0.08;
    if (leftBrow && leftBrowBase && leftBrowBaseRot) {
      leftBrow.position.y = leftBrowBase.y - 0.02;
      leftBrow.rotation.z = leftBrowBaseRot.z + 0.12;
    }
    if (rightBrow && rightBrowBase && rightBrowBaseRot) {
      rightBrow.position.y = rightBrowBase.y - 0.02;
      rightBrow.rotation.z = rightBrowBaseRot.z - 0.12;
    }
  }
}

function animate() {
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
    applyVrmMouth(avatarParts, mouthOpen, mouthForm);
  } else {
    avatarParts.mouth.scale.y = 1 + mouthOpen * 0.72;
    avatarParts.mouth.scale.x = 1 + mouthOpen * 0.1 + mouthForm * 0.16;
    avatarParts.mouth.scale.z = 1 + mouthForm * 0.05;
  }

  // Waving animation
  if (props.waving && avatarParts.__avatarKind === "vrm") {
    const humanoid = avatarParts.__vrm?.humanoid;
    const rightUpperArm = humanoid?.getNormalizedBoneNode("rightUpperArm");
    const rightLowerArm = humanoid?.getNormalizedBoneNode("rightLowerArm");
    const rightHand = humanoid?.getNormalizedBoneNode("rightHand");

    const waveSpeed = 6.0;
    const waveAngle = Math.sin(t * waveSpeed) * 0.55;

    if (rightUpperArm) {
      rightUpperArm.rotation.x = -1.55;
      rightUpperArm.rotation.y = 0.0;
      rightUpperArm.rotation.z = 0.0;
    }
    if (rightLowerArm) {
      rightLowerArm.rotation.x = 1.55;
      rightLowerArm.rotation.y = 0.0;
      rightLowerArm.rotation.z = waveAngle;
    }
    if (rightHand) {
      rightHand.rotation.z = waveAngle * 0.7;
      rightHand.rotation.y = 0.0;
    }
  }

  // Head idle sway
  const swayX = Math.sin(t * 0.7) * 0.03;
  const swayY = Math.sin(t * 0.5) * 0.02;
  avatarParts.group.rotation.x = swayY + mouthState.open * 0.04;
  avatarParts.group.rotation.y = swayX;
  if (lookAtTarget) {
    lookAtTarget.position.x = Math.sin(t * 0.28) * 0.18;
    lookAtTarget.position.y = 0.92 + Math.sin(t * 0.19) * 0.08;
  }

  if (props.avatarState === "thinking") {
    avatarParts.group.rotation.z = Math.sin(t * 0.45) * 0.05;
  }

  // Blink
  blinkTimer += dt;
  if (blinkTimer > nextBlink) {
    if (avatarParts.__avatarKind === "vrm") {
      setBlinkState(avatarParts, 1);
    } else {
      avatarParts.leftEye.scale.y = 0.05;
      avatarParts.rightEye.scale.y = 0.05;
    }
    const blinkingAvatar = avatarParts;
    clearTimeout(blinkTimeout);
    blinkTimeout = setTimeout(() => {
      if (blinkingAvatar === avatarParts) {
        if (blinkingAvatar.__avatarKind === "vrm") {
          setBlinkState(blinkingAvatar, 0);
        } else {
          blinkingAvatar.leftEye.scale.y = 1;
          blinkingAvatar.rightEye.scale.y = 1;
        }
      }
    }, 150);
    blinkTimer = 0;
    if (props.avatarState === "listening") {
      nextBlink = 1 + Math.random() * 2;
    } else if (props.avatarState === "thinking") {
      nextBlink = 3 + Math.random() * 3;
    } else {
      nextBlink = 2 + Math.random() * 3;
    }
  }

  // Pupil look
  if (avatarParts.__avatarKind !== "vrm") {
    const lookX = Math.sin(t * 0.35) * 0.015;
    avatarParts.leftPupil.position.z = 0.68 + lookX;
    avatarParts.rightPupil.position.z = 0.68 + lookX;
  }

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

  applyEmotion();
  avatarParts.__vrm?.update(dt);
  renderer.render(scene, camera);
}

function resizeRenderer() {
  const wrapper = canvasRef.value?.parentElement;
  if (!renderer || !camera || !wrapper) return;
  const width = Math.max(wrapper.clientWidth, 1);
  const height = Math.max(wrapper.clientHeight, 1);
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
    renderer.setSize(width, height, false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.shadowMap.enabled = true;

    camera = new THREE.PerspectiveCamera(28, width / height, 0.8, 20);
    camera.position.set(0, 1.0 + props.cameraOffsetY, 4.8);
    camera.lookAt(0, 1.0 + props.cameraOffsetY, 0);

    buildScene();
    animate();
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
  clearTimeout(blinkTimeout);
  if (animId) cancelAnimationFrame(animId);
  resizeObserver?.disconnect();
  disposeAvatarParts(avatarParts);
  particles?.geometry?.dispose();
  particles?.material?.dispose();
  renderer?.dispose();
});

watch(() => props.preset, () => {
  avatarLoadToken += 1;
  if (scene && avatarParts) {
    scene.remove(avatarParts.group);
    disposeAvatarParts(avatarParts);
    avatarParts = buildFallbackAvatar(props.preset);
    cacheAvatarDefaults(avatarParts);
    scene.add(avatarParts.group);
    error.value = "";
    avatarStatus.value = "fallback";
    void tryUpgradeAvatarToVrm(props.preset);
  }
});

watch(() => props.emotion, applyEmotion);
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
