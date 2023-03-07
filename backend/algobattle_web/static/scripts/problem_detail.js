import { createApp, reactive } from "vue"
import { send_request, send_get, send_form, fmt_date } from "base"


const store = reactive({
    problem: problem,
    contexts: contexts,
    doc_file: null,
    docs: {},
    teams: {},
})


function create_edit(problem) {
    const edit = {...problem}
    for (const name of ["file", "config", "description", "image"]) {
        edit[name] = {
            location: problem[name] ? problem[name].location : null,
        }
    }
    return edit
}


async function get_desc(data) {
    const response = await send_get(`problem/${data.problem.id}/description_content`)
    if (response.ok) {
        data.description = await response.json()
    } else {
        data.description = "__ERROR__"
    }
}

async function get_doc_files(page) {
    var query = ""
    if (page) {
        query = `?page={page}`
    }
    const response = send_request("documentation" + query, {problem: store.problem.id})
    if (response.ok) {
        store.docs = await response.json()
        const team_ids = Object.values(store.docs).map(o => o.id)
        const response = await send_request("teams", team_ids)
        if (response.ok) {
            store.teams = await response.json()
        }
    }
}


const app = createApp({
    data() {
        return {
            store: store,
            problem: store.problem,
            edit_data: create_edit(problem),
            modal: null,
            description: null,
            docs: null,
            doc_modal: null,
        }
    },
    methods: {
        fmt_date: fmt_date,
        open_modal() {
            this.modal = bootstrap.Modal.getOrCreateInstance("#editModal")
            this.edit_data = create_edit(this.problem)
            this.modal.toggle()
        },
        open_doc_modal() {
            this.doc_modal = bootstrap.Modal.getOrCreateInstance("#docModal")
            this.doc_modal.toggle()
        },
        new_problem(data) {
            this.problem = data
            this.edit_data = create_edit(data)
        },
    },
    async created() {
        await get_desc(this)
        await get_doc_files(0)
    },
    watch: {
        problem: get_desc,
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]

app.component("editWindow", {
    template: "#editWindow",
    props: ["problem", "modal"],
    data() {
        return {
            store: store,
            error: null,
            confirm_delete: false,
        }
    },
    methods: {
        async delete_problem(event) {
            if (!this.confirm_delete) {
                this.confirm_delete = true
                return
            }
            var response = await send_request(`problem/${this.problem.id}/delete`)
            if (response.ok) {
                delete store.users[this.user.id]
                this.modal.toggle()
                window.location.href = "/problems"
            }
        },
        async submit_edit(event) {
            const form = new FormData(event.target)
            for (const name of ["file", "config", "description", "image"]) {
                if (this.problem[name].edit === undefined) {
                    form.delete(name)
                } else {
                    form.set(name, this.problem[name].edit)
                }
            }
            var response = await send_form(`problem/${this.problem.id}/edit`, form)
            if (response.ok) {
                this.$emit("new_problem", await response.json())
                this.modal.toggle()
                return
            }
            if (response.status == 409) {
                const error = await response.json()
                if (error.type == "value_taken") {
                    this.error = "name"
                    return
                }
            }
            this.error = "other"
        },
        async check_name() {
            const context = store.contexts[this.context]
            if (context == null) {
                return
            }
            const response = await send_get(`problem/${context.name}/${this.name}`)
            if (response.ok) {
                const existing = await response.json()
                if (existing.id != this.problem.id) {
                    this.error = "name"
                }
            } else {
                this.error = null
            }
        },
    },
})


app.component("FileEdit", {
    template: "#fileEdit",
    props: ["file", "nullable"],
    data() {
        return {
        }
    },
    watch: {
        file(data, old) {
            this.$refs.file_select.value = null
        }
    },
    methods: {
        select_file(event) {
            const files = event.target.files || event.dataTransfer.files
            if (files.length == 0) {
                return
            }
            this.file.edit = files[0]
            this.file.location = URL.createObjectURL(files[0])
        },
        remove_file() {
            this.file.edit = null
            this.file.location = null
            this.$refs.file_select.value = null
        },
    },
    computed: {
    },
})


app.component("editDoc", {
    template: "#editDoc",
    props: ["problem", "modal"],
    data() {
        return {
            store: store,
            file: null,
            confirm_delete: false,
        }
    },
    methods: {
        select_file(event) {
            const files = event.target.files || event.dataTransfer.files
            if (files.length == 0) {
                return
            }
            this.file = files[0]
        },
        async upload_doc() {
            const form = new FormData()
            if (this.file == 0) {
                return
            }
            form.set("file", this.file)
            const response = await send_form(`documentation/${this.problem.id}`, form)
            if (response.ok) {
                store.doc_file = (await response.json()).file
                this.$refs.doc_file_select.value = null
                this.modal.toggle()
            }
        },
        async remove_doc() {
            if (!this.confirm_delete) {
                this.confirm_delete = true
                return
            }
            const response = await send_request(`documentation/${this.problem.id}/delete`)
            if (response.ok) {
                store.doc_file = null
                this.$refs.doc_file_select.value = null
                this.confirm_delete = false
                this.modal.toggle()
            }
        },
    },
})


app.mount("#app")