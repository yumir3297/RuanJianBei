// Browser lifecycle check with mocked geolocation and API; no real location is used.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';

const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
try {
  await page.route(url => url.origin === 'http://127.0.0.1:5173' && url.pathname.startsWith('/api/'), async route => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/guide/bootstrap') return route.fulfill({ json: { available: true, enabled: false, demo_enabled: false, catalog: [] } });
    return route.fulfill({ status: 404, json: { detail: 'mock unavailable' } });
  });
  await page.addInitScript(() => {
    window.testGeo = { callbacks: [], cleared: [] };
    Object.defineProperty(navigator, 'geolocation', { configurable: true, value: {
      watchPosition(success, error) { window.testGeo.callbacks.push({ success, error }); return window.testGeo.callbacks.length; },
      clearWatch(id) { window.testGeo.cleared.push(id); },
    } });
  });
  await page.goto('http://127.0.0.1:5173/tourist');
  const state = page.locator('.cass-state').first();
  await state.filter({ hasText: '地图未激活，定位已停止' }).waitFor();
  await page.getByRole('button', { name: '实时地图' }).click();
  await page.getByRole('button', { name: '开启讲解设置' }).click();
  await page.waitForFunction(() => window.testGeo.callbacks.length === 1);
  await page.evaluate(() => window.testGeo.callbacks[0].success({ coords: { latitude: 31.4285, longitude: 120.0998, accuracy: 8 }, timestamp: Date.now() }));
  await state.filter({ hasText: '真实设备提示' }).waitFor();
  await page.getByRole('button', { name: '收起导览工具' }).click();
  await state.filter({ hasText: '地图未激活，定位已停止' }).waitFor();
  assert.deepEqual(await page.evaluate(() => window.testGeo.cleared), [1]);
  await page.getByRole('button', { name: '实时地图' }).click();
  await page.getByRole('button', { name: '开启讲解设置' }).click();
  await page.waitForFunction(() => window.testGeo.callbacks.length === 2);
  await page.evaluate(() => window.testGeo.callbacks[1].success({ coords: { latitude: 31.4285, longitude: 120.0998, accuracy: 8 }, timestamp: Date.now() }));
  await state.filter({ hasText: '真实设备提示' }).waitFor();
  await page.evaluate(() => window.testGeo.callbacks[0].error({ code: 1 }));
  await page.waitForTimeout(100);
  assert.match(await state.innerText(), /真实设备提示/);
  console.log('PASS: map activation, hide, reopen and stale geolocation callback isolation');
} finally { await browser.close(); }
