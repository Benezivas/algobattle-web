import * as bootstrap from "bootstrap"
import { createApp, reactive } from 'vue'
import App from './App.vue'
import router from './router'
import { useCookies } from "vue3-cookies"

import "./assets/styles.scss"
import {
    Configuration,
    ContextApi,
    DocsApi,
    MatchApi,
    ProblemApi,
    ProgramApi,
    TeamApi,
    UserApi,
    type UserWithSettings
} from "../typescript_client"

const { cookies } = useCookies()
const configuration = new Configuration({
    basePath: "http://127.0.0.1:8000",
    apiKey: () => cookies.get("user_token"),
})

export const userApi = new UserApi(configuration)
export const contextApi = new ContextApi(configuration)
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
