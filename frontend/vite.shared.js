import { fileURLToPath } from "node:url";

export const frontendRoot = fileURLToPath(new URL(".", import.meta.url));

export function makeAppConfig({ app, port }) {
  return {
    root: `${frontendRoot}/apps/${app}`,
    cacheDir: `${frontendRoot}/node_modules/.vite/${app}`,
    envDir: frontendRoot,
    publicDir: `${frontendRoot}/.public-${app}`,
    server: {
      host: "0.0.0.0",
      port,
      strictPort: true,
      fs: { allow: [frontendRoot] },
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: false,
        },
        "/ui-assets": { target: "http://127.0.0.1:8000", changeOrigin: true },
      },
    },
    preview: { host: "0.0.0.0", port: port + 1000, strictPort: true },
    build: {
      outDir: `${frontendRoot}/dist/${app}`,
      emptyOutDir: false,
      manifest: true,
      rollupOptions: { input: `${frontendRoot}/apps/${app}/index.html` },
    },
  };
}
