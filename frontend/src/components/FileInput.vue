<script setup lang="ts">
import { ref, watch } from "vue";

interface InputFileEvent extends InputEvent {
  target: HTMLInputElement;
}

const props = defineProps<{
  modelValue?: File;
}>();
const emit = defineEmits<{
  (e: "update:modelValue", newValue: File): void;
}>();

watch(
  () => props.modelValue,
  (value) => {
    if (!value && fileSelect.value) {
      fileSelect.value.value = "";
    }
  }
);

const fileSelect = ref<HTMLInputElement>();

function selectFile(event: InputFileEvent) {
  const files = event.target.files || event.dataTransfer?.files;
  if (files && files.length != 0) {
    emit("update:modelValue", files[0]);
  }
}
</script>

<template>
  <input type="file" class="form-control" ref="fileSelect" @change="(e: any) => selectFile(e)" />
</template>
