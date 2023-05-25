<script setup lang="ts">
import type { Tournament, Problem } from 'typescript_client';
import { computed } from 'vue';

const props = defineProps<{
  problem: Problem,
  tournament: Tournament,
}>()

const problem_url = computed(() => {
  const tournamentStr = encodeURIComponent(props.tournament.name)
  const name = encodeURIComponent(props.problem.name)
  return `/problems/${tournamentStr}/${name}`
})

</script>

<template>
  <div class="card m-2 border border-5" style="width: 18rem; height: 24rem;" :style="{borderColor: problem.colour + ' !important'}">
    <img v-if="problem.image" :src="problem.image.location" class="card-img-top object-fit-cover" style="height: 10.125rem" :style="{backgroundColor: problem.colour + ' !important'}" :alt="problem.image.altText">
    <div class="card-body d-flex flex-column" style="height: 13.5rem">
      <h5 class="card-title">{{problem.name}}</h5>
      <p class="card-text overflow-hidden">{{problem.shortDescription}}</p>
      <RouterLink :to="problem_url" class="btn btn-sm btn-primary mt-auto stretched-link">View details</RouterLink>
    </div>
  </div>
</template>
