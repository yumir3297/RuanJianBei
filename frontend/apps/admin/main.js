import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import App from "./App.vue";
import router from "./router.js";
import "../../src/style.css";
import "../../src/assets/admin-workbench.css";

createApp(App).use(createPinia()).use(router).use(ElementPlus).mount("#app");
