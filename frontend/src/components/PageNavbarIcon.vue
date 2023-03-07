<script setup lang="ts">
import { useRoute } from 'vue-router';

defineProps<{
  link: string,
  icon: string,
}>()

const route = useRoute()
</script>

<template>
  <li class="nav-item mx-2">
    <a :href="link" class="nav-link align-middle" :class="{active: route.name == link}" :aria-current="route.name == link">
      <i class="bi bi-{{ icon }}"></i> <span class="ms-1"><slot/></span>
    </a>
  </li>
</template>
