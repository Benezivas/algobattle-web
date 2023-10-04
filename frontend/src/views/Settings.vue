<script setup lang="ts">
import { store, type ModelDict } from "@/main";
import { UserService, type Tournament, TournamentService } from "@client";
import { onMounted, ref } from "vue";

const userEdit = ref({
  email: store.user?.email,
  tournament: store.user?.settings.selected_tournament,
});
const error = ref("");
const tournaments = ref<ModelDict<Tournament>>({})

onMounted(async () => {
  tournaments.value = await TournamentService.get({});
})

async function saveEdit() {
  const newUser = await UserService.settings({
      email: userEdit.value.email,
      tournament: userEdit.value.tournament?.id,
  });
  store.user = newUser;
  error.value = "success";
}
</script>

<template>
  <template v-if="store.user">
    <div class="alert alert-success" role="alert" v-if="error == 'success'">Changes have been saved.</div>
    <h3>User settings</h3>
    <label class="form-label" for="emailInput">Email address</label>
    <input type="email" class="form-control  mb-2" id="emailInput" v-model="userEdit.email" />
    <template v-if="store.user.is_admin">
      <label for="tournament_select" class="form-label">Select tournament</label>
      <select id="tournament_select" class="form-select" v-model="userEdit.tournament">
        <option v-for="(tournament, id) in tournaments" :value="tournament" :key="id">{{ tournament.name }}</option>
      </select>
    </template>
    <button type="submit" class="btn btn-primary mt-4" @click="saveEdit">Save changes</button>
  </template>
    <div v-else class="alert alert-danger" role="alert">You are not logged in so you cannot edit any settings.</div>
</template>
