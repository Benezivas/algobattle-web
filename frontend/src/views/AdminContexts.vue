<script setup lang="ts">
import { contextApi } from '@/main';
import { Modal } from 'bootstrap';
import type { Context } from 'typescript_client';
import { onMounted, ref } from 'vue';


const contexts = ref<{[key: string]: Context}>({})


onMounted(async () => {
  contexts.value = await contextApi.allContexts()
})

const error = ref("")

const data = ref({
  name: "",
  id: "",
  action: "create",
  confirmDelete: false,
})
function openModal(action: string, context: Context | null) {
  data.value.action = action
  if (action == "create") {
    data.value.id = ""
    data.value.name = ""
  } else {
    if (!context) {
      return
    }
    data.value.id = context.id
    data.value.name = context.name
  }
  data.value.confirmDelete = false
  error.value = ""
  Modal.getOrCreateInstance("#contextModal").toggle()
}
async function submitEdit() {
  try {
    if (data.value.action == "create") {
      const newContext = await contextApi.createContext({createContext: {name: data.value.name}})
      contexts.value[newContext.id] = newContext
    } else {
      const edited = await contextApi.editContext({id: data.value.id, editContext: {name: data.value.name}})
      contexts.value[edited.id] = edited
    }
    Modal.getOrCreateInstance("#contextModal").toggle()
  } catch {
    error.value = "name"
  }
}
async function deleteContext() {
  if (!data.value.confirmDelete) {
    data.value.confirmDelete = true
    return
  }
  await contextApi.deleteContext({id: data.value.id})
  delete contexts.value[data.value.id]
  Modal.getOrCreateInstance("#contextModal").toggle()
}
</script>

<template>
  <table class="table table-hover mb-2">
    <thead>
      <tr>
        <th scope="col">Name</th>
        <th scope="col"></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="context in contexts">
        <td>
          {{context.name}}
        </td>
        <td class="text-end">
          <button type="button" class="btn btn-warning btn-sm" title="Edit context" @click="e => openModal('edit', context)"><i class="bi bi-pencil"></i></button>
        </td>
      </tr>
    </tbody>
  </table>

  <button type="button" class="btn btn-primary btn-sm ms-2" @click="e => openModal('create', null)">Create new context</button>


  <div class="modal fade" id="contextModal" tabindex="-1" aria-labelledby="modalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <form class="modal-content" @submit.prevent="submitEdit">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="modalLabel">
          <span v-if="data.action == 'edit'">Edit context</span>
          <span v-else>Create new context</span>
          </h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <label for="name" class="form-label">Name</label>
          <input class="form-control w-em" type="text" v-model="data.name" required :class="{'is-invalid': error == 'name'}">
          <div class="invalid-feedback">
            Another context with that name exists already
          </div>
        </div>
        <div class="modal-footer">
          <button v-if="data.confirmDelete" type="button" class="btn btn-secondary" @click="(e) => data.confirmDelete = false">Cancel</button>
          <button v-if="data.action == 'edit'" type="button" class="btn btn-danger ms-2" @click="deleteContext">
            {{data.confirmDelete ? "Confirm deletion" : "Delete context"}}
          </button>
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">{{ data.action == "edit" ? "Save" : "Create" }}</button>
        </div>
      </form>
    </div>
  </div>
</template>
