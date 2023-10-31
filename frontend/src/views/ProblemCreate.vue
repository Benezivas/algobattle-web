<script setup lang="ts">
import FileInput from "../components/FileInput.vue";
import { ProblemService } from "@client";
import router from "@/router";
import type { Problem } from "@client";
import { computed, onMounted, ref, watch } from "vue";
import { store } from "@/shared";

const page = ref(0);
const error = ref<{
  type?: string;
  detail?: string;
}>({});
const problems = ref<{ [key: string]: Problem }>({});
const data = ref({
  file: undefined as File | undefined,
  copyFrom: undefined as string | undefined,

  name: "",
  start: undefined as string | undefined,
  end: undefined as string | undefined,
  image: undefined as File | undefined,
  alt: "",
  description: "",
  color: "#000000",
});
const imageUrl = computed(() => {
  if (data.value.image) {
    return URL.createObjectURL(data.value.image);
  }
});

onMounted(async () => {
  problems.value = await ProblemService.get({ tournament: store.tournament?.id });
});

async function createProblem() {
  if (!store.tournament) {
    return;
  }
  try {
    const { file, copyFrom, ...payload } = data.value;
    const location = await ProblemService.create({
      formData: { ...payload, problem: file || copyFrom!, tournament: store.tournament.id },
    });
    router.push(location);
  } catch {
    error.value.type = "server";
  }
}
function checkName() {
  if (Object.values(problems.value).filter((prob) => prob.name == data.value.name).length != 0) {
    error.value.type = "name";
  } else {
    error.value = {};
  }
}

watch(() => data.value.file, () => data.value.copyFrom = undefined);
</script>

