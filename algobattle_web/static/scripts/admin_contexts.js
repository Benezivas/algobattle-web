import { createApp, reactive } from "vue"
import { send_request, send_get, pick, queryParams, omit } from "base"


const store = reactive({
    contexts: contexts_input,
})


const params = queryParams()
const app = createApp({
    data() {
        return {
            store: store,
            has_params: Object.keys(omit(params, "page", "limit")).length != 0,
            filter: {
                name: params.name || "",
                limit: params.limit || 25,
            },
            modal_context: {},
            action: "edit",
            modal: null,
        }
    },
    methods: {
        open_modal(action, context) {
            this.action = action
            if (action == "create") {
                this.modal_context = {}
            } else {
                this.modal_context = context
            }
            this.modal = bootstrap.Modal.getOrCreateInstance("#contextModal")
            this.modal.toggle()
        },
        apply_filters(page) {
            var filters = []
            if (this.filter.name != "") {
                filters.push(`name=${this.filter.name}`)
            }
            if (this.filter.limit != "") {
                filters.push(`limit=${this.filter.limit}`)
            }
            if (page != 1) {
                filters.push(`page=${page}`)
            }
            return `/admin/contexts?${filters.join("&")}`
        },
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]

app.component("ContextWindow", {
    template: "#contextWindow",
    props: ["context", "action", "modal"],
    data() {
        return {
            store: store,
            data: {},
            error: null,
        }
    },
    watch: {
        context(context) {
            this.data.name = context.name
            this.error = null
        }
    },
    methods: {
        async delete_context() {
            var response = await send_request(`context/${this.context.id}/delete`)
            if (response.ok) {
                delete store.contexts[this.context.id]
                this.modal.toggle()
            }
        },
        async submit_data() {
            if (this.action == "edit") {
                var response = await send_request(`context/${this.context.id}/edit`, this.data)
                if (response.ok) {
                    Object.assign(store.contexts[this.context.id], await response.json())
                    this.modal.toggle()
                    return
                }
            } else {
                var response = await send_request("context/create", this.data)
                if (response.ok) {
                    store.contexts[response.id] = await response.json()
                    this.modal.toggle()
                    return
                }
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
    },
})


app.mount("#app")


