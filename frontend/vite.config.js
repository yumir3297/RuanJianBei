import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

import { offlineServiceWorkerPlugin } from "./scripts/offline-sw-plugin.mjs";

const rootDir = fileURLToPath(new URL(".", import.meta.url));
const pkg = JSON.parse(readFileSync(path.join(rootDir, "package.json"), "utf8"));

const devProxy = {
  "/api": {
    target: "http://127.0.0.1:8000",
    changeOrigin: true,
  },
  "/ui-assets": {
    target: "http://127.0.0.1:8000",
    changeOrigin: true,
  },
  // 离线伴游的同源连通性探针；开发环境必须与生产保持同一路径。
  "/health": {
    target: "http://127.0.0.1:8000",
    changeOrigin: true,
  },
};

export default defineConfig({
  plugins: [
    vue(),
    offlineServiceWorkerPlugin({
      templatePath: path.join(rootDir, "src/offline/service-worker.js"),
      publicDir: path.join(rootDir, "public"),
      distDir: path.join(rootDir, "dist"),
      version: pkg.version,
    }),
  ],
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
  server: {
    port: 5173,
    host: "0.0.0.0",
    proxy: devProxy,
  },
  preview: {
    port: 4173,
    host: "0.0.0.0",
    proxy: devProxy,
  },
  build: {
    rollupOptions: {
      input: {
        main: path.join(rootDir, "index.html"),
        offline: path.join(rootDir, "offline.html"),
      },
    },
  },
});
