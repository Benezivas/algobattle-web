<script setup lang="ts">
import { computed, ref } from "vue";

const props = defineProps<{
  type: "add" | "remove";
}>();
const emit = defineEmits<{
  (e: "click"): void;
}>();

const hovering = ref(false);
const bgClass = computed(() => ({
  "text-bg-success": props.type == "add",
  "text-bg-danger": props.type == "remove" && hovering.value,
  "text-bg-warning": props.type == "remove" && !hovering.value,
}));
</script>

<template>
  <span class="badge rounded-pill m-1" :class="bgClass">
    <slot />
    <a
      @click.prevent="(e) => emit('click')"
      href="#"
      @mouseover="(e) => (hovering = true)"
      @mouseleave="(e) => (hovering = false)"
      :title="props.type"
      ><i class="bi" :class="[props.type == 'add' ? 'text-light bi-plus-lg' : 'bi-x-lg']"></i
    ></a>
  </span>
</template>
