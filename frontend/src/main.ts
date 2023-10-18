import * as bootstrap from "bootstrap";
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { OpenAPI } from "@client";
import { useCookies } from "@vueuse/integrations/useCookies";

import "./assets/styles.scss";

const cookies = useCookies();
OpenAPI.HEADERS = async () => {
  return { "X-User-Token": cookies.get("algobattle_user_token") };
};

const app = createApp(App);

app.use(router);

app.mount("#app");
