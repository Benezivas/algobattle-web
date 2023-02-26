import { createApp, reactive } from "vue"
import { send_request, send_get, pick, queryParams, omit } from "base"

const store = reactive({
    problem: problem,
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
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]


app.mount("#app")
