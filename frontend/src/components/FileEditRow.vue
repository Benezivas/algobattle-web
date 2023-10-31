<script setup lang="ts">
import FileInput from "./FileInput.vue";
import type { DbFile } from "@client";

const props = defineProps<
  | {
      modelValue: DbFile | undefined | null | File | "remove";
      removable: true;
    }
  | {
      modelValue: DbFile | File;
      removable: false;
    }
>();

const emit = defineEmits<{
  "update:modelValue": [newValue: File | "remove"];
}>();
</script>

<template>
  <tr>
    <td><slot /></td>
    <td>
      <template v-if="modelValue instanceof Object && 'location' in modelValue">
        <a
          role="button"
          class="btn btn-primary btn-sm me-2"
          :href="modelValue.location"
          title="File download"
        >
          Current file<i class="bi bi-download ms-1"></i>
        </a>
        <button
          v-if="removable"
          type="button"
          class="btn btn-sm btn-danger"
          @click="emit('update:modelValue', 'remove')"
        >
          Remove
        </button>
      </template>
    </td>
    <FileInput
      class="form-control form-control-sm w-em"
      @update:model-value="(file) => emit('update:modelValue', file)"
    />
  </tr>
</template>
