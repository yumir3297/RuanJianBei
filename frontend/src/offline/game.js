/**
 * 固定场景 Q 版跑酷渲染层：Canvas 2D + requestAnimationFrame。
 * 规则全部在 game-state.js；这里只处理画布尺寸、绘制与生命周期。
 *
 * 画风：纸雕山水（分层撕纸山峦 + 墨线小人 + 朱砂印章），
 * 参考 Tengami 的纸片层次与 Alto's Odyssey 的剪影视差 + 极简 HUD。
 */

import {
  GAME_STATES,
  WORLD,
  createGameState,
  pauseGame,
  resetGame,
  resumeGame,
  startGame,
  jump as tryJump,
  updateGame,
} from "./game-state.js";

const PALETTE = Object.freeze({
  paper: "#f4eddc",
  paperLight: "#fbf6ea",
  ink: "#242b26",
  far: "#c2cfbe",
  mid: "#93ac96",
  near: "#6e8b72",
  ground: "#4f6357",
  groundDeep: "#33463c",
  zhu: "#b4462f",
  zhuDark: "#8e3323",
  gold: "#c39a5c",
  stone: "#9aa894",
  stoneDeep: "#6e7c6c",
  lantern: "#8e7b5f",
  lanternDeep: "#63543f",
  pine: "#6f8a72",
  pineDeep: "#4f6a55",
});

