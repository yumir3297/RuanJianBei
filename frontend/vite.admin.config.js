import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { makeAppConfig, frontendRoot } from "./vite.shared.js";

export default defineConfig(({ command }) => {
  const config = makeAppConfig({ app: "admin", port: 5174 });
  // Keep dev assets in frontend/public so build preparation cannot remove
  // files from a running development server.
  config.publicDir = command === "serve"
    ? `${frontendRoot}/public`
    : `${frontendRoot}/.public-admin`;
  return { ...config, plugins: [vue()] };
});
