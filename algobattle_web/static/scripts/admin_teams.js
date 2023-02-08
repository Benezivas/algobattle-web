import { createApp, reactive } from "vue"
import { send_request, send_get, pick, queryParams, omit } from "base"


const store = reactive({
    teams: teams_input,
    users: users_input,
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
                context: params.context || null,
                limit: params.limit || 25,
            },
            modal_team: {
                members: [],
            },
            action: "edit",
            modal: null,
        }
    },
    methods: {
        open_modal(action, team) {
            this.action = action
            if (action == "create") {
                this.modal_team = {
                    members: [],
                }
            } else {
                this.modal_team = team
            }
            this.modal = bootstrap.Modal.getOrCreateInstance("#teamModal")
            this.modal.toggle()
        },
        apply_filters(page) {
            var filters = []
            if (this.filter.name != "") {
                filters.push(`name=${this.filter.name}`)
            }
            if (this.filter.context != null) {
                filters.push(`context=${this.filter.context}`)
            }
            if (this.filter.limit != "") {
                filters.push(`limit=${this.filter.limit}`)
            }
            if (page != 1) {
                filters.push(`page=${page}`)
            }
            return `/admin/teams?${filters.join("&")}`
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


app.component("TeamWindow", {
    template: "#teamWindow",
    props: ["team", "action", "modal"],
    data() {
        return {
            store: store,
            data: {
                members: {},
            },
            display_members: [],
            search: {
                name: "",
                email: "",
                result: [],
            },
            error: null,
        }
    },
    watch: {
        team(team) {
            this.data = pick(team, "name", "email", "is_admin")
            this.data.members = {}
            this.display_members = [...team.members]
            this.error = null
        }
    },
    methods: {
        async remove_user(user) {
            if (this.data.members[user.id] == undefined) {
                this.data.members[user.id] = false
            } else {
                delete this.data.members[user.id]
            }
            const index = this.display_members.indexOf(user.id)
            this.display_members.splice(index, 1)
        },
        async add_user(user) {
            if (this.display_members.includes(user.id)) {
                return
            }
            if (this.data.members[user.id] == null) {
                this.data.members[user.id] = true
            } else {
                delete this.data.members[user.id]
            }
            this.display_members.push(user.id)
            store.users[user.id] = user
            this.search.name = ""
            this.search.email = ""
            this.search.result = []
        },
        async delete_team(event) {
            var response = await send_request(`team/${this.team.id}/delete`)
            if (response.ok) {
                delete store.teams[this.team.id]
                this.modal.toggle()
            }
        },
        async submit_data() {
            if (this.action == "edit") {
                var response = await send_request(`team/${this.team.id}/edit`, this.data)
                if (response.ok) {
                    Object.assign(store.teams[this.team.id], response)
                    this.modal.toggle()
                    return
                }
            } else {
                const processed = omit(this.data, "members")
                processed.members = Object.keys(this.data.members)
                var response = await send_request("team/create", processed)
                if (response.ok) {
                    store.teams[response.id] = response
                    this.modal.toggle()
                    return
                }
            }
            if (response.status == 409) {
                const error = await response.json()
                if (error.type == "value_taken") {
                    this.error = "name"
                    return
                }
            }
            this.error = "other"
        },
        async send_search() {
            const filter = {limit: 5}
            if (this.search.name != "") {
                filter.name = this.search.name
            }
            if (this.search.email != "") {
                filter.email = this.search.email
            }
            const response = await send_get("user/search", filter)
            if (response.ok) {
                this.search.result = await response.json()
            }
        },
    },
})


app.mount("#app")


