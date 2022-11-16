import { createApp, reactive } from "vue"
import { send_form, send_request } from "base"


const store = reactive({
    problems: problems,
    teams: teams,
    user: user,
    docs: docs,
    user_team: user_team,
    curr_row: {},
})


const app = createApp({
    methods: {
        async upload(event) {
            const payload = new FormData(event.currentTarget)
            payload.append("problem", this.problem.id)
            var response = await send_form("documentation/create", payload)
            if (response) {
                response = await response.json()
                store.docs[response.problem][response.team] = response
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
            if (this.editing) {
                this.editing = false
                store.curr_row = {}
            } else {
                store.curr_row.editing = false
                store.curr_row = this
                this.editing = true
            }
        },
        async remove(doc) {
            var response = await send_request("documentation/delete/" + doc.id)
            if (response) {
                delete store.docs[this.problem.id][doc.team]
                this.toggle_editing()
            }
        },
        async upload(event) {
            const payload = new FormData(event.currentTarget)
            payload.append("problem", this.problem.id)
            var response = await send_form("documentation/create", payload)
            if (response) {
                response = await response.json()
                store.docs[response.problem][response.team] = response
            }
        },
    }
})

app.component("ProblemRow", {
    template: "#problem_row",
    props: ["problem"],
    data() {
        return {
            editing: false,
            store: store,
        }
    },
    methods: {
        toggle_editing() {
            if (this.editing) {
                this.editing = false
                store.curr_row = {}
            } else {
                store.curr_row.editing = false
                store.curr_row = this
                this.editing = true
            }
        },
        async remove(doc) {
            var response = await send_request("documentation/delete/" + doc.id)
            if (response) {
                delete store.docs[this.problem.id][doc.team]
                this.toggle_editing()
            }
        },
        async upload(event) {
            const payload = new FormData(event.currentTarget)
            payload.append("problem", this.problem.id)
            var response = await send_form("documentation/create", payload)
            if (response) {
                response = await response.json()
                store.docs[response.problem][response.team] = response
            }
        },
    },
})


app.mount("#app")
