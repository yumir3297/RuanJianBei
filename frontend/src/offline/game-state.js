/**
 * Q 版跑酷的确定性状态与碰撞逻辑（无 DOM 依赖，可直接单测）。
 * 渲染在 game.js，本文件只负责规则。
 */

export const GAME_STATES = Object.freeze({
  READY: "READY",
  RUNNING: "RUNNING",
  PAUSED: "PAUSED",
  GAME_OVER: "GAME_OVER",
});

export const WORLD = Object.freeze({
  width: 640,
  height: 280,
  groundY: 236,
  gravity: 2200,
  jumpVelocity: -760,
  baseSpeed: 240,
  maxSpeedBonus: 330,
  speedRampPerPixel: 0.028,
  playerX: 96,
  playerWidth: 34,
  playerHeight: 44,
  scorePerPixel: 1 / 16,
});

const OBSTACLE_KINDS = Object.freeze({
  rock: { width: 30, height: 28, hitInsetX: 4, hitInsetY: 3 },
  sign: { width: 24, height: 50, hitInsetX: 3, hitInsetY: 4 },
  crate: { width: 32, height: 34, hitInsetX: 4, hitInsetY: 3 },
});

export const OBSTACLE_TYPES = Object.freeze(Object.keys(OBSTACLE_KINDS));

// mulberry32：把随机状态存进 state.rngState，保证同一 seed 下序列可复现。
function nextRandom(state) {
  state.rngState = (state.rngState + 0x6d2b79f5) >>> 0;
  let t = state.rngState;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}

export function createGameState(options = {}) {
  const rngState = Number.isFinite(options.seed) ? options.seed : Math.floor(Math.random() * 0xffffffff);
  return {
    status: GAME_STATES.READY,
    distance: 0,
    score: 0,
    bestScore: Math.max(0, Math.floor(Number(options.bestScore) || 0)),
    speed: WORLD.baseSpeed,
    elapsedMs: 0,
    playerY: WORLD.groundY,
    playerVy: 0,
    grounded: true,
    obstacles: [],
    nextObstacleId: 1,
    spawnCooldown: 1.1,
    rngState,
    lastRunScore: 0,
    reason: "",
  };
}

export function startGame(state) {
  const fresh = createGameState({ seed: state.rngState, bestScore: state.bestScore });
  Object.assign(state, fresh, { status: GAME_STATES.RUNNING });
  return state;
}

export function pauseGame(state) {
  if (state.status === GAME_STATES.RUNNING) state.status = GAME_STATES.PAUSED;
  return state;
}

export function resumeGame(state) {
  if (state.status === GAME_STATES.PAUSED) state.status = GAME_STATES.RUNNING;
  return state;
}

export function jump(state) {
  if (state.status !== GAME_STATES.RUNNING || !state.grounded) return false;
  state.playerVy = WORLD.jumpVelocity;
  state.grounded = false;
  return true;
}

export function playerHitbox(state) {
  const x = WORLD.playerX + 6;
  const width = WORLD.playerWidth - 12;
  const height = WORLD.playerHeight - 6;
  return { x, y: state.playerY - height, width, height };
}

export function obstacleHitbox(obstacle) {
  const spec = OBSTACLE_KINDS[obstacle.kind] || OBSTACLE_KINDS.rock;
  return {
    x: obstacle.x + spec.hitInsetX,
    y: WORLD.groundY - spec.height + spec.hitInsetY,
    width: spec.width - spec.hitInsetX * 2,
    height: spec.height - spec.hitInsetY * 2,
  };
}

export function obstacleSize(kind) {
  const spec = OBSTACLE_KINDS[kind] || OBSTACLE_KINDS.rock;
  return { width: spec.width, height: spec.height };
}

export function rectsOverlap(a, b) {
  return (
    a.x < b.x + b.width &&
    a.x + a.width > b.x &&
    a.y < b.y + b.height &&
    a.y + a.height > b.y
  );
}

export function checkCollision(state) {
  const player = playerHitbox(state);
  return state.obstacles.some((obstacle) => rectsOverlap(player, obstacleHitbox(obstacle)));
}

function spawnObstacle(state) {
  const kind = OBSTACLE_TYPES[Math.floor(nextRandom(state) * OBSTACLE_TYPES.length)] || "rock";
  const size = obstacleSize(kind);
  state.obstacles.push({
    id: state.nextObstacleId++,
    kind,
    x: WORLD.width + 24,
    width: size.width,
    height: size.height,
    bobPhase: nextRandom(state) * Math.PI * 2,
  });
}

/**
 * 推进一帧。dt 以毫秒计，内部钳制到 50ms，避免后台恢复后瞬移。
 * 返回本帧是否发生了状态变化（供 UI 更新）。
 */
export function updateGame(state, deltaMs) {
  if (state.status !== GAME_STATES.RUNNING) return false;
  const dtMs = Math.min(Math.max(Number(deltaMs) || 0, 0), 50);
  if (dtMs === 0) return false;

  const dt = dtMs / 1000;
  state.elapsedMs += dtMs;

  state.speed = WORLD.baseSpeed + Math.min(WORLD.maxSpeedBonus, state.distance * WORLD.speedRampPerPixel);
  state.distance += state.speed * dt;

  if (!state.grounded) {
    state.playerVy += WORLD.gravity * dt;
    state.playerY += state.playerVy * dt;
    if (state.playerY >= WORLD.groundY) {
      state.playerY = WORLD.groundY;
      state.playerVy = 0;
      state.grounded = true;
    }
  }

  for (const obstacle of state.obstacles) {
    obstacle.x -= state.speed * dt;
  }
  state.obstacles = state.obstacles.filter((obstacle) => obstacle.x + obstacle.width > -40);

  state.spawnCooldown -= dt;
  if (state.spawnCooldown <= 0) {
    spawnObstacle(state);
    const quickest = Math.max(0.72, 1.18 - state.distance * 0.00004);
    const spread = Math.max(0.28, 0.62 - state.distance * 0.00003);
    state.spawnCooldown = quickest + nextRandom(state) * spread;
  }

  state.score = Math.floor(state.distance * WORLD.scorePerPixel);

  if (checkCollision(state)) {
    state.status = GAME_STATES.GAME_OVER;
    state.lastRunScore = state.score;
    state.bestScore = Math.max(state.bestScore, state.score);
    state.reason = "collision";
    return true;
  }
  return false;
}

export function resetGame(state) {
  const bestScore = state.bestScore;
  Object.assign(state, createGameState({ seed: state.rngState, bestScore }));
  return state;
}
