import { createApp, reactive } from "vue"

const store = reactive({
    curr_row: {},
    users: users_input,
    teams: teams_input,
})

async function send_request(action, content) {
    var response = await fetch("/api/user/" + action, {
        "method": "POST",
        "headers": {"Content-type": "application/json"},
        "body": JSON.stringify(content),
    })
    if (response.ok) {
        return response.json()
    }
}


async function create_user(event) {
    var fields = event.currentTarget.elements

    var response = await send_request("create", {
        name: fields.name.value,
        email: fields.email.value,
        is_admin: fields.is_admin.checked,
    })
    if (response) {
        store.users.push(response)
        fields.name.value = ""
        fields.email.value = ""
        fields.is_admin.checked = false
    }
}


async function edit_user(event) {
    var fields = event.currentTarget.elements
    var user = store.curr_row.user

    var response = await send_request("edit", {
        id: user.id,
        name: fields.name.value ? fields.name.value : undefined,
        email: fields.email.value ? fields.email.value : undefined,
        is_admin: fields.is_admin.checked,
    })
    if (response) {
        user.name = response.name
        user.email = response.email
        user.is_admin = response.is_admin
        curr_row.editing = false
    }
}


async function delete_user(event) {
    var user = store.curr_row.user

    var response = await send_request("delete", {
        id: user.id
    })
    if (response) {
        store.curr_row = {}
        delete store.users[user.id]
    }
}


const app = createApp({
    data() {
        return {
            store: store,
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
