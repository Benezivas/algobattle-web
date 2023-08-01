<script setup lang="ts">
import { TournamentService } from "../../typescript_client";
import { Modal } from 'bootstrap';
import { onMounted, ref } from 'vue';
import type { Tournament } from '../types';


const tournaments = ref<{[key: string]: Tournament}>({})


onMounted(async () => {
  tournaments.value = await TournamentService.allTournaments()
})

const error = ref("")

const data = ref({
  name: "",
  id: "",
  action: "create",
  confirmDelete: false,
})
function openModal(action: string, tournament: Tournament | null) {
  data.value.action = action
  if (action == "create") {
    data.value.id = ""
    data.value.name = ""
  } else {
    if (!tournament) {
      return
    }
    data.value.id = tournament.id
    data.value.name = tournament.name
  }
  data.value.confirmDelete = false
  error.value = ""
  Modal.getOrCreateInstance("#tournamentModal").toggle()
}
async function submitEdit() {
  try {
    if (data.value.action == "create") {
      const newTournament = await TournamentService.createTournament({requestBody: {name: data.value.name}})
      tournaments.value[newTournament.id] = newTournament
    } else {
      const edited = await TournamentService.editTournament({id: data.value.id, requestBody: {name: data.value.name}})
      tournaments.value[edited.id] = edited
    }
    Modal.getOrCreateInstance("#tournamentModal").toggle()
  } catch {
    error.value = "name"
  }
}
async function deleteTournament() {
  if (!data.value.confirmDelete) {
    data.value.confirmDelete = true
    return
  }
  await TournamentService.deleteTournament({id: data.value.id})
  delete tournaments.value[data.value.id]
  Modal.getOrCreateInstance("#tournamentModal").toggle()
}
</script>

<template>
  <table class="table table-hover mb-2">
    <thead>
      <tr>
        <th scope="col">Name</th>
        <th scope="col"></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="tournament in tournaments">
        <td>
          {{tournament.name}}
        </td>
        <td class="text-end">
          <button type="button" class="btn btn-warning btn-sm" title="Edit tournament" @click="e => openModal('edit', tournament)"><i class="bi bi-pencil"></i></button>
        </td>
      </tr>
    </tbody>
  </table>

  <button type="button" class="btn btn-primary btn-sm ms-2" @click="e => openModal('create', null)">Create new tournament</button>


  <div class="modal fade" id="tournamentModal" tabindex="-1" aria-labelledby="modalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <form class="modal-content" @submit.prevent="submitEdit">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="modalLabel">
          <span v-if="data.action == 'edit'">Edit tournament</span>
          <span v-else>Create new tournament</span>
          </h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <label for="name" class="form-label">Name</label>
          <input class="form-control w-em" type="text" v-model="data.name" required :class="{'is-invalid': error == 'name'}">
          <div class="invalid-feedback">
            Another tournament with that name exists already
          </div>
        </div>
        <div class="modal-footer">
          <button v-if="data.confirmDelete" type="button" class="btn btn-secondary" @click="(e) => data.confirmDelete = false">Cancel</button>
          <button v-if="data.action == 'edit'" type="button" class="btn btn-danger ms-2" @click="deleteTournament">
            {{data.confirmDelete ? "Confirm deletion" : "Delete tournament"}}
          </button>
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">{{ data.action == "edit" ? "Save" : "Create" }}</button>
        </div>
      </form>
    </div>
  </div>
</template>
