<script setup lang="ts">
import { store, type ModelDict, programApi, type InputFileEvent } from "@/main";
import { Modal } from "bootstrap";
import type { Problem, Program, AlgobattleWebModelsTeamSchema as Team, Role } from "typescript_client";
import type { UploadProgramRequest } from "typescript_client/apis/ProgramApi";
import { onMounted, ref } from "vue";

const programs = ref<ModelDict<Program>>({});
const problems = ref<ModelDict<Problem>>({});
const teams = ref<ModelDict<Team>>({});
const currPage = ref(1);
const maxPage = ref(1);
const searchData = ref({
  name: "",
  team: "",
  role: "",
  limit: 25,
})

async function search(
  page: number = 1
) {
  const ret = await programApi.searchProgram({page: page});
  programs.value = ret.programs;
  problems.value = ret.problems;
  teams.value = ret.teams;
  currPage.value = ret.page;
  maxPage.value = ret.maxPage;
}

const newProgData = ref<Partial<UploadProgramRequest>>({});
async function openModal() {
  Modal.getOrCreateInstance("#uploadProgram").show()
}
function selectFile(event: InputFileEvent) {
  const files = event.target.files || event.dataTransfer?.files
  if (files && files.length != 0) {
    newProgData.value.file = files[0]
  }
}
async function uploadProgram() {
  if (!newProgData.value.file || newProgData.value.file.size == 0
  || !newProgData.value.problem || !newProgData.value.role) {
    return
  }
  if (!newProgData.value.name) {
    newProgData.value.name = "";
  }
  const newProgram = await programApi.uploadProgram({
    name: newProgData.value.name,
    role: newProgData.value.role,
    problem: newProgData.value.problem,
    file: newProgData.value.file,
  });
  programs.value[newProgram.id] = newProgram;
}

onMounted(search);
</script>

<template>
  <table class="table table-hover mb-2" id="programs">
    <thead>
      <tr>
        <th scope="col">Problem</th>
        <th scope="col" v-if="store.user.isAdmin">Team</th>
        <th scope="col">Role</th>
        <th scope="col">Uploaded</th>
        <th scope="col">Name</th>
        <th scope="col">File</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="program in programs">
        <td>{{ problems[program.problem].name }}</td>
        <td v-if="store.user.isAdmin">{{ teams[program.team].name }}</td>
        <td>{{ program.role }}</td>
        <td>{{ program.creationTime.toLocaleString() }}</td>
        <td>{{ program.name }}</td>
        <td>
          <a role="button" class="btn btn-primary btn-sm" :href="program.file.location" title="Download program file">Download <i class="bi bi-download ms-1"></i></a>
        </td>
      </tr>
    </tbody>
  </table>

  <div class="d-flex mb-3 pe-2">
    <button type="button" class="btn btn-primary btn-sm me-auto" @click="openModal">Upload new program</button>
    <nav v-if="maxPage > 1" aria-label="Table pagination">
      <ul class="pagination pagination-sm justify-content-end mb-0 ms-2">
        <li class="page-item"><a class="page-link" :class="{disabled: currPage <= 1}" @click="e => search(1)"><i class="bi bi-chevron-double-left"></i></a></li>
        <li class="page-item"><a class="page-link" :class="{disabled: currPage <= 1}" @click="e => search(currPage - 1)"><i class="bi bi-chevron-compact-left"></i></a></li>
        <li class="page-item">currPage / maxPage</li>
        <li class="page-item"><a class="page-link" :class="{disabled: currPage >= maxPage}" @click="e => (currPage + 1)"><i class="bi bi-chevron-compact-right"></i></a></li>
        <li class="page-item"><a class="page-link" :class="{disabled: currPage >= maxPage}" @click="e => (maxPage)"><i class="bi bi-chevron-double-right"></i></a></li>
      </ul>
    </nav>
  </div>

  <div class="modal fade" id="uploadProgram" tabindex="-1" aria-labelledby="docLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable">
      <form class="modal-content" @submit.prevent="uploadProgram">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="docLabel">Upload program</h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body row">
          <div class="col-md-6">
            <div class="mb-3">
              <label for="problem_sel" class="form-label">Problem</label>
              <select class="form-select w-em" id="problem_sel" name="problem" required v-model="newProgData.problem">
                <option :value="undefined">Select problem</option>
                <option v-for="(problem, id) in problems" :value="id">{{problem.name}}</option>
              </select>
            </div>
            <div class="mb-3">
              <label for="prog_name" class="form-label">Name</label>
              <input type="text" class="form-control w-em" name="name" id="prog_name" v-model="newProgData.name"/>
            </div>
          </div>
          <div class="col-md-6">
            <div class="mb-3">
              <label for="role_sel" class="form-label">Role</label>
              <select class="form-select w-em" id="role_sel" name="role" required v-model="newProgData.role">
                <option :value="undefined">Select role</option>
                <option value="generator">Generator</option>
                <option value="solver">Solver</option>
              </select>
            </div>
            <div class="mb-3">  
              <label for="file_select" class="form-label mt-3">Select new program file</label>
              <input type="file" class="form-control w-em" id="file_select" @change="(e) => selectFile(e as any)"/>
            </div>
          </div>

        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">Upload</button>
        </div>
      </form>
    </div>
  </div>
</template>
