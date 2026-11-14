// Run only against the isolated local demo backend and admin server.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';

if (process.env.DEMO_SYNTHETIC_CONFIRM !== '1' || !process.env.DEMO_ADMIN_PASSWORD) {
  throw new Error('Set DEMO_SYNTHETIC_CONFIRM=1 and DEMO_ADMIN_PASSWORD for an isolated demo database.');
}
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage();
const errors = [];
page.on('pageerror', error => errors.push(error.message));
try {
  if (process.env.DEMO_MOCK_API === '1') {
    await page.route(url => url.pathname.startsWith('/api/'), route => route.fulfill({
      status: route.request().url().includes('/auth/login') ? 200 : 503,
      contentType: 'application/json',
      body: route.request().url().includes('/auth/login') ? JSON.stringify({ token: 'layout-test-token' }) : JSON.stringify({ detail: '测试接口暂不可用' }),
    }));
  }
  await page.goto(process.env.DEMO_ADMIN_URL || 'http://127.0.0.1:5174');
  await page.locator('input[type=password]').fill(process.env.DEMO_ADMIN_PASSWORD);
  await page.getByRole('button', { name: '登录管理后台' }).click();
  await page.waitForURL('**/admin/dashboard');
  const routes = [
    ['总览', '/admin/dashboard'], ['知识管理', '/admin/knowledge'], ['知识盲区', '/admin/blind-spots'],
    ['数字人配置', '/admin/avatar'], ['页面与素材', '/admin/assets'],
    ['问答分析', '/admin/analytics'], ['游客反馈', '/admin/experience-report'],
  ];
  for (const width of [1440, 736, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (const [label, path] of routes) {
      await page.getByRole('link', { name: label, exact: true }).click();
      await page.waitForURL(`**${path}`);
      await page.locator('.admin-main > *').first().waitFor();
      const state = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth,
        sidebar: getComputedStyle(document.querySelector('.admin-sidebar')).backgroundColor,
        selected: document.querySelector('.sidebar-nav-link[aria-current="page"]')?.textContent.trim() }));
      assert.equal(state.selected, label, `${width} ${path}: active navigation`);
      assert.ok(state.scrollWidth <= state.width + 1, `${width} ${path}: horizontal overflow ${JSON.stringify(state)}`);
      assert.equal(state.sidebar, 'rgb(255, 255, 255)', `${width} ${path}: light sidebar`);
      if (process.env.DEMO_MOCK_API === '1' && path === '/admin/knowledge') {
        await page.getByText('知识数据不可用', { exact: true }).first().waitFor();
        assert.equal(await page.getByText('暂无知识条目，可先导入资料或手动新增', { exact: true }).count(), 0);
      }
    }
    console.log(`PASS: seven admin routes at ${width}px`);
  }
  assert.deepEqual(errors, [], 'browser page errors');
} finally { await browser.close(); }
