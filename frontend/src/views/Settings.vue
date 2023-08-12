<script setup lang="ts">
import { type ModelDict, store } from '@/main';
import { TeamService, TournamentService, UserService } from "@client";
import type { Team, Tournament } from "@client";
import { onMounted, ref } from 'vue';


const userEdit = ref({
  email: store.user.email,
  selectedTeam: store.user.selected_team?.id,
  selectedTournament: store.user.selected_tournament?.id,
})
const teams = ref<ModelDict<Team>>({})
const tournaments = ref<{[key: string]: Tournament}>({})
const error = ref("")

onMounted(async () => {
  teams.value = await TeamService.getTeams({requestBody: store.user.teams})
  if (store.user.is_admin) {
    tournaments.value = await TournamentService.allTournaments()
  }
})

async function saveEdit() {
  const newUser = await UserService.settings({requestBody: {
    email: userEdit.value.email,
    team: userEdit.value.selectedTeam,
    tournament: userEdit.value.selectedTournament,
  }})
  Object.assign(store.user, newUser)
  error.value = "success"
}
</script>

<template>
  <div class="alert alert-success" role="alert" v-if="error == 'success'">
    Changes have been saved.
  </div>
  <h3>User settings</h3>
  <label class="form-label" for="emailInput">Email address</label>
  <input type="email" class="form-control w-em mb-2" id="emailInput" v-model="userEdit.email">
  <label for="selectedTeam" class="form-label">Selected team</label>
  <select class="form-select w-em" name="selectedTeam" v-model="userEdit.selectedTeam">
    <option v-for="(team, id) in teams" :value="id">{{team.name + ` (${tournaments[team.tournament]?.name})`}}</option>
  </select>
  <template v-if="store.user.is_admin">
    <label for="currTournament" class="form-label">Current Tournament</label>
    <select class="form-select w-em" name="currTournament" v-model="userEdit.selectedTournament">
      <option v-for="(tournament, id) in tournaments" :value="id">{{ tournament.name }}</option>
    </select>
  </template>
  <button type="submit" class="btn btn-primary mt-4" @click="saveEdit">Save changes</button>
</template>
