// Simulates an incomplete deployment using only temporary copies of the tourist build.
import assert from 'node:assert/strict';
import { cp, mkdtemp, readFile, rename, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';
import { startStaticServer } from '../../scripts/offline-test-server.mjs';

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const temp = await mkdtemp(path.join(os.tmpdir(), 'offline-failed-update-'));
const root = path.join(temp, 'served'), next = path.join(temp, 'next');
let browser, server;
try {
  await cp(path.join(frontend, 'dist/tourist'), root, { recursive: true });
  await cp(root, next, { recursive: true });
  const manifest = JSON.parse(await readFile(path.join(root, 'offline-precache-manifest.json'), 'utf8'));
  const oldId = manifest.buildId, newId = `fail${oldId.slice(4)}`;
  assert.notEqual(oldId, newId);
  await writeFile(path.join(next, 'offline-precache-manifest.json'), JSON.stringify({ ...manifest, buildId: newId }));
  const sw = await readFile(path.join(next, 'sw.js'), 'utf8');
  assert.ok(sw.includes(`"buildId":"${oldId}"`));
  await writeFile(path.join(next, 'sw.js'), sw.replace(`"buildId":"${oldId}"`, `"buildId":"${newId}"`));
  await rm(path.join(next, 'offline/help/contacts.json'));
  const handle = await startStaticServer({ distDir: root });
  server = handle.server;
  browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(`${handle.origin}/tourist`);
  await page.waitForFunction(async id => (await caches.keys()).includes(`a5-offline-${id}`) && Boolean((await navigator.serviceWorker.ready).active), oldId, { timeout: 45000 });
  await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller));
  await rename(root, path.join(temp, 'old'));
  await rename(next, root);
  const outcome = await page.evaluate(async () => {
    const registration = await navigator.serviceWorker.getRegistration('/');
    return new Promise(async (resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('worker update did not finish')), 15000);
      const done = value => { clearTimeout(timer); resolve(value); };
      registration.addEventListener('updatefound', () => {
        const worker = registration.installing;
        worker?.addEventListener('statechange', () => {
          if (worker.state === 'redundant') done('redundant');
          if (worker.state === 'activated') done('activated');
        });
      }, { once: true });
      try { await registration.update(); } catch (error) { clearTimeout(timer); reject(error); }
    });
  });
  assert.equal(outcome, 'redundant', 'incomplete new cache must not activate');
  await context.setOffline(true);
  const offline = await context.newPage();
  await offline.goto(`${handle.origin}/offline.html`);
  assert.match(await offline.locator('h1').innerText(), /离线伴游/);
  const contact = await offline.evaluate(async () => (await fetch('/offline/help/contacts.json')).ok);
  assert.equal(contact, true);
  assert.ok((await offline.evaluate(() => caches.keys())).includes(`a5-offline-${oldId}`));
  console.log('PASS: failed update leaves the previous package usable offline from the tourist app');
  await context.close();
} finally {
  await browser?.close();
  if (server) await new Promise(resolve => server.close(resolve));
  await rm(temp, { recursive: true, force: true });
}
