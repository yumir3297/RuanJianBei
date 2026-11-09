import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';

let vite;
let player;
let releaseOldDecode;
let starts = [];
let startTimes = [];
let nodes = [];
let decodeCount = 0;
let audioContext;

before(async () => {
  class FakeAudioContext {
    constructor() { this.state = 'running'; this.currentTime = 0; this.destination = {}; audioContext = this; }
    createAnalyser() { return { connect() {}, getByteTimeDomainData(data) { data.fill(128); } }; }
    createGain() { return { gain: { value: 1 }, connect() {}, disconnect() {} }; }
    resume() { return Promise.resolve(); }
    createBuffer(channels, length, sampleRate) {
      return { length, duration: length / sampleRate, getChannelData() { return new Float32Array(length); } };
    }
    createBufferSource() {
      const node = { playbackRate: { value: 1 }, connect() {}, disconnect() {},
        start(time = 0) { starts.push(node.buffer.id); startTimes.push(time); }, stop() { this.stopped = true; this.onended?.(); } };
      nodes.push(node);
      return node;
    }
    decodeAudioData() {
      decodeCount++;
      if (decodeCount === 1) return new Promise(resolve => { releaseOldDecode = resolve; });
      return Promise.resolve({ id: 'new', duration: 1 });
    }
  }
  globalThis.window = { AudioContext: FakeAudioContext };
  globalThis.AudioContext = FakeAudioContext;
  globalThis.requestAnimationFrame = () => 1;
  globalThis.cancelAnimationFrame = () => {};
  vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-audio-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  player = (await vite.ssrLoadModule('/src/composables/useAudioPlayer.js')).useAudioPlayer();
});

after(async () => { player?.stop(); await vite?.close(); });

test('an audio decode finishing after stop cannot play or end a newer answer', async () => {
  const old = player.enqueue('AA==');
  await Promise.resolve();
  player.stop();
  const current = player.enqueue('AA==');
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.deepEqual(starts, ['new']);
  releaseOldDecode({ id: 'old', duration: 1 });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.deepEqual(starts, ['new']);
  assert.equal(player.isPlaying.value, true);
  nodes.at(-1).onended();
  await Promise.all([old, current]);
});

test('a delayed PCM progress callback cannot update a newer stream', () => {
  const originalSetInterval = globalThis.setInterval;
  const originalClearInterval = globalThis.clearInterval;
  const timers = [];
  globalThis.setInterval = (callback) => { timers.push(callback); return timers.length; };
  globalThis.clearInterval = () => {};
  try {
    let newerUpdates = 0;
    player.startPCMStream(() => {}, () => {});
    player.feedPCMChunk('AAA=', 24000, 1, 16);
    const oldTick = timers[0];
    player.stop();
    player.startPCMStream(() => { newerUpdates++; }, () => {});
    player.feedPCMChunk('AAA=', 24000, 1, 16);
    oldTick();
    assert.equal(newerUpdates, 0);
  } finally {
    player.stop();
    globalThis.setInterval = originalSetInterval;
    globalThis.clearInterval = originalClearInterval;
  }
});

test('after a network stall PCM chunks resume in order without scheduling in the past', () => {
  startTimes = [];
  player.startPCMStream(null, null);
  audioContext.currentTime = 0;
  player.feedPCMChunk('AAA=', 24000, 1, 16);
  audioContext.currentTime = 1;
  player.feedPCMChunk('AAA=', 24000, 1, 16);
  player.feedPCMChunk('AAA=', 24000, 1, 16);
  assert.equal(startTimes[1], 1);
  assert.ok(startTimes[2] > startTimes[1]);
  player.stop();
});

test('experimental buffering adds a bounded recovery delay after a large stall', () => {
  startTimes = [];
  player.startPCMStream(null, null, null, { adaptive: true });
  if (audioContext) audioContext.currentTime = 0;
  player.feedPCMChunk('AAA=', 24000, 1, 16);
  audioContext.currentTime = 0;
  audioContext.currentTime = 1;
  player.feedPCMChunk('AAA=', 24000, 1, 16);
  assert.equal(startTimes[1], 1.08);
  player.stop();
});

test('a suspended audio context keeps pending PCM stoppable until it can play', () => {
  const originalSetTimeout = globalThis.setTimeout;
  const originalClearTimeout = globalThis.clearTimeout;
  const timers = [];
  globalThis.setTimeout = (callback) => { timers.push(callback); return timers.length; };
  globalThis.clearTimeout = () => {};
  try {
    player.startPCMStream(null, null);
    player.feedPCMChunk('AAA=', 24000, 1, 16);
    const source = nodes.at(-1);
    audioContext.state = 'suspended';
    player.endPCMStream();
    timers[0]();
    assert.equal(player.isPCMStreaming.value, true);
    player.stop();
    assert.equal(source.stopped, true);
  } finally {
    audioContext.state = 'running';
    player.stop();
    globalThis.setTimeout = originalSetTimeout;
    globalThis.clearTimeout = originalClearTimeout;
  }
});

