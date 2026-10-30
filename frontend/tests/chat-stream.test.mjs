import { test, before, after, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';
import { createPinia, setActivePinia } from 'pinia';
import { watch } from 'vue';

let vite;
let useChatStore;
let useAudioPlayer;
let getRecentChatMetrics;
let originalFetch;

before(async () => {
  vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-chat-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ useChatStore } = await vite.ssrLoadModule('/src/stores/chat.js'));
  ({ useAudioPlayer } = await vite.ssrLoadModule('/src/composables/useAudioPlayer.js'));
  ({ getRecentChatMetrics } = await vite.ssrLoadModule('/src/utils/chatMetrics.js'));
  originalFetch = globalThis.fetch;
});
beforeEach(() => { setActivePinia(createPinia()); });
after(async () => { globalThis.fetch = originalFetch; await vite?.close(); });

const response = (events) => new Response(events, { headers: { 'content-type': 'text/event-stream' } });

test('truncated stream retains partial answer and offers a retry', async () => {
  globalThis.fetch = async () => response('event: text_chunk\ndata: {"token":"部分内容"}\n\n');
  const store = useChatStore();
  await store.sendMessage('问题');
  assert.equal(store.messages.at(-1).content, '部分内容');
  assert.equal(store.messages.at(-1).completion, 'incomplete');
  assert.match(store.errorMessage, /中断|未完成/);
  assert.equal(store.streaming, false);
});

test('server terminal incomplete status preserves result without claiming completion', async () => {
  globalThis.fetch = async () => response('event: text_chunk\ndata: {"token":"部分内容"}\n\nevent: done\ndata: {"completion":"incomplete"}\n\n');
  const store = useChatStore();
  await store.sendMessage('问题');
  assert.equal(store.messages.at(-1).content, '部分内容');
  assert.equal(store.messages.at(-1).completion, 'incomplete');
  assert.match(store.errorMessage, /中断|未完成/);
});

test('an old failed request cannot change the new request state', async () => {
  let failOld;
  let finishNew;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    if (calls === 1) return new Promise((resolve, reject) => { failOld = reject; });
    return new Promise(resolve => { finishNew = resolve; });
  };
  const store = useChatStore();
  const oldRequest = store.sendMessage('旧问题');
  const newRequest = store.sendMessage('新问题');
  failOld(new Error('旧请求失败'));
  await oldRequest;
  assert.equal(store.streaming, true);
  assert.equal(store.errorMessage, '');
  finishNew(response('event: text\ndata: {"text":"新答案","is_complete":true}\n\nevent: done\ndata: {}\n\n'));
  await newRequest;
  assert.equal(store.messages.at(-1).content, '新答案');
  assert.equal(store.errorMessage, '');
});

test('successful chat records a first-text duration without recording the question or answer', async () => {
  globalThis.fetch = async () => response('event: text_chunk\ndata: {"token":"私有答案"}\n\nevent: done\ndata: {}\n\n');
  const store = useChatStore();
  await store.sendMessage('私有问题');
  await new Promise(resolve => setTimeout(resolve, 0));
  const sample = getRecentChatMetrics().at(-1);
  assert.equal(sample.outcome, 'complete');
  assert.equal(typeof sample.text_received_ms, 'number');
  assert.doesNotMatch(JSON.stringify(sample), /私有/);
});

test('incremental text updates are observable while the stream remains open', async () => {
  let stream;
  globalThis.fetch = async () => new Response(new ReadableStream({ start(controller) { stream = controller; } }));
  const store = useChatStore();
  const contentChanges = [];
  const unwatch = watch(() => store.messages.at(-1)?.content, value => contentChanges.push(value), { flush: 'sync' });
  const pending = store.sendMessage('问题');
  await Promise.resolve();
  stream.enqueue(new TextEncoder().encode('event: text_chunk\ndata: {"token":"实时"}\n\n'));
  await new Promise(resolve => setTimeout(resolve, 25));
  assert.equal(store.streaming, true);
  assert.ok(contentChanges.includes('实时'));
  stream.enqueue(new TextEncoder().encode('event: done\ndata: {}\n\n'));
  stream.close();
  await pending;
  unwatch();
});

test('stopping before the next text flush preserves received text', async () => {
  let stream;
  globalThis.fetch = async (_path, options) => new Response(new ReadableStream({
    start(controller) {
      stream = controller;
      options.signal.addEventListener('abort', () => { try { controller.error(options.signal.reason); } catch {} }, { once: true });
    },
  }));
  const store = useChatStore();
  const pending = store.sendMessage('问题');
  await Promise.resolve();
  stream.enqueue(new TextEncoder().encode('event: text_chunk\ndata: {"token":"已收到"}\n\n'));
  await new Promise(resolve => setTimeout(resolve, 0));
  store.stopOutput();
  await pending;
  assert.equal(store.messages.at(-1).content, '已收到');
  assert.equal(store.messages.at(-1).completion, 'stopped');
});

