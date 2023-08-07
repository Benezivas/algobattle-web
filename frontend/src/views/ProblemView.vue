<script setup lang="ts">
import ProblemCard from '@/components/ProblemCard.vue';
import { store } from "../main";
import { ProblemService, TournamentService } from "@client";
import type { Tournament, Problem } from "@client";
import { computed, onMounted, ref, watch, type Ref } from 'vue';

let tournaments: Ref<{
    [key: string]: Tournament
}> = ref({})
let selectedTournament: Ref<string | undefined> = ref(undefined)
const problems: Ref<{[key: string]: Problem}> = ref({})

onMounted(async () => {
  tournaments.value = await TournamentService.allTournaments()
  selectedTournament.value = store.user.settings.selected_team?.tournament
  problems.value = await ProblemService.allProblems({tournament: selectedTournament.value})
})

watch(selectedTournament, async (newTournament: string | undefined, oldTournament: string | undefined) => {
  if (newTournament != oldTournament) {
    problems.value = await ProblemService.allProblems({tournament: newTournament})
  }
})

function inTournament(problem: Problem) {
    if (selectedTournament.value == undefined) {
        return true
    } else {
        return problem.tournament == selectedTournament.value
    }
}
const now = new Date()

const future_problems = computed(() => {
  return Object.fromEntries(Object.entries(problems.value)
    .filter(([id, problem]) => 
    inTournament(problem)
      && problem.start != null
      && new Date(problem.start) > now
    ))
})

const current_problems = computed(() => {
  return Object.fromEntries(Object.entries(problems.value)
    .filter(([id, problem]) =>
    inTournament(problem)
      && (problem.start == null || new Date(problem.start) <= now)
      && (problem.end == null || new Date(problem.end) > now)
    ))
})

const past_problems = computed(() => {
  return Object.fromEntries(Object.entries(problems.value)
    .filter(([id, problem]) =>
    inTournament(problem)
      && problem.end != null
      && new Date(problem.end) < now
    ))
})
</script>

<template>
  <template v-if="store.user.is_admin">
    <div class="mb-5">
      <label for="tournament_select" class="form-label">Select tournament</label>
      <select id="tournament_select" class="form-select w-em" v-model="selectedTournament">
        <option :value="undefined" selected>All</option>
        <option v-for="(tournament, id) in tournaments" :value="id">{{tournament.name}}</option>
      </select>
    </div>
    
    <h3>Upcoming</h3>
    <div class="d-flex flex-wrap mb-5">
      <ProblemCard v-for="(problem, id) in future_problems" :problem="problem" :tournament="tournaments[problem.tournament]" :key="id" />
      <div class="card border border-success-subtle m-2" style="width: 18rem; height: 24rem;">
        <img src="/default_problem.png" style="height: 10.125rem; object-fit: contain" class="card-img-top" alt="">
        <div class="card-body d-flex flex-column">
          <h5 class="card-title mb-auto">New problem</h5>
          <RouterLink to="/problems/create" class="btn btn-success mt-auto stretched-link">Create</RouterLink>
        </div>
      </div>
    </div>
  </template>
  <h3 v-if="Object.keys(current_problems).length != 0">Current</h3>
  <div class="d-flex flex-wrap mb-5">
    <ProblemCard v-for="(problem, id) in current_problems" :problem="problem" :tournament="tournaments[problem.tournament]" :key="id" />
  </div>
  <h3 v-if="Object.keys(past_problems).length != 0">Past</h3>
  <div class="d-flex flex-wrap">
    <ProblemCard v-for="(problem, id) in past_problems" :problem="problem" :tournament="tournaments[problem.tournament]" :key="id" />
  </div>
</template>
