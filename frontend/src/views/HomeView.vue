<script setup lang="ts">
import { store, formatDateTime } from "@/shared";
import { computed, onMounted, ref } from "vue";
import {
  type Problem,
  SettingsService,
  ProblemService,
  type ScheduledMatch,
  MatchService,
  ProgramService,
  type Program,
} from "@client";
import ProblemCard from "@/components/ProblemCard.vue";
import { DateTime } from "luxon";

const home_page = ref<string | null>();
const curr_prob = ref<Problem>();
const next_match = ref<ScheduledMatch>();
const generator = ref<Program>();
const solver = ref<Program>();
onMounted(async () => {
  home_page.value = await SettingsService.home();
  if (!store.team) {
    return;
  }
  const problems = await ProblemService.get({ tournament: store.tournament?.id });
  curr_prob.value = Object.values(problems).sort((a, b) => {
    if (!a.end) {
      return 1;
    } else if (!b.end) {
      return -1;
    } else {
      return a.end.localeCompare(b.end);
    }
  })[0];
  const schedules = await MatchService.getScheduled();
  next_match.value = Object.values(schedules.matches)
    .filter((m) => m.problem == curr_prob.value?.id)
    .sort((a, b) => a.time.localeCompare(b.time))[0];
  if (store.team instanceof Object) {
    const programs = await ProgramService.get({ team: store.team.id, problem: curr_prob.value.id });
    var generators = Object.values(programs.programs).filter((p) => p.role == "generator");
    var solvers = Object.values(programs.programs).filter((p) => p.role == "solver");
    if (programs.total != generators.length + solvers.length) {
      if (generators.length == 0) {
        generators = Object.values(
          (await ProgramService.get({ team: store.team.id, problem: curr_prob.value.id, role: "generator" }))
            .programs
        );
      }
      if (solvers.length == 0) {
        solvers = Object.values(
          (await ProgramService.get({ team: store.team.id, problem: curr_prob.value.id, role: "solver" }))
            .programs
        );
      }
    }
    generator.value = generators.sort((a, b) => b.creation_time.localeCompare(a.creation_time))[0];
    solver.value = solvers.sort((a, b) => b.creation_time.localeCompare(a.creation_time))[0];
  }
});
function until(timestamp: string): string {
  return DateTime.fromISO(timestamp).diff(DateTime.now().startOf("minute"), ["minutes"]).rescale().toHuman();
}
</script>

<template>
  <main v-if="store.user">
    <div v-if="curr_prob">
      <h1>Current Problem</h1>
      <div id="problem-box">
        <ProblemCard :problem="curr_prob" />
        <table class="table" id="problem-data">
          <thead>
            <th scope="col"></th>
          </thead>
          <tbody>
            <tr v-if="curr_prob.end">
              <td>Ends in {{ until(curr_prob.end) }}</td>
            </tr>
            <template v-if="next_match">
              <tr>
                <td>
                  Next match {{ next_match.name ? "(" + next_match.name + ") " : "" }}in
                  {{ until(next_match.time) }}
                </td>
              </tr>
              <tr v-if="generator">
                <td>
                  Using generator
                  {{
                    generator.name
                      ? generator.name
                      : "uploaded at " + formatDateTime(generator.creation_time)
                  }}
                </td>
              </tr>
              <tr v-else-if="(store.team instanceof Object)">
                <td class="text-danger">You still need to uploaded a generator for this problem!</td>
              </tr>
              <tr v-if="solver">
                <td>
                  Using solver
                  {{
                    solver.name
                      ? solver.name
                      : "uploaded at " + formatDateTime(solver.creation_time)
                  }}
                </td>
              </tr>
              <tr v-else-if="(store.team instanceof Object)">
                <td class="text-danger">You still need to uploaded a solver for this problem!</td>
              </tr>
            </template>
            <tr v-else>
              <td>No matches scheduled for this problem</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else-if="store.tournament" class="alert alert-info" role="alert">
      There aren't any current problems in this tournament.
    </div>
    <div v-else-if="!store.team" class="alert alert-danger" role="alert">
      You aren't member of any team. You may need to add your account to a team or reach out to your course
      administrators to do so.
    </div>
    <div v-else class="alert alert-danger" role="alert">
      You haven't selected a team. You can do so in the <RouterLink to="settings">user settings</RouterLink>.
    </div>
  </main>
  <main v-else-if="typeof home_page === 'string'" v-html="home_page" />
  <main v-else-if="home_page === null">
    <h1>Algobattle</h1>
    <p>
      Algobattle is a framework for running a theory based but also highly hands-on computer science lab
      course. It is developed by the
      <a href="https://tcs.rwth-aachen.de/">Computer Science Theory group of RWTH Aachen University</a>
      which runs a course using it since 2019. This website is used to run the course and contains
      documentation for students participating in it and others who may want to run an Algobattle course
      themselves.
    </p>
    <p>
      During a course teams of students are given various algorithmic problems. They then are tasked with
      writing programs that both create hard-to-solve instances of these problems and solve arbitrary
      instances as best they can. We then take their code and run matches where the team's programs challenge
      each other to see which can generate the hardest instances and solve the others' the best.
    </p>
    <p>Key features are:</p>
    <ul>
      <li>
        <strong>All in one place</strong>: An easy to use webserver to manage everything that happens during
        the course, host documentation, distribute files to and from students, run matches, and much more.
      </li>
      <li>
        <strong>Tailored to your students</strong>: Algobattle is built to be customizable. A modern and
        intuitive development environment lets course instructors create new problems for their students to
        tackle and exciting match types.
      </li>
      <li>
        <strong>Easy to learn</strong>: We have extensive documentation to help course instructors and
        students along their way. Tutorials guide you through every step of the way with many tips to get
        everything we have to offer.
      </li>
      <li>
        <strong>Flexible</strong>: Courses can use any programming language. Instructors are free to use
        whatever language they want to teach, or leave the choice open to the students themselves. Algobattle
        will work with all of them, even letting you mix it up in different programs.
      </li>
      <li>
        <strong>Secure</strong>: Student code is only ever executed in secured environments. This lets
        students use the full extend programming has to offer without anyone having to worry about malicious
        actions or cheating.
      </li>
      <li>
        <strong>Elegant</strong>: Our command line tools and provided webserver are designed with modern
        tastes in mind. The Algobattle web sites, documentation, and command line interface tool are designed
        to not only be functional but also fun to use. There is an emphasis placed on making them look
        appealing and provide a good user experience.
      </li>
      <li>
        <strong>Open source</strong>: Every part of the framework is distributed with open source licences.
        This means that you can easily see how everything works, or even modify our code to perfectly tailor
        it to your needs.
      </li>
    </ul>
    <p>
      The best place to start is the user guide linked at the top of the page. You can also log in at the top
      right to see everything currently available in your course.
    </p>
  </main>
</template>

<style>
h1 {
  font-size: 2rem;
}

#problem-box {
  display: block flex;
  flex-direction: row;
}

#problem-data {
  max-width: 28rem;
  margin-left: 1rem;
  align-self: flex-start;
}
</style>
