<script setup lang="ts">
import { computed, ref } from "vue";

const PAGE_SIZE = 25;

const props = defineProps<{
  modelValue: number,
  total: number;
}>();
const emit = defineEmits<{
  "update:modelValue": [offset: number];
}>();

const currPage = computed(() => {
  return Math.floor(props.modelValue / PAGE_SIZE);
});
const maxPage = computed(() => {
  return Math.ceil(props.total / PAGE_SIZE) - 1;
});
</script>

<template>
  <nav v-if="total > PAGE_SIZE" aria-label="Table pagination">
    <ul class="pagination pagination-sm justify-content-end mb-0 ms-2">
      <li class="page-item">
        <a class="page-link" :class="{ disabled: currPage === 0 }" @click="emit('update:modelValue', 0)"
          ><i class="bi bi-chevron-double-left"></i
        ></a>
      </li>
      <li class="page-item">
        <a
          class="page-link"
          :class="{ disabled: currPage === 0 }"
          @click="emit('update:modelValue', (currPage - 1) * PAGE_SIZE)"
          ><i class="bi bi-chevron-compact-left"></i
        ></a>
      </li>
      <li class="page-item" id="text">{{currPage + 1}} / {{maxPage + 1}}</li>
      <li class="page-item">
        <a
          class="page-link"
          :class="{ disabled: currPage >= maxPage }"
          @click="emit('update:modelValue', (currPage + 1) * PAGE_SIZE)"
          ><i class="bi bi-chevron-compact-right"></i
        ></a>
      </li>
      <li class="page-item">
        <a
          class="page-link"
          :class="{ disabled: currPage >= maxPage }"
          @click="emit('update:modelValue', maxPage * PAGE_SIZE)"
          ><i class="bi bi-chevron-double-right"></i
        ></a>
      </li>
    </ul>
  </nav>
</template>

<style>
#text {
  margin-left: 0.4rem;
  margin-right: 0.4rem;
  align-self: center;
}
</style>
