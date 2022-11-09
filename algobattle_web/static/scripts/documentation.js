import { createApp, reactive } from "vue"
import { send_form, send_request } from "base"


const store = reactive({
    problems: problems,
    teams: teams,
    user: user,
    docs: docs,
    user_team: user_team,
})


const app = createApp({
    methods: {
        async upload(event) {
            const payload = new FormData(event.currentTarget)
            var response = await send_form("documentation/create", payload)
            if (response) {
                response = await response.json()
                store.docs[response.team.id][response.problem.id] = response
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
        doc(id) {
            return store.docs[id][this.problem.id]
        },
        async remove(id) {
            var response = await send_request("documentation/delete/" + this.doc(id).id)
            if (response) {
                delete store.docs[this.doc(id).id]
            }
        },
        async upload(event) {
            const payload = new FormData(event.currentTarget)
            payload.append("problem", this.problem.id)
            var response = await send_form("documentation/create", payload)
            if (response) {
                response = await response.json()
                store.docs[response.team][response.problem] = response
            }
        },
    }
})


app.mount("#app")
