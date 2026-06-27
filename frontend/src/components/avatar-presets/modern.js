import * as THREE from "three";

// ═══════════════════ 景行 · 配色体系 ═══════════════════
// 设定稿配色：深藏青 / 青绿 / 亮米白 / 亮琥珀
const SKIN        = 0xd8b091;  // 中性暖肤色
const SKIN_DARK   = 0xbf9578;  // 暗面
const SKIN_DARKER = 0xa88062;  // 最深阴影
const SKIN_LIGHT  = 0xe8c8a8;  // 高光面

const NAVY        = 0x243447;  // 深藏青 — 主制服
const TEAL        = 0x2f7f79;  // 青绿 — 领口/配饰
const CREAM       = 0xe6e2d3;  // 亮米白 — 内衬/领片
const AMBER       = 0xe39b43;  // 亮琥珀 — 点缀/徽标
const BADGE_BG    = 0x1a2a3a;

const BROW        = 0x2e2018;
const BROW_DARK   = 0x1e140e;
const LIP         = 0xbc7265;
const LIP_DARK    = 0x945548;

const HAIR        = 0x2d1b0e;
const HAIR_TOP    = 0x3d2818;

const IRIS        = 0x221812;
const IRIS_RING   = 0x3d2818;

const addPair = (g, fn) => { const l = fn(-1), r = fn(1); g.add(l, r); return [l, r]; };

