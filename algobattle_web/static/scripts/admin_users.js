import { createApp, reactive } from "https://unpkg.com/petite-vue@0.4.1/dist/petite-vue.es.js?module"



async function send_request(content) {
    var response = await fetch("/admin/users/edit", {
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

    var response = await send_request({
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

    console.log("user: ", this.curr_row.user.id)
    console.log("name: ", fields.name.value)
    console.log("email: ", fields.email.value)
    console.log("is_admin: ", fields.is_admin.checked)
    console.log("old name: ", this.curr_row.user.name)
}



function TableRow(user) {
    return {
        $template: "#table_row",
        user: user,
        editing: false,
        toggle_editing() {
            this.editing = !this.editing
            if (this.editing) {
                this.curr_row = this
                // make all other rows not editing
            }
        }
    }
}


createApp({
    $delimiters: ["${", "}"],
    curr_row: {},
    send_form,
    TableRow,
}).mount()

