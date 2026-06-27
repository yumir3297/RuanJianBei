import * as THREE from "three";

const SKIN = 0xd9b08c;
const SKIN_SHADOW = 0xc59d75;
const SKIN_LIGHT = 0xe6c7a6;
const SCALP = 0xcaa37b;
const ROBE = 0xa06a2c;
const ROBE_DEEP = 0x5c3b24;
const ROBE_LIGHT = 0xd8c3a5;
const BEAD = 0x8c6a3a;
const BEAD_DARK = 0x6a4b2a;
const BEAD_HI = 0xb99662;
const BROW = 0x4f3827;
const LIP = 0xac6c61;
const LIP_DARK = 0x8a4f47;
const IRIS = 0x241a14;

function mat(color, roughness = 0.5, metalness = 0.02) {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness });
}

function addMirrored(group, build) {
  const left = build(-1);
  const right = build(1);
  if (left) group.add(left);
  if (right) group.add(right);
  return [left, right];
}

function buildBrow(group, side, material) {
  const brow = new THREE.Group();
  brow.position.set(side * 0.18, 1.075, 0.6);
  brow.rotation.z = side * -0.1;

  const inner = new THREE.Mesh(new THREE.BoxGeometry(0.085, 0.018, 0.022), material);
  inner.position.set(side * -0.018, 0, 0);
  brow.add(inner);

  const mid = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.017, 0.02), material);
  mid.position.set(side * 0.04, -0.01, 0.004);
  mid.rotation.z = side * -0.12;
  brow.add(mid);

  const tail = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.015, 0.018), material);
  tail.position.set(side * 0.085, -0.024, 0.008);
  tail.rotation.z = side * -0.22;
  brow.add(tail);

  group.add(brow);
  return brow;
}

