import { createApp, reactive } from "vue"
import { send_form, send_request, fmt_date, remove_unchanged } from "base"


const store = reactive({
})


const app = createApp({
    data() {
        return {
            store: store,
            form_index: 0,

            name: null,
            description: null,
            problem_schema: null,
            solution_schema: null,

            context: null,
            start: null,
            end: null,

            image: null,
            alt: null,
            short_description: null,

        }
    },
    methods:  {
        async send_file(event) {
            const form = new FormData(event.currentTarget)
            const reponse = await send_form("/api/problem/", form)
            if (response.ok) {
                this.form_index = 1
            }
            send_form(event)
        },
    },
    computed: {
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]




app.mount("#app")
