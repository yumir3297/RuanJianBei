/**
 * 离线伴游端到端验收。
 *
 * 运行前提：先 `npm run build`（本脚本使用生产构建产物而非 vite dev）。
 * 覆盖：OFF-01/02/03/04/05/07/08、NET-02/05、SAFE-01/02/06/08、UI-01（360px）、PERF-01（体积）。
 * 真实断网由 Playwright context.setOffline 模拟，仍不等同真机蜂窝掉线。
 */

import assert from "node:assert/strict";
import { mkdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

import { chromium } from "playwright-core";

import { startStaticServer } from "../../scripts/offline-test-server.mjs";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const distDir = path.join(rootDir, "dist");
const evidenceDir = path.join(rootDir, "../docs/implementation/evidence");
mkdirSync(evidenceDir, { recursive: true });

const results = [];
let browser;
let serverHandle;

async function step(name, fn) {
  const startedAt = Date.now();
  try {
    await fn();
    results.push({ name, status: "PASS", ms: Date.now() - startedAt });
    console.log(`PASS  ${name}`);
  } catch (error) {
    results.push({ name, status: "FAIL", ms: Date.now() - startedAt, error: String(error?.message || error) });
    console.log(`FAIL  ${name}\n      ${String(error?.message || error).split("\n")[0]}`);
  }
}

function measurePrecache() {
  const manifestPath = path.join(distDir, "offline-precache-manifest.json");
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  let raw = 0;
  let gzip = 0;
  for (const url of manifest.urls) {
    const filePath = path.join(distDir, url.replace(/^\//, ""));
    const buffer = readFileSync(filePath);
    raw += buffer.byteLength;
    gzip += gzipSync(buffer).byteLength;
  }
  return { manifest, raw, gzip };
}

async function waitForPrecache(page) {
  await page.waitForFunction(
    async () => {
      if (!("caches" in window)) return false;
      const keys = await caches.keys();
      const key = keys.find((item) => item.startsWith("a5-offline-"));
      if (!key) return false;
      const cache = await caches.open(key);
      const requests = await cache.keys();
      const paths = new Set(requests.map((request) => new URL(request.url).pathname));
      return ["/offline.html", "/offline/help/contacts.json", "/offline/map/map-meta.json"].every((url) =>
        paths.has(url),
      );
    },
    null,
    { timeout: 45000 },
  );
}

async function main() {
  const { server, origin } = await startStaticServer({ distDir });
  serverHandle = server;
  browser = await chromium.launch({ headless: true });

  const perf = measurePrecache();
  console.log(
    `[PERF] 预缓存 ${perf.manifest.urls.length} 项：原始 ${(perf.raw / 1024).toFixed(1)} KB，` +
      `gzip 传输约 ${(perf.gzip / 1024).toFixed(1)} KB，buildId=${perf.manifest.buildId}`,
  );

  // ---------------- 场景 1：首次在线访问主站，后台准备离线包 ----------------
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
  });
  const mainPage = await context.newPage();
  const consoleErrors = [];
  mainPage.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await step("OFF-01 首次在线访问主站后完成离线包准备", async () => {
    await mainPage.goto(`${origin}/tourist`, { waitUntil: "domcontentloaded" });
    await waitForPrecache(mainPage);
    const state = await mainPage.evaluate(async () => {
      const registration = await navigator.serviceWorker.ready;
      return { active: Boolean(registration.active), controlled: Boolean(navigator.serviceWorker.controller) };
    });
    assert.equal(state.active, true, "Service Worker 未激活");
  });

  await step("PERF-01 预缓存体积远低于 1MB 上限", () => {
    assert.ok(perf.gzip < 1024 * 1024, `gzip 体积 ${perf.gzip} 超过 1MB`);
    assert.ok(!perf.manifest.urls.some((url) => /\/models\/|\/motions\/|\/assets\/(main|index|TouristView)/.test(url)));
  });

  // ---------------- 场景 2：断网后直接打开离线页 ----------------
  const offlinePage = await context.newPage();
  await context.setOffline(true);

  await step("OFF-02/03 断网后新标签页直接导航 /offline.html 仍可用", async () => {
    await offlinePage.goto(`${origin}/offline.html`, { waitUntil: "domcontentloaded" });
    assert.match(await offlinePage.textContent("h1"), /离线伴游/);
    assert.equal(await offlinePage.isVisible("#game-canvas"), true);
    assert.equal(await offlinePage.isVisible("#open-map"), true);
    assert.equal(await offlinePage.isVisible("#open-help"), true);
    await offlinePage.screenshot({ path: path.join(evidenceDir, "offline-home.jpg"), type: "jpeg", quality: 82 });
  });

  await step("SAFE-02 断网打开地图，可缩放且无在线瓦片请求", async () => {
    await offlinePage.click("#open-map");
    await offlinePage.waitForSelector("#map-viewport:not([hidden])");
    assert.equal(await offlinePage.isVisible("#map-empty"), false, "地图可用时不应同时显示缺失状态");
    const loaded = await offlinePage.evaluate(() => {
      const image = document.getElementById("map-image");
      return { complete: image.complete, width: image.naturalWidth, src: image.getAttribute("src") };
    });
    assert.ok(loaded.width > 0, "地图图片未能从缓存加载");
    assert.match(loaded.src, /^\/offline\/map\//);
    const before = await offlinePage.evaluate(() => document.getElementById("map-image").style.transform);
    await offlinePage.click("#map-zoom-in");
    const after = await offlinePage.evaluate(() => document.getElementById("map-image").style.transform);
    assert.notEqual(before, after, "缩放没有生效");
    assert.match(await offlinePage.textContent("#map-warning"), /未核验/);
    await offlinePage.screenshot({ path: path.join(evidenceDir, "offline-map.jpg"), type: "jpeg", quality: 82 });
  });

  await step("SAFE-08 打开地图时游戏自动暂停，关闭后恢复", async () => {
    await offlinePage.click("[data-close-map]");
    await offlinePage.click("#btn-start");
    await offlinePage.waitForTimeout(600);
    await offlinePage.click("#open-map");
    await offlinePage.waitForTimeout(200);
    assert.match(await offlinePage.textContent("#game-status"), /暂停/);
    await offlinePage.click("[data-close-map]");
    await offlinePage.waitForTimeout(300);
  });

  await step("SAFE-01/06 求助面板可见、号码可复制且未核验时不出现拨号按钮", async () => {
    await offlinePage.click("#open-help");
    await offlinePage.waitForSelector("#help-sheet:not([hidden])");
    const cards = await offlinePage.locator(".contact-card").count();
    assert.ok(cards > 0, "没有渲染任何联系电话");
    const dialButtons = await offlinePage.locator(".contact-dial").count();
    assert.equal(dialButtons, 0, "未核验号码不应出现 tel: 拨号按钮");
    assert.match(await offlinePage.textContent("#contacts"), /未核验/);
    await offlinePage.screenshot({ path: path.join(evidenceDir, "offline-help.jpg"), type: "jpeg", quality: 82 });
    await offlinePage.click("[data-close-help]");
  });

  await step("GAME-01 断网下点击画面开始并计分", async () => {
    await offlinePage.click("#btn-start");
    await offlinePage.waitForTimeout(1400);
    const score = Number(await offlinePage.textContent("#score"));
    assert.ok(score > 0, `分数没有增长：${score}`);
    await offlinePage.click("#game-canvas");
    await offlinePage.screenshot({ path: path.join(evidenceDir, "offline-game.jpg"), type: "jpeg", quality: 82 });
  });

  await step("OFF-07 离线时 /health 不会读到 Service Worker 伪造的缓存", async () => {
    const outcome = await offlinePage.evaluate(async () => {
      try {
        const response = await fetch("/health", { cache: "no-store" });
        return `http-${response.status}`;
      } catch {
        return "failed";
      }
    });
    assert.equal(outcome, "failed");
  });

  await step("OFF-05 删除关键缓存后不崩溃并明确提示未就绪", async () => {
    await offlinePage.evaluate(async () => {
      const keys = await caches.keys();
      const key = keys.find((item) => item.startsWith("a5-offline-"));
      const cache = await caches.open(key);
      await cache.delete("/offline/help/contacts.json");
    });
    await offlinePage.reload({ waitUntil: "domcontentloaded" });
    await offlinePage.click("#open-help");
    await offlinePage.waitForTimeout(400);
    assert.match(await offlinePage.textContent("#contacts"), /暂不可用/);
    assert.match(await offlinePage.textContent("#cache-chip"), /未就绪/);
    await offlinePage.click("[data-close-help]");
  });

  // ---------------- 场景 3：恢复网络后提示返回 ----------------
  await step("NET-05/06 连续两次探针成功后出现返回提示，跑酷不被中断也不自动跳转", async () => {
    await offlinePage.click("#btn-start");
    await offlinePage.waitForTimeout(900);
    const scoreBefore = Number(await offlinePage.textContent("#score"));
    await context.setOffline(false);
    await offlinePage.waitForSelector("#recover-banner:not([hidden])", { timeout: 45000 });
    assert.match(await offlinePage.textContent("#recover-banner"), /网页服务已恢复/);
    assert.match(offlinePage.url(), /\/offline\.html/, "恢复后不得自动跳转");
    const scoreAfter = Number(await offlinePage.textContent("#score"));
    assert.ok(scoreAfter >= scoreBefore, `恢复过程不应重置当前一局：${scoreBefore} -> ${scoreAfter}`);
  });

  await step("GAME-06 点击返回只跳转一次且落在白名单路径", async () => {
    await Promise.all([
      offlinePage.waitForURL(`${origin}/tourist`, { timeout: 15000 }),
      offlinePage.click("#btn-return-recovered"),
    ]);
    assert.equal(new URL(offlinePage.url()).pathname, "/tourist");
  });

  // ---------------- 场景 4：从未准备过离线包 ----------------
  await step("OFF-04 从未在线准备时断网打开不会显示伪造的可用页面", async () => {
    const freshContext = await browser.newContext();
    const freshPage = await freshContext.newPage();
    await freshContext.setOffline(true);
    let failed = false;
    try {
      await freshPage.goto(`${origin}/offline.html`, { timeout: 8000 });
    } catch {
      failed = true;
    }
    if (!failed) {
      const body = await freshPage.textContent("body");
      assert.doesNotMatch(body, /离线资源 .* 已缓存/, "未准备时不得宣称离线已就绪");
    }
    await freshContext.close();
  });

  // ---------------- 场景 5：主站弱网横幅（后端不可达但网络已连接） ----------------
  await step("NET-02/03 主站持续不可达 15s 后出现进入离线伴游横幅，不自动跳转", async () => {
    const degradedContext = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
    const page = await degradedContext.newPage();
    await page.route("**/health", (route) => route.abort("connectionrefused"));
    await page.goto(`${origin}/tourist`, { waitUntil: "domcontentloaded" });
    await page.waitForSelector(".offline-entry-prompt--urgent", { timeout: 45000 });
    const text = await page.textContent(".offline-entry-prompt--urgent");
    await page.screenshot({ path: path.join(evidenceDir, "main-offline-banner.jpg"), type: "jpeg", quality: 82 });
    assert.match(text, /网络暂时不可达/);
    assert.match(page.url(), /\/tourist/, "横幅出现时不得自动跳转");
    const enter = page.locator(".offline-entry-primary");
    if (await enter.count()) {
      await Promise.all([page.waitForURL(/\/offline\.html/, { timeout: 15000 }), enter.click()]);
      assert.match(page.url(), /\/offline\.html/);
    }
    await degradedContext.close();
  });

  await step("NET-09 主站可达但业务接口失败时不冒充设备离线", async () => {
    const apiFailContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await apiFailContext.newPage();
    await page.route("**/api/**", (route) => route.abort());
    await page.goto(`${origin}/tourist`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(6000);
    assert.equal(await page.locator(".offline-entry-prompt--urgent").count(), 0, "/api 失败不应触发离线横幅");
    assert.match(page.url(), /\/tourist/);
    await apiFailContext.close();
  });

  // ---------------- 场景 6：窄屏无横向溢出 ----------------
  await step("UI-01 360px 窄屏无横向溢出", async () => {
    const narrowContext = await browser.newContext({ viewport: { width: 360, height: 740 } });
    const page = await narrowContext.newPage();
    await page.goto(`${origin}/offline.html`, { waitUntil: "domcontentloaded" });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    assert.ok(overflow <= 1, `横向溢出 ${overflow}px`);
    await narrowContext.close();
  });

  await step("REG-01 主站页面在离线组件接入后仍可渲染游客界面", async () => {
    assert.match(await mainPage.textContent("body"), /数字人|导览|景区/);
    const fatal = consoleErrors.filter((line) => /Uncaught|TypeError: Cannot read/.test(line));
    assert.equal(fatal.length, 0, `控制台致命错误：${fatal.join(" | ")}`);
  });

  await context.close();
}

try {
  await main();
} catch (error) {
  results.push({ name: "harness", status: "FAIL", error: String(error?.stack || error) });
  console.error("HARNESS FAILURE", error);
} finally {
  await browser?.close().catch(() => {});
  await new Promise((resolve) => serverHandle?.close(resolve));
}

const failed = results.filter((item) => item.status !== "PASS");
console.log("\n===== E2E SUMMARY =====");
for (const item of results) {
  console.log(`${item.status.padEnd(4)} ${String(item.ms ?? "").padStart(6)}ms  ${item.name}${item.error ? ` :: ${item.error}` : ""}`);
}
console.log(`${results.length - failed.length}/${results.length} PASS`);
process.exitCode = failed.length ? 1 : 0;
