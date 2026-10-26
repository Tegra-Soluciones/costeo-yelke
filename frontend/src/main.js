import { createApp } from "vue";
import App from "./App.vue";
import router from "./router/index.js";
import "./style.css";
import mayus from "./directivas/mayus.js";

createApp(App).use(router).directive("mayus", mayus).mount("#app");
