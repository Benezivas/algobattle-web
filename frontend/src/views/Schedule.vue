<script setup lang="ts">
import { store, type ModelDict } from "@/shared";
import { MatchService, TournamentService, ProblemService } from "@client";
import { Modal } from "bootstrap";
import type { ScheduledMatch, Problem, Tournament } from "@client";
import { computed, onMounted, ref, toRaw } from "vue";

const matches = ref<ModelDict<ScheduledMatch>>({});
const problems = ref<ModelDict<Problem>>({});
const sortedMatches = computed(() => {
  const sorted = Object.values(matches.value);
  sorted.sort((a, b) => {
    if (a.time < b.time) {
      return -1;
    } else if (a.time > b.time) {
      return 1;
    } else {
      return 0;
    }
  });
  return sorted;
});

let modal: Modal;
onMounted(async () => {
  const results = await MatchService.getScheduled();
  problems.value = results.problems;
  matches.value = results.matches;
  modal = Modal.getOrCreateInstance("#editModal");
  if (store.team == "admin") {
    problems.value = await ProblemService.get({});
  }
});

function openModal(match: ScheduledMatch | undefined) {
  editData.value = match
    ? { ...structuredClone(toRaw(match)), time: match.time.slice(0, 19) }
    : { points: 100 };
  modal.show();
}

const editData = ref<Partial<ScheduledMatch>>({});
const confirmDelete = ref<boolean>(false);
async function sendData() {
  let newMatch;
  if (editData.value.id) {
    newMatch = await MatchService.editSchedule({ id: editData.value.id, requestBody: editData.value });
  } else {
    if (
      editData.value.time === undefined ||
      editData.value.problem === undefined ||
      editData.value.points === undefined
    ) {
      return;
    }
    newMatch = await MatchService.createSchedule({
      requestBody: editData.value.name,
      time: editData.value.time,
      problem: editData.value.problem,
      points: editData.value.points,
    });
  }
  matches.value[newMatch.id] = newMatch;
  modal.hide();
}
async function deleteMatch() {
  if (editData.value.id) {
    await MatchService.deleteSchedule({ id: editData.value.id });
    delete matches.value[editData.value.id];
    modal.hide();
  }
}
</script>

<template>
  <template v-if="store.tournament">
    <table v-if="sortedMatches.length !== 0" class="table">
      <thead>
        <tr>
          <th scope="col">Name</th>
          <th scope="col">Time</th>
          <th scope="col">Problem</th>
          <th scope="col">Points</th>
          <th v-if="store.team == 'admin'" scope="col"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="match in sortedMatches" :match="match" :key="match.id">
          <td>{{ match.name }}</td>
          <td>{{ new Date(match.time).toLocaleString() }}</td>
          <td>
            <RouterLink :to="problems[match.problem].link">{{ problems[match.problem].name }}</RouterLink>
          </td>
          <td>{{ match.points }}</td>
          <td v-if="store.team == 'admin'" class="text-end">
            <button
              type="button"
              class="btn btn-sm btn-warning"
              title="Edit"
              @click="(e) => openModal(match)"
            >
              <i class="bi bi-pencil"></i>
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="alert alert-info" role="alert">
      There aren't any matches scheduled in the {{ store.tournament.name }} tournament yet.
    </div>
    <button
      v-if="store.team == 'admin'"
      type="button"
      class="btn btn-primary btn-sm me-auto"
      @click="(e) => openModal(undefined)"
    >
      Schedule new match
    </button>
  </template>
  <div v-else-if="!store.user" class="alert alert-danger" role="alert">
    You need to log in before you can view the scheduled matches.
  </div>
  <div v-else class="alert alert-danger" role="alert">
    You need to select a team before you can view the scheduled matches.
  </div>

  <div class="modal fade" id="editModal" tabindex="-1" aria-labelledby="modalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <form class="modal-content" @submit.prevent="sendData">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="modalLabel">
            <span v-if="editData.id">Edit scheduled match</span>
            <span v-else>Schedule new match</span>
          </h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <label for="name" class="form-label">Name</label>
          <input id="name" class="form-control" type="text" maxlength="32" v-model="editData.name" />
          <label for="time" class="form-label">Time</label>
          <input id="time" class="form-control" type="datetime-local" required v-model="editData.time" />
          <label for="problem" class="form-label">Problem</label>
          <select id="problem" class="form-select" required v-model="editData.problem">
            <option v-for="(problem, id) in problems" :value="id">{{ problem.name }}</option>
          </select>
          <label for="points" class="form-label">Points</label>
          <input id="points" class="form-control" type="number" min="0" required v-model="editData.points" />
        </div>
        <div class="modal-footer">
          <button
            v-if="confirmDelete"
            type="button"
            class="btn btn-secondary"
            @click="(e) => (confirmDelete = false)"
          >
            Cancel
          </button>
          <button v-if="editData.id" type="button" class="btn btn-danger ms-2" @click="deleteMatch">
            {{ confirmDelete ? "Confirm deletion" : "Delete match" }}
          </button>
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">{{ editData.id ? "Save" : "Schedule" }}</button>
        </div>
      </form>
    </div>
  </div>
</template>
