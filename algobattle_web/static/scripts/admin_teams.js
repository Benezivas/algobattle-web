import { createApp } from "vue"

var curr_row = {}

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
        this.teams[response.id] = response
        this.$forceUpdate()
        fields.name.value = ""
    }
}

async function edit_team(event) {
    var fields = event.currentTarget.elements
    var team = curr_row.team

    var response = await send_request("team/edit", {
        id: team.id,
        name: fields.name.value ? fields.name.value : undefined,
        context: fields.context.value != team.context ? fields.context.value : undefined,
    })
    if (response) {
        team.name = response.name
        team.context = response.context
        curr_row.editing = false
    }
}


async function delete_team(event) {
    var team = curr_row.team

    var response = await send_request("team/delete", {
        id: team.id,
    })
    if (response) {
        curr_row = {}
        this.$emit("delteam", team)
    }
}


function del_team_event(team) {
    this.teams[team.id] = undefined
    this.$forceUpdate()
}


async function add_member(event) {
    var response = await send_request("team/add_member", {
        team: this.edit_team_member_team,
        user: this.edit_team_member_user,
    })
    if (response) {
        var [team, user] = response
        this.teams[team.id] = team
        this.users[user.id] = user
        this.$forceUpdate()
    }
}


async function remove_member(event) {
    var response = await send_request("team/remove_member", {
        team: this.edit_team_member_team,
        user: this.edit_team_member_user,
    })
    if (response) {
        var [team, user] = response
        this.teams[team.id] = team
        this.users[user.id] = user
        this.$forceUpdate()
    }
}


async function create_context(event) {
    var fields = event.currentTarget.elements

    var response = await send_request("context/create", {
        name: fields.name.value,
    })
    if (response) {
        this.contexts[response.id] = response
        this.$forceUpdate()
        fields.name.value = ""
    }

}

async function edit_context(event) {
    var fields = event.currentTarget.elements
    var context = curr_row.context

    var response = await send_request("context/edit", {
        id: context.id,
        name: fields.name.value,
    })
    if (response) {
        context.name = response.name
        curr_row.editing = false
        curr_row = {}
        this.$forceUpdate()
    }
}


async function delete_context(event) {
    var context = curr_row.context

    var response = await send_request("context/delete", {
        id: context.id,
    })
    if (response) {
        this.curr_row = {}
        this.$emit("delcontext", context)
    }
}

function del_context_event(context) {
    this.contexts[context.id] = undefined
    this.$forceUpdate()
}

function toggle_editing() {
    if (this.editing) {
        this.editing = false
        curr_row = {}
    } else {
        curr_row.editing = false
        curr_row = this
        this.editing = true
    }
}


const app = createApp({
    props: ["teams", "contexts", "users"],
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
        }
    },
}, {
    teams: teams_input,
    contexts: contexts_input,
    users: users_input
})
app.config.compilerOptions.delimiters = ["${", "}"]

app.component("TeamRow", {
    template: "#team_row",
    props: ["team"],
    data() {
        return {
            editing: false,
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
            return this.team.members.map(u => this.$parent.users[u].name).join(", ")
        },
    }
})

app.component("ContextRow", {
    template: "#context_row",
    props: ["context"],
    data() {
        return {
            editing: false,
        }
    },
    methods: {
        toggle_editing,
        delete_context,
    }
})

app.mount("#app")


