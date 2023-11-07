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
  const results = [...props.results];
  results.sort((a, b) => a.time.localeCompare(b.time));
  return results;
});

function scores(team: Team) {
  return orderedResults.value
    .map((r) => r.participants.find((p) => p.team_id == team.id)?.points || 0)
    .reduce((acc, next) => acc.concat(acc[acc.length - 1] + next), [0]);
}

const timestamps = computed(() => {
  const t = orderedResults.value.map((r) => DateTime.fromISO(r.time));
  if (t.length == 0) {
    return t;
  } else {
    t.splice(0, 0, t[0].minus({ days: 1 }).startOf("day"));
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

function interpolate(main: DateTime, offset: DateTime) {
  return main.plus(offset.minus(main.toMillis()).toMillis() / 3);
}

const options = computed<ChartOptions<"line">>(() => {
  interface Block {
    start: number;
    end: number;
    problem: string;
    id: string;
  }
  const blocks: Block[] = [];
  var currProb: string | undefined = undefined;
  orderedResults.value.forEach((result, index) => {
    if (currProb !== result.problem) {
      blocks.push({
        id: "block" + index,
        start: index,
        end: index,
        problem: result.problem,
      });
      currProb = result.problem;
    } else {
      blocks[blocks.length - 1].end = index;
    }
  });
  const times = orderedResults.value.map((r) => DateTime.fromISO(r.time));
  const blocksTimed = blocks.map((b) => {
    return {
      ...b,
      start:
        b.start === 0
          ? interpolate(times[0], times[0].minus({ days: 1 }).startOf("day"))
          : interpolate(times[b.start], times[b.end - 1]),
      end: b.end === times.length - 1 ? times[times.length - 1] : interpolate(times[b.end], times[b.end + 1]),
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
        type: "timeseries",
        time: {
          unit: "day",
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
          blocksTimed.map((b) => {
            return [
              b.id,
              {
                type: "box",
                xMin: b.start as any,
                xMax: b.end as any,
                backgroundColor: props.problems[b.problem].colour + "4D",
                borderWidth: 0,
                label: {
                  content: props.problems[b.problem].name,
                  display: true,
                  position: {
                    x: "center",
                    y: "start"
                  }
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
