import { createApp, reactive } from "vue"
import { send_request, pick } from "base"

const store = reactive({
    users: users_input,
    teams: teams_input,
    contexts: contexts_input,
})


const app = createApp({
    data() {
        return {
            store: store,
            filter: {
                name: "",
                email: "",
                is_admin: null,
                context: null,
                team: null,
            },
            editing_new: false,
            new_user: {
                name: null,
                email: null,
                is_admin: false,
            },
        }
    },
    computed: {
        apply_filters() {
            var filters = []
            if (this.filter.name != "") {
                filters.push(`name=${this.filter.name}`)
            }
            if (this.filter.email != "") {
                filters.push(`email=${this.filter.email}`)
            }
            if (this.filter.is_admin != null) {
                filters.push(`is_admin=${this.filter.is_admin}`)
            }
            if (this.filter.context != null) {
                filters.push(`context=${this.filter.context}`)
            }
            if (this.filter.team != null) {
                filters.push(`team=${this.filter.team}`)
            }
            return `/admin/users?${filters.join("&")}`
        }
    },
    methods: {
        async create_user() {
            var response = await send_request("user/create", this.new_user)
            if (response) {
                store.users[response.id] = response
                this.new_user = {
                    name: null,
                    email: null,
                    is_admin: false,
                }
            }
        },
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]

app.component("TableRow", {
    template: "#table_row",
    props: ["user"],
    data() {
        return {
            editing: false,
            store: store,
        }
    },
    methods: {
        async edit_user(event) {
            var response = await send_request(`user/${this.user.id}/edit`, pick(this.user, "name", "email", "is_admin"))
            if (response) {
                Object.assign(this.user, response)
                this.editing = false
            }
        },
        async delete_user(event) {
            var response = await send_request(`user/${this.user.id}/delete`)
            if (response) {
                delete store.users[this.user.id]
            }
        },
    },
    computed: {
        teams_str() {
            return this.user.teams.map(t => store.teams[t].name).join(", ")
        }
    }
})


app.mount("#app")
