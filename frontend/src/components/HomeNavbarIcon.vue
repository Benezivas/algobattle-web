<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router';

defineProps<{
  link: string,
  icon: string,
}>()

const route = useRoute()
</script>

<template>
  <li class="nav-item mx-2">
    <RouterLink :to="link" class="nav-link align-middle" :class="{active: route.path.startsWith(link)}" :aria-current="route.path.startsWith(link)">
      <i class="me-1 bi" :class="['bi-' + icon]"></i><slot/>
    </RouterLink>
  </li>
</template>
