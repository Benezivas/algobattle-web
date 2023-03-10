<script setup lang="ts">
import { Modal } from "bootstrap"
import { contextApi, docsApi, problemApi, store } from '@/main';
import type { Context, Documentation, DbFile, Problem, AlgobattleWebModelsTeamSchema } from 'typescript_client';
import { computed, onMounted, ref, type Ref } from 'vue';
import { useRoute } from 'vue-router';

interface InputFileEvent extends InputEvent {
    target: HTMLInputElement;
}

const problem = ref({} as Problem)
const contexts: Ref<{
    [key: string]: Context
}> = ref({})
const selectedTeam: Ref<AlgobattleWebModelsTeamSchema | undefined> = ref(undefined)
const docs: Ref<{[key: string]: Documentation}> = ref({})
const description: Ref<string | undefined> = ref(undefined)

const route = useRoute()
const error = ref(null as null | string)
const ownDoc = computed(() => {
  const team = selectedTeam.value
  if (!team) {
    return null
  } else {
    const docList = Object.values(docs.value).filter(doc => doc.team == team.id)
    return docList.length != 0 ? docList[0] : null
  }
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


const editDoc = {
  problem: "",
  team: "",
  newFile: null as File | null,
  fileSelect: ref<HTMLInputElement | null>(null),
  confirmDelete: ref(false),
  docId: ref<string | undefined>(undefined),
}
function selectFile(event: InputFileEvent) {
  const files = event.target.files || event.dataTransfer?.files
  if (files && files.length != 0) {
    editDoc.newFile = files[0]
  }
}
async function openDocEdit(docId: string | null) {
  const modal = Modal.getOrCreateInstance("#docModal")
  if (docId) {
    editDoc.problem = docs.value[docId].problem
    editDoc.team = docs.value[docId].team
    editDoc.docId.value = docId
  } else if (store.user.settings.selectedTeam) {
    editDoc.problem = problem.value.id
    editDoc.team = store.user.settings.selectedTeam.id
    editDoc.docId.value = ownDoc.value?.id
  } else {
    return
  }
  editDoc.confirmDelete.value = false
  editDoc.newFile = null
  if (editDoc.fileSelect.value) {
    editDoc.fileSelect.value.value = ""
  }
  modal.show()
}
async function upload_doc() {
  if (!editDoc.newFile || editDoc.newFile.size == 0) {
    return
  }
  var newDoc = null
  if (store.user.isAdmin) {
    newDoc = await docsApi.uploadDocs({problemId: editDoc.problem, teamId: editDoc.team, file: editDoc.newFile})
  } else {
    newDoc = await docsApi.uploadOwnDocs({problemId: editDoc.problem, file: editDoc.newFile})
  }
  if (editDoc.fileSelect.value) {
    editDoc.fileSelect.value.value = ""
  }
  docs.value[newDoc.id] = newDoc
  Modal.getOrCreateInstance("#docModal").hide()
}
async function removeDoc() {
  if (!editDoc.docId.value) {
    return
  }
  if (!editDoc.confirmDelete.value) {
    editDoc.confirmDelete.value = true
    return
  }
  if (store.user.isAdmin) {
    docsApi.deleteAdminDocs({teamId: editDoc.team, problemId: editDoc.problem})
  } else {
    docsApi.deleteOwnDocs({problemId: editDoc.problem})
  }
  editDoc.confirmDelete.value = false
  if (editDoc.fileSelect.value) {
    editDoc.fileSelect.value.value = ""
  }
  delete docs.value[editDoc.docId.value]
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
      <li v-if="store.user.isAdmin || ownDoc" class="nav-item">
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
            <button role="button" class="btn btn-warning btn-sm" title="Edit documentation" @click="(e) => openDocEdit(null)">Edit documentation<i class="bi bi-pencil ms-1"></i></button>
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
    <a v-if="ownDoc" role="button" class="btn btn-primary btn-sm mb-3" :href="ownDoc.file.location" title="Download documentation">Download documentation<i class="bi bi-download ms-1"></i></a>
    <template v-if="problem.problemSchema">
      <h4 id="problem_schema" class="mt-5">Problem schema</h4>
      <pre><code>{{problem.problemSchema}}</code></pre>
    </template>
    <template v-if="problem.solutionSchema">
      <h4 id="solution_schema" class="mt-5">Solution schema</h4>
      <pre><code>{{problem.solutionSchema}}</code></pre>
    </template>
  </div>

  <div class="modal fade" id="docModal" tabindex="-1" aria-labelledby="docLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable">
      <form class="modal-content" @submit.prevent="upload_doc">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="docLabel">Edit documentation</h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body row">
          <label for="file_select" class="form-label mt-3">Select new file</label>
          <input type="file" class="form-control w-em" id="file_select" ref="editDoc.fileSelect" @change="(e) => selectFile(e as any)"/>

        </div>
        <div class="modal-footer">
          <button v-if="editDoc.confirmDelete.value" type="button" class="btn btn-secondary" @click="(e) => editDoc.confirmDelete.value = false">Cancel</button>
          <button v-if="editDoc.docId" type="button" class="btn btn-danger ms-2" @click="removeDoc">
            {{editDoc.confirmDelete.value ? "Confirm deletion" : "Delete documentation"}}
          </button>
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">Upload</button>
        </div>
      </form>
    </div>
  </div>
</template>
