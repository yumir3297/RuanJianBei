// Synthetic delayed SSE response; no external model or real audio is used.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.setDefaultTimeout(10000);
let release;
const pending = new Promise(resolve => { release = resolve; });
let arrived;
const requested = new Promise(resolve => { arrived = resolve; });
try {
  await page.route(url => url.origin === 'http://127.0.0.1:5173' && url.pathname.startsWith('/api/'), async route => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/guide/bootstrap') return route.fulfill({ json: { available: true, enabled: true, demo_enabled: true, site_id: 'demo', catalog: [] } });
    if (path === '/api/chat/stream') {
      arrived();
      await pending;
      try { await route.fulfill({ status: 200, contentType: 'text/event-stream', body: 'event: text\ndata: {"text":"迟到的模拟讲解","is_complete":true}\n\n' }); } catch { /* aborted request */ }
      return;
    }
    return route.fulfill({ status: 404, json: { detail: 'mock unavailable' } });
  });
  await page.goto('http://127.0.0.1:5173/tourist');
  await page.getByRole('button', { name: '键盘输入' }).click();
  await page.locator('#tourist-query').fill('请介绍这个景区');
  await page.locator('#tourist-query').press('Enter');
  await Promise.race([requested, new Promise((_, reject) => setTimeout(() => reject(new Error('stream request did not start')), 10000))]);
  await page.getByRole('button', { name: '演示预警抢占' }).click();
  await page.getByRole('button', { name: '继续演示：模拟预警变化' }).click();
  await page.getByText('安全提醒期间，普通讲解已暂停').waitFor();
  release();
  await page.waitForTimeout(500);
  assert.equal(await page.getByText('迟到的模拟讲解').count(), 0);
  assert.equal(await page.getByRole('button', { name: '停止回答' }).count(), 0);
  console.log('Simulated warning aborts pending stream and late response stays hidden: PASS');
} finally { release(); await browser.close(); }
