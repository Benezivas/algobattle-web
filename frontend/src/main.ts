import * as bootstrap from "bootstrap"
import { createApp, reactive } from 'vue'
import App from './App.vue'
import router from './router'

import "./assets/styles.scss"
import { Configuration, UserApi } from "../typescript_client"

const configuration = new Configuration({
    basePath: "http://127.0.0.1:8000",
})

const userApi = new UserApi(configuration)


export const store = reactive({
    user:  await userApi.getSelf(),
})

const app = createApp(App)

app.use(router)

app.mount('#app')
