import { createApp, reactive } from "vue"
import { send_form, send_request, fmt_date } from "base"


const store = reactive({
    programs: programs,
    problems: problems,
    roles: roles,
    teams: teams,
})


const app = createApp({
    methods: {
        async create_program(event) {
            const payload = new FormData(event.currentTarget)
            if (payload.get("file").size == 0) {
                payload.delete("file")
            }
            var response = await send_form("program/create", payload)
            if (response) {
                response = await response.json()
                store.programs[response.id] = response
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


app.component("Program", {
    template: "#program",
    props: ["program"],
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
            var response = await send_request("program/delete/" + this.problem.id)
            if (response) {
                delete store.programs[this.problem.id]
            }
        },
        async edit(event) {
            const payload = new FormData(event.currentTarget)
            payload.append("id", this.problem.id)
            if (payload.get("file").size == 0) {
                payload.delete("file")
            }
            var response = await send_form("program/edit", payload)
            if (response) {
                response = await response.json()
                store.programs[response.id] = response
                this.toggle_editing()
            }
        },
        fmt_date
    }
})


app.mount("#app")
