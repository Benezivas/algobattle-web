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
import {
  TournamentService,
  type MatchEvent,
  type ExtraEvent,
  type MatchResult,
  type Problem,
  type ScoreData,
  type Team,
  type Tournament,
} from "@client";
import { computed, onMounted, ref, watch } from "vue";
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

type DataObject = {
  x: number;
  y: number;
  points: number;
  event?: MatchEvent | ExtraEvent;
};

const props = defineProps<{
  tournament: Tournament;
  state: number;
}>();

const scoreData = ref<ScoreData>();
const matchEvents = computed(
  () => (scoreData.value?.events.filter((e) => e.type === "match") as MatchEvent[]) || []
);

async function getData() {
  scoreData.value = await TournamentService.getScores({ id: props.tournament.id });
}
watch(() => props.state, getData);
onMounted(getData);

const labels = computed(() => {
  const t = matchEvents.value.map((e) => DateTime.fromISO(e.time).toLocaleString(DateTime.DATE_MED));
  t.splice(0, 0, "Start");
  return t;
});

const positionedEvents = computed(() => {
  const events = scoreData.value?.events;
  if (!events || events.length === 0) {
    return [];
  }
  var last = DateTime.fromISO(events[0].time);
  var interval: number | undefined;
  var index = 0;
  return events.map((event, i) => {
    if ("problem" in event) {
      last = DateTime.fromISO(event.time);
      interval = undefined;
      index++;
      return { ...event, position: index };
    } else {
      if (!interval) {
        var nextEvent = events.find((e) => e.type === "match" && e.time > event.time);
        if (!nextEvent) {
          nextEvent = events[events.length - 1];
        }
        interval = DateTime.fromISO(nextEvent.time).diff(last).toMillis();
      }
      var fractional = DateTime.fromISO(event.time).diff(last).toMillis() / interval;
      if (index === 0) {
        fractional = fractional * 0.7 + 0.3;
      } else if (index === matchEvents.value.length) {
        fractional = fractional * 0.7;
      }
      return { ...event, position: index + fractional };
    }
  });
});

function scores(team: string) {
  return positionedEvents.value
    .filter((e) => team in e.points)
    .map((e) => ({ points: e.points[team] || 0, position: e.position, event: e }))
    .reduce(
      (acc, event) =>
        acc.concat({
          x: event.position,
          y: acc[acc.length - 1].y + event.points,
          event: event.event,
          points: event.points,
        }),
      [{ x: 0, y: 0, points: 0 } as DataObject]
    );
}

const data = computed(() => {
  const orig = scoreData.value;
  if (!orig) {
    return { datasets: [] };
  }
  const data: ChartData<"line", DataObject[], string> = {
    datasets: Object.entries(orig.teams).map(([id, name]) => ({
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
  const lastIndex = positionedEvents.value[positionedEvents.value.length - 1]?.position || 0;
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
        end: Math.min(b.end + 1.3, lastIndex),
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
          callback: (value, index, ticks) => labels.value[value as number],
        },
      },
    },
    plugins: {
      title: {
        display: true,
        text: "Total points",
      },
      tooltip: {
        callbacks: {
          title: function (tooltipItems) {
            const event = (tooltipItems[0].raw as DataObject).event;
            if (!event) {
              return "Start";
            }
            const matchType = event.type === "match" ? "Match" : "Bonus Points";
            return `${matchType} on ${DateTime.fromISO(event.time).toLocaleString(DateTime.DATE_SHORT)}`;
          },
          label: function (tooltipItem) {
            return `${(tooltipItem.raw as DataObject).points.toString()} points`;
          },
        },
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
