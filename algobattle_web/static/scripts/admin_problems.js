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


async function send_form(endpoint, content) {
    var response = await fetch("/api/" + endpoint, {
        "method": "POST",
        "body": content,
    })
    if (response.ok) {
        return response
    }
}


const app = createApp({
    methods: {
        async create_problem(event) {
            const payload = new FormData(event.currentTarget)
            if (payload.get("description").size == 0) {
                payload.delete("description")
            }
            var response = await send_form("problem/create", payload)
            if (response) {
                response = await response.json()
                store.problems[response.id] = response
            }
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
        delete() {

        },
        edit() {
            
        },
        fmt_date(date) {
            if (!date) {
                return ""
            }
            date = new Date(date)
            return date.toLocaleString()
        }
    }
})


app.mount("#app")
