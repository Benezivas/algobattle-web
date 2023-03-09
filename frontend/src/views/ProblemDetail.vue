<script setup lang="ts">
import { contextApi, docsApi, problemApi, store } from '@/main';
import type { Context, Documentation, DbFile, Problem, AlgobattleWebModelsTeamSchema } from 'typescript_client';
import { computed, onMounted, ref, type Ref } from 'vue';
import { useRoute } from 'vue-router';

const problem = ref({} as Problem)
const contexts: Ref<{
    [key: string]: Context
}> = ref({})
const selectedTeam: Ref<AlgobattleWebModelsTeamSchema | undefined> = ref(undefined)
const docs: Ref<{[key: string]: Documentation}> = ref({})
const description: Ref<string | undefined> = ref(undefined)

const route = useRoute()
const error = ref(null as null | string)
const own_doc = computed(() => {
  if (!selectedTeam.value) {
    return null
  }
  return docs.value[selectedTeam.value.id]
})


onMounted(async () => {
  selectedTeam.value = store.user.settings.selectedTeam
  try {
    const problemInfo = await problemApi.problemByName({
      problemName: route.params.problemName as string,
      contextName: route.params.contextName as string,
    })
    problem.value = problemInfo.problem
    if (store.user.isAdmin) {
      contexts.value = await contextApi.allContexts()
    } else {
      contexts.value = {[problemInfo.context.id]: problemInfo.context}
    }
    docs.value = await docsApi.getDocs({getDocs: {problem: problem.value.id}})
    description.value = (await problemApi.problemDesc({id: problem.value.id})).data
  } catch (e) {
    console.log(e)
    error.value = "problem"
  }
})

async function openEdit() {
  
}

async function openDocEdit() {
  
}

</script>

<template>
  <nav id="navbar" class="navbar bg-body-tertiary px-3 mb-3 sticky-top" style="top: 62px">
    <RouterLink class="navbar-brand" to="#">
      {{problem.name + store.user.isAdmin ? `(${contexts[problem.context]?.name})`: ""}}
    </RouterLink>
    <ul class="nav nav-pills">
      <li v-if="problem.description" class="nav-item">
        <a class="nav-link" href="#description">Description</a>
      </li>
      <li v-if="store.user.isAdmin || own_doc" class="nav-item">
        <a class="nav-link" href="#documentation">Documentation</a>
      </li>
      <li v-if="problem.problemSchema" class="nav-item">
        <a class="nav-link" href="#problem_schema">Problem schema</a>
      </li>
      <li v-if="problem.solutionSchema" class="nav-item">
        <a class="nav-link" href="#solution_schema">Solution schema</a>
      </li>
    </ul>
  </nav>
  <div data-bs-spy="scroll" data-bs-target="#navbar" data-bs-root-margin="0px 0px -40%" data-bs-smooth-scroll="true" class="bg-body-tertiary p-3 rounded-2" tabindex="0">
    <div class="row">
      <div class="col-md-9">
        <img v-if="problem.image" :src="problem.image.location" :alt="problem.image.altText" class="object-fit-cover border rounded mb-4" style="width: 100%;">
      </div>
      <div class="col-md-3">
        <ul class="list-group list-group-flush bg-body-tertiary w-em">
          <li class="list-group-item bg-body-tertiary">{{problem.name}}</li>
          <li v-if="store.user.isAdmin" class="list-group-item bg-body-tertiary">{{contexts[problem.context]?.name}}</li>
          <li v-if="problem.start" class="list-group-item bg-body-tertiary">Start: {{problem.start.toLocaleString()}}</li>
          <li v-if="problem.end" class="list-group-item bg-body-tertiary">End: {{problem.end.toLocaleString()}}</li>
          <li class="list-group-item bg-body-tertiary">
            <a role="button" class="btn btn-primary btn-sm" :href="`/api/problem/${problem.id}/download_all`" title="Download problem files">Download problem files <i class="bi bi-download ms-1"></i></a>
          </li>
          <li v-if="store.user.isAdmin" class="list-group-item bg-body-tertiary">
            <button role="button" class="btn btn-warning btn-sm" title="Edit problem" @click="openEdit">Edit problem<i class="bi bi-pencil ms-1"></i></button>
          </li>
          <li v-if="selectedTeam" class="list-group-item bg-body-tertiary">
            <button role="button" class="btn btn-warning btn-sm" title="Edit documentation" @click="openDocEdit">Edit documentation<i class="bi bi-pencil ms-1"></i></button>
          </li>
        </ul>
      </div>
    </div>
    <template v-if="problem.description">
      <h4 id="description" class="mt-5">Description</h4>
      <a v-if="description == '__DONWLOAD_BUTTON__'" role="button" class="btn btn-primary btn-sm" :href="problem.description.location" title="Download file">Download description file <i class="bi bi-download ms-1"></i></a>
      <div v-else v-html="description"></div>
    </template>
    <h4 id="documentation" class="mt-5">Documentation</h4>
    <a v-if="own_doc" role="button" class="btn btn-primary btn-sm mb-3" :href="own_doc.file.location" title="Download documentation">Download documentation<i class="bi bi-download ms-1"></i></a>
    <template v-if="problem.problemSchema">
      <h4 id="problem_schema" class="mt-5">Problem schema</h4>
      <pre><code>{{problem.problemSchema}}</code></pre>
    </template>
    <template v-if="problem.solutionSchema">
      <h4 id="solution_schema" class="mt-5">Solution schema</h4>
      <pre><code>{{problem.solutionSchema}}</code></pre>
    </template>
  </div>

</template>
