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
            var response = await send_form(`documentation/${store.curr_row.problem.id}/upload`, payload)
            if (response) {
                response = await response.json()
                store.docs[response.problem] = response
                store.curr_row.toggle_editing()
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
            editing: undefined,
            store: store,
        }
    },
    methods: {
        toggle_editing(team_id) {
            if (this.editing == team_id) {
                this.editing = undefined
            } else {
                this.editing = team_id
            }
        },
        async remove(doc) {
            var response = await send_request(`documentation/${doc.id}/delete/`)
            if (response) {
                delete store.docs[this.problem.id][doc.team]
                this.toggle_editing()
            }
        },
        async upload(event) {
            const payload = new FormData(event.currentTarget)
            var response = await send_form(`documentation/${this.problem.id}/upload`, payload)
            if (response) {
                response = await response.json()
                store.docs[response.problem][response.team] = response
                this.editing = undefined
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
        async remove(problem) {
            var response = await send_request("documentation/delete/" + store.docs[problem.id].id)
            if (response) {
                delete store.docs[this.problem.id]
                this.toggle_editing()
            }
        },
    },
})


app.mount("#app")
