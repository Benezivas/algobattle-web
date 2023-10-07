<script setup lang="ts">
import { ref } from "vue";

const props = defineProps<{
  position: "before" | "after";
}>();
const emits = defineEmits<{
  delete: [];
}>();
const confirming = ref(false);

function del() {
  if (confirming.value) {
    emits("delete");
  } else {
    confirming.value = true;
  }
}
</script>

<template>
  <button
    v-if="confirming && props.position === 'before'"
    type="button"
    class="btn btn-secondary me-2"
    @click="() => (confirming = false)"
  >
    Cancel
  </button>
  <button type="button" class="btn btn-danger" @click="del">
    {{ confirming ? "Confirm deletion" : "Delete" }}
  </button>
  <button
    v-if="confirming && props.position === 'after'"
    type="button"
    class="btn btn-secondary ms-2"
    @click="() => (confirming = false)"
  >
    Cancel
  </button>
</template>
