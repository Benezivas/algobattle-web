import { createApp, reactive } from "vue"
import { send_request, send_get, pick, queryParams, omit } from "base"

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
            has_params: Object.keys(omit(params, "page", "limit")).length != 0,
            filter: {
                name: params.name || "",
                email: params.email || "",
                is_admin: params.is_admin != null ? params.is_admin : null,
                context: params.context || null,
                team: params.team || null,
                limit: params.limit || 25,
            },
            modal_user: {
                teams: [],
            },
            action: "edit",
            modal: null,
        }
    },
    methods: {
        open_modal(action, user) {
            this.action = action
            if (action == "create") {
                this.modal_user = {
                    teams: [],
                }
            } else {
                this.modal_user = user
            }
            this.modal = bootstrap.Modal.getOrCreateInstance("#userModal")
            this.modal.toggle()
        },
        apply_filters(page) {
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
            if (this.filter.limit != "") {
                filters.push(`limit=${this.filter.limit}`)
            }
            return `/admin/users?${filters.join("&")}`
        },
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]

app.component("HoverBadge", {
    template: "#hoverBadge",
    props: ["data"],
    data() {
        return {
            hover: false,
        }
    },
})

app.component("UserWindow", {
    template: "#userWindow",
    props: ["user", "action", "modal"],
    data() {
        return {
            store: store,
            data: {
                name: this.user.name,
                email: this.user.email,
                is_admin: this.user.is_admin,
                teams: {},
            },
            display_teams: [...this.user.teams],
            search: {
                name: "",
                context: null,
                result: [],
            },
        }
    },
    watch: {
        user(new_user) {
            this.data = pick(new_user, "name", "email", "is_admin")
            this.data.teams = {}
            this.display_teams = [...new_user.teams]
        }
    },
    methods: {
        async remove_team(team) {
            if (this.data.teams[team.id] == undefined) {
                this.data.teams[team.id] = false
            } else {
                delete this.data.teams[team.id]
            }
            const index = this.display_teams.indexOf(team.id)
            this.display_teams.splice(index, 1)
        },
        async add_team(team) {
            if (this.display_teams.includes(team.id)) {
                return
            }
            if (this.data.teams[team.id] == null) {
                this.data.teams[team.id] = true
            } else {
                delete this.data.teams[team.id]
            }
            this.display_teams.push(team.id)
            store.teams[team.id] = team
        },
        async delete_user(event) {
            var response = await send_request(`user/${this.user.id}/delete`)
            if (response) {
                delete store.users[this.user.id]
                this.modal.toggle()
            }
        },
        async submit_data() {
            if (this.action == "edit") {
                var response = await send_request(`user/${this.user.id}/edit`, this.data)
                if (response) {
                    Object.assign(store.users[this.user.id], response)
                    this.modal.toggle()
                }
            } else {
                const processed = omit(this.data, "teams")
                processed.teams = Object.keys(this.data.teams)
                var response = await send_request("user/create", processed)
                if (response) {
                    store.users[response.id] = response
                    this.modal.toggle()
                }
            }
        },
        async send_search() {
            const filter = {limit: 5}
            if (this.search.name != "") {
                filter.name = this.search.name
            }
            if (this.search.context != "") {
                filter.context = this.search.context
            }
            const response = await send_get("team/search", filter)
            if (response) {
                this.search.result = response
            }
        },
    },
})


app.mount("#app")
