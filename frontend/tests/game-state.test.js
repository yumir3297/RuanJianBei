import test from "node:test";
import assert from "node:assert/strict";

import {
  GAME_STATES as S,
  WORLD,
  checkCollision,
  createGameState,
  jump,
  pauseGame,
  resetGame,
  resumeGame,
  startGame,
  updateGame,
} from "../src/offline/game-state.js";

function runningState(seed = 42) {
  const state = createGameState({ seed, bestScore: 0 });
  startGame(state);
  return state;
}

test("开始/暂停/继续/重开的状态流转", () => {
  const state = createGameState({ seed: 1 });
  assert.equal(state.status, S.READY);
  startGame(state);
  assert.equal(state.status, S.RUNNING);
  pauseGame(state);
  assert.equal(state.status, S.PAUSED);
  resumeGame(state);
  assert.equal(state.status, S.RUNNING);
  state.score = 88;
  resetGame(state);
  assert.equal(state.status, S.READY);
  assert.equal(state.score, 0);
});

test("GAME-01 只有落地时才能起跳", () => {
  const state = runningState();
  assert.equal(jump(state), true);
  assert.equal(state.grounded, false);
  assert.equal(jump(state), false);

  for (let i = 0; i < 200; i += 1) updateGame(state, 16);
  assert.equal(state.grounded, true);
  assert.equal(jump(state), true);
});

test("GAME-03 单帧 delta 被钳制，后台恢复不会瞬移", () => {
  const state = runningState();
  const before = state.distance;
  updateGame(state, 10_000);
  assert.ok(state.distance - before <= WORLD.baseSpeed * 0.05 + 1);
});

test("GAME-01 碰撞结束并在 1 秒内可重开", () => {
  const state = runningState();
  state.obstacles.push({ id: 1, kind: "rock", x: WORLD.playerX, width: 28, height: 26 });
  assert.equal(checkCollision(state), true);
  const changed = updateGame(state, 16);
  assert.equal(changed, true);
  assert.equal(state.status, S.GAME_OVER);
  assert.ok(state.bestScore >= state.lastRunScore);
  assert.equal(state.lastRunScore, state.score);
  resetGame(state);
  startGame(state);
  assert.equal(state.status, S.RUNNING);
  assert.equal(state.obstacles.length, 0);
});

test("已跳过障碍时不误判碰撞", () => {
  const state = runningState();
  state.obstacles.push({ id: 1, kind: "rock", x: WORLD.playerX, width: 28, height: 26 });
  state.playerY = 120;
  state.grounded = false;
  assert.equal(checkCollision(state), false);
});

test("暂停时画面不再推进", () => {
  const state = runningState();
  pauseGame(state);
  const distance = state.distance;
  updateGame(state, 16);
  assert.equal(state.distance, distance);
});

test("同 seed 下障碍生成序列可复现", () => {
  const a = runningState(7);
  const b = runningState(7);
  for (let i = 0; i < 400; i += 1) {
    updateGame(a, 16);
    updateGame(b, 16);
  }
  assert.deepEqual(
    a.obstacles.map((item) => `${item.kind}:${item.x.toFixed(3)}`),
    b.obstacles.map((item) => `${item.kind}:${item.x.toFixed(3)}`),
  );
});

test("速度随距离提升但有上限", () => {
  const state = runningState();
  state.distance = 1_000_000;
  updateGame(state, 16);
  assert.ok(state.speed <= WORLD.baseSpeed + WORLD.maxSpeedBonus);
  assert.ok(state.score > 0);
});
