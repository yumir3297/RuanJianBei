#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { randomUUID } = require('node:crypto');

let chromium;
try {
  ({ chromium } = require('playwright'));
} catch {
  try {
    ({ chromium } = require('../../frontend/node_modules/playwright'));
  } catch {
    console.error('Playwright is not installed in this evaluation environment. Install it outside production dependencies, then rerun this script.');
    process.exit(2);
  }
}

const baseUrl = process.env.GUIDELOOP_BASE_URL || 'http://127.0.0.1:5175/admin/blind-spots';
const adminPassword = process.env.GUIDELOOP_ADMIN_PASSWORD;
const screenshotDir = process.env.GUIDELOOP_SCREENSHOT_DIR || path.resolve(__dirname, '../results/guideloop-pilot-2026-11-10/screenshots');
const sourceRef = 'https://daj.wuxi.gov.cn/doc/2013/03/05/2426800.shtml';
const answer = '莲花里有太子佛立像。';
const frozenEffectiveFrom = '2026-11-10T00:00:00+08:00';

if (!adminPassword) {
  console.error('GUIDELOOP_ADMIN_PASSWORD is required; do not put credentials in the script or repository.');
  process.exit(2);
}

async function postJson(origin, route, payload, token) {
  const response = await fetch(new URL(route, origin), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });
  const text = await response.text();
  let body;
  try { body = text ? JSON.parse(text) : {}; } catch { body = { raw: text }; }
  if (!response.ok) throw new Error(`${route} returned ${response.status}: ${JSON.stringify(body)}`);
  return body;
}

async function login(page) {
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => {
    const hasPassword = !!document.querySelector('input[type="password"]');
    const hasPilotButton = [...document.querySelectorAll('button')].some(button => button.innerText.includes('GuideLoop 试验'));
    return hasPassword || hasPilotButton;
  }, null, { timeout: 15000 });
  if (await page.getByLabel('管理密码').isVisible().catch(() => false)) {
    await page.getByLabel('管理密码').fill(adminPassword);
    await page.getByRole('button', { name: '登录管理后台' }).click();
    await page.locator('input[type="password"]').waitFor({ state: 'detached', timeoutMs: 10000 });
  }
  await page.getByRole('heading', { name: '知识盲区' }).waitFor({ state: 'visible', timeout: 15000 });
  await page.getByRole('button', { name: 'GuideLoop 试验' }).waitFor({ state: 'visible', timeout: 15000 });
  await page.getByRole('button', { name: 'GuideLoop 试验' }).click();
  await page.getByRole('heading', { name: 'GuideLoop 知识演化试验' }).waitFor({ state: 'visible' });
}

