import { createApp, reactive } from "vue"
import { send_request, pick, queryParams } from "base"
import "bootstrap"

const store = reactive({
    users: users_input,
    teams: teams_input,
    contexts: contexts_input,
    new: {
        data: {
            name: null,
            email: null,
            is_admin: false,
            teams: [],
        },
        new_team: null,
    }
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
            edit_user: {
                teams: [],
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
        },
    },
    methods: {
        async create_user(user) {
            var response = await send_request("user/create", user)
            if (response) {
                store.users[response.id] = response
                store.new.data = {
                    name: null,
                    email: null,
                    is_admin: false,
                    teams: [],
                }
            }
        },
        new_teams(teams) {
            return Object.entries(store.teams).filter(data => !teams.includes(data[0]))
        },
        user_create_add_team() {
            const team = store.new.new_team
            if (store.new.data.teams.includes(team)) {
                return
            }
            store.new.data.teams.push(team)
            store.new.new_team = null
        },
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]

app.component("TableRow", {
    template: "#table_row",
    props: ["user"],
    data() {
        return {
            store: store,
        }
    },
    computed: {
        teams_str() {
            return this.user.teams.map(t => store.teams[t].name).join(", ")
        },
    }
})

app.component("HoverBadge", {
    template: "#hoverBadge",
    props: ["team"],
    data() {
        return {
            hover: false,
        }
    },
})

app.component("EditWindow", {
    template: "#editWindow",
    props: ["user"],
    data() {
        return {
            store: store,
            edit: {
                name: this.user.name,
                email: this.user.email,
                is_admin: this.user.is_admin,
                teams: {},
            },
            display_teams: [...this.user.teams],
            new_team: null,
        }
    },
    watch: {
        user(new_user) {
            this.edit = pick(new_user, "name", "email", "is_admin")
            this.edit.teams = {}
            this.display_teams = [...new_user.teams]
        }
    },
    methods: {
        async remove_team(team) {
            if (this.edit.teams[team.id] == undefined) {
                this.edit.teams[team.id] = false
            } else {
                delete this.edit.teams[team.id]
            }
            const index = this.teams.indexOf(team.id)
            this.teams.splice(index, 1)
        },
        async add_team() {
            const team = this.new_team
            if (this.teams.includes(team)) {
                return
            }
            if (this.edit.teams[team] == null) {
                this.edit.teams[team] = true
            } else {
                delete this.edit.teams[team]
            }
            this.teams.push(team)
            this.new_team = null
        },
        async delete_user(event) {
            var response = await send_request(`user/${this.user.id}/delete`)
            if (response) {
                delete store.users[this.user.id]
            }
        },
        async submit_edit() {
            var response = await send_request(`user/${this.user.id}/edit`, this.edit)
            if (response) {
                Object.assign(store.users[this.user.id], response)
                /* Doesnt actually work, but we need to do something like this
                var modalEl = document.querySelector("#editModal")
                var modal = bootstrap.Modal.getInstance(modalEl)
                modal.toggle()*/
            }
        },
    },
    computed: {
        new_teams() {
            return Object.entries(store.teams).filter(data => !this.display_teams.includes(data[0]))
        },
    },
})


app.mount("#app")
