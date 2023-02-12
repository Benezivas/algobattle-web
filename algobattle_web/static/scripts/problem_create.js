import { createApp, reactive } from "vue"
import { send_form, send_request, fmt_date, remove_unchanged } from "base"


const store = reactive({
    problems: problems,
})


const app = createApp({
    data() {
        return {
            store: store,
            page: 0,
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
                console.log(form.get("problem_id"))
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
            } else {
                this.error = "file"
            }
        },
        async send_all(event) {
            if (this.page != 3) {
                return
            }
        }
    },
    computed: {
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]




app.mount("#app")
