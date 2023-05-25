import * as bootstrap from "bootstrap"
import { createApp, reactive } from 'vue'
import App from './App.vue'
import router from './router'
import { useCookies } from "vue3-cookies"

import "./assets/styles.scss"
import {
    Configuration,
    TournamentApi,
    DocsApi,
    MatchApi,
    ProblemApi,
    ProgramApi,
    TeamApi,
    UserApi,
    type UserWithSettings
} from "../typescript_client"

export type ModelDict<T> = {[key: string]: T}
export interface InputFileEvent extends InputEvent {
  target: HTMLInputElement;
}

const { cookies } = useCookies()
const configuration = new Configuration({
    basePath: "http://127.0.0.1:8000",
    apiKey: () => cookies.get("algobattle_user_token"),
})

export const userApi = new UserApi(configuration)
export const tournamentApi = new TournamentApi(configuration)
export const teamApi = new TeamApi(configuration)
export const problemApi = new ProblemApi(configuration)
export const docsApi = new DocsApi(configuration)
export const programApi = new ProgramApi(configuration)
export const matchApi = new MatchApi(configuration)


export const store = reactive({
    user: {} as UserWithSettings,
})

const app = createApp(App)

app.use(router)

app.mount('#app')
