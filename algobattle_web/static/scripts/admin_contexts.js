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
        }
    },
    watch: {
        context(context) {
            this.data.name = context.name
        }
    },
    methods: {
        async delete_context() {
            var response = await send_request(`context/${this.context.id}/delete`)
            if (response) {
                delete store.contexts[this.context.id]
                this.modal.toggle()
            }
        },
        async submit_data() {
            if (this.action == "edit") {
                var response = await send_request(`context/${this.context.id}/edit`, this.data)
                if (response) {
                    Object.assign(store.contexts[this.context.id], response)
                    this.modal.toggle()
                }
            } else {
                var response = await send_request("context/create", this.data)
                if (response) {
                    store.contexts[response.id] = response
                    this.modal.toggle()
                }
            }
        },
    },
})


app.mount("#app")

