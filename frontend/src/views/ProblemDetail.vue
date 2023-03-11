<script setup lang="ts">
import { Modal } from "bootstrap"
import { contextApi, docsApi, problemApi, store, teamApi } from '@/main';
import type { Context, Documentation, DbFile, Problem, AlgobattleWebModelsTeamSchema } from 'typescript_client';
import { computed, onMounted, ref, type Ref } from 'vue';
import { useRoute } from 'vue-router';
import router from "@/router";
import FileEditRow from "@/components/FileEditRow.vue";

interface InputFileEvent extends InputEvent {
  target: HTMLInputElement;
}
interface DbFileEdit {
  location?: string,
  edit?: File | null,
}
interface ProblemEdit {
  name: string,
  context: string,
  file: DbFileEdit,
  config: DbFileEdit,
  start?: Date,
  end?: Date,
  description: DbFileEdit,
  shortDescription: string,
  image: DbFileEdit,
  alt?: string,
  problemSchema?: string,
  solutionSchema?: string,
  colour: string,
}

const problem = ref({} as Problem)
const contexts: Ref<{
    [key: string]: Context
}> = ref({})
const selectedTeam: Ref<AlgobattleWebModelsTeamSchema | undefined> = ref(undefined)
const docs: Ref<{[key: string]: Documentation}> = ref({})
const description: Ref<string | undefined> = ref(undefined)
const teams: Ref<{[key: string]: AlgobattleWebModelsTeamSchema}> = ref({})

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
    teams.value = await teamApi.getTeams({requestBody: Object.values(docs.value).map((doc) => doc.team)})
    if (selectedTeam.value) {
      teams.value[selectedTeam.value.id] = selectedTeam.value
    }
  } catch {
    error.value = "problem"
  }
})

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
  Modal.getOrCreateInstance("#docModal").show()
}
async function uploadDoc() {
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
  Modal.getOrCreateInstance("#docModal").hide()
}

let editProblem = ref(createProblemEdit(problem.value))
let confirmDeleteProblem = ref(false)
function createProblemEdit(problem: Problem): ProblemEdit {
  return {
    ...problem,
    file: {...problem.file},
    config: {...problem.config},
    description: problem.description ? {...problem.description} : {},
    image: problem.image ? {...problem.image} : {},
    alt: problem.image?.altText
  }
}
function openEdit() {
  editProblem.value = createProblemEdit(problem.value)
  confirmDeleteProblem.value = false
  error.value = null
  Modal.getOrCreateInstance("#problemModal").show()
}
async function submitEdit() {
  try {
    const prob = editProblem.value
    problem.value = await problemApi.editProblem({
      id: problem.value.id,
      problemEdit: {
        name: prob.name,
        context: prob.context,
        start: prob.start,
        end: prob.end,
        shortDescription: prob.shortDescription,
        alt: prob.alt,
        problemSchema: prob.problemSchema,
        solutionSchema: prob.solutionSchema,
        colour: prob.colour,
      }
    })
  } catch {
    error.value = "name"
    return
  }
  for (const key of ["file", "config", "description", "image"] as (keyof ProblemEdit)[]) {
    try {
      const editFile = editProblem.value[key] as DbFileEdit
      if (editFile.edit !== undefined) {
        problem.value = await problemApi.editProblemFile({
          id: problem.value.id,
          name: key as any,
          file: editFile.edit === null ? undefined : editFile.edit,
        })
      }
    } catch {
      error.value = "file"
      return
    }
  }
  Modal.getOrCreateInstance("#problemModal").hide()
}
function checkName() {
  const context = contexts.value[editProblem.value.context]
  if (!context) {
    return
  }
  try {
    problemApi.problemByName({contextName: context.name, problemName: editProblem.value.name})
    error.value = "name"
  } catch {
    error.value = null
  }
}
async function deleteProblem() {
  if (!confirmDeleteProblem.value) {
    confirmDeleteProblem.value = true
    return
  }
  problemApi.deleteProblem({id: problem.value.id})
  router.push("problems")
}

</script>

