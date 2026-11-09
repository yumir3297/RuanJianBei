import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';
let vite;
let player;
let utterance;

before(async () => {
  globalThis.window = { speechSynthesis: {
    getVoices: () => [{ lang: 'zh-CN' }],
    speak(value) { utterance = value; },
    cancel() {}, addEventListener() {}, removeEventListener() {},
  } };
  globalThis.SpeechSynthesisUtterance = class { constructor(text) { this.text = text; } };
  globalThis.requestAnimationFrame = () => 1;
  globalThis.cancelAnimationFrame = () => {};
  vite = await createServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-speech-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  player = (await vite.ssrLoadModule('/src/composables/useAudioPlayer.js')).useAudioPlayer();
});
after(async () => { player?.stop(); await vite?.close(); });

test('late speech callbacks after stop cannot report progress or restart timers', async () => {
  let updates = 0;
  const pending = player.enqueue('', 1000, null, '测试', () => { updates++; }, { allowBrowserSpeech: true });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.ok(utterance);
  player.stop();
  utterance.onstart?.();
  utterance.onboundary?.({ charIndex: 1 });
  assert.equal(updates, 0);
  await Promise.race([pending, new Promise((_, reject) => setTimeout(() => reject(new Error('cancel did not finish')), 50))]);
});

test('browser speech uses the selected rate and keeps reported time on the content timeline', async () => {
  const originalDateNow = Date.now;
  let now = 1000;
  Date.now = () => now;
  const reports = [];
  try {
    const pending = player.enqueue('', 1000, null, '测试语速', (...args) => reports.push(args), {
      allowBrowserSpeech: true,
      rate: 1.2,
    });
    await new Promise(resolve => setTimeout(resolve, 0));
    assert.equal(utterance.rate, 1.2);
    utterance.onstart?.();
    assert.equal(reports.at(-1)[1], 0);
    assert.equal(reports.at(-1)[2], 1000);
    now = 1500;
    utterance.onboundary?.({ charIndex: 2 });
    assert.deepEqual(reports.at(-1).slice(0, 3), [0.5, 600, 1000]);
    utterance.onend?.();
    assert.deepEqual(reports.at(-1).slice(0, 3), [1, 1000, 1000]);
    await pending;
  } finally {
    Date.now = originalDateNow;
    player.stop();
  }
});
