import { createApp, reactive } from "vue"


const store = reactive({
    teams: teams_input,
    contexts: contexts_input,
    users: users_input,
    curr_row: {},
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
        store.curr_row = {}
        this.$emit("delteam", team)
    }
}


function del_team_event(team) {
    store.teams[team.id] = undefined
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
        this.$emit("delcontext", context)
    }
}

function del_context_event(context) {
    store.contexts[context.id] = undefined
}

function toggle_editing() {
    if (this.editing) {
        this.editing = false
        store.curr_row = {}
    } else {
        store.curr_row.editing = false
        store.curr_row = this
        this.editing = true
    }
}


const app = createApp({
    methods: {
        create_team,
        edit_team,
        del_team_event,
        add_member,
        remove_member,
        create_context,
        edit_context,
        del_context_event,
    },
    data() {
        return {
            edit_team_member_team: "",
            edit_team_member_user: "",
            store: store,
        }
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]

app.component("TeamRow", {
    template: "#team_row",
    props: ["team"],
    data() {
        return {
            editing: false,
            store: store,
        }
    },
    computed: {
        members_stra() {
            return this.team.members.map(u => u.name).join(", ")
        },
    },
    methods: {
        toggle_editing,
        delete_team,
        members_str() {
            return this.team.members.map(u => store.users[u].name).join(", ")
        },
    }
})

app.component("ContextRow", {
    template: "#context_row",
    props: ["context"],
    data() {
        return {
            editing: false,
            store: store,
        }
    },
    methods: {
        toggle_editing,
        delete_context,
    }
})

app.mount("#app")


