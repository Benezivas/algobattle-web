<script setup lang="ts">
import { Modal } from "bootstrap";
import { store } from "../main";
import { TournamentService, ReportService, ProblemService, TeamService, ApiError } from "@client";
import type { Tournament, Report, DbFile, Problem, Team, ProblemPageData } from "@client";
import type { InputFileEvent, ModelDict } from "@/main";
import { computed, onMounted, ref, type Ref } from "vue";
import { useRoute } from "vue-router";
import router from "@/router";
import FileEditRow from "@/components/FileEditRow.vue";
import type { DbFileEdit } from "@/components/FileEditRow.vue";

interface ProblemEdit extends Omit<Problem, "file" | "image"> {
  file: DbFileEdit;
  image: DbFileEdit;
  alt: string;
}

const problem = ref<Problem>();
const pageData = ref<ProblemPageData | null>(null);
const tournaments: Ref<{
  [key: string]: Tournament;
}> = ref({});
const reports = ref<ModelDict<Report>>({});
const teams = ref<ModelDict<Team>>({});

const route = useRoute();
const error = ref(null as null | string);
const now = new Date();

onMounted(async () => {
  const problems = await ProblemService.get({
    name: route.params.problemName as string,
    tournamentName: route.params.tournamentName as string,
  });
  if (Object.values(problems).length === 1) {
    problem.value = Object.values(problems)[0];
  } else {
    return;
  }
  pageData.value = await ProblemService.pageData({ id: problem.value.id });
  if (store.team == "admin") {
    tournaments.value = await TournamentService.get({});
  }
  const ret = await ReportService.get({ problem: problem.value.id });
  reports.value = Object.fromEntries(Object.values(ret.reports).map((report) => [report.team, report]));
  teams.value = (await TeamService.get({ tournament: problem.value.tournament.id })).teams;
});

const editReport = {
  team: null as Team | null,
  newFile: null as File | null,
  fileSelect: ref<HTMLInputElement | null>(null),
  confirmDelete: ref(false),
};
function selectFile(event: InputFileEvent) {
  const files = event.target.files || event.dataTransfer?.files;
  if (files && files.length != 0) {
    editReport.newFile = files[0];
  }
}
async function openReportEdit(team: Team) {
  editReport.team = team;
  editReport.confirmDelete.value = false;
  editReport.newFile = null;
  if (editReport.fileSelect.value) {
    editReport.fileSelect.value.value = "";
  }
  Modal.getOrCreateInstance("#reportModal").show();
}
async function uploadReport() {
  if (!editReport.newFile || editReport.newFile.size == 0 || !problem.value || !editReport.team) {
    return;
  }
  var newReport = null;
  newReport = await ReportService.upload({
    problem: problem.value.id,
    team: editReport.team.id,
    formData: { file: editReport.newFile },
  });
  reports.value[newReport.team] = newReport;
  if (editReport.fileSelect.value) {
    editReport.fileSelect.value.value = "";
  }
  Modal.getOrCreateInstance("#reportModal").hide();
}
async function removeReport() {
  if (!problem.value || !editReport.team) {
    return;
  }
  if (!editReport.confirmDelete.value) {
    editReport.confirmDelete.value = true;
    return;
  }
  ReportService.delete({ problem: problem.value.id, team: editReport.team.id });
  editReport.confirmDelete.value = false;
  if (editReport.fileSelect.value) {
    editReport.fileSelect.value.value = "";
  }
  delete reports.value[editReport.team.id];
  Modal.getOrCreateInstance("#reportModal").hide();
}
function reportEditable() {
  return store.team != "admin" || !problem.value?.end || new Date(problem.value.end) >= now;
}

let editProblem = ref<ProblemEdit>();
let confirmDeleteProblem = ref(false);
function createProblemEdit(problem: Problem): ProblemEdit {
  return {
    ...problem,
    start: problem?.start?.slice(0, 19),
    end: problem?.end?.slice(0, 19),
    file: { location: problem.file.location },
    image: problem.image ? { location: problem.image?.location } : {},
    alt: problem.image?.alt_text || "",
  };
}
function openEdit() {
  editProblem.value = createProblemEdit(problem.value!);
  confirmDeleteProblem.value = false;
  error.value = null;
  Modal.getOrCreateInstance("#problemModal").show();
}
async function submitEdit() {
  const prob = editProblem.value!;
  problem.value = await ProblemService.edit({
    id: problem.value!.id,
    formData: {
      name: prob.name,
      tournament: prob.tournament.id,
      start: prob.start,
      end: prob.end,
      description: prob.description,
      alt_text: prob.alt,
      colour: prob.colour,
      file: prob.file.edit,
      image: prob.image.edit,
    },
  });
  Modal.getOrCreateInstance("#problemModal").hide();
}
async function checkName() {
  const tournament = editProblem.value!.tournament;
  try {
    const probs = Object.values(
      await ProblemService.get({
        tournament: tournament.name,
        name: editProblem.value!.name,
      })
    );
    if (probs.length != 1 || probs[0].id != problem.value!.id) {
      error.value = "name";
      return;
    }
  } catch {}
  error.value = null;
}
async function deleteProblem() {
  if (!confirmDeleteProblem.value) {
    confirmDeleteProblem.value = true;
    return;
  }
  await ProblemService.delete({ id: problem.value!.id });
  Modal.getOrCreateInstance("#problemModal").hide();
  router.push({ name: "problems" });
}
</script>

