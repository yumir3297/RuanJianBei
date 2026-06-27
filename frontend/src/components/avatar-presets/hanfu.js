import * as THREE from "three";

// --------------- 清岚 · 配色（米白主袍 + 青绿披帛 + 墨青交领）---------------
const SKIN        = 0xedd0b4;  // 柔和暖白（比原版更暖）
const SKIN_SHADE  = 0xdbaf93;
const BROW        = 0x3d2b1f;
const LIP         = 0xd4908a;  // 柔和暖粉（比原版更自然）
const HAIR        = 0x1e1008;  // 深黑棕
const HAIR_LIGHT  = 0x3a2218;
const HANFU_MAIN  = 0xe9e0d1;  // 米白（外袍主色）
const HANFU_TEAL  = 0x729987;  // 青绿（披帛，比原版稍沉静）
const HANFU_DEEP  = 0x4f6b63;  // 墨青（交领镶边）
const JADE        = 0xa7c7b7;  // 玉石青
const GOLD        = 0xb9a06a;  // 淡金

function addPair(group, fn) {
  const l = fn(-1); const r = fn(1);
  group.add(l, r);
  return [l, r];
}

export function buildHanfu() {
  const group = new THREE.Group();
  group.position.y = -0.10;
  group.scale.setScalar(0.94);

  // ---- 材质 ----
  const skinM  = new THREE.MeshStandardMaterial({ color: SKIN,       roughness: 0.48, metalness: 0.02 });
  const skinS  = new THREE.MeshStandardMaterial({ color: SKIN_SHADE, roughness: 0.52, metalness: 0.02 });
  const browM  = new THREE.MeshStandardMaterial({ color: BROW,       roughness: 0.60 });
  const lipM   = new THREE.MeshStandardMaterial({ color: LIP,        roughness: 0.38 });
  const hairM  = new THREE.MeshStandardMaterial({ color: HAIR,       roughness: 0.38, metalness: 0.04 });
  const hairLM = new THREE.MeshStandardMaterial({ color: HAIR_LIGHT, roughness: 0.40, metalness: 0.03 });
  const clothM = new THREE.MeshStandardMaterial({ color: HANFU_MAIN, roughness: 0.60, metalness: 0.02 });
  const clothT  = new THREE.MeshStandardMaterial({ color: HANFU_TEAL, roughness: 0.58, metalness: 0.03 });
  const clothD  = new THREE.MeshStandardMaterial({ color: HANFU_DEEP, roughness: 0.62, metalness: 0.02 });
  const jadeM  = new THREE.MeshStandardMaterial({ color: JADE,       roughness: 0.30, metalness: 0.15 });
  const goldM  = new THREE.MeshStandardMaterial({ color: GOLD,       roughness: 0.28, metalness: 0.45 });

  // ---- 头部：鹅蛋脸（略长、略窄）----
  const headGeo = new THREE.SphereGeometry(0.72, 36, 32);
  headGeo.scale(0.98, 1.12, 0.92);
  const head = new THREE.Mesh(headGeo, skinM);
  head.position.set(0, 0.98, 0);
  group.add(head);

  // ---- 耳朵 ----
  const earGeo = new THREE.SphereGeometry(0.15, 14, 14);
  addPair(group, (side) => {
    const ear = new THREE.Mesh(earGeo, skinM);
    ear.scale.set(0.42, 0.72, 0.28);
    ear.position.set(side * 0.60, 0.93, 0.02);
    ear.rotation.y = side * 0.20;
    return ear;
  });

  // ---- 眉毛：柔和弧形（通过角度表达）----
  const browGeo = new THREE.BoxGeometry(0.24, 0.035, 0.05);
  const [leftBrow, rightBrow] = addPair(group, (side) => {
    const brow = new THREE.Mesh(browGeo, browM);
    brow.position.set(side * 0.20, 1.10, 0.56);
    brow.rotation.set(-0.06, 0, side * -0.14);
    return brow;
  });

  // ---- 眼睛：较明亮，不做二次元放大 ----
  const eyeGeo = new THREE.SphereGeometry(0.095, 22, 16);
  const eyeMat = new THREE.MeshStandardMaterial({ color: 0xfcfaf5, roughness: 0.08 });
  const [leftEye, rightEye] = addPair(group, (side) => {
    const eye = new THREE.Mesh(eyeGeo, eyeMat);
    eye.scale.set(1.04, 0.86, 0.55);
    eye.position.set(side * 0.20, 0.98, 0.60);
    return eye;
  });

  // ---- 瞳孔：明亮有神 ----
  const pupilGeo = new THREE.SphereGeometry(0.040, 16, 16);
  const pupilMat = new THREE.MeshStandardMaterial({ color: 0x2a1a10, roughness: 0.22 });
  const [leftPupil, rightPupil] = addPair(group, (side) => {
    const pupil = new THREE.Mesh(pupilGeo, pupilMat);
    pupil.scale.set(0.92, 1.04, 0.68);
    pupil.position.set(side * 0.20, 0.97, 0.67);
    return pupil;
  });

  // ---- 鼻子 ----
  const noseBridgeGeo = new THREE.CapsuleGeometry(0.040, 0.14, 4, 10);
  const noseBridge = new THREE.Mesh(noseBridgeGeo, skinS);
  noseBridge.scale.set(0.50, 0.90, 0.34);
  noseBridge.position.set(0, 0.88, 0.62);
  group.add(noseBridge);

  const noseTipGeo = new THREE.SphereGeometry(0.040, 12, 12);
  const noseTip = new THREE.Mesh(noseTipGeo, skinS);
  noseTip.scale.set(0.88, 0.70, 1.06);
  noseTip.position.set(0, 0.80, 0.68);
  group.add(noseTip);

  // ---- 嘴：嘴角自然微扬 ----
  const mouthGeo = new THREE.TorusGeometry(0.12, 0.025, 14, 18, Math.PI);
  const mouth = new THREE.Mesh(mouthGeo, lipM);
  mouth.position.set(0, 0.70, 0.67);
  mouth.rotation.set(-0.08, 0, Math.PI);
  group.add(mouth);

  // ---- 下巴 ----
  const chinGeo = new THREE.SphereGeometry(0.11, 14, 12);
  const chin = new THREE.Mesh(chinGeo, skinS);
  chin.scale.set(0.88, 0.60, 0.72);
  chin.position.set(0, 0.58, 0.48);
  group.add(chin);

  // ---- 颈部 ----
  const neckGeo = new THREE.CylinderGeometry(0.17, 0.21, 0.42, 18);
  const neck = new THREE.Mesh(neckGeo, skinM);
  neck.position.set(0, 0.34, 0.01);
  group.add(neck);

  // ---- 盘发（发髻主体）----
  const bunGeo = new THREE.SphereGeometry(0.16, 20, 16);
  bunGeo.scale(1.2, 0.85, 1.0);
  const bun = new THREE.Mesh(bunGeo, hairLM);
  bun.position.set(0, 1.32, -0.25);
  group.add(bun);

  // 发髻下半部 — 筒形
  const bunBaseGeo = new THREE.CylinderGeometry(0.14, 0.16, 0.18, 16);
  const bunBase = new THREE.Mesh(bunBaseGeo, hairM);
  bunBase.position.set(0, 1.20, -0.22);
  group.add(bunBase);

  // 头顶发包
  const topKnotGeo = new THREE.SphereGeometry(0.11, 14, 12);
  const topKnot = new THREE.Mesh(topKnotGeo, hairM);
  topKnot.position.set(0, 1.42, -0.28);
  topKnot.scale.set(1.1, 0.9, 0.95);
  group.add(topKnot);

  // ---- 玉簪（横穿发髻）----
  const pinGeo = new THREE.CylinderGeometry(0.025, 0.030, 0.40, 10);
  const pin = new THREE.Mesh(pinGeo, jadeM);
  pin.position.set(0.16, 1.28, -0.18);
  pin.rotation.set(Math.PI / 2, 0, 0.3);
  group.add(pin);

  // 簪头小珠
  const pinBeadGeo = new THREE.SphereGeometry(0.035, 8, 8);
  const pinBead = new THREE.Mesh(pinBeadGeo, jadeM);
  pinBead.position.set(0.30, 1.30, -0.12);
  group.add(pinBead);

  // ---- 两侧轻发束 ----
  const strandGeo = new THREE.PlaneGeometry(0.10, 0.48, 4, 8);
  addPair(group, (side) => {
    const strand = new THREE.Mesh(strandGeo, hairM);
    strand.position.set(side * 0.40, 0.78, 0.15);
    strand.rotation.set(0.05, side * 0.30, side * 0.12);
    return strand;
  });

  // ---- 交领汉服：内衬 ----
  const innerGeo = new THREE.CylinderGeometry(0.38, 0.48, 0.52, 20);
  const innerGarment = new THREE.Mesh(innerGeo, clothM);
  innerGarment.position.set(0, 0.02, 0.12);
  innerGarment.scale.z = 0.70;
  group.add(innerGarment);

  // ---- 交领汉服：外袍躯干（米白主色）----
  const outerTorsoGeo = new THREE.CylinderGeometry(0.92, 1.22, 1.04, 24, 1, true);
  const outerTorso = new THREE.Mesh(outerTorsoGeo, clothM);
  outerTorso.position.set(0, -0.72, 0.02);
  outerTorso.scale.z = 0.76;
  group.add(outerTorso);

  // ---- 交领结构（左压右 Y 字交叠，墨青色）----
  // 左领片（在上，从右肩斜向左腋）
  const leftCollarGeo = new THREE.BoxGeometry(0.32, 0.72, 0.10);
  const leftCollar = new THREE.Mesh(leftCollarGeo, clothD);
  leftCollar.position.set(-0.10, 0.14, 0.46);
  leftCollar.rotation.set(-0.06, 0.10, 0.48);
  group.add(leftCollar);

  // 右领片（在下，从左肩斜向右腋）
  const rightCollarGeo = new THREE.BoxGeometry(0.30, 0.66, 0.09);
  const rightCollar = new THREE.Mesh(rightCollarGeo, clothD);
  rightCollar.position.set(0.16, 0.04, 0.40);
  rightCollar.rotation.set(0.02, -0.08, -0.38);
  group.add(rightCollar);

  // 领缘淡金镶边
  const collarEdgeGeo = new THREE.BoxGeometry(0.07, 0.60, 0.12);
  const leftEdge = new THREE.Mesh(collarEdgeGeo, goldM);
  leftEdge.position.set(-0.24, 0.22, 0.47);
  leftEdge.rotation.set(0, 0.06, 0.48);
  group.add(leftEdge);

  // ---- 披帛（肩部青绿披挂）----
  const capeGeo = new THREE.SphereGeometry(1.32, 26, 16, 0, Math.PI * 2, 0, Math.PI * 0.44);
  capeGeo.scale(1, 0.50, 0.66);
  const cape = new THREE.Mesh(capeGeo, clothT);
  cape.position.set(0, -0.18, 0.12);
  group.add(cape);

  // 披帛前缘（轻搭在胸前）
  const drapeGeo = new THREE.PlaneGeometry(0.40, 0.74, 6, 8);
  const drapeL = new THREE.Mesh(drapeGeo, clothM);
  drapeL.position.set(-0.36, -0.12, 0.44);
  drapeL.rotation.set(0.08, 0.14, 0.36);
  group.add(drapeL);

  const drapeR = new THREE.Mesh(drapeGeo, clothT);
  drapeR.position.set(0.32, -0.16, 0.40);
  drapeR.rotation.set(0.06, -0.12, -0.30);
  group.add(drapeR);

  // ---- 腰带（墨青束腰）----
  const beltGeo = new THREE.TorusGeometry(0.64, 0.05, 10, 24, Math.PI);
  const belt = new THREE.Mesh(beltGeo, clothD);
  belt.position.set(0, -0.66, 0.34);
  belt.rotation.set(Math.PI * 0.52, 0, 0);
  group.add(belt);

  // ---- 流苏（耳侧轻装饰）----
  const tasselGeo = new THREE.CylinderGeometry(0.015, 0.018, 0.22, 8);
  addPair(group, (side) => {
    const tassel = new THREE.Mesh(tasselGeo, goldM);
    tassel.position.set(side * 0.05, 1.18, -0.04);
    tassel.rotation.set(side * 0.12, 0, 0);
    return tassel;
  });

  return { group, head, leftEye, rightEye, leftPupil, rightPupil, mouth, leftBrow, rightBrow };
}