test('a burst of text is coalesced before the terminal event without losing content', async () => {
  const events = Array.from({ length: 12 }, () => 'event: text_chunk\ndata: {"token":"字"}\n\n').join('');
  globalThis.fetch = async () => response(`${events}event: done\ndata: {}\n\n`);
  const store = useChatStore();
  let changes = 0;
  const unwatch = watch(() => store.messages.at(-1)?.content, () => { changes++; }, { flush: 'sync' });
  await store.sendMessage('问题');
  unwatch();
  assert.equal(store.messages.at(-1).content, '字'.repeat(12));
  assert.ok(changes < 12, `rendered ${changes} updates for 12 chunks`);
});

test('unsupported PCM playback keeps the text and reports unavailable voice', async () => {
  globalThis.fetch = async () => response(
    'event: text_chunk\ndata: {"token":"文字讲解"}\n\n' +
    'event: audio_chunk\ndata: {"base64":"AAA=","sample_rate":24000,"channels":1,"bits":16}\n\n' +
    'event: done\ndata: {}\n\n'
  );
  const store = useChatStore();
  await store.sendMessage('问题');
  assert.equal(store.messages.at(-1).content, '文字讲解');
  assert.equal(store.voiceFallback, true);
  assert.match(store.statusText, /语音暂不可用/);
});

test('taking over chat playback from the map notifies the chat playback owner', async () => {
  useAudioPlayer().stop();
  globalThis.fetch = async () => response('event: text\ndata: {"text":"导览结果","is_complete":true}\n\nevent: done\ndata: {}\n\n');
  const store = useChatStore();
  let stopped = 0;
  await store.sendMessage('问题', null, { onPlaybackStopped: () => { stopped++; } });

  useAudioPlayer().claimPlayback('map-narration');
  assert.equal(stopped, 1);
  useAudioPlayer().stop();
});

test('visitor playback rate stays client-side instead of changing the TTS request rate', async () => {
  let requestBody;
  globalThis.fetch = async (_url, options) => {
    requestBody = JSON.parse(options.body);
    return response('event: text\ndata: {"text":"回答","is_complete":true}\n\nevent: done\ndata: {}\n\n');
  };
  const store = useChatStore();
  await store.sendMessage('问题', null, {
    ttsConfig: { playbackRate: 1.5, speechRate: 150, volume: 80 },
  });
  assert.equal(requestBody.tts_rate, 100);
});

test('retry uses the latest visitor playback rate while keeping other TTS options', async () => {
  globalThis.fetch = async () => response('event: error\ndata: {"message":"连接中断"}\n\n');
  const store = useChatStore();
  await store.sendMessage('问题', null, {
    ttsConfig: { playbackRate: 1, voiceType: 'calm-female', volume: 70 },
  });

  let retried;
  store.sendMessage = async (...args) => { retried = args; };
  await store.retryLastMessage({ ttsConfig: { playbackRate: 1.5 } });

  assert.equal(retried[2].ttsConfig.playbackRate, 1.5);
  assert.equal(retried[2].ttsConfig.voiceType, 'calm-female');
  assert.equal(retried[2].ttsConfig.volume, 70);
});

test('each answer retains its own sources across later turns', async () => {
  let turn = 0;
  globalThis.fetch = async () => response(`event: sources\ndata: ${JSON.stringify({docs:[{evidence_id:'证据1',title:++turn === 1 ? 'A' : 'B'}]})}\n\nevent: text\ndata: {"text":"回答[证据1]","is_complete":true}\n\nevent: done\ndata: {}\n\n`);
  const store = useChatStore();
  await store.sendMessage('A');
  const first = store.messages.at(-1);
  await store.sendMessage('B');
  assert.equal(first.sources[0].title, 'A');
  assert.equal(store.messages.at(-1).sources[0].title, 'B');
});

test('unconfirmed photo warning stays attached to its answer after completion', async () => {
  globalThis.fetch = async () => response('event: context\ndata: {"warnings":["vision_scope_unconfirmed"]}\n\nevent: text\ndata: {"text":"可能是某景点","is_complete":true}\n\nevent: done\ndata: {}\n\n');
  const store = useChatStore();
  await store.sendMessage('这是什么');
  assert.match(store.messages.at(-1).warning, /照片.*未确认.*核对/);
});
