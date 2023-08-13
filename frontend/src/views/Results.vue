<script setup lang="ts">
import { store, type ModelDict, formatDateTime } from "@/main";
import {
  MatchService,
  TournamentService,
  ProblemService,
  MatchStatus,
  ProgramService,
  Role,
  TeamService,
} from "@client";
import { Modal } from "bootstrap";
import type { Problem, Tournament, MatchResult, Team, DbFile, ResultParticipant, Program } from "@client";
import { onMounted, ref, toRaw } from "vue";
import DownloadButtonVue from "@/components/DownloadButton.vue";

const problems = ref<ModelDict<Problem>>({});
const results = ref<ModelDict<MatchResult>>({});
const teams = ref<ModelDict<Team>>({});
const programs = ref<{ [key: string]: Program[] }>({});

let editModal: Modal;
onMounted(async () => {
  const res = await MatchService.results();
  problems.value = res.problems;
  results.value = res.results;
  teams.value = res.teams;
  if (store.user.is_admin) {
    const res = await TeamService.searchTeam({ tournament: store.user.current_tournament?.id });
    // TODO: get all teams not just first page
    teams.value = res.teams;
  }
  editModal = Modal.getOrCreateInstance("#editModal");
  if (store.user.is_admin) {
    problems.value = await ProblemService.allProblems({
      tournament: store.user.current_tournament?.id,
    });
  }
});

interface EditData {
  id?: string;
  status: MatchStatus;
  time?: string;
  problem?: string;
  logs?: DbFile | null;
  participants: Partial<ResultParticipant>[];
  confirmDelete: boolean;
}

const editData = ref<EditData>({
  status: MatchStatus.COMPLETE,
  participants: [],
  confirmDelete: false,
});

function openEdit(match: MatchResult | undefined) {
  editData.value = match
    ? { ...structuredClone(toRaw(match)), confirmDelete: false }
    : {
        status: MatchStatus.COMPLETE,
        problem: undefined,
        participants: [],
        confirmDelete: false,
      };
  editModal.show();
}

async function sendData() {}

async function deleteResult() {}

function getPrograms(team: string, role: Role) {
  if (!editData.value.problem || programs.value[editData.value.problem + team + role]) {
    return;
  }
  programs.value[editData.value.problem + team + role] = [];
  ProgramService.searchProgram({
    team: team,
    role: role,
    problem: editData.value.problem,
  }).then((response) => {
    programs.value[editData.value.problem + team + role] = Object.values(response.programs);
  });
}

function getAllPrograms() {
  for (const participant of editData.value.participants) {
    if (participant.team_id) {
      getPrograms(participant.team_id, Role.GENERATOR);
      getPrograms(participant.team_id, Role.SOLVER);
    }
  }
}
</script>

<template>
  <table class="table">
    <thead>
      <tr>
        <th scope="col">Time</th>
        <th scope="col">Problem</th>
        <th scope="col">Status</th>
        <th scope="col">Details</th>
        <th v-if="store.user.is_admin" scope="col"></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(result, id) in results" :result="result" :key="id">
        <td>{{ result.time }}</td>
        <td>
          <RouterLink :to="problems[result.problem].link">{{ problems[result.problem].name }}</RouterLink>
        </td>
        <td>{{ result.status }}</td>
        <td>Details</td>
        <td v-if="store.user.is_admin" class="text-end">
          <button type="button" class="btn btn-sm btn-warning" title="Edit" @click="(e) => openEdit(result)">
            <i class="bi bi-pencil"></i>
          </button>
        </td>
      </tr>
    </tbody>
  </table>
  <button type="button" class="btn btn-primary btn-sm me-auto" @click="(e) => openEdit(undefined)">
    Add new result
  </button>

  <div class="modal fade" id="editModal" tabindex="-1" aria-labelledby="modalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-xl">
      <form class="modal-content" @submit.prevent="sendData">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="modalLabel">
            <span v-if="editData.id">Edit result</span>
            <span v-else>Add new result</span>
          </h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" />
        </div>
        <div class="modal-body">
          <label for="time" class="form-label">Time</label>
          <input id="time" class="form-control" type="datetime-local" required v-model="editData.time" />
          <label for="problem" class="form-label">Problem</label>
          <select
            id="problem"
            class="form-select"
            required
            v-model="editData.problem"
            @click="getAllPrograms"
          >
            <option v-for="(problem, id) in problems" :value="id">{{ problem.name }}</option>
          </select>
          <label for="status" class="form-label">Status</label>
          <select id="status" class="form-select" required v-model="editData.status">
            <option v-for="status in Object.values(MatchStatus)" :value="status">
              {{ status }}
            </option>
          </select>
          <table class="table">
            <thead>
              <tr>
                <th scope="col">Team</th>
                <th scope="col">Generator</th>
                <th scope="col">Solver</th>
                <th scope="col">Points</th>
                <th scope="col"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="participant in editData.participants">
                <td>
                  <select
                    :id="participant.team_id + 'team'"
                    class="form-select"
                    required
                    v-model="participant.team_id"
                  >
                    <option v-for="(team, id) in teams" :value="id">
                      {{ team.name }}
                    </option>
                  </select>
                </td>
                <td>
                  <select
                    v-if="participant.team_id && editData.problem"
                    :id="participant.team_id + 'gen'"
                    class="form-select"
                    required
                    v-model="participant.generator"
                    @click="getPrograms(participant.team_id, Role.GENERATOR)"
                  >
                    <option
                      v-for="prog in programs[editData.problem + participant.team_id + Role.GENERATOR]"
                      :value="prog"
                    >
                      {{ `${prog.name}(${formatDateTime(prog.creation_time)})` }}
                    </option>
                  </select>
                </td>
                <td>
                  <select
                    v-if="participant.team_id && editData.problem"
                    :id="participant.team_id + 'gen'"
                    class="form-select"
                    required
                    v-model="participant.solver"
                    @click="getPrograms(participant.team_id, Role.SOLVER)"
                  >
                    <option
                      v-for="prog in programs[editData.problem + participant.team_id + Role.SOLVER]"
                      :value="prog"
                    >
                      {{ `${prog.name}(${formatDateTime(prog.creation_time)})` }}
                    </option>
                  </select>
                </td>
                <td>
                  <template v-if="participant.team_id">
                    <input class="form-control" type="number" v-model="participant.points" required />
                  </template>
                </td>
                <td>
                  <button
                    type="button"
                    class="btn btn-danger btn-sm"
                    title="Remove"
                    @click="editData.participants.splice(editData.participants.indexOf(participant), 1)"
                  >
                    <i class="bi bi-x"></i>
                  </button>
                </td>
              </tr>
              <tr>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td>
                  <button
                    type="button"
                    class="btn btn-sm btn-success"
                    @click="editData.participants.push({})"
                  >
                    <i class="bi bi-plus-square-dotted"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="modal-footer">
          <button
            v-if="editData.confirmDelete"
            type="button"
            class="btn btn-secondary"
            @click="(e) => (editData.confirmDelete = false)"
          >
            Cancel
          </button>
          <button v-if="editData.id" type="button" class="btn btn-danger ms-2" @click="deleteResult">
            {{ editData.confirmDelete ? "Confirm deletion" : "Delete result" }}
          </button>
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">{{ editData.id ? "Save" : "Add" }}</button>
        </div>
      </form>
    </div>
  </div>
</template>
