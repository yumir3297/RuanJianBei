import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';
import { createPinia, setActivePinia } from 'pinia';
let vite;
let useChatStore;
let realFetch;
let source;

before(async () => {
  class Context {
    constructor() { this.state = 'running'; this.currentTime = 0; this.destination = {}; }
    createAnalyser() { return { connect() {}, getByteTimeDomainData(data) { data.fill(128); } }; }
    createGain() { return { gain: { value: 1 }, connect() {}, disconnect() {} }; }
    createBuffer(_channels, length, rate) { return { length, duration: length / rate, getChannelData: () => new Float32Array(length) }; }
    createBufferSource() {
      source = { playbackRate: { value: 1 }, connect() {}, disconnect() {}, start() {}, stop() { this.stopped = true; this.onended?.(); } };
      return source;
    }
  }
  globalThis.window = { AudioContext: Context };
  globalThis.AudioContext = Context;
  globalThis.requestAnimationFrame = () => 1;
  globalThis.cancelAnimationFrame = () => {};
  vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-pcm-error-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ useChatStore } = await vite.ssrLoadModule('/src/stores/chat.js'));
  realFetch = globalThis.fetch;
});
after(async () => { globalThis.fetch = realFetch; await vite?.close(); });

test('a stream error immediately stops queued PCM and retains partial text', async () => {
  globalThis.fetch = async () => new Response(
    'event: text_chunk\ndata: {"token":"部分文字"}\n\n' +
    'event: audio_chunk\ndata: {"base64":"AAA=","sample_rate":24000}\n\n' +
    'event: error\ndata: {"message":"内容已更新"}\n\n'
  );
  setActivePinia(createPinia());
  const store = useChatStore();
  await store.sendMessage('问题');
  assert.equal(store.messages.at(-1).content, '部分文字');
  assert.equal(store.messages.at(-1).completion, 'incomplete');
  assert.equal(source.stopped, true);
});
