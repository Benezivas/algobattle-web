import { createApp, reactive } from "vue"
import { send_form, send_request, fmt_date } from "base"


const store = reactive({
    schedules: schedules,
    problems: problems,
    teams: teams,
    configs: configs,
    programs: programs,
})

function prog_spec(data) {
    if (data == "team_spec") {
        return {
            src: "team_spec",
            program: undefined,
        }
    } else {
        return {
            src: "program",
            program: data,
        }
    }
}


const app = createApp({
    data() {
        return {
            store: store,
            new_schedule: {
                participants: [],
            },
        }
    },
    methods: {
        async create(event) {
            var data = {}
            for (const element of ["name", "problem", "time", "config", "points"]) {
                data[element] = this.new_schedule[element]
            }
            data.participants = this.new_schedule.participants.map(p => {
                    return {
                        team: p.team,
                        generator: prog_spec(p.generator),
                        solver: prog_spec(p.solver),
                    }
                })
            var response = await send_request("schedule/create", data)
            if (response) {
                console.log(response)
                response = await response.json()
                store.schedule[response.id] = response
                this.editing = undefined
            }
        },
        add_participant() {
            this.new_schedule.participants.push({
                team: undefined,
                generator: "team_spec",
                solver: "team_spec",
            })
        }
    },
})
app.config.compilerOptions.delimiters = ["${", "}"]


app.component("Schedule", {
    template: "#schedule",
    props: ["schedule"],
    data() {
        return {
            editing: false,
            store: store,
        }
    },
    computed: {
        participants_str() {
            return this.schedule.participants.map(t => store.teams[t].name).join(", ")
        },
    },
    methods: {
        toggle_editing(team_id) {
            if (this.editing == team_id) {
                this.editing = false
            } else {
                this.editing = team_id
            }
        },
        async remove() {
            var response = await send_request("schedule/delete/" + this.schedule.id)
            if (response) {
                delete store.schedule[this.schedule.id]
                this.toggle_editing()
            }
        },
        async edit(event) {
            var response = await send_request("schedule/update", this.schedule)
            if (response) {
                response = await response.json()
                store.schedule[response.id] = response
                this.editing = undefined
            }
        },
        fmt_date,
    }
})


app.mount("#app")
