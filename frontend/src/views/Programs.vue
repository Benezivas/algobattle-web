<script setup lang="ts">
import { ProgramService, Role } from "@client";
import { store, type ModelDict } from "@/main";
import { Modal } from "bootstrap";
import type { Problem, Program, Team } from "@client";
import { onMounted, ref } from "vue";
import FileInput from "@/components/FileInput.vue";

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
});

async function search(page: number = 1) {
  const ret = await ProgramService.searchProgram({ page: page });
  programs.value = ret.programs;
  problems.value = ret.problems;
  teams.value = ret.teams;
  currPage.value = ret.page;
  maxPage.value = ret.max_page;
}

const newProgData = ref<{
  name?: string;
  role?: Role;
  problem?: string;
  file?: File;
}>({
  name: "",
});
let modal: Modal;
async function openModal() {
  newProgData.value = {
    name: "",
  };
  modal.show();
}

async function uploadProgram() {
  if (
    !newProgData.value.file ||
    newProgData.value.file.size == 0 ||
    !newProgData.value.problem ||
    !newProgData.value.role
  ) {
    return;
  }
  const newProgram = await ProgramService.uploadProgram({
    role: newProgData.value.role,
    problem: newProgData.value.problem,
    formData: {
      file: newProgData.value.file,
    },
  });
  programs.value[newProgram.id] = newProgram;
  modal.hide();
}

onMounted(() => {
  search();
  modal = Modal.getOrCreateInstance("#uploadProgram");
});
</script>

<template>
  <table class="table table-hover mb-2" id="programs">
    <thead>
      <tr>
        <th scope="col">Problem</th>
        <th scope="col" v-if="store.user.is_admin">Team</th>
        <th scope="col">Role</th>
        <th scope="col">Uploaded</th>
        <th scope="col">Name</th>
        <th scope="col">File</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(program, id) in programs" :key="id">
        <td>{{ problems[program.problem].name }}</td>
        <td v-if="store.user.is_admin">{{ teams[program.team].name }}</td>
        <td>{{ program.role }}</td>
        <td>{{ program.creation_time.toLocaleString() }}</td>
        <td>{{ program.name }}</td>
        <td>
          <a
            role="button"
            class="btn btn-primary btn-sm"
            :href="program.file.location"
            title="Download program file"
            >Download <i class="bi bi-download ms-1"></i
          ></a>
        </td>
      </tr>
    </tbody>
  </table>

  <div class="d-flex mb-3 pe-2">
    <button type="button" class="btn btn-primary btn-sm me-auto" @click="openModal">
      Upload new program
    </button>
    <nav v-if="maxPage > 1" aria-label="Table pagination">
      <ul class="pagination pagination-sm justify-content-end mb-0 ms-2">
        <li class="page-item">
          <a class="page-link" :class="{ disabled: currPage <= 1 }" @click="(e) => search(1)"
            ><i class="bi bi-chevron-double-left"></i
          ></a>
        </li>
        <li class="page-item">
          <a class="page-link" :class="{ disabled: currPage <= 1 }" @click="(e) => search(currPage - 1)"
            ><i class="bi bi-chevron-compact-left"></i
          ></a>
        </li>
        <li class="page-item">currPage / maxPage</li>
        <li class="page-item">
          <a class="page-link" :class="{ disabled: currPage >= maxPage }" @click="(e) => currPage + 1"
            ><i class="bi bi-chevron-compact-right"></i
          ></a>
        </li>
        <li class="page-item">
          <a class="page-link" :class="{ disabled: currPage >= maxPage }" @click="(e) => maxPage"
            ><i class="bi bi-chevron-double-right"></i
          ></a>
        </li>
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
              <select
                class="form-select"
                id="problem_sel"
                name="problem"
                required
                v-model="newProgData.problem"
              >
                <option v-for="(problem, id) in problems" :value="id">{{ problem.name }}</option>
              </select>
            </div>
            <div class="mb-3">
              <label for="prog_name" class="form-label">Name</label>
              <input
                type="text"
                class="form-control "
                name="name"
                id="prog_name"
                v-model="newProgData.name"
              />
            </div>
          </div>
          <div class="col-md-6">
            <div class="mb-3">
              <label for="role_sel" class="form-label">Role</label>
              <select class="form-select" id="role_sel" name="role" required v-model="newProgData.role">
                <option value="generator">Generator</option>
                <option value="solver">Solver</option>
              </select>
            </div>
            <div class="mb-3">
              <label for="file_select" class="form-label mt-3">Select new program file</label>
              <FileInput
                id="file_select"
                v-model="newProgData.file"
                required
              />
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
