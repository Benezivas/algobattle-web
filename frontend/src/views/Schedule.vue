<script setup lang="ts">
import { store, type ModelDict } from "@/main";
import { MatchService, TournamentService, ProblemService } from "../../typescript_client";
import { Modal } from "bootstrap";
import type { ScheduledMatch, Problem, Tournament } from "../../typescript_client";
import { onMounted, ref, toRaw } from "vue";

let selectedTournament = ref<string>("");
const matches = ref<ModelDict<ScheduledMatch>>({});
const problems = ref<ModelDict<Problem>>({});
const tournaments = ref<ModelDict<Tournament>>({});

let modal: Modal;
onMounted(async () => {
  selectedTournament.value = store.user.settings.selected_team?.tournament || "";
  const results = await MatchService.scheduledMatches({});
  tournaments.value = await TournamentService.allTournaments();
  problems.value = results.problems;
  matches.value = results.matches;
  modal = Modal.getOrCreateInstance("#editModal");
  if (store.user.is_admin) {
    problems.value = await ProblemService.allProblems({tournament: selectedTournament.value})
  }
})

function openModal(match: ScheduledMatch | undefined) {
  editData.value = match ? structuredClone(toRaw(match)) : {points: 100};
  modal.show();
}

const editData = ref<Partial<ScheduledMatch>>({});
const confirmDelete = ref<boolean>(false);
async function sendData() {
  let newMatch;
  if (editData.value.id) {
    newMatch = await MatchService.editSchedule(editData.value as ScheduledMatch);
  } else {
    if (!editData.value.time || !editData.value.problem || !editData.value.points) {
      return;
    }
    newMatch = await MatchService.createSchedule({
      name: editData.value.name,
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
    await MatchService.deleteSchedule({id: editData.value.id});
    delete matches.value[editData.value.id];
    modal.hide();
  }
}

</script>

<template>
  <template v-if="store.user.is_admin">
    <div class="mb-5">
      <label for="tournament_select" class="form-label">Select tournament</label>
      <select id="tournament_select" class="form-select w-em" v-model="selectedTournament">
        <option v-for="(tournament, id) in tournaments" :value="id">{{tournament.name}}</option>
      </select>
    </div>
  </template>

  <table class="table">
    <thead>
      <tr>
        <th scope="col">Name</th>
        <th scope="col">Time</th>
        <th scope="col">Problem</th>
        <th scope="col">Points</th>
        <th v-if="store.user.is_admin" scope="col"></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(match, id) in matches" :match="match" :key="id">
        <td>{{ match.name }}</td>
        <td>{{ match.time.toLocaleString() }}</td>
        <td><RouterLink :to="`/problems/${tournaments[selectedTournament].name}/${problems[match.problem].name}`">{{ problems[match.problem].name }}</RouterLink></td>
        <td>{{ match.points }}</td>
        <td v-if="store.user.is_admin" class="text-end">
          <button type="button" class="btn btn-sm btn-warning" title="Edit" @click="e => openModal(match)"><i class="bi bi-pencil"></i></button>
        </td>
      </tr>
    </tbody>
  </table>
  <button type="button" class="btn btn-primary btn-sm me-auto" @click="e => openModal(undefined)">Schedule new match</button>

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
          <input id="name" class="form-control w-em mb-3" type="text" v-model="editData.name">
          <label for="time" class="form-label">Time</label>
          <input id="time" class="form-control w-em mb-3" type="datetime-local" required v-model="editData.time"/>
          <label for="problem" class="form-label">Problem</label>
          <select id="problem" class="form-select w-em mb-3" required v-model="editData.problem">
            <option v-for="(problem, id) in problems" :value="id">{{ problem.name }}</option>
          </select>
          <label for="points" class="form-label">Points</label>
          <input id="points" class="form-control w-em mb-3" type="number" min="0" required v-model="editData.points"/>
        </div>
        <div class="modal-footer">
          <button v-if="confirmDelete" type="button" class="btn btn-secondary" @click="(e) => confirmDelete = false">Cancel</button>
          <button v-if="editData.id" type="button" class="btn btn-danger ms-2" @click="deleteMatch">
            {{confirmDelete ? "Confirm deletion" : "Delete match"}}
          </button>
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">{{ editData.id ? "Save" : "Schedule" }}</button>
        </div>
      </form>
    </div>
  </div>
</template>
