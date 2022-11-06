import { createApp, reactive } from "vue"
import { send_request } from "base"

const store = reactive({
    user: user,
})

const app = createApp({
    methods: {
        async edit_data(event) {
            var response = await send_request("user/edit_self", {
                name: this.store.user.name,
                email: this.store.user.email,
            })
            if (response) {
                store.user = response
                this.toggle_editing()
            }
        },
        toggle_editing() {
            this.editing = !this.editing
        }
    },
    data() {
        return {
            store: store,
            editing: false,
        }
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]





app.mount("#app")
