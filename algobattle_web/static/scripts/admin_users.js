import { createApp } from "vue"

var curr_row = {}

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
        this.$forceUpdate()
        fields.name.value = ""
        fields.email.value = ""
        fields.is_admin.checked = false
    }
}


async function edit_user(event) {
    var fields = event.currentTarget.elements
    var user = curr_row.user

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
    var user = curr_row.user

    var response = await send_request("delete", {
        id: user.id
    })
    if (response) {
        this.$emit("deluser", user)
    }
}

async function del_event(user)  {
    var i = this.users.indexOf(user)
    this.users.splice(i, 1)
    this.$forceUpdate()
}



const app = createApp({
    props: ["users"],
    methods: {
        create_user,
        edit_user,
        del_event,
    },
}, {
    users: users_input,
})
app.config.compilerOptions.delimiters = ["${", "}"]

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
                curr_row = {}
            } else {
                curr_row.editing = false
                curr_row = this
                this.editing = true
            }
        },
        delete_user,
    },
})


app.mount("#app")