<template>
  <div class="container">
    <div class="row justify-content-center">
      <div class="col mx-0" style="max-width: 40rem">
        <h2 class="mb-5 text-center"><strong>Create new problem</strong></h2>
        <ul id="progressbar" class="text-center ps-0">
          <li class="first" :class="{ active: page == 0, set: page > 0 }">
            <i class="bi bi-file-earmark-code progress-icon"></i>
            <strong>Problem</strong>
          </li>
          <li :class="{ active: page == 1, set: page > 1 }">
            <i class="bi bi-gear progress-icon"></i>
            <strong>Settings</strong>
          </li>
          <li :class="{ active: page == 2, set: page > 2 }">
            <i class="bi bi-image progress-icon"></i>
            <strong>Display</strong>
          </li>
        </ul>
        <div class="card">
          <form v-if="page == 0" id="file_form" class="card-body" @submit.prevent="page++" novalidate>
            <div class="alert alert-danger" role="alert" v-if="error.type == 'missing'">
              Select either a problem file to upload, or an already existing problem to copy.
            </div>
            <div class="alert alert-danger" role="alert" v-if="error.type == 'duplicate'">
              You can only select one source for the problem file at once.
            </div>
            <div class="alert alert-danger" role="alert" v-if="error.type == 'file'">
              The uploaded file does not contain a valid problem class.<br />
              {{ error.detail }}
            </div>
            <label for="prob_file" class="form-label">Upload a new problem file</label>
            <FileInput
              class="w-em mb-2"
              id="prob_file"
              v-model="data.file"
              accept=".algo"
            />
            <label for="prob_select" class="form-label">Or copy an already existing one</label>
            <select
              class="form-select"
              id="prob_select"
              @change="(e) => (data.file = undefined)"
              v-model="data.copyFrom"
            >
              <option selected value=""></option>
              <option v-for="(problem, id) in problems" :value="id">
                {{ problem.name + ` (${problem.tournament.name})` }}
              </option>
            </select>
            <div class="d-flex mt-3">
              <button v-if="data.copyFrom || data.file" class="btn btn-primary ms-auto" type="submit">
                Next
              </button>
            </div>
          </form>

          <form
            v-if="page == 1"
            id="settings_form"
            ref="settings_form"
            class="card-body"
            @submit.prevent="(e) => page++"
          >
            <div class="mb-3">
              <label for="prob_name" class="form-label">Name</label>
              <input
                type="text"
                class="form-control"
                id="prob_name"
                v-model="data.name"
                maxlength="64"
                required
                @input="checkName"
                :class="{ 'is-invalid': error.type == 'name' }"
              />
              <div class="invalid-feedback">A problem with this name already exists in this tournament.</div>
            </div>
            <div class="mb-3">
              <label for="start_time" class="form-label">Starting time</label>
              <input type="datetime-local" class="form-control" id="start_time" v-model="data.start" />
            </div>
            <div class="mb-3">
              <label for="end_time" class="form-label">Ending time</label>
              <input type="datetime-local" class="form-control" id="end_time" v-model="data.end" />
            </div>

            <div class="d-flex mt-3">
              <button class="btn btn-secondary" @click="(e) => page--">Back</button>
              <button class="btn btn-primary ms-auto" type="submit">Next</button>
            </div>
          </form>

          <form
            v-if="page == 2"
            id="display_form"
            ref="display_form"
            class="card-body"
            @submit.prevent="createProblem"
          >
            <div class="row">
              <div class="col-5">
                <div class="alert alert-danger" role="alert" v-if="error.type == 'server'">
                  There was an error when processing the submitted data.
                </div>
                <div class="mb-3">
                  <label for="image_file" class="form-label">Thumbnail image</label>
                  <FileInput class="w-em" id="image_file" v-model="data.image" accept="image/*" />
                </div>
                <div class="mb-3">
                  <label for="short_desc" class="form-label">Thumbnail alt text</label>
                  <textarea
                    class="form-control"
                    name="alt_text"
                    id="alt_text"
                    rows="5"
                    maxlength="256"
                    v-model="data.alt"
                  />
                </div>
                <div class="mb-3">
                  <label for="short_desc" class="form-label">Description</label>
                  <textarea
                    class="form-control"
                    name="short_description"
                    id="short_desc"
                    rows="5"
                    maxlength="256"
                    v-model="data.description"
                  ></textarea>
                </div>
                <div class="mb-3">
                  <label for="prob_col" class="form-label">Problem colour</label>
                  <input
                    type="color"
                    name="colour"
                    class="form-control form-control-color"
                    id="prob_col"
                    v-model="data.color"
                  />
                </div>
              </div>
              <div class="col-7">
                <h3>Card preview</h3>
                <div
                  class="card m-2 border border-5"
                  style="width: 18rem; height: 24rem"
                  :style="{ borderColor: data.color + ' !important' }"
                >
                  <img
                    v-if="data.image"
                    :src="imageUrl"
                    class="card-img-top object-fit-cover"
                    style="height: 10.125rem"
                    :style="{ backgroundColor: data.color + ' !important' }"
                    :alt="data.alt"
                  />
                  <div class="card-body d-flex flex-column" style="height: 13.5rem">
                    <h5 class="card-title">{{ data.name }}</h5>
                    <p class="card-text overflow-hidden">{{ data.description }}</p>
                    <a class="btn btn-sm btn-primary mt-auto disabled" aria-disabled="true">View details</a>
                  </div>
                </div>
              </div>
            </div>

            <div class="d-flex mt-3">
              <button class="btn btn-secondary" @click="(e) => page--">Back</button>
              <button class="btn btn-success ms-auto" type="submit">Create</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
#progressbar {
  overflow: hidden;
  color: lightgrey;
}

#progressbar .set,
#progressbar .active {
  color: #000000;
}

#progressbar li {
  list-style-type: none;
  width: 25%;
  float: left;
  position: relative;
}

#progressbar i.progress-icon {
  width: 50px;
  height: 50px;
  line-height: 45px;
  display: block;
  font-size: 18px;
  color: #ffffff;
  background: lightgray;
  border-radius: 50%;
  margin: 0 auto 10px auto;
  padding: 2px;
}

#progressbar li:not(.first):after {
  content: "";
  width: 100%;
  height: 2px;
  background: lightgray;
  position: absolute;
  top: 25px;
  z-index: -1;
  right: 50%;
}

#progressbar .active i.progress-icon,
#progressbar li.active:after {
  background: mediumturquoise;
}

#progressbar .set i.progress-icon,
#progressbar li.set:after {
  background: steelblue;
}
</style>
