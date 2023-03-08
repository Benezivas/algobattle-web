import * as bootstrap from "bootstrap"
import { createApp, reactive } from 'vue'
import App from './App.vue'
import router from './router'
import { useCookies } from "vue3-cookies"

import "./assets/styles.scss"
import { Configuration, UserApi } from "../typescript_client"
import type { AlgobattleWebModelsUserSchema } from "../typescript_client"

const { cookies } = useCookies()
const configuration = new Configuration({
    basePath: "http://127.0.0.1:8000",
    apiKey: () => cookies.get("user_token"),
})

export const userApi = new UserApi(configuration)


export const store = reactive({
    user: {} as AlgobattleWebModelsUserSchema,
})

const app = createApp(App)

app.use(router)

app.mount('#app')
