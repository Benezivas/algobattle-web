<script setup lang="ts">
import { ref } from 'vue';
import AdminUsers from "./AdminUsers.vue"
import AdminTeams from "./AdminTeams.vue"
import AdminContexts from "./AdminContexts.vue"

const tab = ref("users")
</script>

<template>
  <ul class="nav nav-tabs">
    <li class="nav-item">
      <button class="nav-link" :class="{active: tab == 'users'}" :aria-current="tab == 'users'" @click="e => tab = 'users'">Users</button>
    </li>
    <li class="nav-item">
      <button class="nav-link" :class="{active: tab == 'teams'}" :aria-current="tab == 'teams'" @click="e => tab = 'teams'">Teams</button>
    </li>
    <li class="nav-item">
      <button class="nav-link" :class="{active: tab == 'contexts'}" :aria-current="tab == 'contexts'" @click="e => tab = 'contexts'">Contexts</button>
    </li>
  </ul>

  <AdminUsers v-if="tab == 'users'" />
  <AdminTeams v-if="tab == 'teams'" />
  <AdminContexts v-if="tab == 'contexts'" />
</template>
