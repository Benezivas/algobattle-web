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
    console.log([...payload])
    var response = await send_form("config/add", payload)
    if (response) {
        response = await response.json()
        store.configs[response.id] = response
        fields.name.value = ""
    }
}

async function edit_config(event) {
    const payload = new FormData(event.currentTarget)
    payload.append("id", store.curr_row.config.id)
    console.log([...payload])
    var response = await send_form("config/edit", payload)
    if (response) {
        response = await response.json()
        store.configs[response.id] = response
        store.curr_row.toggle_editing()
    }
}


async function delete_config(event) {
    var config = store.curr_row.config

    var response = await send_request("config/delete/" + config.id)
    if (response) {
        store.curr_row.editing = false
        store.curr_row = {}
        delete store.configs[config.id]
    }
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
    }
})

app.mount("#app")


