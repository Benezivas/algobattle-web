import { createApp, reactive } from "vue"


const store = reactive({
    problems: problems,
    configs: configs,
})



async function send_request(action, content) {
    var response = await fetch("/api/" + action, {
        "method": "POST",
        "headers": {"Content-type": "application/json"},
        "body": JSON.stringify(content),
    })
    if (response.ok) {
        return response.json()
    }
}

async function create_team(event) {
    var fields = event.currentTarget.elements

    var response = await send_request("team/create", {
        name: fields.name.value,
        context: fields.context.value,
    })
    if (response) {
        store.teams[response.id] = response
        fields.name.value = ""
    }
}

async function edit_team(event) {
    var fields = event.currentTarget.elements
    var team = store.curr_row.team

    var response = await send_request("team/edit", {
        id: team.id,
        name: fields.name.value ? fields.name.value : undefined,
        context: fields.context.value != team.context ? fields.context.value : undefined,
    })
    if (response) {
        team.name = response.name
        team.context = response.context
        store.curr_row.editing = false
    }
}


async function delete_team(event) {
    var team = store.curr_row.team

    var response = await send_request("team/delete", {
        id: team.id,
    })
    if (response) {
        store.curr_row.editing = false
        store.curr_row = {}
        delete store.teams[team.id]
    }
}


async function add_member(event) {
    var response = await send_request("team/add_member", {
        team: this.edit_team_member_team,
        user: this.edit_team_member_user,
    })
    if (response) {
        var [team, user] = response
        store.teams[team.id] = team
        store.users[user.id] = user
    }
}


async function remove_member(event) {
    var response = await send_request("team/remove_member", {
        team: this.edit_team_member_team,
        user: this.edit_team_member_user,
    })
    if (response) {
        var [team, user] = response
        store.teams[team.id] = team
        store.users[user.id] = user
    }
}


async function create_context(event) {
    var fields = event.currentTarget.elements

    var response = await send_request("context/create", {
        name: fields.name.value,
    })
    if (response) {
        store.contexts[response.id] = response
        fields.name.value = ""
    }

}

async function edit_context(event) {
    var fields = event.currentTarget.elements
    var context = store.curr_row.context

    var response = await send_request("context/edit", {
        id: context.id,
        name: fields.name.value,
    })
    if (response) {
        context.name = response.name
        store.curr_row.editing = false
        store.curr_row = {}
    }
}


async function delete_context(event) {
    var context = store.curr_row.context

    var response = await send_request("context/delete", {
        id: context.id,
    })
    if (response) {
        store.curr_row = {}
        delete store.contexts[context.id]
    }
}




const app = createApp({
    methods: {
        create_problem() {

        },
    },
    data() {
        return {
            store: store,
        }
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]

app.component("Problem", {
    template: "#problem",
    props: ["problem"],
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
        delete_problem() {

        },
    }
})

app.mount("#app")


