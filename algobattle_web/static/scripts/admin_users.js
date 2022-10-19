import { createApp } from "https://unpkg.com/petite-vue@0.4.1/dist/petite-vue.es.js?module"


async function send_request(action, content) {
    var response = await fetch("/admin/users/" + action, {
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
        
    }
}


function TableRow(user) {
    return {
        $template: "#table_row",
        user: user,
        editing: false,
        toggle_editing() {
            this.editing = !this.editing
            if (this.editing) {
                this.curr_row.editing = false
                this.curr_row = this
            } else {
                this.curr_row = {}
            }
        }
    }
}


createApp({
    $delimiters: ["${", "}"],
    curr_row: {},
    send_form,
    delete_user,
    TableRow,
}).mount()
