<script setup lang="ts">
import ProblemCard from '@/components/ProblemCard.vue';
import { contextApi, problemApi, store } from '@/main';
import type { AlgobattleWebModelsContextSchema, AlgobattleWebModelsProblemSchema } from 'typescript_client';
import { computed, onMounted, ref, watch, type Ref } from 'vue';

let contexts: Ref<{
    [key: string]: AlgobattleWebModelsContextSchema
}> = ref({})
let selectedContext: Ref<string | undefined> = ref(undefined)
const problems: Ref<{[key: string]: AlgobattleWebModelsProblemSchema}> = ref({})

onMounted(async () => {
  contexts.value = await contextApi.allContexts()
  selectedContext.value = store.user.settings.selectedTeam?.context
  problems.value = await problemApi.allProblems({context: selectedContext.value})
})

watch(selectedContext, async (newContext: string | undefined) => {
  problems.value = await problemApi.allProblems({context: newContext})
})

function inContext(problem: AlgobattleWebModelsProblemSchema) {
    if (selectedContext.value == undefined) {
        return true
    } else {
        return problem.context == selectedContext.value
    }
}
const now = new Date()

const future_problems = computed(() => {
  return Object.fromEntries(Object.entries(problems.value)
    .filter(([id, problem]) => 
    inContext(problem)
      && problem.start != null
      && problem.start > now
    ))
})

const current_problems = computed(() => {
  return Object.fromEntries(Object.entries(problems.value)
    .filter(([id, problem]) =>
    inContext(problem)
      && (problem.start == null || problem.start <= now)
      && (problem.end == null || problem.end > now)
    ))
})

const past_problems = computed(() => {
  return Object.fromEntries(Object.entries(problems.value)
    .filter(([id, problem]) =>
    inContext(problem)
      && problem.end != null
      && problem.end < now
    ))
})
</script>

<template>
  <template v-if="store.user.isAdmin">
    <div class="mb-5">
      <label for="context_select" class="form-label">Select context</label>
      <select id="context_select" class="form-select w-em" v-model="selectedContext">
        <option :value="undefined" selected>All</option>
        <option v-for="(context, id) in contexts" :value="id">{{context.name}}</option>
      </select>
    </div>
    
    <h3>Upcoming</h3>
    <div class="d-flex flex-wrap mb-5">
      <ProblemCard v-for="(problem, id) in future_problems" :problem="problem" :context="contexts[problem.context]" :key="id" />
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
    <ProblemCard v-for="(problem, id) in current_problems" :problem="problem" :context="contexts[problem.context]" :key="id" />
  </div>
  <h3 v-if="Object.keys(past_problems).length != 0">Past</h3>
  <div class="d-flex flex-wrap">
    <ProblemCard v-for="(problem, id) in past_problems" :problem="problem" :context="contexts[problem.context]" :key="id" />
  </div>
</template>
