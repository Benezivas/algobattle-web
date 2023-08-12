import * as bootstrap from "bootstrap"
import { createApp, reactive } from 'vue'
import App from './App.vue'
import router from './router'
import { useCookies } from "vue3-cookies"
import { OpenAPI, type UserWithSettings, type DbFile } from "../typescript_client";

import "./assets/styles.scss"

export type ModelDict<T> = {[key: string]: T}
export interface InputFileEvent extends InputEvent {
  target: HTMLInputElement;
}

export interface DbFileLoc extends DbFile{
    location: string,
}

export function formatDateTime(datetime: string): string {
    return (new Date(datetime)).toLocaleString()
}

const { cookies } = useCookies()
OpenAPI.BASE = import.meta.env.MODE == "production" ? "" : "http://127.0.0.1:8000";
OpenAPI.HEADERS = async () => {
    return {"X-User-Token": cookies.get("algobattle_user_token")};
};


export const store = reactive({
    user: {} as UserWithSettings,
})

const app = createApp(App)

app.use(router)

app.mount('#app')
