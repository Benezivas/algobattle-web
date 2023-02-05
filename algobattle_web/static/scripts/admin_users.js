import { createApp, reactive } from "vue"
import { send_request, pick, queryParams } from "base"
import "bootstrap"

const store = reactive({
    users: users_input,
    teams: teams_input,
    contexts: contexts_input,
    edit: {
        id: null,
        edit: {},
        teams: [],
        new_team: null,
    },
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
        async delete_user(event) {
            var response = await send_request(`user/${store.edit.id}/delete`)
            if (response) {
                delete store.users[this.user.id]
            }
        },
        async edit_user(data) {
            var response = await send_request(`user/${data.id}/edit`, data.edit)
            if (response) {
                Object.assign(store.users[data.id], response)
                /* Doesnt actually work, but we need to do something like this
                var modalEl = document.querySelector("#editModal")
                var modal = bootstrap.Modal.getInstance(modalEl)
                modal.toggle()*/
            }
        },
        async add_team() {
            const team = store.edit.new_team
            if (store.edit.teams.includes(team)) {
                return
            }
            if (store.edit.edit.teams[team] == null) {
                store.edit.edit.teams[team] = true
            } else {
                delete store.edit.edit.teams[team]
            }
            store.edit.teams.push(team)
            store.edit.new_team = null
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
    methods: {
        async open_edit(event) {
            store.edit.id = this.user.id
            store.edit.teams = [...this.user.teams]
            store.edit.edit = pick(this.user, "name", "email", "is_admin")
            store.edit.edit.teams = {}
        },
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
            store: store,
            hover: false,
        }
    },
    methods: {
        async remove() {
            if (store.edit.edit.teams[this.team.id] == null) {
                store.edit.edit.teams[this.team.id] = false
            } else {
                delete store.edit.edit.teams[this.team.id]
            }
            const index = store.edit.teams.indexOf(this.team.id)
            store.edit.teams.splice(index, 1)
        },
    },
})


app.mount("#app")
