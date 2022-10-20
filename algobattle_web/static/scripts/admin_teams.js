import { createApp } from "https://unpkg.com/petite-vue@0.4.1/dist/petite-vue.es.js?module"

async function send_request(action, content) {
    var response = await fetch("/admin/" + action, {
        "method": "POST",
        "headers": {"Content-type": "application/json"},
        "body": JSON.stringify(content),
    })
    if (response.ok) {
        return response.json()
    }
}


async function edit_team(event) {
    var fields = event.currentTarget.elements
    var team = this.curr_row.team

    var response = await send_request("teams/edit", {
        id: team.id,
        name: fields.name.value ? fields.name.value : undefined,
        context: fields.context.value != team.context.name ? fields.context.value : undefined,
    })
    if (response) {
        team.name = response.name
        team.context = response.context
        this.curr_row.editing = false
    }
}


async function delete_team(event) {
    var team = this.curr_row.team

    var response = await send_request("teams/delete", {
        id: team.id,
    })
    if (response) {
        event.target.closest("tr").remove()
    }
}


function TableRow(team) {
    return {
        $template: "#table_row",
        team: team,
        editing: false,
        toggle_editing() {
            this.editing = !this.editing
            if (this.editing) {
                this.curr_row.editing = false
                this.curr_row = this
            } else {
                this.curr_row = {}
            }
        },
    }
}

async function edit_context(event) {
    var fields = event.currentTarget.elements
    var context = this.curr_row.context

    var response = await send_request("teams/edit", {
        id: context.id,
        name: fields.name.value ? fields.name.value : undefined,
    })
    if (response) {
        context.name = response.name
        this.curr_row.editing = false
    }
}


async function delete_context(event) {
    var context = this.curr_row.context

    var response = await send_request("teams/delete", {
        id: context.id,
    })
    if (response) {
        event.target.closest("tr").remove()
    }
}


function ContextRow(context) {
    return {
        $template: "#context_row",
        context: context,
        editing: false,
        toggle_editing() {
            this.editing = !this.editing
            if (this.editing) {
                this.curr_row.editing = false
                this.curr_row = this
            } else {
                this.curr_row = {}
            }
        },
    }
}

createApp({
    $delimiters: ["${", "}"],
    curr_row: {},
    edit_team,
    delete_team,
    TableRow,
    edit_context,
    delete_context,
    ContextRow,
}).mount()
