<script setup lang="ts">
import { store } from "@/shared";
import { onMounted, ref } from "vue";
import HomeDefault from "./HomeDefault.vue";
import { SettingsService } from "@client";

const home_page = ref<string | null>();
onMounted(async () => {
  home_page.value = await SettingsService.home();
})

</script>

<template>
  <div v-if="store.user">
    <main>Home page</main>
  </div>
  <div v-else-if="(typeof home_page === 'string')" v-html="home_page"/>
  <HomeDefault v-else-if="home_page === null" />
</template>
