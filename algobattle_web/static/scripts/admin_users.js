import { createApp, reactive } from "vue"
import { send_request } from "base"

const store = reactive({
    curr_row: {},
    users: users_input,
    teams: teams_input,
    contexts: contexts_input,
})


async function create_user(event) {
    var fields = event.currentTarget.elements

    var response = await send_request("user/create", {
        name: fields.name.value,
        email: fields.email.value,
        is_admin: fields.is_admin.checked,
    })
    if (response) {
        store.users[response.id] = response
        fields.name.value = ""
        fields.email.value = ""
        fields.is_admin.checked = false
    }
}


async function edit_user(event) {
    var user = store.curr_row.user

    var response = await send_request(`user/${user.id}/edit`, {
        name: user.name,
        email: user.email,
        is_admin: user.is_admin,
    })
    if (response) {
        user.name = response.name
        user.email = response.email
        user.is_admin = response.is_admin
        store.curr_row.toggle_editing()
    }
}


async function delete_user(event) {
    var user = store.curr_row.user

    var response = await send_request(`user/${user.id}/delete`)
    if (response) {
        store.curr_row = {}
        delete store.users[user.id]
    }
}


const app = createApp({
    data() {
        return {
            store: store,
            filter: {
                name: "",
                email: "",
                is_admin: null,
                context: "",
                team: "",
            },
        }
    },
    methods: {
        create_user,
        edit_user,
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
        delete_user,
    },
    computed: {
        teams_str() {
            return this.user.teams.map(t => store.teams[t].name).join(", ")
        }
    }
})


app.mount("#app")
