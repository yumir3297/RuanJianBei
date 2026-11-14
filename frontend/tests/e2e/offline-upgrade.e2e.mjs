// Uses copies of the built output in a temporary directory; never changes dist.
import assert from 'node:assert/strict';
import { cp, mkdtemp, readFile, rename, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';
import { startStaticServer } from '../../scripts/offline-test-server.mjs';

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const temp = await mkdtemp(path.join(os.tmpdir(), 'offline-upgrade-'));
const root = path.join(temp, 'served');
const next = path.join(temp, 'next');
let browser, server;
try {
  await cp(path.join(frontendRoot, 'dist/tourist'), root, { recursive: true });
  await writeFile(path.join(root, 'probe.html'), '<!doctype html><title>offline upgrade test</title>');
  await cp(root, next, { recursive: true });
  const manifest = JSON.parse(await readFile(path.join(root, 'offline-precache-manifest.json'), 'utf8'));
  const oldId = manifest.buildId;
  const newId = `test${oldId.slice(4)}`;
  assert.notEqual(oldId, newId);
  const newManifest = { ...manifest, buildId: newId };
  await writeFile(path.join(next, 'offline-precache-manifest.json'), JSON.stringify(newManifest));
  const sw = await readFile(path.join(next, 'sw.js'), 'utf8');
  assert.ok(sw.includes(`"buildId":"${oldId}"`));
  await writeFile(path.join(next, 'sw.js'), sw.replace(`"buildId":"${oldId}"`, `"buildId":"${newId}"`));
  const contactPath = path.join(next, 'offline/help/contacts.json');
  const contacts = JSON.parse(await readFile(contactPath, 'utf8'));
  contacts.upgrade_test_marker = 'synthetic-version-two';
  await writeFile(contactPath, JSON.stringify(contacts));

  const handle = await startStaticServer({ distDir: root });
  server = handle.server;
  browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(`${handle.origin}/probe.html`);
  await page.evaluate(() => navigator.serviceWorker.register('/sw.js', { scope: '/', updateViaCache: 'none' }));
  await page.waitForFunction(async id => Boolean((await navigator.serviceWorker.ready).active) && (await caches.keys()).includes(`a5-offline-${id}`), oldId);
  await page.reload();
  await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller));

  await rename(root, path.join(temp, 'old'));
  await rename(next, root);
  await page.evaluate(async () => (await navigator.serviceWorker.getRegistration('/')).update());
  await page.waitForFunction(async id => Boolean((await navigator.serviceWorker.getRegistration('/'))?.waiting) && (await caches.keys()).includes(`a5-offline-${id}`), newId, { timeout: 30000 });
  const waitingState = await page.evaluate(async () => {
    const reg = await navigator.serviceWorker.getRegistration('/');
    const waiting = reg.waiting?.state;
    const value = await (await fetch('/offline/help/contacts.json')).json();
    return { waiting, active: reg.active?.state, marker: value.upgrade_test_marker || null, keys: await caches.keys() };
  });
  assert.equal(waitingState.marker, null, 'existing page must still see its old worker cache');
  await page.close();
  const fresh = await context.newPage();
  await fresh.goto(`${handle.origin}/probe.html`);
  await fresh.waitForFunction(async id => {
    const keys = await caches.keys();
    return keys.includes(`a5-offline-${id}`) && keys.filter(key => key.startsWith('a5-offline-')).length === 1;
  }, newId, { timeout: 30000 });
  await context.setOffline(true);
  const offline = await context.newPage();
  await offline.goto(`${handle.origin}/offline.html`);
  assert.match(await offline.locator('h1').innerText(), /离线伴游/);
  const updated = await offline.evaluate(async () => (await (await fetch('/offline/help/contacts.json')).json()).upgrade_test_marker);
  assert.equal(updated, 'synthetic-version-two');
  console.log('PASS: old page holds old version; new worker activates after close; updated data works offline');
  await context.close();
} finally {
  await browser?.close();
  if (server) await new Promise(resolve => server.close(resolve));
  await rm(temp, { recursive: true, force: true });
}
