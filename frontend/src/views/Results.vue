<script setup lang="ts">
import { store, type ModelDict, formatDateTime } from "@/shared";
import {
  MatchService,
  TournamentService,
  ProblemService,
  type MatchStatus,
  ProgramService,
  type Role,
  TeamService,
} from "@client";
import { Modal } from "bootstrap";
import type { Problem, Tournament, MatchResult, Team, DbFile, ResultParticipant, Program } from "@client";
import { computed, onMounted, ref, toRaw } from "vue";
import DownloadButton from "@/components/DownloadButton.vue";
import FileInput from "@/components/FileInput.vue";

const problems = ref<ModelDict<Problem>>({});
const results = ref<ModelDict<MatchResult>>({});
const teams = ref<ModelDict<Team>>({});
const programs = ref<{ [key: string]: Program[] }>({});
const sortedResults = computed(() => {
  const sorted = Object.values(results.value);
  sorted.sort((a, b) => {
    if (a.time < b.time) {
      return 1;
    } else if (a.time > b.time) {
      return -1;
    } else {
      return 0;
    }
  });
  return sorted;
});

let editModal: Modal;
let detailModal: Modal;
onMounted(async () => {
  const res = await MatchService.getResult({ tournament: store.tournament?.id });
  problems.value = res.problems;
  results.value = res.results;
  teams.value = res.teams;
  if (store.team == "admin") {
    const res = await TeamService.get({ tournament: store.tournament?.id });
    // TODO: get all teams not just first page
    teams.value = res.teams;
  }
  editModal = Modal.getOrCreateInstance("#editModal");
  if (store.team == "admin") {
    problems.value = await ProblemService.get({
      tournament: store.tournament?.id,
    });
  }
  detailModal = Modal.getOrCreateInstance("#detailModal");
});

interface EditData {
  id?: string;
  status: MatchStatus;
  time?: string;
  problem?: string;
  logs?: DbFile | null;
  participants: Partial<ResultParticipant>[];
  confirmDelete: boolean;
  newLogs?: File;
}

const editData = ref<EditData>({
  status: "complete",
  participants: [],
  confirmDelete: false,
});

function openEdit(match: MatchResult | undefined) {
  editData.value = match
    ? { ...structuredClone(toRaw(match)), time: match.time.slice(0, 19), confirmDelete: false }
    : {
        status: "complete",
        problem: undefined,
        participants: [],
        confirmDelete: false,
      };
  editModal.show();
}

async function sendData() {
  if (editData.value.id) {
    const res = await MatchService.editResult({
      id: editData.value.id,
      formData: {
        problem: editData.value.problem!,
        status: editData.value.status!,
        time: editData.value.time!,
        logs: editData.value.newLogs,
        teams: editData.value.participants.map((p) => p.team_id!),
        generators: editData.value.participants.map((p) => p.generator?.id!),
        solvers: editData.value.participants.map((p) => p.solver?.id!),
        points: editData.value.participants.map((p) => p.points!),
      },
    });
    results.value[res.id] = res;
    editModal.hide();
  } else {
    const res = await MatchService.createResult({
      problem: editData.value.problem!,
      status: editData.value.status!,
      time: editData.value.time!,
      formData: {
        logs: editData.value.newLogs,
        teams: editData.value.participants.map((p) => p.team_id!),
        generators: editData.value.participants.map((p) => p.generator?.id!),
        solvers: editData.value.participants.map((p) => p.solver?.id!),
        points: editData.value.participants.map((p) => p.points!),
      },
    });
    results.value[res.id] = res;
    editModal.hide();
  }
}

async function deleteResult() {
  if (editData.value.id) {
    await MatchService.deleteResults({
      id: editData.value.id,
    });
    delete results.value[editData.value.id];
    editModal.hide();
  }
}

