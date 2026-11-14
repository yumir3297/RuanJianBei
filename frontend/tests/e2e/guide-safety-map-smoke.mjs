// Mocked service data; checks browser interaction between the safety panel and map.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.setDefaultTimeout(10000);
try {
  await page.route(url => url.origin === 'http://127.0.0.1:5173' && url.pathname.startsWith('/api/'), route => {
    if (new URL(route.request().url()).pathname === '/api/guide/bootstrap') return route.fulfill({ json: { available: true, enabled: true, demo_enabled: true, site_id: 'demo', catalog: [] } });
    return route.fulfill({ status: 404, json: { detail: 'mock unavailable' } });
  });
  await page.goto('http://127.0.0.1:5173/tourist');
  await page.getByRole('button', { name: '实时地图' }).click();
  const ask = page.locator('.map-tool .tool-primary');
  await ask.waitFor({ state: 'visible' });
  assert.equal(await ask.isEnabled(), true);
  await page.getByRole('button', { name: '演示预警抢占' }).click();
  await page.getByRole('button', { name: '继续演示：模拟预警变化' }).click();
  await page.getByText('安全提醒期间，普通讲解已暂停').waitFor();
  assert.equal(await ask.isDisabled(), true);
  await page.getByRole('button', { name: '我已了解' }).click();
  assert.equal(await ask.isDisabled(), true);
  await page.getByRole('button', { name: '继续演示（需再次确认）' }).click();
  await page.waitForFunction(() => !document.querySelector('.map-tool .tool-primary')?.disabled);
  console.log('Simulated warning holds map question until explicit resume: PASS');
} finally { await browser.close(); }
