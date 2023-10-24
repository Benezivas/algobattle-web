<script setup lang="ts">
import { store } from "@/shared";
import { onMounted, ref } from "vue";
import { SettingsService } from "@client";

const home_page = ref<string | null>();
onMounted(async () => {
  home_page.value = await SettingsService.home();
});
</script>

<template>
  <main v-if="store.user">Home page</main>
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
