import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { makeAppConfig } from "./vite.shared.js";
import { frontendRoot } from "./vite.shared.js";
import { offlineServiceWorkerPlugin } from "./scripts/offline-sw-plugin.mjs";
import { readFileSync } from "node:fs";

const version = JSON.parse(readFileSync(`${frontendRoot}/package.json`, "utf8")).version;

export default defineConfig(({ command }) => {
  const config = makeAppConfig({ app: "tourist", port: 5173 });
  // The dev server must read the stable source assets. The prepare-public
  // script recreates .public-tourist for production builds and can run while
  // a dev server is active.
  config.publicDir = command === "serve"
    ? `${frontendRoot}/public`
    : `${frontendRoot}/.public-tourist`;
  config.build.rollupOptions.input = {
    main: `${frontendRoot}/apps/tourist/index.html`,
    offline: `${frontendRoot}/apps/tourist/offline.html`,
  };
  config.server.proxy["/health"] = { target: "http://127.0.0.1:8000", changeOrigin: false };
  return {
    ...config,
    define: { __APP_VERSION__: JSON.stringify(version) },
    plugins: [vue(), offlineServiceWorkerPlugin({
      templatePath: `${frontendRoot}/src/offline/service-worker.js`,
      publicDir: `${frontendRoot}/.public-tourist`,
      distDir: `${frontendRoot}/dist/tourist`,
      offlineHtmlPath: `${frontendRoot}/apps/tourist/offline.html`,
      version,
    })],
  };
});
