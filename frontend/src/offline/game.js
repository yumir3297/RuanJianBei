/**
 * 固定场景 Q 版跑酷渲染层：Canvas 2D + requestAnimationFrame。
 * 规则全部在 game-state.js；这里只处理画布尺寸、绘制与生命周期。
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

const COLORS = Object.freeze({
  skyTop: "#dce9e2",
  skyBottom: "#f4efe2",
  hillFar: "#a8c3ae",
  hillNear: "#7ea78c",
  ground: "#35594a",
  groundLine: "#22402f",
  ink: "#1f3a2d",
  accent: "#c25b3a",
});

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

function drawPlayer(ctx, state, runPhase) {
  const feetY = state.playerY;
  const x = WORLD.playerX;
  const airborne = !state.grounded;
  const legSwing = airborne ? 0.35 : Math.sin(runPhase) * 0.55;

  ctx.save();
  // 影子
  const shadowScale = Math.max(0.45, 1 - (WORLD.groundY - feetY) / 140);
  ctx.globalAlpha = 0.18 * shadowScale;
  ctx.fillStyle = COLORS.ink;
  ctx.beginPath();
  ctx.ellipse(x + 17, WORLD.groundY + 3, 16 * shadowScale, 4 * shadowScale, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 1;

  // 腿
  ctx.strokeStyle = COLORS.ink;
  ctx.lineWidth = 5;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(x + 12, feetY - 14);
  ctx.lineTo(x + 12 - legSwing * 8, feetY - 2);
  ctx.moveTo(x + 22, feetY - 14);
  ctx.lineTo(x + 22 + legSwing * 8, feetY - 2);
  ctx.stroke();

  // 身体
  ctx.fillStyle = "#e8845c";
  drawRoundRect(ctx, x + 7, feetY - 34, 20, 22, 8);
  ctx.fill();

  // 手臂
  ctx.strokeStyle = "#e8845c";
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.moveTo(x + 10, feetY - 30);
  ctx.lineTo(x + 4 - legSwing * 4, feetY - 20);
  ctx.moveTo(x + 24, feetY - 30);
  ctx.lineTo(x + 30 + legSwing * 4, feetY - 20);
  ctx.stroke();

  // 头
  ctx.fillStyle = "#f7d3b4";
  ctx.beginPath();
  ctx.arc(x + 17, feetY - 44, 11, 0, Math.PI * 2);
  ctx.fill();
  // 头发
  ctx.fillStyle = COLORS.ink;
  ctx.beginPath();
  ctx.arc(x + 17, feetY - 46, 11, Math.PI * 1.05, Math.PI * 1.95);
  ctx.fill();
  // 眼睛
  ctx.fillStyle = COLORS.ink;
  ctx.beginPath();
  ctx.arc(x + 21, feetY - 43, 1.6, 0, Math.PI * 2);
  ctx.fill();
  // 围巾
  ctx.fillStyle = "#3f7d68";
  drawRoundRect(ctx, x + 8, feetY - 35, 18, 5, 2.5);
  ctx.fill();
  ctx.restore();
}

function drawObstacle(ctx, obstacle) {
  const size = { width: obstacle.width, height: obstacle.height };
  const baseY = WORLD.groundY;
  ctx.save();
  if (obstacle.kind === "sign") {
    ctx.fillStyle = "#8a6a4a";
    ctx.fillRect(obstacle.x + size.width / 2 - 2, baseY - size.height + 12, 4, size.height - 12);
    ctx.fillStyle = "#cf7a4c";
    drawRoundRect(ctx, obstacle.x, baseY - size.height, size.width, 16, 3);
    ctx.fill();
    ctx.strokeStyle = "#7c4128";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  } else if (obstacle.kind === "crate") {
    ctx.fillStyle = "#b98a55";
    drawRoundRect(ctx, obstacle.x, baseY - size.height, size.width, size.height, 4);
    ctx.fill();
    ctx.strokeStyle = "#8a6238";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(obstacle.x + 3, baseY - size.height + 3);
    ctx.lineTo(obstacle.x + size.width - 3, baseY - 3);
    ctx.moveTo(obstacle.x + size.width - 3, baseY - size.height + 3);
    ctx.lineTo(obstacle.x + 3, baseY - 3);
    ctx.stroke();
  } else {
    ctx.fillStyle = "#7d8f83";
    ctx.beginPath();
    ctx.moveTo(obstacle.x, baseY);
    ctx.lineTo(obstacle.x + 6, baseY - size.height + 6);
    ctx.lineTo(obstacle.x + size.width * 0.55, baseY - size.height);
    ctx.lineTo(obstacle.x + size.width, baseY - size.height + 9);
    ctx.lineTo(obstacle.x + size.width - 4, baseY);
    ctx.closePath();
    ctx.fill();
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
    const scaleX = width / WORLD.width;
    const scaleY = height / WORLD.height;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.setTransform(scaleX, 0, 0, scaleY, 0, 0);

    const sky = ctx.createLinearGradient(0, 0, 0, WORLD.groundY);
    sky.addColorStop(0, COLORS.skyTop);
    sky.addColorStop(1, COLORS.skyBottom);
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, WORLD.width, WORLD.height);

    const drift = motionReduced ? 0 : (state.distance * 0.12) % WORLD.width;
    ctx.fillStyle = COLORS.hillFar;
    ctx.globalAlpha = 0.55;
    for (let index = -1; index < 3; index += 1) {
      const baseX = index * 280 - drift * 0.3;
      ctx.beginPath();
      ctx.moveTo(baseX, WORLD.groundY);
      ctx.quadraticCurveTo(baseX + 100, WORLD.groundY - 92, baseX + 210, WORLD.groundY);
      ctx.fill();
    }
    ctx.globalAlpha = 1;

    const nearDrift = motionReduced ? 0 : (state.distance * 0.55) % 360;
    ctx.fillStyle = COLORS.hillNear;
    ctx.globalAlpha = 0.7;
    for (let index = -1; index < 3; index += 1) {
      const baseX = index * 240 - nearDrift;
      ctx.beginPath();
      ctx.moveTo(baseX, WORLD.groundY);
      ctx.quadraticCurveTo(baseX + 80, WORLD.groundY - 52, baseX + 180, WORLD.groundY);
      ctx.fill();
    }
    ctx.globalAlpha = 1;

    ctx.fillStyle = COLORS.ground;
    ctx.fillRect(0, WORLD.groundY, WORLD.width, WORLD.height - WORLD.groundY);
    ctx.strokeStyle = COLORS.groundLine;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(0, WORLD.groundY + 1.5);
    ctx.lineTo(WORLD.width, WORLD.groundY + 1.5);
    ctx.stroke();

    // 地面短划线
    const dashDrift = (state.distance * 0.9) % 48;
    ctx.fillStyle = "rgba(255,255,255,0.22)";
    for (let x = -48; x < WORLD.width + 48; x += 48) {
      ctx.fillRect(x - dashDrift, WORLD.groundY + 14, 22, 4);
    }

    for (const obstacle of state.obstacles) drawObstacle(ctx, obstacle);
    drawPlayer(ctx, state, runPhase);
  }

  function frame(timestamp) {
    animationId = null;
    if (destroyed) return;
    const delta = lastTimestamp ? timestamp - lastTimestamp : 16;
    lastTimestamp = timestamp;

    if (state.status === GAME_STATES.RUNNING) {
      runPhase += delta / 1000 * 14;
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
