import { createApp } from "vue";
import App from "./App.vue";
import router from "./router/index.js";
import "./style.css";
import soloLectura from "./directivas/soloLectura.js";
import mayus from "./directivas/mayus.js";

createApp(App).use(router).directive("mayus", mayus).directive("solo-lectura", soloLectura).mount("#app");
