<script setup lang="ts">
import { ref, watch } from "vue";
import { store } from "@/shared";

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
const file = ref<File | undefined>();

function selectFile(event: InputFileEvent) {
  const files = event.target.files || event.dataTransfer?.files;
  if (files && files.length != 0) {
    file.value = files[0];
    emit("update:modelValue", files[0]);
  }
}
</script>

<template>
  <input
    type="file"
    class="form-control"
    v-bind="$attrs"
    :class="{'is-invalid': file?.size && store.serverSettings!.upload_file_limit < file.size}"
    ref="fileSelect"
    @change="(e: any) => selectFile(e)"
  />
  <div class="invalid-feedback">Selected file is too large</div>
</template>
