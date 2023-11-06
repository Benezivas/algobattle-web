<script setup lang="ts">
import { Line } from "vue-chartjs";
import type { MatchResult } from "@client";

const props = defineProps<{
  results: MatchResult[];
}>();


</script>

<template>
  <Line :data="data" />
</template>
