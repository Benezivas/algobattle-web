<script setup lang="ts">
import { contextApi } from '@/main';
import type { Context } from 'typescript_client';
import { onMounted, ref } from 'vue';


const contexts = ref<{[key: string]: Context}>({})


onMounted(async () => {
  contexts.value = await contextApi.allContexts()
})

const filters = ref({
  page: 1,
  limit: 25,
  isFiltered: false,
})

function openModal(action: string, context: Context | null) {

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

  <div class="d-flex mb-3 pe-2">
    <button type="button" class="btn btn-primary btn-sm me-auto" @click="e => openModal('create', null)">Create new context</button>
  </div>
</template>
