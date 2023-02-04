import { createApp, reactive } from "vue"
import { send_request, pick, queryParams } from "base"

const store = reactive({
    users: users_input,
    teams: teams_input,
    contexts: contexts_input,
})

const params = queryParams()
const app = createApp({
    data() {
        return {
            store: store,
            has_params: Object.keys(params).length != 0,
            filter: {
                name: params.name || "",
                email: params.email || "",
                is_admin: params.is_admin != null ? params.is_admin : null,
                context: params.context || null,
                team: params.team || null,
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
            team_edit: {},
            new_team: {},
            hover: false,
        }
    },
    methods: {
        async edit_user(event) {
            var edit = pick(this.user, "name", "email", "is_admin")
            edit.teams = this.team_edit
            var response = await send_request(`user/${this.user.id}/edit`, edit)
            if (response) {
                Object.assign(this.user, response)
                this.team_edit = {}
                this.editing = false
            }
        },
        async delete_user(event) {
            var response = await send_request(`user/${this.user.id}/delete`)
            if (response) {
                delete store.users[this.user.id]
            }
        },
        async remove_team(team) {
            if (this.team_edit[team] == null) {
                this.team_edit[team] = false
            } else {
                delete this.team_edit[team]
            }
            const index = this.user.teams.indexOf(team)
            this.user.teams.splice(index, 1)
        },
        async add_team() {
            const team = this.new_team
            if (this.user.teams.includes(team)) {
                return
            }
            if (this.team_edit[team] == null) {
                this.team_edit[team] = true
            } else {
                delete this.team_edit[team]
            }
            this.user.teams.push(team)
            this.new_team = null
        },
    },
    computed: {
        teams_str() {
            return this.user.teams.map(t => store.teams[t].name).join(", ")
        }
    }
})


app.mount("#app")
