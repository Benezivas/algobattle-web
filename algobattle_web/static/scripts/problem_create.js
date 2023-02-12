import { createApp, reactive } from "vue"
import { send_form, send_request, fmt_date, remove_unchanged } from "base"


const store = reactive({
})


const app = createApp({
    data() {
        return {
            store: store,
            form_index: 0,
            error: null,

            name: null,
            problem_schema: null,
            solution_schema: null,
        }
    },
    methods:  {
        async send_file(event) {
            const form = new FormData(event.currentTarget)
            if (form.get("file").size == 0) {
                if (form.get("problem_id") == null) {
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
                this.form_index = 1
            } else {
                this.error = "file"
            }
        },
    },
    computed: {
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]




app.mount("#app")
