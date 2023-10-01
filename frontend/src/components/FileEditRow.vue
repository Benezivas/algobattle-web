<script setup lang="ts">
import { ref } from "vue";

export interface DbFileEdit {
  location?: string;
  edit?: File | null;
}
interface InputFileEvent extends InputEvent {
  target: HTMLInputElement;
}

const props = defineProps<{
  file: DbFileEdit;
  removable: boolean;
}>();

const fileSelect = ref<HTMLInputElement | null>(null);

function removeFile() {
  if (!props.file) {
    return;
  }
  props.file.edit = null;
  if (fileSelect.value) {
    fileSelect.value.value = "";
  }
}
function selectFile(event: InputFileEvent) {
  const files = event.target.files || event.dataTransfer?.files;
  if (files && files.length != 0) {
    props.file.edit = files[0];
    props.file.location = URL.createObjectURL(files[0]);
  }
}
</script>

<template>
  <tr>
    <td><slot /></td>
    <td>
      <template v-if="file.location">
        <a role="button" class="btn btn-primary btn-sm me-2" :href="file.location" title="File download">
          {{ file.edit === undefined ? "Current" : "New" }} file<i class="bi bi-download ms-1"></i>
        </a>
        <button v-if="removable" type="button" class="btn btn-sm btn-danger" @click="removeFile">
          Remove
        </button>
      </template>
    </td>
    <input
      type="file"
      class="form-control form-control-sm w-em"
      id="prob_file"
      ref="fileSelect"
      @change="(e) => selectFile(e as any)"
    />
  </tr>
</template>