<template>
  <template v-if="error != 'problem'">
    <nav id="navbar" class="navbar bg-body-tertiary px-3 mb-3 sticky-top" style="top: 62px">
      <a class="navbar-brand" href="#">
        {{problem.name + (store.user.isAdmin ? ` (${contexts[problem.context]?.name})`: "")}}
      </a>
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
      <template v-if="ownDoc || store.user.isAdmin">
        <h4 id="documentation" class="mt-5">Documentation</h4>
        <a v-if="ownDoc && !store.user.isAdmin" role="button" class="btn btn-primary btn-sm mb-3" :href="ownDoc.file.location" title="Download documentation">Download documentation<i class="bi bi-download ms-1"></i></a>
        <table v-else class="table">
          <thead>
            <tr>
              <th>Team</th>
              <th>File</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(doc, id) in docs">
              <td>{{ teams[doc.team]?.name }}</td>
              <td>
                <a class="btn btn-primary btn-sm" :href="doc.file.location" title="Download file">Download <i class="bi bi-download ms-1"></i></a>
                <button role="button" class="btn btn-warning btn-sm ms-2" title="Edit" @click="(e) => openDocEdit(id as string)">Edit <i class="bi bi-pencil ms-1"></i></button>
              </td>
            </tr>
          </tbody>
        </table>
      </template>
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
  <div v-else class="alert alert-danger" role="alert">
    There is no problem with this name in this context.
    <button type="button" class="btn-close float-end" data-bs-dismiss="alert" aria-label="Close"></button>
  </div>

  <div class="modal fade" id="docModal" tabindex="-1" aria-labelledby="docLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable">
      <form class="modal-content" @submit.prevent="uploadDoc">
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
  
  <div class="modal fade" id="problemModal" tabindex="-1" aria-labelledby="modalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable">
      <form class="modal-content" @submit.prevent="submitEdit">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="modalLabel">Edit problem</h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body row">
          <div class="col-md-6">
            <div class="mb-3">
              <label for="context_sel" class="form-label">Context</label>
              <select class="form-select w-em" id="context_sel" name="context" required v-model="editProblem.context" @change="checkName">
                <option v-for="(context, id) in contexts" :value="id">{{context.name}}</option>
              </select>
              <div class="invalid-feedback">
              </div>
            </div>
            <div class="mb-3">
              <label for="start_time" class="form-label">Starting time</label>
              <input type="datetime-local" name="start" class="form-control w-em" id="start_time" v-model="editProblem.start"/>
            </div>
            <div class="mb-3">
              <label for="prob_schema" class="form-label">Problem schema</label>
              <textarea class="form-control" name="problem_schema" id="prob_schema" rows="10" v-model="editProblem.problemSchema"></textarea>
            </div>

          </div>
          <div class="col-md-6">
            <div class="mb-3">
              <label for="prob_name" class="form-label">Name</label>
              <input type="text" class="form-control w-em" name="name" id="prob_name" v-model="editProblem.name" required @input="checkName" :class="{'is-invalid': error == 'name'}"/>
              <div class="invalid-feedback">
                A problem with this name already exists in this context.
              </div>
            </div>
            <div class="mb-3">
              <label for="end_time" class="form-label">Ending time</label>
              <input type="datetime-local" name="end" class="form-control w-em" id="end_time" v-model="editProblem.end"/>
            </div>
            <div class="mb-3">
              <label for="sol_schema" class="form-label">Solution schema</label>
              <textarea class="form-control" name="solution_schema" id="sol_schema" rows="10" v-model="editProblem.solutionSchema"></textarea>
            </div>

          </div>

          <table class="table">
            <thead>
              <tr>
                <th scope="col"></th>
                <th scope="col">File</th>
                <th scope="col">Upload new file</th>
              </tr>
            </thead>
            <tbody>
              <FileEditRow :removable="false" :file="editProblem.file">Problem</FileEditRow>
              <FileEditRow :removable="false" :file="editProblem.config">Config</FileEditRow>
              <FileEditRow :removable="true" :file="editProblem.description">Description</FileEditRow>
              <FileEditRow :removable="true" :file="editProblem.image">Image</FileEditRow>
            </tbody>
          </table>

          <div class="col-md-6">
            <div class="mb-3">
              <label for="short_desc" class="form-label">Image alt text</label>
              <textarea class="form-control w-em" name="alt" id="alt_text" rows="5" v-model="editProblem.alt"></textarea>
            </div>
          </div>
          <div class="col-md-6">
            <div class="mb-3">
              <label for="short_desc" class="form-label">Short description</label>
              <textarea class="form-control w-em" name="short_description" id="short_desc" rows="5" v-model="editProblem.shortDescription"></textarea>
            </div>
          </div>
          <div class="mb-3">
            <label for="prob_col" class="form-label">Problem colour</label>
            <input type="color" name="colour" class="form-control form-control-color" id="prob_col" v-model="editProblem.colour"/>
          </div>
        </div>
        <div class="modal-footer">
          <button v-if="confirmDeleteProblem" type="button" class="btn btn-secondary" @click="(e) => confirmDeleteProblem = false">Cancel</button>
          <button type="button" class="btn btn-danger ms-2" @click="deleteProblem">
            {{confirmDeleteProblem ? "Confirm deletion" : "Delete Problem"}}
          </button>
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">Save</button>
        </div>
      </form>
    </div>
  </div>
</template>
