import { createApp, reactive } from 'vue'
import App from './App.vue'
import router from './router'

import "./assets/styles.scss"
import * as bootsrap from "bootstrap"
import './assets/main.css'

const store = reactive({
    user: {},
})

const app = createApp(App)

app.use(router)

app.mount('#app')
