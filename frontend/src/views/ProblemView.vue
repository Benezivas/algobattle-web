<script setup lang="ts">
import { contextApi, problemApi, store } from '@/main';
import type { AlgobattleWebModelsProblemSchema } from 'typescript_client';
import { computed, onMounted, ref, type Ref } from 'vue';

let contexts = {}
let selectedContext: string | undefined = undefined
const problems: Ref<{[key: string]: AlgobattleWebModelsProblemSchema}> = ref({})

onMounted(async () => {
  contexts = await contextApi.allContexts()
  selectedContext = store.user.settings.selectedTeam?.context
  problems.value = await problemApi.allProblems({context: selectedContext})
})

function inContext(problem: AlgobattleWebModelsProblemSchema) {
    if (selectedContext == undefined) {
        return true
    } else {
        return problem.context == selectedContext
    }
}
const now = new Date()

const future_problems = computed(() => {
  return Object.fromEntries(Object.entries(problems)
    .filter(([id, problem]) => 
    inContext(problem)
      && problem.start != null
      && problem.start > now
    ))
})

const current_problems = computed(() => {
  return Object.fromEntries(Object.entries(problems)
    .filter(([id, problem]) =>
    inContext(problem)
      && (problem.start == null || problem.start <= now)
      && (problem.end == null || problem.end > now)
    ))
})

const past_problems = computed(() => {
  return Object.fromEntries(Object.entries(problems)
    .filter(([id, problem]) =>
    inContext(problem)
      && problem.end != null
      && problem.end < now
    ))
})
</script>

<template>
  {% if user.is_admin %}
  <div class="mb-5">
    <label for="context_select" class="form-label">Select context</label>
    <select id="context_select" class="form-select w-em" v-model="selectedContext">
      <option :value="null" selected>All</option>
      <option v-for="(context, id) in contexts" :value="id">${context.name}</option>
    </select>
  </div>

  <h3>Upcoming</h3>
  <div class="d-flex flex-wrap mb-5">
    <problem v-for="(problem, id) in future_problems" :problem="problem" :key="id"></problem>
    <div class="card border border-success-subtle m-2" style="width: 18rem; height: 24rem;">
      <img src="/static/images/default_problem.png" style="height: 10.125rem; object-fit: contain" class="card-img-top" alt="">
      <div class="card-body d-flex flex-column">
        <h5 class="card-title mb-auto">New problem</h5>
        <a href="/problems/create" class="btn btn-success mt-auto stretched-link">Create</a>
      </div>
    </div>
  </div>
  {% endif %}
  <h3 v-if="Object.keys(current_problems).length != 0">Current</h3>
  <div class="d-flex flex-wrap mb-5">
    <problem v-for="(problem, id) in current_problems" :problem="problem" :key="id"></problem>
  </div>
  <h3 v-if="Object.keys(past_problems).length != 0">Past</h3>
  <div class="d-flex flex-wrap">
    <problem v-for="(problem, id) in past_problems" :problem="problem" :key="id"></problem>
  </div>
</template>
