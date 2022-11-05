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
            this.editing = !this.editing
        },
        async delete_problem() {
            var response = await send_request("problem/delete/" + this.problem.id)
            if (response) {
                delete store.problems[this.problem.id]
            }
        },
        async edit(event) {
            const payload = new FormData(event.currentTarget)
            payload.append("id", this.problem.id)
            var response = await send_form("problem/edit", payload)
            if (response) {
                response = await response.json()
                store.problems[response.id] = response
                this.toggle_editing()
            }
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
