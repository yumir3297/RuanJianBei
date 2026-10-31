/**
 * 构建期生成离线预缓存清单与 sw.js。
 *
 * 关键点：清单必须来自真实构建产物图（offline 入口 chunk → 静态 import → CSS/资源），
 * 不能在构建前猜哈希文件名；public/offline 下的静态资源按目录枚举并校验存在。
 */

import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

const OFFLINE_ENTRY_SUFFIX = "/src/offline/main.js";
const CACHE_PREFIX = "a5-offline-";

function collectPublicFiles(rootDir) {
  const files = [];
  const walk = (dir) => {
    if (!existsSync(dir)) return;
    for (const name of readdirSync(dir)) {
      const full = path.join(dir, name);
      if (statSync(full).isDirectory()) walk(full);
      else files.push(full);
    }
  };
  walk(rootDir);
  return files;
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function offlineServiceWorkerPlugin({ templatePath, publicDir, distDir, version }) {
  return {
    name: "a5-offline-service-worker",
    apply: "build",
    generateBundle(_options, bundle) {
      // HTML 入口的 chunk 以 html 文件作为 facade，因此同时按入口名判定。
      const entry = Object.values(bundle).find(
        (item) =>
          item.type === "chunk" &&
          item.isEntry &&
          (item.name === "offline" ||
            String(item.facadeModuleId || "").replace(/\\/g, "/").endsWith(OFFLINE_ENTRY_SUFFIX)),
      );
      if (!entry) {
        this.error("[offline-sw] 未找到 offline 入口 chunk，请检查 vite.config.js 的 rollupOptions.input");
        return;
      }

      const bundleFiles = new Set();
      const collectChunk = (chunk) => {
        if (!chunk || bundleFiles.has(chunk.fileName)) return;
        bundleFiles.add(chunk.fileName);
        for (const imported of chunk.imports || []) collectChunk(bundle[imported]);
        for (const imported of chunk.dynamicImports || []) collectChunk(bundle[imported]);
        for (const css of chunk.viteMetadata?.importedCss || []) bundleFiles.add(css);
        for (const asset of chunk.viteMetadata?.importedAssets || []) bundleFiles.add(asset);
      };
      collectChunk(entry);

      // 统计用：来自真实 bundle 的字节数（含 HTML 与 CSS 资产）。
      const sizes = new Map();
      for (const [fileName, item] of Object.entries(bundle)) {
        const bytes =
          item.type === "chunk"
            ? Buffer.byteLength(item.code || "")
            : Buffer.byteLength(item.source || "");
        sizes.set(fileName, bytes);
      }

      // 只枚举 public/offline 下的离线静态资源，绝不把 VRM/模型/主站图片打进预缓存。
      const offlinePublicDir = path.join(publicDir, "offline");
      const publicFiles = collectPublicFiles(offlinePublicDir).map((full) => ({
        url: `/${path.relative(publicDir, full).split(path.sep).join("/")}`,
        full,
        bytes: statSync(full).size,
      }));

      const missingPublic = publicFiles.filter((file) => !existsSync(path.join(distDir, file.url.replace(/^\//, ""))));
      if (missingPublic.length) {
        this.error(
          `[offline-sw] 以下 public 资源未出现在构建输出中：${missingPublic.map((file) => file.url).join(", ")}`,
        );
        return;
      }

      const urls = Array.from(
        new Set([
          "/offline.html",
          "/favicon.svg",
          "/offline-precache-manifest.json",
          ...[...bundleFiles].map((fileName) => `/${fileName}`),
          ...publicFiles.map((file) => file.url),
        ]),
      ).sort();

      const sizeOf = (url) => {
        const key = url.replace(/^\//, "");
        if (sizes.has(key)) return sizes.get(key);
        const publicFile = publicFiles.find((file) => file.url === url);
        if (publicFile) return publicFile.bytes;
        const diskPath = path.join(publicDir, key);
        return existsSync(diskPath) ? statSync(diskPath).size : null;
      };

      let totalBytes = 0;
      const unknownSizes = [];
      for (const url of urls) {
        const bytes = sizeOf(url);
        if (bytes == null) unknownSizes.push(url);
        else totalBytes += bytes;
      }

      const buildId = createHash("sha256")
        .update(`${version}\n${urls.join("\n")}`)
        .digest("hex")
        .slice(0, 12);

      const buildInfo = {
        buildId,
        version,
        generatedAt: new Date().toISOString(),
        cachePrefix: CACHE_PREFIX,
        urls,
      };

      const template = readFileSync(templatePath, "utf8");
      if (!template.includes("__OFFLINE_BUILD_INFO__")) {
        this.error("[offline-sw] Service Worker 模板缺少 __OFFLINE_BUILD_INFO__ 占位符");
        return;
      }

      // manifest 自身也列入预缓存，离线时页面仍可读取它做完整性校验；
      // buildId 只由版本号与 URL 列表决定，不依赖 manifest 内容，因此不存在循环。
      this.emitFile({
        type: "asset",
        fileName: "offline-precache-manifest.json",
        source: JSON.stringify({ ...buildInfo, totalBytes }, null, 2),
      });
      this.emitFile({
        type: "asset",
        fileName: "sw.js",
        source: template.replace("__OFFLINE_BUILD_INFO__", JSON.stringify(buildInfo)),
      });

      this.info(
        `[offline-sw] buildId=${buildId} 预缓存 ${urls.length} 项，` +
          `可统计原始体积 ${formatBytes(totalBytes)}` +
          (unknownSizes.length ? `（构建期无法统计：${unknownSizes.join(", ")}）` : ""),
      );
      for (const url of urls) {
        const bytes = sizeOf(url);
        this.info(`[offline-sw]   ${(bytes == null ? "—" : formatBytes(bytes)).padStart(9)}  ${url}`);
      }
    },
  };
}