test('a browser that never resumes audio eventually reports voice unavailable', async () => {
  const originalSetTimeout = globalThis.setTimeout;
  const originalClearTimeout = globalThis.clearTimeout;
  const timers = [];
  globalThis.setTimeout = (callback) => { timers.push(callback); return timers.length; };
  globalThis.clearTimeout = () => {};
  try {
    let unavailable = 0;
    player.startPCMStream(null, null, null, { onUnavailable: () => { unavailable++; } });
    audioContext.state = 'suspended';
    audioContext.resume = () => new Promise(() => {});
    player.feedPCMChunk('AAA=', 24000, 1, 16);
    await Promise.resolve();
    timers[0]();
    assert.equal(unavailable, 1);
    assert.equal(player.isPlaying.value, false);
  } finally {
    audioContext.state = 'running';
    player.stop();
    globalThis.setTimeout = originalSetTimeout;
    globalThis.clearTimeout = originalClearTimeout;
  }
});

test('a map session replaces chat playback and a stale chat session cannot enqueue or stop it', async () => {
  starts = [];
  const interrupted = [];
  const chatSession = player.claimPlayback('chat', reason => interrupted.push(reason));
  assert.equal(player.activePlayback.value.owner, 'chat');
  const chatPlayback = player.enqueue('AA==', 800, () => assert.fail('replaced chat playback must not finish'), '', null, {
    sessionId: chatSession.id,
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.deepEqual(starts, ['new']);

  const mapSession = player.claimPlayback('map-narration');
  assert.equal(player.activePlayback.value.owner, 'map-narration');
  await chatPlayback;
  assert.deepEqual(interrupted, ['replaced']);

  assert.equal(await player.enqueue('AA==', 800, null, '', null, { sessionId: chatSession.id }), false);
  const mapPlayback = player.enqueue('AA==', 800, null, '', null, { sessionId: mapSession.id });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(player.stop(chatSession.id), false);
  assert.equal(player.isPlaying.value, true);

  nodes.at(-1).onended();
  await mapPlayback;
  player.stop(mapSession.id);
  assert.equal(player.activePlayback.value, null);
});

test('a replaced PCM session cannot start, feed, or end the current owner stream', () => {
  const chatSession = player.claimPlayback('chat');
  const mapSession = player.claimPlayback('map-narration');
  assert.equal(player.startPCMStream(null, null, null, { sessionId: chatSession.id }), false);
  assert.equal(player.startPCMStream(null, null, null, { sessionId: mapSession.id }), true);
  assert.equal(player.feedPCMChunk('AAA=', 24000, 1, 16, chatSession.id), false);
  player.endPCMStream(chatSession.id);
  assert.equal(player.isPCMStreaming.value, true);
  player.stop(mapSession.id);
});

test('unlocking audio for map controls does not stop the current playback owner', async () => {
  const chatSession = player.claimPlayback('chat');
  const playback = player.enqueue('AA==', 800, null, '', null, { sessionId: chatSession.id });
  await new Promise(resolve => setTimeout(resolve, 0));

  await player.unlock();
  assert.equal(player.isPlaying.value, true);
  assert.equal(player.activePlayback.value.owner, 'chat');

  nodes.at(-1).onended();
  await playback;
  player.stop(chatSession.id);
});

test('AudioBuffer rate changes output speed while progress stays in content time', async () => {
  const originalSetInterval = globalThis.setInterval;
  const originalClearInterval = globalThis.clearInterval;
  const ticks = [];
  const reports = [];
  globalThis.setInterval = (callback) => { ticks.push(callback); return ticks.length; };
  globalThis.clearInterval = () => {};
  try {
    audioContext.currentTime = 0;
    const pending = player.enqueue('AA==', 1000, null, '', (...args) => reports.push(args), { rate: 1.5 });
    await new Promise(resolve => setTimeout(resolve, 0));
    assert.equal(nodes.at(-1).playbackRate.value, 1.5);
    audioContext.currentTime = 0.2;
    ticks.at(-1)();
    assert.deepEqual(reports.at(-1), [0.3, 300, 1000]);
    nodes.at(-1).onended();
    await pending;
  } finally {
    player.stop();
    globalThis.setInterval = originalSetInterval;
    globalThis.clearInterval = originalClearInterval;
  }
});

test('PCM rate shortens source scheduling and reports source-content progress', () => {
  const originalSetInterval = globalThis.setInterval;
  const originalClearInterval = globalThis.clearInterval;
  const ticks = [];
  const reports = [];
  globalThis.setInterval = (callback) => { ticks.push(callback); return ticks.length; };
  globalThis.clearInterval = () => {};
  try {
    startTimes = [];
    audioContext.currentTime = 0;
    player.startPCMStream((...args) => reports.push(args), null, null, { rate: 1.5 });
    const chunk = Buffer.alloc(2400 * 2).toString('base64'); // 100 ms at 24 kHz
    player.feedPCMChunk(chunk, 24000, 1, 16);
    player.feedPCMChunk(chunk, 24000, 1, 16);
    assert.equal(nodes.at(-1).playbackRate.value, 1.5);
    assert.ok(Math.abs(startTimes[1] - 100 / 1500) < 0.000001);
    audioContext.currentTime = 0.02;
    ticks.at(-1)();
    assert.ok(Math.abs(reports.at(-1)[1] - 30) < 0.001);
    assert.ok(Math.abs(reports.at(-1)[2] - 200) < 0.001);
    assert.ok(Math.abs(reports.at(-1)[0] - 0.15) < 0.001);
  } finally {
    player.stop();
    globalThis.setInterval = originalSetInterval;
    globalThis.clearInterval = originalClearInterval;
  }
});
