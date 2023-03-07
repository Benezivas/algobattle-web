import { createApp, reactive } from "vue"
import { send_form, send_request, fmt_date } from "base"


const store = reactive({
    programs: programs,
    problems: problems,
    roles: roles,
    teams: teams,
    user: user,
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
            user_editable: false,
        }
    },
    methods: {
        toggle_editing() {
            this.editing = !this.editing
        },
        async remove() {
            var response = await send_request(`program/${this.program.id}/delete/`)
            if (response) {
                delete store.programs[this.program.id]
            }
        },
        async edit(event) {
            const payload = new FormData(event.currentTarget)
            var response = await send_form(`program/${this.program.id}/edit`, payload)
            if (response) {
                response = await response.json()
                store.programs[response.id] = response
                this.toggle_editing()
            }
        },
        async set_user_editable(event) {
            var response = await send_request(`program/${this.program.id}/user_editable`, this.user_editable)
            if (response) {
                store.programs[response.id] = response
            }
        },
        fmt_date
    }
})


app.mount("#app")
