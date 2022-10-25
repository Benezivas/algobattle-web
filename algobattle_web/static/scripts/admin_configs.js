import { createApp, reactive } from "vue"


const store = reactive({
    configs,
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

async function send_form(endpoint, content) {
    var response = await fetch("/api/" + endpoint, {
        "method": "POST",
        "body": content,
    })
    if (response.ok) {
        return response
    }
}

async function create_config(event) {
    var fields = event.currentTarget.elements

    const payload = new FormData(event.currentTarget)

    console.log([[...payload]])
    var response = await send_form("config/add", payload)
    if (response) {
        response = await response.json()
        store.configs[response.id] = response
        fields.name.value = ""
    }
}

async function edit_config(event) {
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


async function delete_config(event) {
    var config = store.curr_row.config

    var response = await send_request("config/delete/" + config.id)
    if (response) {
        console.log(store.configs)
        store.curr_row.editing = false
        store.curr_row = {}
        delete store.configs[config.id]
    }
}

async function download_config(event) {

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
        create_config,
        edit_config,
    },
    data() {
        return {
            store: store,
        }
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]

app.component("ConfigRow", {
    template: "#config_row",
    props: ["config"],
    data() {
        return {
            editing: false,
            store: store,
        }
    },
    methods: {
        toggle_editing,
        delete_config,
        download_config,
    }
})

app.mount("#app")


