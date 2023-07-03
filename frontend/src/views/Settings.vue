<script setup lang="ts">import { tournamentApi, store, teamApi, userApi } from '@/main';
import type { Team, Tournament } from 'typescript_client';
import { onMounted, ref } from 'vue';


const userEdit = ref({
  name: store.user.name,
  email: store.user.email,
  settings: {
    selectedTeam: store.user.settings.selectedTeam?.id,
  },
})
const teams = ref<{[key: string]: Team}>({})
const tournaments = ref<{[key: string]: Tournament}>({})
const error = ref("")

onMounted(async () => {
  teams.value = await teamApi.getTeams({requestBody: store.user.teams})
  tournaments.value = await tournamentApi.getTournaments({requestBody: Object.values(teams.value).map(t => t.tournament)})
})

async function saveEdit() {
  const newUser = await userApi.editSelf({editSelf: {name: userEdit.value.name, email: userEdit.value.email}})
  Object.assign(store.user, newUser)
  store.user.settings = await userApi.editSettings({editSettings: {selectedTeam: userEdit.value.settings.selectedTeam}})
  error.value = "success"
}
</script>

<template>
  <div class="alert alert-success" role="alert" v-if="error == 'success'">
    Changes have been saved.
  </div>
  <h3>User data</h3>
  <label class="form-label" for="nameInput">Name</label>
  <input type="text" class="form-control w-em mb-2" id="nameInput" v-model="userEdit.name">
  <label class="form-label" for="emailInput">Email address</label>
  <input type="email" class="form-control w-em mb-2" id="emailInput" v-model="userEdit.email">
  <h3 class="mt-5">User settings</h3>
  <label for="selectedTeam" class="form-label">Selected team</label>
  <select class="form-select w-em" name="selectedTeam" v-model="userEdit.settings.selectedTeam">
    <option :value="undefined">Select a team</option>
    <option v-for="(team, id) in teams" :value="id">{{team.name + ` (${tournaments[team.tournament]?.name})`}}</option>
  </select>
  <button type="submit" class="btn btn-primary mt-4" @click="saveEdit">Save changes</button>
</template>
