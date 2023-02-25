import { createApp, reactive } from "vue"
import { send_form, send_get } from "base"


const store = reactive({
    problems: problems,
    contexts: contexts,
})


const app = createApp({
    data() {
        return {
            store: store,
            page: 0,
            error: null,

            name: null,
            context: null,

            problem_schema: null,
            solution_schema: null,

            img_file: null,
            img_alt: "",
            short_desc: null,
            color: "#000000",

            file_form: null,
            docs_form: null,
            settings_form: null,
        }
    },
    methods:  {
        async send_file(event) {
            const form = new FormData(event.currentTarget)
            this.file_form = new FormData(event.currentTarget)
            if (form.get("file").size == 0) {
                if (form.get("problem_id") == "") {
                    this.error = "missing"
                    return
                }
                form.delete("file")
            } else {
                if (form.get("problem_id") != null) {
                    this.error = "duplicate"
                    return
                }
            }
            const response = await send_form("problem/verify", form)
            if (response.ok) {
                const data = await response.json()
                this.name = data.name
                this.problem_schema = data.problem_schema
                this.solution_schema = data.solution_schema
                this.error = null
                this.page = 1
                this.check_name()
            } else {
                this.error = "file"
            }
        },
        next(key) {
            if (this.error != null) {
                return
            }
            this[key] = new FormData(this.$refs[key])
            this.page++
        },
        async check_name() {
            const context = store.contexts[this.context]
            if (context == null) {
                return
            }
            const response = await send_get(`problem/${context.name}/${this.name}`)
            if (response.ok) {
                this.error = "name"
            } else {
                this.error = null
            }
        },
        file_change(event) {
            const files = event.target.files || event.dataTransfer.files
            if (!files.length) {
                return
            }
            this.img_file = files[0]
        },
        async send_all(event) {
            if (this.page != 3) {
                return
            }
            const data = this.file_form
            for (const [key, val] of this.docs_form) {
                data.set(key, val)
            }
            for (const [key, val] of this.settings_form) {
                data.set(key, val)
            }
            for (const [key, val] of new FormData(event.currentTarget)) {
                data.set(key, val)
            }
            const file_keys = ["file", "description", "config", "image"]
            for (const key of file_keys) {
                if (!data.get(key)) {
                    data.delete(key)
                }
            }
            const response = await send_form("problem/create", data)
            if (response.ok) {
                window.location.href = await response.text()
            } else {
                this.error = "server"
            }
        }
    },
    computed: {
        img_url() {
            return URL.createObjectURL(this.img_file)
        }
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]


app.mount("#app")
