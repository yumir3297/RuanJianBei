import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { makeAppConfig } from "./vite.shared.js";

export default defineConfig({ ...makeAppConfig({ app: "admin", port: 5174 }), plugins: [vue()] });
