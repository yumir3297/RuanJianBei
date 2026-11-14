// Seed only the persisted hold marker; no real warning or external API is used.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
try {
  await page.route(url => url.origin === 'http://127.0.0.1:5173' && url.pathname.startsWith('/api/'), route => {
    if (new URL(route.request().url()).pathname === '/api/guide/bootstrap') return route.fulfill({ json: { available: true, enabled: true, demo_enabled: true, site_id: 'demo', catalog: [] } });
    return route.fulfill({ status: 404, json: { detail: 'mock unavailable' } });
  });
  await page.goto('http://127.0.0.1:5173/tourist');
  await page.evaluate(() => sessionStorage.setItem('a5-guide-real-safety-hold-v1', '1'));
  await page.reload();
  await page.getByText('安全提醒期间，普通讲解已暂停').waitFor({ timeout: 10000 });
  await page.getByText('预警结束状态尚未核实').waitFor();
  await page.getByRole('button', { name: '实时地图' }).click();
  assert.equal(await page.locator('.map-tool .tool-primary').isDisabled(), true);
  assert.equal(await page.getByRole('button', { name: '演示预警抢占' }).isDisabled(), true);
  console.log('Persisted real-hold marker restores pause after reload: PASS');
} finally { await browser.close(); }
