import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer as createViteServer } from 'vite';

let vite;
let postStream;
let realFetch;

before(async () => {
  vite = await createViteServer({ configFile: false, cacheDir: '/private/tmp/guide-vite-tests', server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ postStream } = (await vite.ssrLoadModule('/src/composables/useSSEStream.js')).useSSEStream());
  realFetch = globalThis.fetch;
  globalThis.fetch = async (path, options) => {
    let timer;
    const bytes = new TextEncoder();
    const body = new ReadableStream({
      start(controller) {
        options.signal.addEventListener('abort', () => {
          clearInterval(timer);
          try { controller.error(options.signal.reason); } catch {}
        }, { once: true });
        if (path === '/split') {
          const data = bytes.encode('event: text_chunk\r\ndata: {"token":"灵山"}\r\n\r\nevent: done\r\ndata: {}\r\n\r\n');
          const utfSplit = Buffer.from(data).indexOf(Buffer.from('灵')) + 1;
          const crSplit = Buffer.from(data).indexOf('\r\n') + 1;
          controller.enqueue(data.slice(0, crSplit));
          controller.enqueue(data.slice(crSplit, utfSplit));
          controller.enqueue(data.slice(utfSplit));
          controller.close();
        } else if (path === '/partial') {
          controller.enqueue(bytes.encode('event: text_chunk\ndata: {"token":"部分"}'));
          controller.close();
        } else {
          controller.enqueue(bytes.encode('event: status\ndata: {"text":"开始"}\n\n'));
          if (path === '/heartbeat') timer = setInterval(() => controller.enqueue(bytes.encode(': ping\n\n')), 10);
          if (path === '/heartbeat-events') timer = setInterval(() => controller.enqueue(bytes.encode('event: heartbeat\ndata: {}\n\n')), 10);
          if (path === '/repeated-status') timer = setInterval(() => controller.enqueue(bytes.encode('event: status\ndata: {"text":"开始"}\n\n')), 10);
        }
      },
      cancel() { clearInterval(timer); },
    });
    return new Response(body, { headers: { 'content-type': 'text/event-stream' } });
  };
});

after(async () => {
  globalThis.fetch = realFetch;
  await vite?.close();
});

test('SSE keeps UTF-8 and CRLF split between network chunks intact', async () => {
  const tokens = [];
  let finished = false;
  await postStream('/split', {}, { text_chunk: ({ token }) => tokens.push(token), done: () => { finished = true; } });
  assert.deepEqual(tokens, ['灵山']);
  assert.equal(finished, true);
});

test('idle connection ends with a recoverable timeout', async () => {
  await assert.rejects(postStream('/idle', {}, {}, { idleTimeoutMs: 50, progressTimeoutMs: 1000, totalTimeoutMs: 1000 }), /超时/);
});

test('heartbeats do not hide a lack of useful progress', async () => {
  await assert.rejects(postStream('/heartbeat', {}, {}, { idleTimeoutMs: 100, progressTimeoutMs: 60, totalTimeoutMs: 1000 }), /超时/);
});

test('heartbeat events do not hide a lack of useful progress', async () => {
  await assert.rejects(postStream('/heartbeat-events', {}, {}, { idleTimeoutMs: 100, progressTimeoutMs: 60, totalTimeoutMs: 200 }), /等待进展超时/);
});

test('repeated identical status does not hide a lack of useful progress', async () => {
  await assert.rejects(postStream('/repeated-status', {}, {}, { idleTimeoutMs: 100, progressTimeoutMs: 60, totalTimeoutMs: 200 }), /等待进展超时/);
});

test('incomplete final event is not dispatched', async () => {
  const tokens = [];
  await postStream('/partial', {}, { text_chunk: ({ token }) => tokens.push(token) });
  assert.deepEqual(tokens, []);
});

test('caller cancellation remains distinguishable from timeout', async () => {
  const controller = new AbortController();
  setTimeout(() => controller.abort(), 20);
  await assert.rejects(postStream('/idle', {}, {}, { signal: controller.signal, idleTimeoutMs: 500 }), { name: 'AbortError' });
});
