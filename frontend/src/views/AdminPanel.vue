<script setup lang="ts">
import { ref } from "vue";
import AdminUsers from "./AdminUsers.vue";
import AdminTeams from "./AdminTeams.vue";
import AdminTournaments from "./AdminTournaments.vue";

const tab = ref("users");
</script>

<template>
  <ul class="nav nav-tabs">
    <li class="nav-item">
      <button
        class="nav-link"
        :class="{ active: tab == 'users' }"
        :aria-current="tab == 'users'"
        @click="(e) => (tab = 'users')"
      >
        Users
      </button>
    </li>
    <li class="nav-item">
      <button
        class="nav-link"
        :class="{ active: tab == 'teams' }"
        :aria-current="tab == 'teams'"
        @click="(e) => (tab = 'teams')"
      >
        Teams
      </button>
    </li>
    <li class="nav-item">
      <button
        class="nav-link"
        :class="{ active: tab == 'tournaments' }"
        :aria-current="tab == 'tournaments'"
        @click="(e) => (tab = 'tournaments')"
      >
        Tournaments
      </button>
    </li>
  </ul>

  <AdminUsers v-if="tab == 'users'" />
  <AdminTeams v-if="tab == 'teams'" />
  <AdminTournaments v-if="tab == 'tournaments'" />
</template>
