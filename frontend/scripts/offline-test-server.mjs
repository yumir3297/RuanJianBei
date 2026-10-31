/**
 * 离线验收用的最小静态服务器（只用于测试，不进入生产部署）。
 *
 * 行为对齐生产：
 * - /offline.html 是真实静态文件，直接返回；
 * - /health 返回 JSON；
 * - 其余未知路径（非 /api）回落 index.html，模拟 FastAPI 的 SPA 兜底；
 * - /api/** 返回 404 JSON，避免被回落成 HTML。
 */

import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import path from "node:path";

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".vrm": "application/octet-stream",
  ".glb": "model/gltf-binary",
  ".vrma": "application/octet-stream",
  ".woff2": "font/woff2",
};

export function startStaticServer({ distDir, port = 0 }) {
  const root = path.resolve(distDir);
  const server = createServer((request, response) => {
    const url = new URL(request.url || "/", "http://127.0.0.1");
    const pathname = decodeURIComponent(url.pathname);

    if (pathname === "/health") {
      response.writeHead(200, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" });
      response.end(JSON.stringify({ status: "ok", service: "offline-e2e" }));
      return;
    }

    if (pathname.startsWith("/api/")) {
      response.writeHead(404, { "Content-Type": "application/json; charset=utf-8" });
      response.end(JSON.stringify({ detail: "not-found" }));
      return;
    }

    let filePath = path.join(root, pathname === "/" ? "index.html" : pathname.slice(1));
    if (!path.resolve(filePath).startsWith(root)) {
      response.writeHead(403);
      response.end("forbidden");
      return;
    }
    if (!existsSync(filePath) || statSync(filePath).isDirectory()) {
      filePath = path.join(root, "index.html");
    }

    const ext = path.extname(filePath).toLowerCase();
    response.writeHead(200, {
      "Content-Type": MIME_TYPES[ext] || "application/octet-stream",
      "Cache-Control": "no-cache",
      "Service-Worker-Allowed": "/",
    });
    if (request.method === "HEAD") {
      response.end();
      return;
    }
    createReadStream(filePath).pipe(response);
  });

  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => {
      resolve({ server, port: server.address().port, origin: `http://127.0.0.1:${server.address().port}` });
    });
  });
}
