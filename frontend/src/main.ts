import * as bootstrap from "bootstrap";
import { createApp, reactive } from "vue";
import App from "./App.vue";
import router from "./router";
import { OpenAPI, type UserLogin, type Team_Output as Team } from "../typescript_client";

import "./assets/styles.scss";
import { useCookies } from "@vueuse/integrations/useCookies";

export type ModelDict<T> = { [key: string]: T };
export interface InputFileEvent extends InputEvent {
  target: HTMLInputElement;
}
export type FixedLogin = Omit<UserLogin, "logged_in"> & {
    logged_in: Team | "admin" | null,
}

export function formatDateTime(datetime: string): string {
  return new Date(datetime).toLocaleString();
}

const cookies = useCookies();
OpenAPI.BASE = import.meta.env.MODE == "production" ? "" : "http://127.0.0.1:8000";
OpenAPI.HEADERS = async () => {
  return { "X-User-Token": cookies.get("algobattle_user_token") };
};

export const store = reactive<{
    user: FixedLogin | null,
}>({
  user: null,
});

const app = createApp(App);

app.use(router);

app.mount("#app");
