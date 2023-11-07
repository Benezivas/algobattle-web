<script setup lang="ts">
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Colors,
  TimeSeriesScale,
type ChartOptions,
type ChartData,
} from "chart.js";
import { Line } from "vue-chartjs";
import type { MatchResult, Problem, Team } from "@client";
import { computed } from "vue";
import type { ModelDict } from "@/shared";
import { DateTime, Duration } from "luxon";
import 'chartjs-adapter-luxon';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, PointElement, LineElement, Colors, TimeSeriesScale);

const props = defineProps<{
  results: MatchResult[];
  teams: ModelDict<Team>;
}>();

const orderedResults = computed(() => {
  const results = [...props.results];
  results.sort((a, b) => a.time.localeCompare(b.time));
  return results;
});

function scores(team: Team) {
  return orderedResults.value
    .map((r) => r.participants.find((p) => p.team_id == team.id)?.points || 0)
    .reduce((acc, next) => acc.concat(acc[acc.length - 1] + next + 25), [0]);
}

const timestamps = computed(() => {
  const t = orderedResults.value.map((r) => DateTime.fromISO(r.time));
  if (t.length == 0) {
    return t;
  } else {
    t.splice(0, 0, t[0].minus(Duration.fromObject({days: 1})).startOf("day"));
    return t;
  }
});

const data = computed(() => {
  const data: ChartData<"line", number[], DateTime> = {
    labels: timestamps.value,
    datasets: Object.values(props.teams).map((t) => ({
      label: t.name,
      data: scores(t),
      cubicInterpolationMode: "monotone",
    })),
  };
  return data;
});

const options: ChartOptions<"line"> = {
  scales: {
    y: {
      title: {
        display: true,
        text: "Points"
      },
    },
    x: {
      type: "timeseries",
    },
  },
  plugins: {
    title: {
      display: true,
      text: "Total points"
    },
  },
}

</script>

<template>
  <Line :data="data" :options="options"/>
</template>
