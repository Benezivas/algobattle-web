<script setup lang="ts">
import { computed, ref } from "vue";

const PAGE_SIZE = 25;

const props = defineProps<{
  total: number;
}>();
const emit = defineEmits<{
  update: [offset: number];
}>();
const offset = ref(0);

const currPage = computed(() => {
  return Math.floor(offset.value / PAGE_SIZE) + 1;
});
const maxPage = computed(() => {
  return Math.ceil(props.total / PAGE_SIZE);
});
</script>

<template>
  <nav v-if="total > PAGE_SIZE" aria-label="Table pagination">
    <ul class="pagination pagination-sm justify-content-end mb-0 ms-2">
      <li class="page-item">
        <a class="page-link" :class="{ disabled: currPage <= 1 }" @click="emit('update', 0)"
          ><i class="bi bi-chevron-double-left"></i
        ></a>
      </li>
      <li class="page-item">
        <a
          class="page-link"
          :class="{ disabled: currPage <= 1 }"
          @click="emit('update', (currPage - 1) * PAGE_SIZE)"
          ><i class="bi bi-chevron-compact-left"></i
        ></a>
      </li>
      <li class="page-item">currPage / maxPage</li>
      <li class="page-item">
        <a
          class="page-link"
          :class="{ disabled: currPage >= maxPage }"
          @click="emit('update', (currPage + 1) * PAGE_SIZE)"
          ><i class="bi bi-chevron-compact-right"></i
        ></a>
      </li>
      <li class="page-item">
        <a
          class="page-link"
          :class="{ disabled: currPage >= maxPage }"
          @click="emit('update', maxPage * PAGE_SIZE)"
          ><i class="bi bi-chevron-double-right"></i
        ></a>
      </li>
    </ul>
  </nav>
</template>
