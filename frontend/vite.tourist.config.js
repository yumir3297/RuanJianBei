import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { makeAppConfig } from "./vite.shared.js";
import { frontendRoot } from "./vite.shared.js";
import { offlineServiceWorkerPlugin } from "./scripts/offline-sw-plugin.mjs";
import { readFileSync } from "node:fs";

const config = makeAppConfig({ app: "tourist", port: 5173 });
const version = JSON.parse(readFileSync(`${frontendRoot}/package.json`, "utf8")).version;
config.build.rollupOptions.input = {
  main: `${frontendRoot}/apps/tourist/index.html`,
  offline: `${frontendRoot}/apps/tourist/offline.html`,
};
config.server.proxy["/health"] = { target: "http://127.0.0.1:8000", changeOrigin: false };
export default defineConfig({
  ...config,
  define: { __APP_VERSION__: JSON.stringify(version) },
  plugins: [vue(), offlineServiceWorkerPlugin({
    templatePath: `${frontendRoot}/src/offline/service-worker.js`,
    publicDir: `${frontendRoot}/.public-tourist`,
    distDir: `${frontendRoot}/dist/tourist`,
    offlineHtmlPath: `${frontendRoot}/apps/tourist/offline.html`,
    version,
  })],
});
