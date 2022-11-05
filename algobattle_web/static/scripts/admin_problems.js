import { createApp, reactive } from "vue"


const store = reactive({
    problems: problems,
    configs: configs,
})


const app = createApp({
    methods: {
        async create_problem(event) {
            const payload = new FormData(event.currentTarget)
            if (payload.get("description").size == 0) {
                payload.delete("description")
            }
            var response = await send_form("problem/create", payload)
            if (response) {
                response = await response.json()
                store.problems[response.id] = response
            }
        },
    },
    data() {
        return {
            store: store,
        }
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]


app.component("Problem", {
    template: "#problem",
    props: ["problem"],
    data() {
        return {
            editing: false,
            store: store,
        }
    },
    methods: {
        toggle_editing() {
            this.editing = !this.editing
        },
        async delete_problem() {
            var response = await send_request("problem/delete/" + this.problem.id)
            if (response) {
                delete store.problems[this.problem.id]
            }
        },
        async edit(event) {
            const payload = new FormData(event.currentTarget)
            payload.append("id", this.problem.id)
            if (payload.get("description").size == 0) {
                payload.delete("description")
            }
            if (payload.get("file").size == 0) {
                payload.delete("file")
            }
            var response = await send_form("problem/edit", payload)
            if (response) {
                response = await response.json()
                store.problems[response.id] = response
                this.toggle_editing()
            }
        },
        fmt_date(date) {
            if (!date) {
                return ""
            }
            date = new Date(date)
            return date.toLocaleString()
        }
    }
})


app.mount("#app")
