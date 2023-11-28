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
import { TournamentService, type MatchEvent, type MatchResult, type Problem, type ScoreData, type Team, type Tournament } from "@client";
import { computed, ref, watch } from "vue";
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
  tournament: Tournament,
  state: number,
}>();

const scoreData = ref<ScoreData>();
const matchEvents = computed(() => scoreData.value?.events.filter(e => e.type === "match") as MatchEvent[]);

watch(() => props.state, async () => {
  scoreData.value = await TournamentService.getScores({id: props.tournament.id});
});

function scores(team: string) {
  return scoreData.value!.events
    .map(e => e.points[team] || 0)
    .reduce((acc, next) => acc.concat(acc[acc.length - 1] + next), [0])
    .map((points, i) => ({
      x: i,
      y: points,
    }));
}

const labels = computed(() => {
  const t = matchEvents.value.map((e) => DateTime.fromISO(e.time).toLocaleString(DateTime.DATE_MED));
  t.splice(0, 0, "Start");
  return t;
});

const data = computed(() => {
  const data: ChartData<"line", Point[], string> = {
    datasets: Object.entries(scoreData.value!.teams).map(([id, name]) => ({
      label: name,
      data: scores(id),
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
  const blocks = matchEvents.value
    .reduce((blocks, event, index) => {
      if (blocks[blocks.length - 1]?.problem !== event.problem) {
        blocks.push({
          id: "block" + index,
          start: index,
          end: index,
          problem: event.problem,
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
        end: Math.min(b.end + 1.3, matchEvents.value.length),
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
                backgroundColor: scoreData.value!.problems[b.problem].colour + "4D",
                borderWidth: 0,
                label: {
                  content: scoreData.value!.problems[b.problem].name,
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
