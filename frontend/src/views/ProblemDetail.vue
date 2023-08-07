<script setup lang="ts">
import { Modal } from "bootstrap"
import { store } from "../main"
import { TournamentService, DocsService, ProblemService, TeamService, ApiError } from "../../typescript_client";
import type { Tournament, Documentation, DbFile, Problem, Team } from '../../typescript_client';
import type { DbFileLoc, InputFileEvent } from '@/main';
import { computed, onMounted, ref, type Ref } from 'vue';
import { useRoute } from 'vue-router';
import router from "@/router";
import FileEditRow from "@/components/FileEditRow.vue";


interface DbFileEdit {
  location?: string,
  edit?: File | null,
}
interface ProblemEdit {
  name: string,
  tournament: string,
  file: DbFileEdit,
  config: DbFileEdit,
  start?: string | null,
  end?: string | null,
  description: DbFileEdit,
  short_description: string,
  image: DbFileEdit,
  alt?: string,
  problem_schema?: string,
  solution_schema?: string,
  colour: string,
}

const problem = ref({} as Problem)
const tournaments: Ref<{
    [key: string]: Tournament
}> = ref({})
const selectedTeam: Ref<Team | null> = ref(null)
const docs: Ref<{[key: string]: Documentation}> = ref({})
const description: Ref<string | null> = ref(null)
const teams: Ref<{[key: string]: Team}> = ref({})

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
const now = new Date()


