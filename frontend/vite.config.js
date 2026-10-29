import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: "0.0.0.0",
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        // Preserve the browser's Host so the API's same-origin CSRF check can
        // compare it with the original Origin header in local development.
        changeOrigin: false,
      },
      "/ui-assets": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
