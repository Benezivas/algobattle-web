import { createApp, reactive } from "vue"
import { send_request } from "base"

const store = reactive({
    user: user,
    teams: teams,
    settings: settings,
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
        },
        async submit_settings(event) {
            var response = await send_request("user/edit_settings", {
                selected_team: this.store.settings.selected_team,
            })
            if (response) {
                store.settings = settings
            }
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
