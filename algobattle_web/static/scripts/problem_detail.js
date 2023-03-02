import { createApp, reactive } from "vue"
import { send_request, send_get, pick, queryParams, omit, fmt_date } from "base"




const store = reactive({
    problem: problem,
    contexts: contexts,
})


const app = createApp({
    data() {
        return {
            store: store,
            problem: store.problem,
        }
    },
    watch: {
    },
    methods: {
        fmt_date: fmt_date,
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]


app.mount("#app")
