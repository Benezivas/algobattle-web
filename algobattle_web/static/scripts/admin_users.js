import { createApp } from "vue"


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
        this.users.push(response)
        fields.name.value = ""
        fields.email.value = ""
        fields.is_admin.checked = false
    }
}


async function edit_user(event) {
    var fields = event.currentTarget.elements
    var user = this.curr_row.user

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
        this.curr_row.editing = false
    }
}


async function delete_user(event) {
    var user = this.curr_row.user

    var response = await send_request("delete", {
        id: user.id
    })
    if (response) {
        event.target.closest("tr").remove()
    }
}


const app = createApp({
    props: ["users"],
    data() {
        return {
            curr_row: {},
        }
    },
    methods: {
        create_user,
        edit_user,
        delete_user,
    },
}, {
    users: users,
})

app.component("TableRow", {
    template: "#table_row",
    props: ["user"],
    data() {
        return {
            editing: false,
        }
    },
    methods: {
        toggle_editing() {
            if (this.editing) {
                this.editing = false
                this.curr_row = {}
            } else {
                this.curr_row.editing = false
                this.curr_row = this
                this.editing = true
            }
        },
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]


app.mount("#app")
