import { createApp, reactive } from "vue"
import { send_request, fmt_date } from "base"


const store = reactive({
    results: results,
    teams: teams,
    programs: programs,
    problems: problems,
})


const app = createApp({
    data() {
        return {
            store: store,
        }
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]


app.component("Result", {
    template: "#result",
    props: ["result"],
    data() {
        return {
            store: store,
        }
    },
    methods: {
        fmt_date,
    }
})


app.mount("#app")
