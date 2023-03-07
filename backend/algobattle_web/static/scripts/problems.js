import { createApp, reactive } from "vue"
import { send_form, send_request, fmt_date, remove_unchanged } from "base"

function parse(problem) {
    if (problem.start != null) {
        problem.start = new Date(problem.start)
    }
    if (problem.end != null) {
        problem.end = new Date(problem.end)
    }
    return problem
}
for (const problem of Object.values(problems)) {
    parse(problem)
}
function in_context(problem) {
    if (store.selected_context == null) {
        return true
    } else {
        return problem.context == store.selected_context
    }
}
const now = new Date()

const store = reactive({
    problems: problems,
    contexts: contexts,
    selected_context: selected_context,
})


const app = createApp({
    data() {
        return {
            store: store,
        }
    },
    computed: {
        future_problems() {
            return Object.fromEntries(Object.entries(store.problems)
                .filter(([id, problem]) => 
                    in_context(problem)
                    && problem.start != null
                    && problem.start > now
                ))
        },
        current_problems() {
            return Object.fromEntries(Object.entries(store.problems)
                .filter(([id, problem]) =>
                    in_context(problem)
                    && (problem.start == null || problem.start <= now)
                    && (problem.end == null || problem.end > now)
                ))
        },
        past_problems() {
            return Object.fromEntries(Object.entries(store.problems)
                .filter(([id, problem]) =>
                    in_context(problem)
                    && problem.end != null
                    && problem.end < now
                ))
        },
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]


app.component("Problem", {
    template: "#problem",
    props: ["problem"],
    data() {
        return {
            store: store,
        }
    },
    methods: {
    },
    computed: {
        problem_url() {
            const context = encodeURIComponent(store.contexts[this.problem.context].name)
            const name = encodeURIComponent(this.problem.name)
            return `/problems/${context}/${name}`
        },
    },
})


app.mount("#app")