export function buildModern() {
  const group = new THREE.Group();
  group.position.y = -0.10;
  group.scale.setScalar(0.93);

  // ══════════ 材质 ══════════
  const sk   = new THREE.MeshStandardMaterial({ color: SKIN,        roughness: 0.48, metalness: 0.02 });
  const skD  = new THREE.MeshStandardMaterial({ color: SKIN_DARK,   roughness: 0.52, metalness: 0.02 });
  const skD2 = new THREE.MeshStandardMaterial({ color: SKIN_DARKER, roughness: 0.56, metalness: 0.02 });
  const skL  = new THREE.MeshStandardMaterial({ color: SKIN_LIGHT,  roughness: 0.46, metalness: 0.02 });

  const nv   = new THREE.MeshStandardMaterial({ color: NAVY,        roughness: 0.50, metalness: 0.04 });
  const nvL  = new THREE.MeshStandardMaterial({ color: 0x304458,    roughness: 0.48, metalness: 0.05 }); // navy light
  const te   = new THREE.MeshStandardMaterial({ color: TEAL,        roughness: 0.45, metalness: 0.06 });
  const cr   = new THREE.MeshStandardMaterial({ color: CREAM,       roughness: 0.55, metalness: 0.02 });
  const am   = new THREE.MeshStandardMaterial({ color: AMBER,       roughness: 0.28, metalness: 0.35 });
  const bg   = new THREE.MeshStandardMaterial({ color: BADGE_BG,    roughness: 0.42, metalness: 0.10 });

  const bw   = new THREE.MeshStandardMaterial({ color: BROW,        roughness: 0.55 });
  const bwD  = new THREE.MeshStandardMaterial({ color: BROW_DARK,   roughness: 0.52 });
  const lp   = new THREE.MeshStandardMaterial({ color: LIP,         roughness: 0.38 });
  const lpD  = new THREE.MeshStandardMaterial({ color: LIP_DARK,    roughness: 0.40 });

  const hm   = new THREE.MeshStandardMaterial({ color: HAIR,        roughness: 0.32, metalness: 0.05 });
  const hmT  = new THREE.MeshStandardMaterial({ color: HAIR_TOP,    roughness: 0.34, metalness: 0.04 });

  const ir   = new THREE.MeshStandardMaterial({ color: IRIS,        roughness: 0.22, metalness: 0.05 });
  const irR  = new THREE.MeshStandardMaterial({ color: IRIS_RING,   roughness: 0.24, metalness: 0.04 });
  const wh   = new THREE.MeshStandardMaterial({ color: 0xffffff,    roughness: 0.05 });

  // ══════════════════ 一、颅骨（方圆脸） ══════════════════
  const headGeo = new THREE.SphereGeometry(0.73, 40, 32);
  headGeo.scale(1.04, 1.02, 0.94);
  const head = new THREE.Mesh(headGeo, sk);
  head.position.set(0, 0.98, 0);
  group.add(head);

  // ══════════════════ 二、眉弓 ══════════════════
  addPair(group, (s) => {
    const g = new THREE.Mesh(new THREE.CapsuleGeometry(0.06, 0.22, 4, 8), skD);
    g.scale.set(1.2, 0.50, 0.65);
    g.position.set(s * 0.20, 1.14, 0.50);
    g.rotation.set(0.15, s * 0.30, s * 0.08);
    return g;
  });

  // ══════════════════ 三、颧骨 ══════════════════
  addPair(group, (s) => {
    const c = new THREE.Mesh(new THREE.SphereGeometry(0.17, 14, 12), skL);
    c.scale.set(0.70, 0.48, 0.28);
    c.position.set(s * 0.38, 0.80, 0.38);
    return c;
  });

  // ══════════════════ 四、耳朵 ══════════════════
  addPair(group, (s) => {
    const ear = new THREE.Mesh(new THREE.SphereGeometry(0.16, 16, 12), skD);
    ear.scale.set(0.44, 0.74, 0.28);
    ear.position.set(s * 0.63, 0.93, 0.03);
    ear.rotation.y = s * 0.22;
    const helix = new THREE.Mesh(new THREE.TorusGeometry(0.08, 0.018, 8, 12), sk);
    helix.position.set(s * 0.64, 0.95, 0.04);
    helix.rotation.set(0.15, s * 0.38, s * 0.10);
    helix.scale.set(0.90, 1.25, 0.60);
    const lobe = new THREE.Mesh(new THREE.SphereGeometry(0.05, 8, 8), sk);
    lobe.position.set(s * 0.65, 0.74, 0.04);
    lobe.scale.set(0.78, 0.52, 0.44);
    group.add(ear, helix, lobe);
    return ear;
  });

  // ══════════════════ 五、眉毛（5段弧形） ══════════════════
  const browSegGeo = new THREE.BoxGeometry(0.06, 0.035, 0.04);
  const [leftBrow, rightBrow] = addPair(group, (s) => {
    const grp = new THREE.Group();
    grp.name = s === -1 ? "leftBrow" : "rightBrow";
    const segs = 5, bx = 0.17, totalLen = 0.28;
    for (let i = 0; i < segs; i++) {
      const t = i / (segs - 1);
      const seg = new THREE.Mesh(browSegGeo, i < 2 ? bwD : bw);
      seg.position.set(
        s * (bx + t * totalLen),
        1.14 - t * 0.03 - Math.sin(t * Math.PI) * 0.025,
        0.55 + t * 0.06
      );
      seg.rotation.set(-0.04, 0, s * (-0.18 + t * 0.12));
      grp.add(seg);
    }
    group.add(grp);
    return grp;
  });

  // ══════════════════ 六、眼睛 + 眼睑 ══════════════════
  const eyeGeo = new THREE.SphereGeometry(0.098, 24, 18);
  const eyeMat = new THREE.MeshStandardMaterial({ color: 0xfdfaf5, roughness: 0.08 });
  const [leftEye, rightEye] = addPair(group, (s) => {
    const e = new THREE.Mesh(eyeGeo, eyeMat);
    e.scale.set(1.06, 0.84, 0.56);
    e.position.set(s * 0.22, 0.99, 0.60);
    return e;
  });

  // 上眼睑
  addPair(group, (s) => {
    const lid = new THREE.Mesh(new THREE.CapsuleGeometry(0.06, 0.12, 6, 12), skD);
    lid.scale.set(1.15, 0.28, 0.45);
    lid.position.set(s * 0.22, 1.01, 0.60);
    lid.rotation.set(0, 0, s * 0.06);
    return lid;
  });

  // 下眼睑
  addPair(group, (s) => {
    const ll = new THREE.Mesh(new THREE.CapsuleGeometry(0.04, 0.08, 5, 10), skL);
    ll.scale.set(1.10, 0.16, 0.35);
    ll.position.set(s * 0.22, 0.96, 0.59);
    return ll;
  });

  // ══════════════════ 七、虹膜 + 高光 ══════════════════
  const pupilGeo = new THREE.SphereGeometry(0.038, 18, 18);
  const [leftPupil, rightPupil] = addPair(group, (s) => {
    const p = new THREE.Mesh(pupilGeo, ir);
    p.scale.set(0.95, 1.06, 0.62);
    p.position.set(s * 0.22, 0.975, 0.67);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.038, 0.008, 8, 16), irR);
    ring.position.set(s * 0.22, 0.975, 0.67);
    ring.rotation.y = Math.PI / 2;
    group.add(ring);
    const hi = new THREE.Mesh(new THREE.SphereGeometry(0.013, 8, 8), wh);
    hi.position.set(s * 0.24, 0.98, 0.688);
    group.add(hi);
    return p;
  });

  // ══════════════════ 八、鼻子 ══════════════════
  const bridge = new THREE.Mesh(new THREE.CapsuleGeometry(0.045, 0.16, 4, 10), skD);
  bridge.scale.set(0.50, 1.0, 0.36);
  bridge.position.set(0, 0.88, 0.64);
  group.add(bridge);

  const tip = new THREE.Mesh(new THREE.SphereGeometry(0.044, 14, 14), sk);
  tip.scale.set(0.88, 0.68, 1.04);
  tip.position.set(0, 0.80, 0.69);
  group.add(tip);

  // 鼻翼
  addPair(group, (s) => {
    const a = new THREE.Mesh(new THREE.SphereGeometry(0.032, 10, 10), skD);
    a.scale.set(0.70, 0.55, 0.80);
    a.position.set(s * 0.10, 0.80, 0.685);
    return a;
  });

  // 鼻孔
  addPair(group, (s) => {
    const n = new THREE.Mesh(new THREE.SphereGeometry(0.016, 6, 6),
      new THREE.MeshStandardMaterial({ color: 0x3a2020, roughness: 0.8 }));
    n.position.set(s * 0.06, 0.79, 0.70);
    return n;
  });

  // ══════════════════ 九、嘴唇 + 唇峰 + 口裂 ══════════════════
  const upperLip = new THREE.Mesh(
    new THREE.TorusGeometry(0.135, 0.020, 12, 18, Math.PI), lpD
  );
  upperLip.position.set(0, 0.705, 0.675);
  upperLip.rotation.set(-0.08, 0, Math.PI);
  group.add(upperLip);

  const lowerLip = new THREE.Mesh(
    new THREE.TorusGeometry(0.12, 0.022, 10, 16, Math.PI), lp
  );
  lowerLip.position.set(0, 0.685, 0.680);
  lowerLip.rotation.set(0.08, 0, 0);
  group.add(lowerLip);

  const lipPeaks = addPair(group, (s) => {
    const p = new THREE.Mesh(new THREE.SphereGeometry(0.016, 6, 6), lp);
    p.position.set(s * 0.038, 0.715, 0.688);
    return p;
  });

  const mouthLine = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.005, 0.03), lpD);
  mouthLine.position.set(0, 0.695, 0.677);
  group.add(mouthLine);

  // 口部 Group
  const mouthGroup = new THREE.Group();
  mouthGroup.name = "mouth";
  group.remove(upperLip, lowerLip, lipPeaks[0], lipPeaks[1], mouthLine);
  mouthGroup.add(upperLip, lowerLip, lipPeaks[0], lipPeaks[1], mouthLine);
  group.add(mouthGroup);

  // ══════════════════ 十、下颌 + 下巴 ══════════════════
  addPair(group, (s) => {
    const j = new THREE.Mesh(new THREE.CapsuleGeometry(0.06, 0.30, 5, 10), skD);
    j.scale.set(1.0, 0.38, 0.52);
    j.position.set(s * 0.35, 0.66, 0.25);
    j.rotation.set(0, s * 0.52, s * 0.28);
    return j;
  });

  const chin = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 14), skL);
  chin.scale.set(1.02, 0.60, 0.76);
  chin.position.set(0, 0.58, 0.47);
  group.add(chin);

  // ══════════════════ 十一、颈部 ══════════════════
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.22, 0.42, 18), sk);
  neck.position.set(0, 0.34, 0.01);
  group.add(neck);

  // ══════════════════ 十二、短发（多层次） ══════════════════
  const hairBase = new THREE.Mesh(
    new THREE.SphereGeometry(0.76, 28, 20, 0, Math.PI * 2, 0, Math.PI * 0.42), hm
  );
  hairBase.position.set(0, 1.10, -0.04);
  group.add(hairBase);

  const hairTop = new THREE.Mesh(
    new THREE.SphereGeometry(0.74, 24, 18, 0, Math.PI * 2, 0, Math.PI * 0.32), hmT
  );
  hairTop.position.set(0, 1.22, -0.06);
  hairTop.scale.set(1.08, 1, 1.02);
  group.add(hairTop);

  addPair(group, (s) => {
    const sh = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.35, 0.20), hm);
    sh.position.set(s * 0.48, 0.86, 0.08);
    sh.rotation.set(0, s * 0.25, s * 0.06);
    return sh;
  });

  const bang = new THREE.Mesh(new THREE.BoxGeometry(0.60, 0.14, 0.12), hmT);
  bang.position.set(0, 1.18, 0.58);
  bang.rotation.set(0.08, 0, 0);
  group.add(bang);

  const bangL = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.10, 0.10), hm);
  bangL.position.set(0.05, 1.14, 0.62);
  bangL.rotation.set(0.10, 0.04, 0.02);
  group.add(bangL);

  // ══════════════════ 十三、立领制服 ══════════════════
  // 内衬（米白色，在立领下方）
  const inner = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.44, 0.40, 20), cr);
  inner.position.set(0, 0.08, 0.10);
  inner.scale.z = 0.66;
  group.add(inner);

  // 立领（高领，藏青色）
  const standCollar = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.34, 0.18, 22), nv);
  standCollar.position.set(0, 0.28, 0.10);
  standCollar.scale.z = 0.66;
  group.add(standCollar);

  // 立领青绿饰边
  const collarTrim = new THREE.Mesh(new THREE.TorusGeometry(0.33, 0.015, 8, 24), te);
  collarTrim.position.set(0, 0.36, 0.10);
  collarTrim.rotation.x = Math.PI / 2;
  group.add(collarTrim);

  // 翻领片（前胸两侧，V形开口）
  addPair(group, (s) => {
    const lp = new THREE.Mesh(new THREE.PlaneGeometry(0.18, 0.62, 5, 8), nv);
    lp.position.set(s * 0.16, 0.10, 0.42);
    lp.rotation.set(-0.08, s * 0.06, s * 0.30);
    return lp;
  });

  // 翻领奶油色衬边
  addPair(group, (s) => {
    const ce = new THREE.Mesh(new THREE.PlaneGeometry(0.06, 0.55, 3, 8), cr);
    ce.position.set(s * 0.22, 0.14, 0.44);
    ce.rotation.set(-0.06, s * 0.04, s * 0.32);
    return ce;
  });

  // ══════════════════ 十四、制服躯干 ══════════════════
  const torso = new THREE.Mesh(
    new THREE.CylinderGeometry(1.00, 1.10, 1.04, 26, 1, true), nv
  );
  torso.position.set(0, -0.70, 0.02);
  torso.scale.z = 0.76;
  group.add(torso);

  // 肩部
  const shoulderGeo = new THREE.SphereGeometry(1.42, 26, 16, 0, Math.PI * 2, 0, Math.PI * 0.45);
  shoulderGeo.scale(1, 0.48, 0.62);
  const shoulder = new THREE.Mesh(shoulderGeo, nv);
  shoulder.position.set(0, -0.22, 0.06);
  group.add(shoulder);

  // 肩部青绿线条
  addPair(group, (s) => {
    const line = new THREE.Mesh(new THREE.BoxGeometry(0.30, 0.015, 0.02), te);
    line.position.set(s * 0.35, -0.18, 0.38);
    line.rotation.set(0.05, s * 0.6, s * 0.08);
    return line;
  });

  // ══════════════════ 十五、胸牌 ══════════════════
  const badge = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.13, 0.03), bg);
  badge.position.set(0.24, 0.68, 0.50);
  group.add(badge);

  // 胸牌琥珀色横条
  const badgeAmber = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.028, 0.035), am);
  badgeAmber.position.set(0.24, 0.71, 0.50);
  group.add(badgeAmber);

  // 胸牌青绿点（小方块）
  const badgeDot = new THREE.Mesh(new THREE.SphereGeometry(0.018, 6, 6), te);
  badgeDot.position.set(0.32, 0.68, 0.51);
  group.add(badgeDot);

  // ══════════════════ 十六、耳麦 ══════════════════
  const earpiece = new THREE.Mesh(new THREE.TorusGeometry(0.06, 0.015, 8, 12), te);
  earpiece.position.set(-0.52, 0.95, 0.18);
  earpiece.rotation.set(0, -0.25, 0.15);
  group.add(earpiece);

  const micArm = new THREE.Mesh(new THREE.CylinderGeometry(0.01, 0.012, 0.20, 8), te);
  micArm.position.set(-0.54, 0.72, 0.34);
  micArm.rotation.set(0.35, -0.15, 0.10);
  group.add(micArm);

  // 耳麦琥珀指示灯
  const micLight = new THREE.Mesh(new THREE.SphereGeometry(0.012, 6, 6), am);
  micLight.position.set(-0.55, 0.62, 0.40);
  group.add(micLight);

  // ══════════════════ 十七、领口琥珀点缀 ══════════════════
  const accent = new THREE.Mesh(new THREE.SphereGeometry(0.025, 6, 6), am);
  accent.position.set(0.16, 0.24, 0.45);
  group.add(accent);

  // ════════════════ 返回 ════════════════
  return {
    group, head, leftEye, rightEye, leftPupil, rightPupil,
    mouth: mouthGroup, leftBrow, rightBrow,
  };
}
