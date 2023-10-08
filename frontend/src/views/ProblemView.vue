<script setup lang="ts">
import ProblemCard from "@/components/ProblemCard.vue";
import { type ModelDict, store } from "../main";
import { ProblemService } from "@client";
import type { Problem } from "@client";
import { computed, onMounted, ref, watch, type Ref } from "vue";

const problems = ref<ModelDict<Problem>>({});

watch(
  () => store.tournament,
  async (newTournament) => {
    if (newTournament) {
      problems.value = await ProblemService.get({ tournament: newTournament.id });
    }
  },
  { immediate: true }
);
const now = new Date();

const future_problems = computed(() => {
  return Object.fromEntries(
    Object.entries(problems.value).filter(
      ([id, problem]) => problem.start != null && new Date(problem.start) > now
    )
  );
});

const current_problems = computed(() => {
  return Object.fromEntries(
    Object.entries(problems.value).filter(
      ([id, problem]) =>
        (problem.start == null || new Date(problem.start) <= now) &&
        (problem.end == null || new Date(problem.end) > now)
    )
  );
});

const past_problems = computed(() => {
  return Object.fromEntries(
    Object.entries(problems.value).filter(
      ([id, problem]) => problem.end != null && new Date(problem.end) < now
    )
  );
});
</script>

<template>
  <template v-if="store.tournament">
    <template v-if="store.team == 'admin'">
      <h3>Upcoming</h3>
      <div class="d-flex flex-wrap mb-5">
        <ProblemCard
          v-for="(problem, id) in future_problems"
          :problem="problem"
          :tournament="problem.tournament"
          :key="id"
        />
        <div class="card border border-success-subtle m-2" style="width: 18rem; height: 24rem">
          <img
            src="/default_problem.png"
            style="height: 10.125rem; object-fit: contain"
            class="card-img-top"
            alt=""
          />
          <div class="card-body d-flex flex-column">
            <h5 class="card-title mb-auto">New problem</h5>
            <RouterLink to="/problems/create" class="btn btn-success mt-auto stretched-link"
              >Create</RouterLink
            >
          </div>
        </div>
      </div>
    </template>
    <template v-if="store.tournament">
      <h3 v-if="Object.keys(current_problems).length != 0">Current</h3>
      <div class="d-flex flex-wrap mb-5">
        <ProblemCard
          v-for="(problem, id) in current_problems"
          :problem="problem"
          :tournament="problem.tournament"
          :key="id"
        />
      </div>
      <h3 v-if="Object.keys(past_problems).length != 0">Past</h3>
      <div class="d-flex flex-wrap">
        <ProblemCard
          v-for="(problem, id) in past_problems"
          :problem="problem"
          :tournament="problem.tournament"
          :key="id"
        />
      </div>
      <div v-if="Object.keys(problems).length === 0" class="alert alert-info" role="alert">
        There aren't any problems in
        {{ store.tournament ? "the " + store.tournament.name : "this" }} tournament yet.
      </div>
    </template>
    <div v-else-if="!store.user" class="alert alert-danger" role="alert">
      You need to log in before you can view the problems.
    </div>
    <div v-else class="alert alert-danger" role="alert">
      You need to select a team before you can view the problems.
    </div>
  </template>
  <div v-else class="alert alert-danger" role="alert">
    You need to select a tournament before you can view the problems.
  </div>
</template>
