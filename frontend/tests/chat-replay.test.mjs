import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';

let vite;
let createChatReplayController;

before(async () => {
  vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-chat-replay-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ createChatReplayController } = await vite.ssrLoadModule('/src/utils/chatReplay.js'));
});

after(async () => { await vite?.close(); });

test('replay requests the saved record and sends it through the shared player at the current rate', async () => {
  const calls = { request: null, enqueue: null, unlockedBeforeRequest: false };
  const message = { chatLogId: 17, content: '保存的完整回答', completion: 'complete' };
  const player = {
    claimPlayback: () => ({ id: 42 }),
    unlock: () => { calls.unlockedBeforeRequest = true; },
    isCurrentPlaybackSession: (id) => id === 42,
    async enqueue(...args) { calls.enqueue = args; },
  };
  const controller = createChatReplayController({
    requestReplay: async (payload) => {
      assert.equal(calls.unlockedBeforeRequest, true);
      calls.request = payload;
      return { base64_audio: 'voice-data', duration_ms: 1200, available: true };
    },
    audioPlayer: player,
    getSessionId: () => 'session-abc',
    getVoice: () => 'deep-male',
    getRate: () => 1.2,
  });

  await controller.replay(message);

  assert.deepEqual(calls.request, {
    chat_log_id: 17,
    session_id: 'session-abc',
    tts_voice: 'deep-male',
  });
  assert.equal(calls.enqueue[0], 'voice-data');
  assert.equal(calls.enqueue[3], '保存的完整回答');
  assert.equal(calls.enqueue[5].sessionId, 42);
  assert.equal(calls.enqueue[5].rate, 1.2);
  assert.equal(calls.enqueue[5].allowBrowserSpeech, true);
  assert.equal(message.replayPlaying, true);
});

test('an unavailable TTS response allows browser speech with the saved answer text', async () => {
  let enqueueOptions;
  const player = {
    claimPlayback: () => ({ id: 3 }),
    isCurrentPlaybackSession: () => true,
    async enqueue(...args) { enqueueOptions = args[5]; },
  };
  const controller = createChatReplayController({
    requestReplay: async () => ({ base64_audio: '', duration_ms: 0, available: false }),
    audioPlayer: player,
    getSessionId: () => 'session',
    getVoice: () => null,
    getRate: () => 0.8,
  });
  const message = { chatLogId: 2, content: '可朗读文本', completion: 'complete' };

  await controller.replay(message);

  assert.equal(enqueueOptions.allowBrowserSpeech, true);
  assert.equal(enqueueOptions.rate, 0.8);
});

test('a replay response that arrives after playback ownership changed is discarded', async () => {
  let resolveReplay;
  let enqueueCalls = 0;
  let current = true;
  const player = {
    claimPlayback: () => ({ id: 9 }),
    isCurrentPlaybackSession: () => current,
    async enqueue() { enqueueCalls++; },
  };
  const controller = createChatReplayController({
    requestReplay: () => new Promise((resolve) => { resolveReplay = resolve; }),
    audioPlayer: player,
    getSessionId: () => 'session',
    getVoice: () => null,
    getRate: () => 1,
  });
  const message = { chatLogId: 3, content: '旧回答', completion: 'complete' };
  const pending = controller.replay(message);
  current = false;
  resolveReplay({ base64_audio: 'late', duration_ms: 500, available: true });

  await pending;

  assert.equal(enqueueCalls, 0);
  assert.equal(message.replayPlaying, false);
});

test('replacing a pending replay does not clear the new replay loading state', async () => {
  const pending = [];
  let nextId = 0;
  let activeStop = null;
  let currentId = null;
  const player = {
    claimPlayback(_owner, onStopped) {
      activeStop?.();
      currentId = ++nextId;
      activeStop = onStopped;
      return { id: currentId };
    },
    isCurrentPlaybackSession: (id) => currentId === id,
    async enqueue() {},
  };
  const controller = createChatReplayController({
    requestReplay: () => new Promise((resolve) => pending.push(resolve)),
    audioPlayer: player,
    getSessionId: () => 'session',
    getVoice: () => null,
    getRate: () => 1,
  });
  const message = { chatLogId: 5, content: '回答', completion: 'complete' };
  const first = controller.replay(message);
  const second = controller.replay(message);

  assert.equal(message.replayLoading, true);
  pending[1]({ base64_audio: 'current', duration_ms: 800, available: true });
  await second;
  pending[0]({ base64_audio: 'stale', duration_ms: 800, available: true });
  await first;
});

test('incomplete or unsaved answers cannot be replayed', async () => {
  let requestCalls = 0;
  const controller = createChatReplayController({
    requestReplay: async () => { requestCalls++; return {}; },
    audioPlayer: { claimPlayback() { throw new Error('must not claim playback'); } },
    getSessionId: () => 'session',
    getVoice: () => null,
    getRate: () => 1,
  });

  await controller.replay({ content: '尚未保存', completion: 'complete' });
  await controller.replay({ chatLogId: 5, content: '未完成', completion: 'incomplete' });

  assert.equal(requestCalls, 0);
});
