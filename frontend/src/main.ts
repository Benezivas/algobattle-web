import * as bootstrap from "bootstrap"
import { createApp, reactive } from 'vue'
import App from './App.vue'
import router from './router'

import "./assets/styles.scss"

export const store = reactive({
    user: {},
})

const app = createApp(App)

app.use(router)

app.mount('#app')
