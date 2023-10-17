import * as bootstrap from "bootstrap";
import { createApp, reactive } from "vue";
import App from "./App.vue";
import router from "./router";
import { OpenAPI, type UserLogin, type Team, type Tournament } from "../typescript_client";

import "./assets/styles.scss";
import { useCookies } from "@vueuse/integrations/useCookies";

export type ModelDict<T> = { [key: string]: T };
export interface InputFileEvent extends InputEvent {
  target: HTMLInputElement;
}

export function formatDateTime(datetime: string): string {
  return new Date(datetime).toLocaleString();
}

const cookies = useCookies();
OpenAPI.HEADERS = async () => {
  return { "X-User-Token": cookies.get("algobattle_user_token") };
};

export const store = reactive<{
  user: UserLogin | null;
  team: Team | "admin" | null;
  tournament: Tournament | null;
}>({
  user: null,
  team: null,
  tournament: null,
});

const app = createApp(App);

app.use(router);

app.mount("#app");