export function buildMonk() {
  const group = new THREE.Group();
  group.position.y = -0.18;
  group.scale.setScalar(0.96);

  const skin = mat(SKIN, 0.48);
  const skinShadow = mat(SKIN_SHADOW, 0.56);
  const skinLight = mat(SKIN_LIGHT, 0.42);
  const scalpMat = mat(SCALP, 0.54, 0.01);
  const robe = mat(ROBE, 0.7);
  const robeDeep = mat(ROBE_DEEP, 0.76);
  const robeLight = mat(ROBE_LIGHT, 0.66);
  const bead = mat(BEAD, 0.42, 0.1);
  const beadDark = mat(BEAD_DARK, 0.46, 0.08);
  const beadHi = mat(BEAD_HI, 0.38, 0.14);
  const browMat = mat(BROW, 0.58, 0);
  const lip = mat(LIP, 0.34, 0.01);
  const lipDark = mat(LIP_DARK, 0.38, 0.01);
  const eyeWhite = mat(0xf6f2eb, 0.08, 0);
  const iris = mat(IRIS, 0.24, 0.04);
  const irisRing = mat(0x3a281d, 0.28, 0.02);
  const eyeHighlight = mat(0xffffff, 0.04, 0);
  const mouthInner = mat(0x5e302c, 0.74, 0);

  const headGeo = new THREE.SphereGeometry(0.73, 40, 32);
  headGeo.scale(0.86, 0.94, 0.76);
  const head = new THREE.Mesh(headGeo, skin);
  head.position.set(0, 0.98, 0);
  group.add(head);

  const facePlane = new THREE.Mesh(new THREE.SphereGeometry(0.46, 24, 18), skin);
  facePlane.scale.set(1.02, 1.18, 0.44);
  facePlane.position.set(0, 0.84, 0.39);
  group.add(facePlane);

  const scalp = new THREE.Mesh(
    new THREE.SphereGeometry(0.62, 28, 16, 0, Math.PI * 2, 0, Math.PI * 0.42),
    scalpMat,
  );
  scalp.scale.set(0.9, 0.56, 0.8);
  scalp.position.set(0, 1.21, -0.08);
  group.add(scalp);

  addMirrored(group, (side) => {
    const temple = new THREE.Mesh(new THREE.SphereGeometry(0.13, 10, 8), skinShadow);
    temple.scale.set(0.8, 1.0, 0.34);
    temple.position.set(side * 0.39, 1.01, 0.12);
    return temple;
  });

  addMirrored(group, (side) => {
    const cheek = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 10), skinLight);
    cheek.scale.set(0.86, 0.68, 0.22);
    cheek.position.set(side * 0.28, 0.8, 0.35);
    return cheek;
  });

  addMirrored(group, (side) => {
    const cheekShadow = new THREE.Mesh(new THREE.SphereGeometry(0.13, 10, 8), skinShadow);
    cheekShadow.scale.set(0.78, 0.54, 0.2);
    cheekShadow.position.set(side * 0.34, 0.79, 0.22);
    return cheekShadow;
  });

  addMirrored(group, (side) => {
    const jaw = new THREE.Mesh(new THREE.CapsuleGeometry(0.06, 0.22, 4, 8), skinShadow);
    jaw.scale.set(0.94, 0.44, 0.56);
    jaw.position.set(side * 0.31, 0.6, 0.16);
    jaw.rotation.set(0.02, side * 0.46, side * 0.24);
    return jaw;
  });

  const chin = new THREE.Mesh(new THREE.SphereGeometry(0.12, 14, 12), skinLight);
  chin.scale.set(0.82, 0.54, 0.64);
  chin.position.set(0, 0.55, 0.46);
  group.add(chin);

  addMirrored(group, (side) => {
    const browRidge = new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.12, 4, 8), skinShadow);
    browRidge.scale.set(1.02, 0.42, 0.54);
    browRidge.position.set(side * 0.18, 1.03, 0.48);
    browRidge.rotation.set(0.06, side * 0.18, side * 0.05);
    return browRidge;
  });

  const leftBrow = buildBrow(group, -1, browMat);
  const rightBrow = buildBrow(group, 1, browMat);

  addMirrored(group, (side) => {
    const socket = new THREE.Mesh(new THREE.SphereGeometry(0.11, 12, 10), skinShadow);
    socket.scale.set(1.06, 0.48, 0.28);
    socket.position.set(side * 0.18, 0.95, 0.53);
    return socket;
  });

  const eyeGeo = new THREE.SphereGeometry(0.08, 16, 14);
  const [leftEye, rightEye] = addMirrored(group, (side) => {
    const eye = new THREE.Mesh(eyeGeo, eyeWhite);
    eye.scale.set(1.06, 0.68, 0.4);
    eye.position.set(side * 0.165, 0.925, 0.61);
    return eye;
  });

  const [leftPupil, rightPupil] = addMirrored(group, (side) => {
    const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.022, 14, 14), iris);
    pupil.scale.set(0.92, 1.02, 0.52);
    pupil.position.set(side * 0.165, 0.92, 0.67);
    group.add(pupil);

    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.024, 0.004, 6, 12), irisRing);
    ring.position.set(side * 0.165, 0.92, 0.674);
    ring.rotation.y = Math.PI / 2;
    group.add(ring);

    const hi = new THREE.Mesh(new THREE.SphereGeometry(0.008, 5, 5), eyeHighlight);
    hi.position.set(side * 0.178, 0.935, 0.682);
    group.add(hi);

    return pupil;
  });

  addMirrored(group, (side) => {
    const upperLid = new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.09, 5, 10), skin);
    upperLid.scale.set(1.12, 0.22, 0.42);
    upperLid.position.set(side * 0.165, 0.95, 0.615);
    upperLid.rotation.z = side * 0.04;
    return upperLid;
  });

  addMirrored(group, (side) => {
    const lowerLid = new THREE.Mesh(new THREE.CapsuleGeometry(0.035, 0.07, 5, 10), skinLight);
    lowerLid.scale.set(1.02, 0.12, 0.28);
    lowerLid.position.set(side * 0.165, 0.893, 0.602);
    return lowerLid;
  });

  const nasalBone = new THREE.Mesh(new THREE.CapsuleGeometry(0.048, 0.18, 4, 8), skinShadow);
  nasalBone.scale.set(0.52, 0.84, 0.26);
  nasalBone.position.set(0, 0.905, 0.56);
  group.add(nasalBone);

  const bridge = new THREE.Mesh(new THREE.CapsuleGeometry(0.046, 0.14, 4, 8), skinShadow);
  bridge.scale.set(0.46, 0.86, 0.32);
  bridge.position.set(0, 0.82, 0.605);
  group.add(bridge);

  const tip = new THREE.Mesh(new THREE.SphereGeometry(0.058, 14, 14), skin);
  tip.scale.set(0.84, 0.66, 0.98);
  tip.position.set(0, 0.73, 0.675);
  group.add(tip);

  addMirrored(group, (side) => {
    const wing = new THREE.Mesh(new THREE.SphereGeometry(0.037, 10, 10), skinShadow);
    wing.scale.set(0.88, 0.54, 0.76);
    wing.position.set(side * 0.088, 0.728, 0.67);
    return wing;
  });

  addMirrored(group, (side) => {
    const nostril = new THREE.Mesh(new THREE.SphereGeometry(0.014, 6, 6), mouthInner);
    nostril.position.set(side * 0.048, 0.716, 0.695);
    return nostril;
  });

  const philtrum = new THREE.Mesh(new THREE.BoxGeometry(0.028, 0.05, 0.016), skinShadow);
  philtrum.position.set(0, 0.685, 0.664);
  group.add(philtrum);

  const mouthGroup = new THREE.Group();
  mouthGroup.position.set(0, 0.615, 0.67);

  const mouthCavity = new THREE.Mesh(new THREE.SphereGeometry(0.062, 14, 12), mouthInner);
  mouthCavity.scale.set(1.0, 0.38, 0.3);
  mouthCavity.position.set(0, -0.002, -0.012);
  mouthGroup.add(mouthCavity);

  addMirrored(mouthGroup, (side) => {
    const upperLip = new THREE.Mesh(new THREE.CapsuleGeometry(0.011, 0.05, 4, 8), lipDark);
    upperLip.scale.set(1.0, 0.86, 0.72);
    upperLip.position.set(side * 0.03, 0.018, 0.006);
    upperLip.rotation.set(0, 0, side * 0.34);
    return upperLip;
  });

  const cupid = new THREE.Mesh(new THREE.SphereGeometry(0.012, 6, 6), lipDark);
  cupid.scale.set(1.2, 0.7, 0.8);
  cupid.position.set(0, 0.016, 0.008);
  mouthGroup.add(cupid);

  const lowerLip = new THREE.Mesh(new THREE.CapsuleGeometry(0.013, 0.09, 4, 8), lip);
  lowerLip.scale.set(1.02, 0.52, 0.54);
  lowerLip.position.set(0, -0.018, 0.01);
  lowerLip.rotation.z = Math.PI / 2;
  mouthGroup.add(lowerLip);

  addMirrored(mouthGroup, (side) => {
    const corner = new THREE.Mesh(new THREE.SphereGeometry(0.012, 6, 6), lip);
    corner.position.set(side * 0.072, -0.003, 0.004);
    return corner;
  });

  group.add(mouthGroup);

  addMirrored(group, (side) => {
    const fold = new THREE.Mesh(new THREE.BoxGeometry(0.005, 0.06, 0.018), skinShadow);
    fold.position.set(side * 0.108, 0.695, 0.645);
    fold.rotation.set(0.06, side * 0.1, side * 0.08);
    return fold;
  });

  addMirrored(group, (side) => {
    const ear = new THREE.Mesh(new THREE.SphereGeometry(0.14, 12, 10), skinShadow);
    ear.scale.set(0.38, 0.72, 0.25);
    ear.position.set(side * 0.56, 0.9, 0.02);
    ear.rotation.y = side * 0.2;
    group.add(ear);

    const helix = new THREE.Mesh(new THREE.TorusGeometry(0.068, 0.014, 6, 10), skin);
    helix.position.set(side * 0.565, 0.915, 0.03);
    helix.rotation.set(0.08, side * 0.28, side * 0.06);
    helix.scale.set(0.82, 1.08, 0.5);
    group.add(helix);

    const lobe = new THREE.Mesh(new THREE.SphereGeometry(0.038, 8, 8), skinLight);
    lobe.scale.set(0.72, 0.56, 0.42);
    lobe.position.set(side * 0.57, 0.74, 0.035);
    group.add(lobe);

    return ear;
  });

  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.21, 0.48, 18), skin);
  neck.position.set(0, 0.25, 0.01);
  group.add(neck);

  const innerCollar = new THREE.Mesh(new THREE.CylinderGeometry(0.29, 0.4, 0.34, 18), robeLight);
  innerCollar.position.set(0, 0.02, 0.07);
  innerCollar.scale.z = 0.68;
  group.add(innerCollar);

  const midCollar = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.46, 0.22, 18), robe);
  midCollar.position.set(0, 0.11, 0.06);
  midCollar.scale.z = 0.64;
  group.add(midCollar);

  const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.74, 0.98, 1.02, 24, 1, true), robeDeep);
  torso.position.set(0, -0.69, 0.01);
  torso.scale.z = 0.74;
  group.add(torso);

  const shoulderCape = new THREE.Mesh(
    new THREE.SphereGeometry(1.18, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.5),
    robe,
  );
  shoulderCape.scale.set(1, 0.44, 0.58);
  shoulderCape.position.set(0, -0.27, 0.02);
  group.add(shoulderCape);

  const lapelLeft = new THREE.Mesh(new THREE.PlaneGeometry(0.18, 0.56, 4, 6), robeLight);
  lapelLeft.position.set(-0.11, -0.03, 0.39);
  lapelLeft.rotation.set(-0.05, 0.08, 0.46);
  group.add(lapelLeft);

  const lapelRight = new THREE.Mesh(new THREE.PlaneGeometry(0.16, 0.48, 4, 6), robeDeep);
  lapelRight.position.set(0.15, -0.05, 0.34);
  lapelRight.rotation.set(0.03, -0.05, -0.34);
  group.add(lapelRight);

  const stole = new THREE.Mesh(new THREE.PlaneGeometry(0.16, 1.02, 4, 8), robe);
  stole.position.set(-0.4, -0.43, 0.18);
  stole.rotation.set(0.05, 0.04, -0.23);
  group.add(stole);

  const belt = new THREE.Mesh(new THREE.TorusGeometry(0.54, 0.045, 10, 22, Math.PI), robeLight);
  belt.position.set(0, -0.8, 0.24);
  belt.rotation.set(Math.PI * 0.56, 0, 0);
  group.add(belt);

  const beadCount = 11;
  const beadGeo = new THREE.SphereGeometry(0.038, 10, 10);
  const points = [];
  for (let i = 0; i < beadCount; i++) {
    const t = i / (beadCount - 1);
    const angle = Math.PI * (0.18 + t * 0.64);
    const point = new THREE.Vector3(
      Math.cos(angle) * 0.32,
      0.01 - Math.sin(t * Math.PI) * 0.26,
      0.54 + Math.sin(angle) * 0.03,
    );
    points.push(point);

    const beadMesh = new THREE.Mesh(
      beadGeo,
      i % 3 === 0 ? beadHi : i % 2 === 0 ? bead : beadDark,
    );
    beadMesh.position.copy(point);
    group.add(beadMesh);
  }

  const beadCurve = new THREE.CatmullRomCurve3(points);
  const beadString = new THREE.Mesh(
    new THREE.TubeGeometry(beadCurve, 36, 0.006, 6, false),
    beadDark,
  );
  group.add(beadString);

  const pendant = new THREE.Mesh(new THREE.SphereGeometry(0.05, 12, 12), beadHi);
  pendant.scale.set(0.9, 1.12, 0.9);
  pendant.position.set(0, -0.17, 0.56);
  group.add(pendant);

  return {
    group,
    head,
    leftEye,
    rightEye,
    leftPupil,
    rightPupil,
    mouth: mouthGroup,
    mouthBaseY: mouthGroup.position.y,
    leftBrow,
    rightBrow,
  };
}
