import { createApp, reactive } from "vue"
import { send_form, send_request, fmt_date, remove_unchanged } from "base"


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
            var response = await send_request(`problem/${this.problem.id}/delete`)
            if (response) {
                delete store.problems[this.problem.id]
            }
        },
        async edit(event) {
            const payload = new FormData(event.currentTarget)
            if (payload.get("description").size == 0) {
                payload.delete("description")
            }
            if (payload.get("file").size == 0) {
                payload.delete("file")
            }
            remove_unchanged(payload, this.problem)
            var response = await send_form(`problem/${this.problem.id}/edit`, payload)
            if (response) {
                response = await response.json()
                store.problems[response.id] = response
                this.toggle_editing()
            }
        },
        fmt_date
    }
})


app.mount("#app")