onMounted(async () => {
  selectedTeam.value = store.user.settings.selected_team
  try {
    const problemInfo = await ProblemService.problemByName({
      problemName: route.params.problemName as string,
      tournamentName: route.params.tournamentName as string,
    })
    problem.value = problemInfo.problem
    if (store.user.is_admin) {
      tournaments.value = await TournamentService.allTournaments()
    } else {
      tournaments.value = {[problemInfo.tournament.id]: problemInfo.tournament}
    }
    docs.value = await DocsService.getDocs({requestBody: {problem: problem.value.id}})
    description.value = (await ProblemService.problemDesc({id: problem.value.id})).data
    teams.value = await TeamService.getTeams({requestBody: Object.values(docs.value).map((doc) => doc.team)})
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
  } else if (store.user.settings.selected_team) {
    editDoc.problem = problem.value.id
    editDoc.team = store.user.settings.selected_team.id
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
  if (store.user.is_admin) {
    newDoc = await DocsService.uploadDocs({problemId: editDoc.problem, teamId: editDoc.team, formData: { file: editDoc.newFile } })
  } else {
    newDoc = await DocsService.uploadOwnDocs({problemId: editDoc.problem, formData: { file: editDoc.newFile } })
  }
  docs.value[newDoc.id] = newDoc
  if (editDoc.fileSelect.value) {
    editDoc.fileSelect.value.value = ""
  }
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
  if (store.user.is_admin) {
    DocsService.deleteAdminDocs({teamId: editDoc.team, problemId: editDoc.problem})
  } else {
    DocsService.deleteOwnDocs({problemId: editDoc.problem})
  }
  editDoc.confirmDelete.value = false
  if (editDoc.fileSelect.value) {
    editDoc.fileSelect.value.value = ""
  }
  delete docs.value[editDoc.docId.value]
  Modal.getOrCreateInstance("#docModal").hide()
}
function docEditable() {
  return (
    selectedTeam.value?.tournament === problem.value.tournament
    && (store.user.is_admin || !problem.value.end || new Date(problem.value.end) >= now)
  )
}

let editProblem = ref(createProblemEdit(problem.value))
let confirmDeleteProblem = ref(false)
function createProblemEdit(problem: Problem): ProblemEdit {
  return {
    ...problem,
    problem_schema: problem.problem_schema || "",
    solution_schema: problem.solution_schema || "",
    file: {location: (problem.file as DbFileLoc).location},
    config: {location: (problem.config as DbFileLoc).location},
    description: problem.description ? {location: (problem.description as DbFileLoc).location} : {},
    image: problem.image ? {location: (problem.image as DbFileLoc)?.location} : {},
    alt: problem.image?.alt_text
  }
}
function openEdit() {
  editProblem.value = createProblemEdit(problem.value)
  confirmDeleteProblem.value = false
  error.value = null
  Modal.getOrCreateInstance("#problemModal").show()
}
async function submitEdit() {
  //try {
    const prob = editProblem.value
    problem.value = await ProblemService.editProblem({
      id: problem.value.id,
      requestBody: {
        name: prob.name,
        tournament: prob.tournament,
        start: prob.start,
        end: prob.end,
        short_description: prob.short_description,
        alt: prob.alt,
        problem_schema: prob.problem_schema,
        solution_schema: prob.solution_schema,
        colour: prob.colour,
      }
    })
  /*} catch {
    throw
    error.value = "name"
    return
  }*/
  for (const key of ["file", "config", "description", "image"] as (keyof ProblemEdit)[]) {
    try {
      const editFile = editProblem.value[key] as DbFileEdit
      if (editFile.edit !== undefined) {
        problem.value = await ProblemService.editProblemFile({
          id: problem.value.id,
          formData: {
            name: key as any,
            file: editFile.edit === null ? undefined : editFile.edit,
          }
        })
      }
    } catch {
      error.value = "file"
      return
    }
  }
  Modal.getOrCreateInstance("#problemModal").hide()
}
async function checkName() {
  const tournament = tournaments.value[editProblem.value.tournament]
  if (!tournament) {
    return
  }
  try {
    const prob = await ProblemService.problemByName({tournamentName: tournament.name, problemName: editProblem.value.name})
    if (prob.problem.id != problem.value.id) {
      error.value = "name"
      return
    }
  } catch {}
  error.value = null
}
async function deleteProblem() {
  if (!confirmDeleteProblem.value) {
    confirmDeleteProblem.value = true
    return
  }
  ProblemService.deleteProblem({id: problem.value.id})
  router.push("problems")
}

</script>

<template>
  <template v-if="error != 'problem'">
    <nav id="navbar" class="navbar bg-body-tertiary px-3 mb-3">
      <a class="navbar-brand" href="#">
        {{problem.name + (store.user.is_admin ? ` (${tournaments[problem.tournament]?.name})`: "")}}
      </a>
      <ul class="nav nav-pills">
        <li v-if="problem.description" class="nav-item">
          <a class="nav-link" href="#description">Description</a>
        </li>
        <li v-if="store.user.is_admin || ownDoc" class="nav-item">
          <a class="nav-link" href="#documentation">Documentation</a>
        </li>
        <li v-if="problem.problem_schema" class="nav-item">
          <a class="nav-link" href="#problem_schema">Problem schema</a>
        </li>
        <li v-if="problem.solution_schema" class="nav-item">
          <a class="nav-link" href="#solution_schema">Solution schema</a>
        </li>
      </ul>
    </nav>
    <div data-bs-spy="scroll" data-bs-target="#navbar" data-bs-root-margin="0px 0px -40%" data-bs-smooth-scroll="true" class="bg-body-tertiary p-3 rounded-2" tabindex="0">
      <div class="row">
        <div class="col-md-9">
          <img v-if="problem.image" :src="(problem.image as DbFileLoc).location" :alt="problem.image.alt_text" class="object-fit-cover border rounded mb-4" style="width: 100%;">
        </div>
        <div class="col-md-3">
          <ul class="list-group list-group-flush bg-body-tertiary w-em">
            <li class="list-group-item bg-body-tertiary">{{problem.name}}</li>
            <li v-if="store.user.is_admin" class="list-group-item bg-body-tertiary">{{tournaments[problem.tournament]?.name}}</li>
            <li v-if="problem.short_description" class="list-group-item bg-body-tertiary">{{ problem.short_description }}</li>
            <li v-if="problem.start" class="list-group-item bg-body-tertiary">Start: {{problem.start.toLocaleString()}}</li>
            <li v-if="problem.end" class="list-group-item bg-body-tertiary">End: {{problem.end.toLocaleString()}}</li>
            <li class="list-group-item bg-body-tertiary">
              <a role="button" class="btn btn-primary btn-sm" :href="`/api/problem/${problem.id}/download_all`" title="Download problem files">Download problem files <i class="bi bi-download ms-1"></i></a>
            </li>
            <li v-if="store.user.is_admin" class="list-group-item bg-body-tertiary">
              <button role="button" class="btn btn-warning btn-sm" title="Edit problem" @click="openEdit">Edit problem<i class="bi bi-pencil ms-1"></i></button>
            </li>
            <li v-if="docEditable()" class="list-group-item bg-body-tertiary">
              <button role="button" class="btn btn-warning btn-sm" title="Edit documentation" @click="(e) => openDocEdit(null)">Edit documentation<i class="bi bi-pencil ms-1"></i></button>
            </li>
          </ul>
        </div>
      </div>
      <template v-if="problem.description">
        <h4 id="description" class="mt-5">Description</h4>
        <a v-if="description == '__DOWNLOAD_BUTTON__'" role="button" class="btn btn-primary btn-sm" :href="(problem.description as DbFileLoc).location" title="Download file">Download description file <i class="bi bi-download ms-1"></i></a>
        <div v-else v-html="description"></div>
      </template>
      <template v-if="ownDoc || store.user.is_admin">
        <h4 id="documentation" class="mt-5">Documentation</h4>
        <a v-if="ownDoc && !store.user.is_admin" role="button" class="btn btn-primary btn-sm mb-3" :href="(ownDoc.file as DbFileLoc).location" title="Download documentation">Download documentation<i class="bi bi-download ms-1"></i></a>
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
                <a class="btn btn-primary btn-sm" :href="(doc.file as DbFileLoc).location" title="Download file">Download <i class="bi bi-download ms-1"></i></a>
                <button role="button" class="btn btn-warning btn-sm ms-2" title="Edit" @click="(e) => openDocEdit(id as string)">Edit <i class="bi bi-pencil ms-1"></i></button>
              </td>
            </tr>
          </tbody>
        </table>
      </template>
      <template v-if="problem.problem_schema">
        <h4 id="problem_schema" class="mt-5">Problem schema</h4>
        <pre><code>{{problem.problem_schema}}</code></pre>
      </template>
      <template v-if="problem.solution_schema">
        <h4 id="solution_schema" class="mt-5">Solution schema</h4>
        <pre><code>{{problem.solution_schema}}</code></pre>
      </template>
    </div>
  </template>
  <div v-else class="alert alert-danger" role="alert">
    There is no problem with this name in this tournament.
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
      <form class="modal-content" @submit.prevent="submitEdit" novalidate>
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="modalLabel">Edit problem</h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body row">
          <div class="col-md-6">
            <div class="mb-3">
              <label for="tournament_sel" class="form-label">Tournament</label>
              <select class="form-select w-em" id="tournament_sel" name="tournament" required v-model="editProblem.tournament" @change="checkName">
                <option v-for="(tournament, id) in tournaments" :value="id">{{tournament.name}}</option>
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
              <textarea class="form-control" name="problem_schema" id="prob_schema" rows="10" v-model="editProblem.problem_schema"></textarea>
            </div>

          </div>
          <div class="col-md-6">
            <div class="mb-3">
              <label for="prob_name" class="form-label">Name</label>
              <input type="text" class="form-control w-em" name="name" id="prob_name" v-model="editProblem.name" required @input="checkName" :class="{'is-invalid': error == 'name'}"/>
              <div class="invalid-feedback">
                A problem with this name already exists in this tournament.
              </div>
            </div>
            <div class="mb-3">
              <label for="end_time" class="form-label">Ending time</label>
              <input type="datetime-local" name="end" class="form-control w-em" id="end_time" v-model="editProblem.end"/>
            </div>
            <div class="mb-3">
              <label for="sol_schema" class="form-label">Solution schema</label>
              <textarea class="form-control" name="solution_schema" id="sol_schema" rows="10" v-model="editProblem.solution_schema"></textarea>
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
              <textarea class="form-control w-em" name="short_description" id="short_desc" rows="5" v-model="editProblem.short_description"></textarea>
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
