<script setup lang="ts">
import type { DbFile } from "@client";

withDefaults(
  defineProps<{
    file: DbFile;
    label?: string;
  }>(),
  {
    label: "Download",
  }
);
</script>

<template>
  <a role="button" class="btn btn-primary btn-sm" :href="file.location" title="Download file"
    >{{ label }} <i class="bi bi-download ms-1"></i
  ></a>
</template>