function getPrograms(team: string, role: Role) {
  if (!editData.value.problem || programs.value[editData.value.problem + team + role]) {
    return;
  }
  programs.value[editData.value.problem + team + role] = [];
  ProgramService.get({
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
      getPrograms(participant.team_id, "generator");
      getPrograms(participant.team_id, "solver");
    }
  }
}

const detailView = ref<MatchResult>();
const ownParticipant = computed(() => {
  const team = store.team;
  if (!team || team == "admin") {
    return undefined;
  }
  const list = detailView.value?.participants.filter((p) => p.team_id == team.id);
  return list && list.length >= 1 ? list[0] : undefined;
});

function openDetail(result: MatchResult) {
  detailView.value = result;
  detailModal.show();
}
</script>

<template>
  <template v-if="store.tournament">
    <table v-if="sortedResults.length !== 0" class="table">
      <thead>
        <tr>
          <th scope="col">Time</th>
          <th scope="col">Problem</th>
          <th scope="col">Status</th>
          <th scope="col">Details</th>
          <th v-if="store.team == 'admin'" scope="col"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="result in sortedResults" :result="result" :key="result.id">
          <td>{{ formatDateTime(result.time) }}</td>
          <td>
            <RouterLink :to="problems[result.problem].link">{{ problems[result.problem].name }}</RouterLink>
          </td>
          <td>{{ result.status }}</td>
          <td>
            <button type="button" class="btn btn-outline-primary btn-sm" @click="openDetail(result)">
              <i class="bi bi-eye-fill"></i>
            </button>
          </td>
          <td v-if="store.team == 'admin'" class="text-end">
            <button
              type="button"
              class="btn btn-sm btn-warning"
              title="Edit"
              @click="(e) => openEdit(result)"
            >
              <i class="bi bi-pencil"></i>
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="alert alert-info" role="alert">
      There aren't any results in the {{ store.tournament.name }} tournament yet.
    </div>
    <button
      v-if="store.team == 'admin'"
      type="button"
      class="btn btn-primary btn-sm me-auto"
      @click="(e) => openEdit(undefined)"
    >
      Add new result
    </button>
  </template>
  <div v-else-if="!store.user" class="alert alert-danger" role="alert">
    You need to log in before you can view the results.
  </div>
  <div v-else class="alert alert-danger" role="alert">
    You need to select a team before you can view the results.
  </div>

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
            <option v-for="status in ['running', 'complete', 'failed']" :value="status">
              {{ status }}
            </option>
          </select>
          <label for="logs" class="form-label">Log file</label>
          <FileInput id="logs" v-model="editData.newLogs" accept=".json, application/json" />
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
                    <i class="bi bi-x-lg"></i>
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

  <div class="modal fade" id="detailModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-l">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Result details</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <template v-if="detailView">
            <table class="table">
              <thead>
                <th scope="col"></th>
                <th scope="col"></th>
              </thead>
              <tbody>
                <tr v-if="ownParticipant?.generator">
                  <td>Generator used</td>
                  <td>
                    <DownloadButton
                      :file="ownParticipant.generator.file"
                      :label="ownParticipant.generator.name"
                    />
                  </td>
                </tr>
                <tr v-if="ownParticipant?.solver">
                  <td>Solver used</td>
                  <td>
                    <DownloadButton :file="ownParticipant.solver.file" :label="ownParticipant.solver.name" />
                  </td>
                </tr>
                <tr v-if="detailView.logs">
                  <td>Log file</td>
                  <td><DownloadButton :file="detailView.logs" /></td>
                </tr>
              </tbody>
            </table>
            <table class="table mt-3">
              <thead>
                <th scope="col">Team</th>
                <th scope="col">Points</th>
              </thead>
              <tbody>
                <tr
                  v-for="participant in detailView.participants"
                  :class="{ 'table-primary': store.team != 'admin' && participant.team_id == store.team?.id }"
                >
                  <td>{{ teams[participant.team_id].name }}</td>
                  <td>{{ participant.points }}</td>
                </tr>
              </tbody>
            </table>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