async function main() {
  fs.mkdirSync(screenshotDir, { recursive: true });
  const origin = new URL(baseUrl).origin;
  const suffix = randomUUID().replaceAll('-', '').slice(0, 12);
  const caseId = `browser-${suffix}`;
  const secondCaseId = `browser-second-${suffix}`;
  const targetId = `prince-browser-${suffix}`;
  const alias = `莲花中的太子像是谁 ${suffix}？`;
  const session = `browser-session-${suffix}`;
  const eventId = `browser-event-${suffix}`;
  const replayId = `browser-replay-${suffix}`;
  const embeddingApiPasswordToken = await postJson(origin, '/api/auth/login', { password: adminPassword });
  const token = embeddingApiPasswordToken.token;
  const launchOptions = { headless: true };
  if (process.env.PLAYWRIGHT_EXECUTABLE_PATH) launchOptions.executablePath = process.env.PLAYWRIGHT_EXECUTABLE_PATH;
  const browser = await chromium.launch(launchOptions);
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  try {
    await postJson(origin, '/api/admin/guide-loop/observations', {
      event_id: eventId,
      session_key: session,
      cluster_id: caseId,
      text: alias,
      poi_id: 'bathing',
      target_id: targetId,
      evidence_ids: [],
      result_code: 'unanswered',
      category: 'retrieval_gap',
      replay_id: replayId,
      origin: 'synthetic',
    }, token);
    await postJson(origin, '/api/admin/guide-loop/observations', {
      event_id: `${eventId}-second`,
      session_key: `${session}-second`,
      cluster_id: secondCaseId,
      text: `大佛手印问法 ${suffix}`,
      poi_id: 'buddha',
      target_id: `mudra-${suffix}`,
      evidence_ids: [],
      result_code: 'unanswered',
      category: 'retrieval_gap',
      replay_id: `${replayId}-second`,
      origin: 'synthetic',
    }, token);

    await login(page);
    const card = page.locator('.case-card').filter({ hasText: caseId });
    await card.waitFor({ state: 'visible', timeout: 15000 });
    await card.getByLabel('对象 ID').fill(targetId);
    await card.getByLabel('游客别名').fill(alias);
    await card.getByLabel('人工审核后的回答').fill(answer);
    await card.getByLabel('证据 ID').fill(`wuxi_gazetteer_${suffix}`);
    await card.getByLabel('来源说明（需人工核验支持关系）').fill(sourceRef);
    await card.getByLabel('生效起始（ISO 时间）').fill(frozenEffectiveFrom);
    await card.getByLabel('基线版本').fill('0');
    await card.getByRole('button', { name: '保存草稿' }).click();
    await page.getByText('草稿已保存', { exact: true }).waitFor({ state: 'visible', timeout: 10000 });
    const secondCard = page.locator('.case-card').filter({ hasText: secondCaseId });
    await secondCard.waitFor({ state: 'visible', timeout: 15000 });
    assert.equal(await secondCard.getByLabel('游客别名').inputValue(), '', 'a different case must not inherit the first case alias');
    await secondCard.getByLabel('对象 ID').fill(`mudra-${suffix}`);
    await secondCard.getByLabel('游客别名').fill(`大佛手印怎么说 ${suffix}？`);
    await secondCard.getByLabel('人工审核后的回答').fill('公开资料对该手印存在冲突，暂不作确定回答。');
    await secondCard.getByLabel('证据 ID').fill(`buddha_source_${suffix}`);
    await secondCard.getByLabel('来源说明（需人工核验支持关系）').fill(sourceRef);
    await secondCard.getByLabel('生效起始（ISO 时间）').fill(frozenEffectiveFrom);
    await secondCard.getByRole('button', { name: '保存草稿' }).click();
    await page.getByText('草稿已保存', { exact: true }).last().waitFor({ state: 'visible', timeout: 10000 });
    await page.reload({ waitUntil: 'domcontentloaded' });
    await login(page);
    const restoredFirst = page.locator('.case-card').filter({ hasText: caseId });
    const restoredSecond = page.locator('.case-card').filter({ hasText: secondCaseId });
    assert.equal(await restoredFirst.getByLabel('游客别名').inputValue(), alias, 'saved draft must restore after refresh');
    assert.equal(await restoredSecond.getByLabel('游客别名').inputValue(), `大佛手印怎么说 ${suffix}？`, 'each case must restore its own saved draft');
    await restoredFirst.getByLabel('人工审核后的回答').fill(`${answer}临时修改`);
    assert.equal(await restoredFirst.getByRole('button', { name: '技术路由验证' }).isDisabled(), true, 'editing a saved draft must invalidate its verification');
    await restoredFirst.getByLabel('人工审核后的回答').fill(answer);
    await restoredFirst.getByRole('button', { name: '保存草稿' }).click();
    await page.getByText('草稿已保存', { exact: true }).last().waitFor({ state: 'visible', timeout: 10000 });
    await restoredFirst.getByRole('button', { name: '技术路由验证' }).click();
    await page.getByText('技术路由验证通过；仍需人工核验来源', { exact: true }).waitFor({ state: 'visible', timeout: 15000 });
    await restoredFirst.getByText('我已人工核对来源确实支持该回答', { exact: true }).click();
    await page.getByRole('button', { name: '刷新待办' }).click();
    assert.equal(await restoredFirst.getByRole('button', { name: '发布版本' }).isDisabled(), true, 'refreshing a case must clear the previous draft attestation');
    await restoredFirst.getByText('我已人工核对来源确实支持该回答', { exact: true }).click();
    await restoredFirst.getByRole('button', { name: '发布版本' }).click();
    const publishToast = page.locator('.el-message__content').filter({ hasText: '已发布' });
    await publishToast.waitFor({ state: 'visible', timeout: 15000 });
    const publicationMessage = await publishToast.innerText();
    const revisionId = publicationMessage.replace('已发布', '').trim();
    await restoredFirst.getByLabel('基线版本').waitFor({ state: 'visible' });
    assert.equal(await restoredFirst.getByLabel('基线版本').inputValue(), revisionId, 'the next revision base must follow the active pointer after publish');

    await restoredFirst.getByPlaceholder('发布后输入未参与编辑的新问法').fill(alias);
    await restoredFirst.getByRole('button', { name: '游客真实 SSE 复测' }).click();
    const liveResult = restoredFirst.locator('.live-result');
    await liveResult.getByText(answer, { exact: false }).waitFor({ state: 'visible', timeout: 30000 });
    const liveText = await liveResult.innerText();
    assert.ok(liveText.includes(revisionId), 'live result must show the published revision');
    assert.ok(liveText.includes(`wuxi_gazetteer_${suffix}`), 'live result must show the evidence id');
    assert.ok(liveText.includes(sourceRef), 'live result must show the public source');
    const checkId = liveText.match(/check：([^\s]+)/)?.[1];
    assert.ok(checkId, 'live SSE result must expose a server check ID');
    const desktopScreenshot = path.join(screenshotDir, 'guideloop-desktop.png');
    await page.screenshot({ path: desktopScreenshot, fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    const mobileColumns = await restoredFirst.locator('.draft-form').evaluate(element => getComputedStyle(element).gridTemplateColumns.trim().split(/\s+/).length);
    assert.equal(mobileColumns, 1, '390px layout must use one form column');
    const mobileScreenshot = path.join(screenshotDir, 'guideloop-mobile.png');
    await page.screenshot({ path: mobileScreenshot, fullPage: true });

    await page.setViewportSize({ width: 1440, height: 900 });
    await liveResult.getByRole('button', { name: '复测通过（人工核对）' }).click();
    await page.getByText('复测状态：closed', { exact: true }).waitFor({ state: 'visible', timeout: 15000 });
    assert.deepEqual(pageErrors, [], 'the browser must not raise uncaught page errors');

    console.log(JSON.stringify({
      passed: true,
      case_id: caseId,
      revision_id: revisionId,
      check_id: checkId,
      live_result: liveText,
      viewports: [{ width: 1440, height: 900 }, { width: 390, height: 844, form_columns: mobileColumns }],
      screenshots: [desktopScreenshot, mobileScreenshot],
      page_errors: pageErrors,
      browser_responses_are_unmocked: true,
    }, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
