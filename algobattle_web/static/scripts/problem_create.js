import { createApp, reactive } from "vue"
import { send_form, send_request, fmt_date, remove_unchanged } from "base"


const store = reactive({
})


const app = createApp({
    data() {
        return {
            store: store,
        }
    },
    computed: {
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]




app.mount("#app")