<template>
  <template v-if="error != 'problem' && problem">
    <nav id="navbar" class="navbar bg-body-tertiary px-3 mb-3">
      <a class="navbar-brand" href="#">
        {{ problem.name }}
      </a>
      <ul class="nav nav-pills">
        <li v-if="pageData?.description" class="nav-item">
          <a class="nav-link" href="#description">Description</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#config">Config</a>
        </li>
        <li v-if="store.team === 'admin'" class="nav-item">
          <a class="nav-link" href="#reports">Reports</a>
        </li>
        <li v-else-if="store.team" class="nav-item">
          <a class="nav-link" href="#report">Report</a>
        </li>
        <li v-if="pageData?.instance_schema" class="nav-item">
          <a class="nav-link" href="#instance_schema">Instance schema</a>
        </li>
        <li v-if="pageData?.solution_schema" class="nav-item">
          <a class="nav-link" href="#solution_schema">Solution schema</a>
        </li>
      </ul>
    </nav>
    <div
      data-bs-spy="scroll"
      data-bs-target="#navbar"
      data-bs-root-margin="0px 0px -40%"
      data-bs-smooth-scroll="true"
      class="bg-body-tertiary p-3 rounded-2"
      tabindex="0"
    >
      <div class="row">
        <div class="col-md-9">
          <img
            v-if="problem.image"
            :src="problem.image.location"
            :alt="problem.image.alt_text"
            class="object-fit-cover border rounded mb-4"
            style="width: 100%"
          />
        </div>
        <div class="col-md-3">
          <ul class="list-group list-group-flush bg-body-tertiary w-em">
            <li class="list-group-item bg-body-tertiary">{{ problem.name }}</li>
            <li v-if="store.team == 'admin'" class="list-group-item bg-body-tertiary">
              {{ problem.tournament.name }}
            </li>
            <li v-if="problem.description" class="list-group-item bg-body-tertiary">
              {{ problem.description }}
            </li>
            <li v-if="problem.start" class="list-group-item bg-body-tertiary">
              Start: {{ new Date(problem.start).toLocaleString() }}
            </li>
            <li v-if="problem.end" class="list-group-item bg-body-tertiary">
              End: {{ new Date(problem.end).toLocaleString() }}
            </li>
            <li class="list-group-item bg-body-tertiary">
              <a
                role="button"
                class="btn btn-primary btn-sm"
                :href="problem.file.location"
                title="Download problem files"
                >Download problem spec file <i class="bi bi-download ms-1"></i
              ></a>
            </li>
            <li v-if="store.team == 'admin'" class="list-group-item bg-body-tertiary">
              <button role="button" class="btn btn-warning btn-sm" title="Edit problem" @click="openEdit">
                Edit problem<i class="bi bi-pencil ms-1"></i>
              </button>
            </li>
          </ul>
        </div>
      </div>
      <template v-if="pageData?.description">
        <h4 id="description" class="mt-5">Description</h4>
        <div v-html="pageData.description"></div>
      </template>
      <template v-if="pageData">
        <h4 id="config" class="mt-5">Config</h4>
        <pre><code>{{pageData.config}}</code></pre>
      </template>
      <template v-if="store.team !== 'admin'">
        <h4 id="report" class="mt-5">Report</h4>
        <a
          v-if="store.team?.id && store.team?.id in reports"
          role="button"
          class="btn btn-primary mb-3 me-3"
          :href="reports[store.team.id].file.location"
          title="Download report"
          >Download report<i class="bi bi-download ms-1"></i
        ></a>
        <button
          v-if="reportEditable() && store.team"
          role="button"
          class="btn btn-warning mb-3"
          title="Edit report"
          @click="(e) => openReportEdit(store.team as any)"
        >
          Edit report<i class="bi bi-pencil ms-1"></i>
        </button>
      </template>
      <template v-else>
        <h4 id="reports" class="mt-5">Reports</h4>
        <table class="table">
          <thead>
            <tr>
              <th>Team</th>
              <th>File</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(team, id) in teams" :key="id">
              <td>{{ team.name }}</td>
              <td>
                <a
                  v-if="reports[id]"
                  class="btn btn-primary btn-sm me-2"
                  :href="reports[id].file.location"
                  title="Download file"
                  >Download <i class="bi bi-download ms-1"></i
                ></a>
                <button
                  role="button"
                  class="btn btn-warning btn-sm"
                  title="Edit"
                  @click="(e) => openReportEdit(team)"
                >
                  Edit <i class="bi bi-pencil ms-1"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </template>
      <template v-if="pageData?.instance_schema">
        <h4 id="instance_schema" class="mt-5">Instance schema</h4>
        <pre><code>{{pageData.instance_schema}}</code></pre>
      </template>
      <template v-if="pageData?.instance_schema">
        <h4 id="solution_schema" class="mt-5">Solution schema</h4>
        <pre><code>{{pageData.solution_schema}}</code></pre>
      </template>
    </div>
  </template>
  <div v-else class="alert alert-danger" role="alert">
    There is no problem with this name in this tournament.
    <button type="button" class="btn-close float-end" data-bs-dismiss="alert" aria-label="Close"></button>
  </div>

  <div class="modal fade" id="reportModal" tabindex="-1" aria-labelledby="reportLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable">
      <form class="modal-content" @submit.prevent="uploadReport">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="reportLabel">Edit report</h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body row">
          <label for="file_select" class="form-label mt-3">Select new file</label>
          <input
            type="file"
            class="form-control"
            id="file_select"
            ref="editReport.fileSelect"
            @change="(e) => selectFile(e as any)"
          />
        </div>
        <div class="modal-footer">
          <button
            v-if="editReport.confirmDelete.value"
            type="button"
            class="btn btn-secondary"
            @click="(e) => (editReport.confirmDelete.value = false)"
          >
            Cancel
          </button>
          <button v-if="editReport.team" type="button" class="btn btn-danger ms-2" @click="removeReport">
            {{ editReport.confirmDelete.value ? "Confirm deletion" : "Delete report" }}
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
        <div class="modal-body row" v-if="editProblem">
          <div class="col-md-6">
            <div class="mb-3">
              <label for="tournament_sel" class="form-label">Tournament</label>
              <select
                class="form-select"
                id="tournament_sel"
                name="tournament"
                required
                v-model="editProblem.tournament"
                @change="checkName"
              >
                <option v-for="(tournament, id) in tournaments" :value="tournament">{{ tournament.name }}</option>
              </select>
              <div class="invalid-feedback"></div>
            </div>
            <div class="mb-3">
              <label for="start_time" class="form-label">Starting time</label>
              <input
                type="datetime-local"
                name="start"
                class="form-control"
                id="start_time"
                v-model="editProblem.start"
              />
            </div>
          </div>
          <div class="col-md-6">
            <div class="mb-3">
              <label for="prob_name" class="form-label">Name</label>
              <input
                type="text"
                class="form-control"
                name="name"
                id="prob_name"
                v-model="editProblem.name"
                required
                autocomplete="off"
                @input="checkName"
                :class="{ 'is-invalid': error == 'name' }"
              />
              <div class="invalid-feedback">A problem with this name already exists in this tournament.</div>
            </div>
            <div class="mb-3">
              <label for="end_time" class="form-label">Ending time</label>
              <input
                type="datetime-local"
                name="end"
                class="form-control"
                id="end_time"
                v-model="editProblem.end"
              />
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
              <FileEditRow :removable="true" :file="editProblem.image">Image</FileEditRow>
            </tbody>
          </table>

          <div class="col-md-6">
            <div class="mb-3">
              <label for="alt_text" class="form-label">Image alt text</label>
              <textarea
                class="form-control"
                name="alt"
                id="alt_text"
                rows="5"
                maxlength="256"
                v-model="editProblem.alt"
              ></textarea>
            </div>
          </div>
          <div class="col-md-6">
            <div class="mb-3">
              <label for="short_desc" class="form-label">Description</label>
              <textarea
                class="form-control"
                name="description"
                id="short_desc"
                rows="5"
                maxlength="256"
                v-model="editProblem.description"
              ></textarea>
            </div>
          </div>
          <div class="mb-3">
            <label for="prob_col" class="form-label">Problem colour</label>
            <input
              type="color"
              name="colour"
              class="form-control form-control-color"
              id="prob_col"
              v-model="editProblem.colour"
            />
          </div>
        </div>
        <div class="modal-footer">
          <button
            v-if="confirmDeleteProblem"
            type="button"
            class="btn btn-secondary"
            @click="(e) => (confirmDeleteProblem = false)"
          >
            Cancel
          </button>
          <button type="button" class="btn btn-danger ms-2" @click="deleteProblem">
            {{ confirmDeleteProblem ? "Confirm deletion" : "Delete Problem" }}
          </button>
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">Save</button>
        </div>
      </form>
    </div>
  </div>
</template>
