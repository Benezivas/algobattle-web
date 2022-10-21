import { createApp } from "https://unpkg.com/petite-vue@0.4.1/dist/petite-vue.es.js?module"


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


async function send_form(event) {
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

async function create_user(event) {
    var fields = event.currentTarget.elements

    var response = await send_request("create", {
        name: fields.name.value,
        email: fields.email.value,
        is_admin: fields.is_admin.checked,
    })
    if (response) {
        users.push(response)
        fields.name.value = ""
        fields.email.value = ""
        fields.is_admin.checked = false
    }
}


function TableRow(user) {
    return {
        $template: "#table_row",
        user: user,
        editing: false,
        toggle_editing() {
            if (this.editing) {
                this.editing = false
                this.curr_row = {}
            } else {
                this.curr_row.editing = false
                this.curr_row = this
                this.editing = true
            }
        }
    }
}


createApp({
    $delimiters: ["${", "}"],
    curr_row: {},
    send_form,
    delete_user,
    create_user,
    TableRow,
}).mount()