function mulberrySeed(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// 撕纸山脊：用多个高斯峰叠出山形，首尾等高，保证平移时无缝拼接。
function createRidge(seed, samples = 19) {
  const random = mulberrySeed(seed);
  const peaks = [
    { at: 0.18 + random() * 0.08, width: 0.1 + random() * 0.03, height: 0.6 + random() * 0.24 },
    { at: 0.6 + random() * 0.1, width: 0.12 + random() * 0.04, height: 0.48 + random() * 0.28 },
    { at: 0.84 + random() * 0.04, width: 0.08 + random() * 0.02, height: 0.3 + random() * 0.2 },
  ];
  const base = 0.14;
  const ridge = [];
  for (let index = 0; index < samples; index += 1) {
    const t = index / (samples - 1);
    let y = base;
    for (const peak of peaks) {
      const falloff = (t - peak.at) / peak.width;
      y += peak.height * Math.exp(-(falloff * falloff));
    }
    y += (random() - 0.5) * 0.028;
    ridge.push({ x: t, y: Math.min(0.96, Math.max(0.1, y)) });
  }
  ridge[0].y = base;
  ridge[ridge.length - 1].y = base;
  return ridge;
}

const RIDGES = [
  { ridge: createRidge(11), period: 720, height: 148, baseY: 206, depth: 0.1, fill: PALETTE.far, edge: "rgba(251,246,234,0.85)" },
  { ridge: createRidge(29), period: 540, height: 118, baseY: 224, depth: 0.28, fill: PALETTE.mid, edge: "rgba(251,246,234,0.8)" },
  { ridge: createRidge(47), period: 400, height: 86, baseY: 240, depth: 0.52, fill: PALETTE.near, edge: "rgba(251,246,234,0.72)" },
];

const CLOUDS = [
  { x: 56, y: 58, width: 66, drift: 0.02 },
  { x: 214, y: 38, width: 48, drift: 0.032 },
  { x: 356, y: 78, width: 58, drift: 0.015 },
  { x: 500, y: 46, width: 40, drift: 0.026 },
];

function drawRoundRect(ctx, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
}

function createGrainPattern(ctx) {
  const tile = document.createElement("canvas");
  tile.width = 96;
  tile.height = 96;
  const tileCtx = tile.getContext("2d");
  const image = tileCtx.createImageData(tile.width, tile.height);
  for (let index = 0; index < image.data.length; index += 4) {
    const value = 150 + Math.floor(Math.random() * 90);
    image.data[index] = value;
    image.data[index + 1] = value;
    image.data[index + 2] = value;
    image.data[index + 3] = 16;
  }
  tileCtx.putImageData(image, 0, 0);
  return ctx.createPattern(tile, "repeat");
}

function drawCloud(ctx, x, y, width) {
  ctx.fillStyle = "rgba(251,246,234,0.92)";
  ctx.strokeStyle = "rgba(36,43,38,0.1)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(x, y + 9);
  ctx.quadraticCurveTo(x + 5, y - 4, x + width * 0.3, y + 2);
  ctx.quadraticCurveTo(x + width * 0.44, y - 8, x + width * 0.62, y + 1);
  ctx.quadraticCurveTo(x + width * 0.82, y - 5, x + width, y + 8);
  ctx.quadraticCurveTo(x + width * 0.58, y + 13, x, y + 9);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
}

function drawSky(ctx, distance, motion) {
  ctx.fillStyle = PALETTE.paper;
  ctx.fillRect(0, 0, WORLD.width, WORLD.height);

  // 朱砂日轮 + 淡淡纸晕
  ctx.save();
  ctx.globalAlpha = 0.16;
  ctx.fillStyle = PALETTE.zhu;
  ctx.beginPath();
  ctx.arc(508, 76, 52, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 0.88;
  ctx.beginPath();
  ctx.arc(508, 76, 38, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 0.3;
  ctx.strokeStyle = PALETTE.zhuDark;
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.arc(508, 76, 44, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();

  // 纸云
  ctx.save();
  const drift = motion ? distance * 0.02 : 0;
  for (const cloud of CLOUDS) {
    const x = ((cloud.x - drift * cloud.drift * 10) % (WORLD.width + 140) + WORLD.width + 140) % (WORLD.width + 140) - 70;
    drawCloud(ctx, x, cloud.y, cloud.width);
  }
  ctx.restore();

  // 归鸟
  ctx.save();
  ctx.strokeStyle = "rgba(36,43,38,0.36)";
  ctx.lineWidth = 1.6;
  ctx.lineCap = "round";
  const birdX = ((WORLD.width * 0.42 - distance * 0.05) % (WORLD.width + 80) + WORLD.width + 80) % (WORLD.width + 80) - 40;
  for (let index = 0; index < 3; index += 1) {
    const x = birdX + index * 16;
    const y = 56 + index * 7;
    ctx.beginPath();
    ctx.moveTo(x - 5, y);
    ctx.quadraticCurveTo(x, y - 4, x + 5, y);
    ctx.stroke();
  }
  ctx.restore();
}

function drawRidge(ctx, layer, distance, motion) {
  const offset = motion ? distance * layer.depth : 0;
  const start = -(offset % layer.period);
  const bottom = WORLD.height + 20;

  ctx.beginPath();
  ctx.moveTo(start, layer.baseY);
  const topPoints = [];
  for (let pass = 0; pass < 2; pass += 1) {
    for (const point of layer.ridge) {
      const x = start + pass * layer.period + point.x * layer.period;
      const y = layer.baseY - point.y * layer.height;
      ctx.lineTo(x, y);
      topPoints.push([x, y]);
    }
  }
  ctx.lineTo(start + layer.period * 2, bottom);
  ctx.lineTo(start, bottom);
  ctx.closePath();
  ctx.fillStyle = layer.fill;
  ctx.fill();

  // 纸边高光与下方浅影，制造“叠纸”的厚度感
  ctx.beginPath();
  topPoints.forEach(([x, y], index) => {
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = layer.edge;
  ctx.lineWidth = 1.6;
  ctx.lineJoin = "round";
  ctx.stroke();

  ctx.beginPath();
  topPoints.forEach(([x, y], index) => {
    if (index === 0) ctx.moveTo(x, y + 3);
    else ctx.lineTo(x, y + 3);
  });
  ctx.strokeStyle = "rgba(36,43,38,0.07)";
  ctx.lineWidth = 4;
  ctx.stroke();
}

function drawGround(ctx, distance, motion) {
  const top = WORLD.groundY;
  ctx.fillStyle = PALETTE.ground;
  ctx.fillRect(0, top, WORLD.width, WORLD.height - top);

  // 撕纸地面边缘
  ctx.save();
  ctx.strokeStyle = PALETTE.groundDeep;
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.moveTo(0, top + 1);
  for (let x = 0; x <= WORLD.width; x += 14) {
    ctx.lineTo(x, top + (x % 28 === 0 ? 2.2 : 0.6));
  }
  ctx.stroke();

  ctx.globalAlpha = 0.4;
  ctx.strokeStyle = PALETTE.paperLight;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, top + 3.6);
  ctx.lineTo(WORLD.width, top + 3.6);
  ctx.stroke();

  // 纸层横纹
  ctx.globalAlpha = 0.12;
  for (let y = top + 18; y < WORLD.height; y += 16) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(WORLD.width, y);
    ctx.stroke();
  }
  ctx.restore();

  // 草簇
  ctx.save();
  ctx.strokeStyle = "rgba(244,237,220,0.38)";
  ctx.lineWidth = 1.6;
  ctx.lineCap = "round";
  const grassOffset = motion ? (distance * 1.1) % 120 : 0;
  for (let x = -120 - grassOffset; x < WORLD.width + 120; x += 120) {
    const base = top + 18;
    ctx.beginPath();
    ctx.moveTo(x + 20, base);
    ctx.lineTo(x + 16, base - 9);
    ctx.moveTo(x + 26, base);
    ctx.lineTo(x + 26, base - 11);
    ctx.moveTo(x + 32, base);
    ctx.lineTo(x + 37, base - 7);
    ctx.stroke();
  }
  ctx.restore();

  // 碎石
  ctx.save();
  ctx.fillStyle = "rgba(29,39,32,0.32)";
  const pebbleOffset = motion ? distance % 96 : 0;
  for (let index = 0; index < 8; index += 1) {
    const x = ((index * 96 - pebbleOffset) % (WORLD.width + 96) + WORLD.width + 96) % (WORLD.width + 96) - 48;
    const y = top + 27 + (index % 3) * 9;
    ctx.beginPath();
    ctx.ellipse(x, y, 3.2, 1.8, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function drawBushes(ctx, distance, motion) {
  const period = 300;
  const offset = motion ? distance * 0.45 : 0;
  for (let index = 0; index < 4; index += 1) {
    const x =
      ((index * period - offset) % (WORLD.width + period) + WORLD.width + period) % (WORLD.width + period) -
      period / 2;
    const scale = 0.8 + (index % 2) * 0.28;
    const baseY = WORLD.groundY + 2;
    const height = 26 * scale;
    const width = 30 * scale;
    ctx.save();
    ctx.fillStyle = PALETTE.pineDeep;
    ctx.globalAlpha = 0.55;
    ctx.beginPath();
    ctx.moveTo(x - width / 2, baseY);
    ctx.lineTo(x, baseY - height);
    ctx.lineTo(x + width / 2, baseY);
    ctx.closePath();
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(x - width * 0.36, baseY - height * 0.42);
    ctx.lineTo(x, baseY - height * 1.25);
    ctx.lineTo(x + width * 0.36, baseY - height * 0.42);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }
}

function drawPlayer(ctx, state, runPhase) {
  const feetY = state.playerY;
  const x = WORLD.playerX;
  const airborne = !state.grounded;
  const swing = airborne ? 0.18 : Math.sin(runPhase) * 0.62;
  const centerX = x + 17;
  const headY = feetY - 45;
  const shoulderY = feetY - 35;
  const hemY = feetY - 19;
  const legTop = hemY - 1;

  ctx.save();
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  // 纸面投影
  const shadowScale = Math.max(0.5, 1 - (WORLD.groundY - feetY) / 160);
  ctx.globalAlpha = 0.13;
  ctx.fillStyle = PALETTE.ink;
  ctx.beginPath();
  ctx.ellipse(centerX, WORLD.groundY + 3, 19 * shadowScale, 3.8 * shadowScale, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 1;

  // 飘带（画在身后，两条细带）
  ctx.strokeStyle = PALETTE.gold;
  ctx.lineWidth = 1.7;
  ctx.beginPath();
  ctx.moveTo(centerX - 7, headY + 14);
  ctx.bezierCurveTo(
    centerX - 18,
    headY + 14 + Math.sin(runPhase) * 3,
    centerX - 25,
    headY + 26 - Math.sin(runPhase) * 2,
    centerX - 34,
    headY + 21,
  );
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(centerX - 7, headY + 17);
  ctx.bezierCurveTo(
    centerX - 16,
    headY + 20 + Math.sin(runPhase + 0.6) * 3,
    centerX - 24,
    headY + 30,
    centerX - 31,
    headY + 27,
  );
  ctx.stroke();

  // 腿与布鞋
  ctx.strokeStyle = PALETTE.ink;
  ctx.lineWidth = 3.4;
  ctx.beginPath();
  ctx.moveTo(centerX - 5, legTop);
  ctx.lineTo(centerX - 6 - swing * 10, feetY - 2);
  ctx.moveTo(centerX + 5, legTop);
  ctx.lineTo(centerX + 6 + swing * 10, feetY - 2);
  ctx.stroke();
  ctx.fillStyle = PALETTE.ink;
  ctx.beginPath();
  ctx.ellipse(centerX - 6 - swing * 10, feetY - 1, 4, 2, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.ellipse(centerX + 6 + swing * 10, feetY - 1, 4, 2, 0, 0, Math.PI * 2);
  ctx.fill();

  // 长袍
  ctx.fillStyle = PALETTE.zhu;
  ctx.strokeStyle = PALETTE.ink;
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.moveTo(centerX - 10, shoulderY);
  ctx.quadraticCurveTo(centerX, shoulderY - 5, centerX + 10, shoulderY);
  ctx.lineTo(centerX + 12, hemY - 2);
  ctx.quadraticCurveTo(centerX, hemY + 4, centerX - 12, hemY - 2);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  // 衣襟与腰带
  ctx.strokeStyle = "rgba(251,246,234,0.9)";
  ctx.lineWidth = 1.7;
  ctx.beginPath();
  ctx.moveTo(centerX - 4.5, shoulderY + 1);
  ctx.lineTo(centerX + 1, shoulderY + 12);
  ctx.lineTo(centerX + 7, shoulderY + 1);
  ctx.stroke();
  ctx.strokeStyle = PALETTE.gold;
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  ctx.moveTo(centerX - 10, shoulderY + 13);
  ctx.lineTo(centerX + 10, shoulderY + 13);
  ctx.stroke();

  // 袖子与手
  ctx.strokeStyle = PALETTE.ink;
  ctx.lineWidth = 3.2;
  ctx.beginPath();
  ctx.moveTo(centerX - 9, shoulderY + 4);
  ctx.lineTo(centerX - 15 - swing * 5, shoulderY + 16);
  ctx.moveTo(centerX + 9, shoulderY + 4);
  ctx.lineTo(centerX + 15 + swing * 5, shoulderY + 16);
  ctx.stroke();
  ctx.fillStyle = PALETTE.paperLight;
  ctx.beginPath();
  ctx.arc(centerX - 15 - swing * 5, shoulderY + 16, 2.4, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(centerX + 15 + swing * 5, shoulderY + 16, 2.4, 0, Math.PI * 2);
  ctx.fill();

  // 头部
  ctx.fillStyle = PALETTE.paperLight;
  ctx.strokeStyle = PALETTE.ink;
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.arc(centerX, headY, 13.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();

  // 刘海、发髻与发簪
  ctx.fillStyle = PALETTE.ink;
  ctx.beginPath();
  ctx.moveTo(centerX - 13.5, headY - 2);
  ctx.quadraticCurveTo(centerX - 11, headY - 17, centerX + 2, headY - 15);
  ctx.quadraticCurveTo(centerX + 13.5, headY - 13, centerX + 13.5, headY - 1);
  ctx.quadraticCurveTo(centerX + 4, headY - 9, centerX - 13.5, headY - 2);
  ctx.closePath();
  ctx.fill();
  ctx.beginPath();
  ctx.arc(centerX - 7, headY - 17, 4.6, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = PALETTE.gold;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(centerX - 12, headY - 17);
  ctx.lineTo(centerX + 1, headY - 20.5);
  ctx.stroke();

  // 五官
  ctx.fillStyle = PALETTE.ink;
  ctx.beginPath();
  ctx.arc(centerX - 3, headY + 2, 1.7, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(centerX + 6, headY + 2, 1.7, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "rgba(36,43,38,0.7)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.arc(centerX + 1.5, headY + 7, 2.2, Math.PI * 0.15, Math.PI * 0.85);
  ctx.stroke();
  ctx.fillStyle = "rgba(180,70,47,0.32)";
  ctx.beginPath();
  ctx.arc(centerX - 8, headY + 7, 2.6, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(centerX + 11, headY + 7, 2.6, 0, Math.PI * 2);
  ctx.fill();

  ctx.restore();
}

function drawRock(ctx, obstacle) {
  const x = obstacle.x;
  const baseY = WORLD.groundY;
  const width = obstacle.width;
  const height = obstacle.height;
  ctx.save();
  ctx.fillStyle = PALETTE.stone;
  ctx.strokeStyle = PALETTE.stoneDeep;
  ctx.lineWidth = 1.8;
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.moveTo(x, baseY);
  ctx.lineTo(x + width * 0.08, baseY - height * 0.55);
  ctx.lineTo(x + width * 0.38, baseY - height * 0.92);
  ctx.lineTo(x + width * 0.66, baseY - height * 0.78);
  ctx.lineTo(x + width, baseY - height * 0.32);
  ctx.lineTo(x + width * 0.9, baseY);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.strokeStyle = PALETTE.stoneDeep;
  ctx.globalAlpha = 0.5;
  ctx.beginPath();
  ctx.moveTo(x + width * 0.42, baseY - height * 0.7);
  ctx.lineTo(x + width * 0.5, baseY - height * 0.28);
  ctx.stroke();
  ctx.restore();
}

function drawLantern(ctx, obstacle) {
  const x = obstacle.x;
  const baseY = WORLD.groundY;
  const width = obstacle.width;
  const height = obstacle.height;
  const centerX = x + width / 2;
  ctx.save();
  ctx.strokeStyle = PALETTE.lanternDeep;
  ctx.lineWidth = 1.6;
  ctx.lineJoin = "round";
  ctx.fillStyle = PALETTE.lantern;

  ctx.beginPath();
  ctx.rect(x + width * 0.1, baseY - 6, width * 0.8, 6);
  ctx.fill();
  ctx.stroke();

  ctx.beginPath();
  ctx.rect(centerX - width * 0.16, baseY - height * 0.55, width * 0.32, height * 0.46);
  ctx.fill();
  ctx.stroke();

  ctx.beginPath();
  ctx.rect(x + width * 0.16, baseY - height * 0.52, width * 0.68, height * 0.3);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = PALETTE.paperLight;
  ctx.beginPath();
  ctx.rect(x + width * 0.28, baseY - height * 0.46, width * 0.28, height * 0.18);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = PALETTE.gold;
  ctx.globalAlpha = 0.85;
  ctx.beginPath();
  ctx.arc(x + width * 0.42, baseY - height * 0.37, width * 0.08, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 1;

  ctx.fillStyle = PALETTE.lanternDeep;
  ctx.beginPath();
  ctx.moveTo(x - width * 0.06, baseY - height * 0.52);
  ctx.lineTo(x + width * 1.06, baseY - height * 0.52);
  ctx.lineTo(x + width * 0.84, baseY - height * 0.66);
  ctx.lineTo(x + width * 0.16, baseY - height * 0.66);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

function drawPine(ctx, obstacle) {
  const x = obstacle.x;
  const baseY = WORLD.groundY;
  const width = obstacle.width;
  const height = obstacle.height;
  const centerX = x + width / 2;
  ctx.save();
  ctx.strokeStyle = PALETTE.pineDeep;
  ctx.lineWidth = 1.6;
  ctx.lineJoin = "round";
  ctx.fillStyle = PALETTE.lanternDeep;
  ctx.beginPath();
  ctx.rect(centerX - width * 0.07, baseY - height * 0.36, width * 0.14, height * 0.36);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = PALETTE.pine;
  const tiers = [
    { y: baseY - height * 0.3, half: width * 0.46 },
    { y: baseY - height * 0.6, half: width * 0.36 },
    { y: baseY - height * 0.92, half: width * 0.24 },
  ];
  for (const tier of tiers) {
    ctx.beginPath();
    ctx.moveTo(centerX - tier.half, tier.y);
    ctx.lineTo(centerX, tier.y - height * 0.34);
    ctx.lineTo(centerX + tier.half, tier.y);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }
  ctx.restore();
}

function drawObstacle(ctx, obstacle) {
  if (obstacle.kind === "sign") drawLantern(ctx, obstacle);
  else if (obstacle.kind === "crate") drawPine(ctx, obstacle);
  else drawRock(ctx, obstacle);
}

function drawLeaves(ctx, distance) {
  ctx.save();
  ctx.fillStyle = PALETTE.zhu;
  for (let index = 0; index < 3; index += 1) {
    const x = ((WORLD.width - distance * (0.25 + index * 0.06) + index * 210) % (WORLD.width + 60) + WORLD.width + 60) % (WORLD.width + 60) - 30;
    const y = 46 + index * 22 + Math.sin(distance * 0.01 + index) * 8;
    ctx.globalAlpha = 0.5 - index * 0.1;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(distance * 0.004 + index);
    ctx.fillRect(-3, -3, 6, 6);
    ctx.restore();
  }
  ctx.restore();
}

export function createRunnerGame(options) {
  const { canvas, reducedMotion = false } = options;
  const ctx = canvas.getContext("2d");
  const listeners = {
    status: options.onStatusChange || (() => {}),
    score: options.onScore || (() => {}),
    gameover: options.onGameOver || (() => {}),
  };

  const state = createGameState({ bestScore: options.bestScore || 0 });
  const grain = createGrainPattern(ctx);
  let animationId = null;
  let lastTimestamp = 0;
  let runPhase = 0;
  let lastReportedScore = -1;
  let destroyed = false;
  let pausedByOverlay = false;
  let motionReduced = Boolean(reducedMotion);

  function emitStatus() {
    listeners.status(state.status, state);
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width));
    const height = Math.max(1, Math.round(rect.height));
    const dpr = Math.min(window.devicePixelRatio || 1, 3);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    render();
  }

  function render() {
    const width = canvas.width || 1;
    const height = canvas.height || 1;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, width, height);

    const scaleX = width / WORLD.width;
    const scaleY = height / WORLD.height;
    ctx.setTransform(scaleX, 0, 0, scaleY, 0, 0);

    const motion = !motionReduced;

    drawSky(ctx, state.distance, motion);
    drawRidge(ctx, RIDGES[0], state.distance, motion);
    drawRidge(ctx, RIDGES[1], state.distance, motion);
    drawRidge(ctx, RIDGES[2], state.distance, motion);
    drawBushes(ctx, state.distance, motion);
    drawGround(ctx, state.distance, motion);
    if (motion) drawLeaves(ctx, state.distance);

    for (const obstacle of state.obstacles) drawObstacle(ctx, obstacle);
    drawPlayer(ctx, state, runPhase);

    // 纸纹叠加：使用设备像素坐标，避免随缩放拉伸
    if (grain) {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalAlpha = 0.5;
      ctx.fillStyle = grain;
      ctx.fillRect(0, 0, width, height);
      ctx.globalAlpha = 1;
    }
  }

  function frame(timestamp) {
    animationId = null;
    if (destroyed) return;
    const delta = lastTimestamp ? timestamp - lastTimestamp : 16;
    lastTimestamp = timestamp;

    if (state.status === GAME_STATES.RUNNING) {
      runPhase += (delta / 1000) * 14;
      const collided = updateGame(state, delta);
      if (state.score !== lastReportedScore) {
        lastReportedScore = state.score;
        listeners.score(state.score, state.bestScore);
      }
      if (collided) {
        listeners.gameover(state.lastRunScore, state.bestScore, state);
        emitStatus();
      }
      render();
    }
    // 暂停/结束时停止帧循环，恢复时由 resume()/start() 重新拉起，
    // 避免后台空转，也避免恢复瞬间累积过大的 delta。
    if (!destroyed && state.status === GAME_STATES.RUNNING) {
      animationId = requestAnimationFrame(frame);
    }
  }

  function ensureLoop() {
    if (animationId == null && !destroyed) animationId = requestAnimationFrame(frame);
  }

  function start() {
    startGame(state);
    lastReportedScore = -1;
    lastTimestamp = 0;
    listeners.score(0, state.bestScore);
    emitStatus();
    render();
    ensureLoop();
  }

  function pause(reason = "manual") {
    if (state.status !== GAME_STATES.RUNNING) return false;
    pauseGame(state);
    lastTimestamp = 0;
    if (reason === "overlay") pausedByOverlay = true;
    render();
    emitStatus();
    return true;
  }

  function resume() {
    if (pausedByOverlay) return false;
    if (state.status !== GAME_STATES.PAUSED) return false;
    resumeGame(state);
    lastTimestamp = 0;
    emitStatus();
    ensureLoop();
    return true;
  }

  function setOverlayPaused(active) {
    if (active) {
      pause("overlay");
      return;
    }
    const shouldResume = pausedByOverlay && state.status === GAME_STATES.PAUSED;
    pausedByOverlay = false;
    if (shouldResume) resume();
  }

  function restart() {
    resetGame(state);
    start();
  }

  function jump() {
    if (state.status === GAME_STATES.READY || state.status === GAME_STATES.GAME_OVER) {
      start();
      return true;
    }
    if (state.status === GAME_STATES.PAUSED) return false;
    const jumped = tryJump(state);
    if (jumped) render();
    return jumped;
  }

  function setReducedMotion(value) {
    motionReduced = Boolean(value);
    render();
  }

  function handleVisibility() {
    if (document.visibilityState === "hidden") {
      pause("hidden");
    }
  }

  document.addEventListener("visibilitychange", handleVisibility);
  const resizeObserver =
    typeof ResizeObserver === "function"
      ? new ResizeObserver(() => resize())
      : null;
  resizeObserver?.observe(canvas);
  resize();

  return {
    start,
    pause,
    resume,
    restart,
    jump,
    setReducedMotion,
    setOverlayPaused,
    getState: () => state,
    destroy() {
      destroyed = true;
      if (animationId != null) cancelAnimationFrame(animationId);
      animationId = null;
      document.removeEventListener("visibilitychange", handleVisibility);
      resizeObserver?.disconnect();
    },
  };
}
