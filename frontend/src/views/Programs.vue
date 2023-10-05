<script setup lang="ts">
import { ProgramService, Role } from "@client";
import { store, type ModelDict } from "@/main";
import { Modal } from "bootstrap";
import type { Problem, Program, Team } from "@client";
import { onMounted, ref } from "vue";
import FileInput from "@/components/FileInput.vue";
import Paginator from "@/components/Paginator.vue";

const programs = ref<ModelDict<Program>>({});
const problems = ref<ModelDict<Problem>>({});
const teams = ref<ModelDict<Team>>({});
const total = ref(0);
const searchData = ref({
  name: null,
  team: null,
  role: null,
});

async function search(offset: number = 0) {
  const ret = await ProgramService.get({offset: offset });
  programs.value = ret.programs;
  problems.value = ret.problems;
  teams.value = ret.teams;
  total.value = ret.total;
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
  const newProgram = await ProgramService.create({
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
  <template v-if="store.tournament">
    <table v-if="Object.keys(programs).length !== 0" class="table table-hover mb-2" id="programs">
      <thead>
        <tr>
          <th scope="col">Problem</th>
          <th scope="col" v-if="store.team == 'admin'">Team</th>
          <th scope="col">Role</th>
          <th scope="col">Uploaded</th>
          <th scope="col">Name</th>
          <th scope="col">File</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(program, id) in programs" :key="id">
          <td>{{ problems[program.problem].name }}</td>
          <td v-if="store.team == 'admin'">{{ teams[program.team].name }}</td>
          <td>{{ program.role }}</td>
          <td>{{ new Date(program.creation_time).toLocaleString() }}</td>
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
    <div v-else class="alert alert-info" role="alert">
      There aren't any programs uploaded already.
    </div>

    <div class="d-flex mb-3 pe-2">
      <button v-if="store.team !== 'admin'" type="button" class="btn btn-primary btn-sm me-auto" @click="openModal">
        Upload new program
      </button>
      <Paginator :total="total" @update="search"/>
    </div>
  </template>
  <div v-else-if="!store.user" class="alert alert-danger" role="alert">
    You need to log in before you can view the programs.
  </div>
  <div v-else class="alert alert-danger" role="alert">
    You need to select a team before you can view your teams programs.
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
                maxlength="32"
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
