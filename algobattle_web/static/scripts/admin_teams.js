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
        this.teams.push(response)
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
        context: fields.context.value != team.context.name ? fields.context.value : undefined,
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
    var i = this.teams.indexOf(team)
    this.teams.splice(i, 1)
    this.$forceUpdate()
}


async function add_member(event) {
    var fields = event.currentTarget.elements

    var response = await send_request("team/add_member", {
        team: fields.team.value,
        user: fields.user.value,
    })
    if (response) {
        i = this.teams.find(t => t.id == response.id)
        this.teams[i] = response
        this.$forceUpdate()
        fields.name.value = ""
    }
}


async function create_context(event) {
    var fields = event.currentTarget.elements

    var response = await send_request("context/create", {
        name: fields.name.value,
    })
    if (response) {
        this.contexts.push(response)
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
    var i = this.contexts.indexOf(context)
    this.contexts.splice(i, 1)
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
        create_context,
        edit_context,
        del_context_event,
    }
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
        members_str() {
            return this.team.members.map(u => u.name).join(", ")
        }
    },
    methods: {
        toggle_editing,
        delete_team,
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


