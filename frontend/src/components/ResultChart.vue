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
  type Point,
} from "chart.js";
import { Line } from "vue-chartjs";
import type { MatchResult, Problem, Team } from "@client";
import { computed } from "vue";
import type { ModelDict } from "@/shared";
import { DateTime } from "luxon";
import "chartjs-adapter-luxon";
import annotationPlugin from "chartjs-plugin-annotation";

ChartJS.register(
  BarElement,
  Title,
  Tooltip,
  Legend,
  PointElement,
  LineElement,
  Colors,
  LinearScale,
  CategoryScale,
  TimeSeriesScale,
  annotationPlugin
);

const props = defineProps<{
  results: MatchResult[];
  teams: ModelDict<Team>;
  problems: ModelDict<Problem>;
}>();

const orderedResults = computed(() => {
  const results = props.results.filter((r) => r.participants.reduce((s, p) => s + p.points, 0) !== 0);
  results.sort((a, b) => a.time.localeCompare(b.time));
  return results;
});

function scores(team: Team) {
  return orderedResults.value
    .map((r) => r.participants.find((p) => p.team_id == team.id)?.points || 0)
    .reduce((acc, next) => acc.concat(acc[acc.length - 1] + next), [0])
    .map((points, i) => ({
      x: i,
      y: points,
    }));
}

const labels = computed(() => {
  const t = orderedResults.value.map((r) => DateTime.fromISO(r.time).toLocaleString(DateTime.DATE_MED));
  if (t.length == 0) {
    return t;
  } else {
    t.splice(0, 0, "Start");
    return t;
  }
});

const data = computed(() => {
  const data: ChartData<"line", Point[], string> = {
    datasets: Object.values(props.teams).map((t) => ({
      label: t.name,
      data: scores(t),
      cubicInterpolationMode: "monotone",
    })),
  };
  return data;
});

const options = computed<ChartOptions<"line">>(() => {
  interface Block {
    start: number;
    end: number;
    problem: string;
    id: string;
  }
  const blocks = orderedResults.value
    .reduce((blocks, result, index) => {
      if (blocks[blocks.length - 1]?.problem !== result.problem) {
        blocks.push({
          id: "block" + index,
          start: index,
          end: index,
          problem: result.problem,
        });
        return blocks;
      } else {
        blocks[blocks.length - 1].end = index;
        return blocks;
      }
    }, [] as Block[])
    .map((b) => {
      return {
        ...b,
        start: b.start + 0.7,
        end: Math.min(b.end + 1.3, orderedResults.value.length),
      };
    });
  const o: ChartOptions<"line"> = {
    scales: {
      y: {
        title: {
          display: true,
          text: "Points",
        },
      },
      x: {
        type: "linear",
        ticks: {
          callback: (value, index, ticks) => labels.value[index],
        },
      },
    },
    plugins: {
      title: {
        display: true,
        text: "Total points",
      },
      annotation: {
        annotations: Object.fromEntries(
          blocks.map((b) => {
            return [
              b.id,
              {
                type: "box",
                xMin: b.start,
                xMax: b.end,
                backgroundColor: props.problems[b.problem].colour + "4D",
                borderWidth: 0,
                label: {
                  content: props.problems[b.problem].name,
                  display: true,
                  position: {
                    x: "center",
                    y: "start",
                  },
                },
              },
            ];
          })
        ),
      },
    },
  };
  return o;
});
</script>

<template>
  <Line :data="data" :options="options" />
</template>
