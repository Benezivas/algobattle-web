<script setup lang="ts">
import { RouterView, useRouter } from "vue-router";
import PageNavbarIcon from "./components/HomeNavbarIcon.vue";
import { store } from "@/shared";
import { UserService, type Team, SettingsService } from "@client";
import LoginPane from "./components/LoginPane.vue";
import { useCookies } from "@vueuse/integrations/useCookies";
import { computed, onMounted, watch } from "vue";
import { Dropdown } from "bootstrap";

const router = useRouter();
const cookies = useCookies();

const queryToken = computed(() => {
  let token = router.currentRoute.value.query.login_token;
  if (token instanceof Array) {
    token = token[0];
  }
  return token;
});
watch(queryToken, async (newToken) => {
  if (newToken) {
    const data = await UserService.getToken({ loginToken: newToken });
    cookies.set("algobattle_user_token", data.token, { expires: new Date(data.expires) });
    router.replace({ path: router.currentRoute.value.path });
  }
});

const userToken = computed(() => {
  return cookies.get("algobattle_user_token");
});
watch(
  userToken,
  async (userToken) => {
    if (userToken) {
      try {
        const response = await UserService.getLogin();
        if (response) {
          store.user = response.user;
          store.team = response.team;
          store.tournament = response.tournament;
          return;
        }
      } catch {}
    }
    store.user = null;
  },
  { immediate: true }
);

async function logout() {
  Dropdown.getOrCreateInstance("#loggedInDropdown").hide();
  cookies.remove("algobattle_user_token");
  router.go(0);
}

async function selectTeam(team: Team | "admin") {
  if (team == "admin" && !store.user?.is_admin) {
    return;
  }
  await SettingsService.editUser({
    requestBody: {
      team: team == "admin" ? team : team.id,
    }
  });
  router.go(0);
}

const displayName = computed(() => {
  if (!store.user) {
    return "Log in";
  } else if (!store.team) {
    return "No team";
  } else if (store.team == "admin") {
    return "Admin";
  } else {
    return store.team.name;
  }
});

onMounted(async () => {
  store.serverSettings = await SettingsService.getServer();
})
</script>

<template>
  <nav class="navbar navbar-expand-md sticky-top bg-primary-subtle" data-bs-theme="dark">
    <div class="container-xxl">
      <RouterLink to="/" class="navbar-brand">
        <span class="fs-4">Algobattle</span>
      </RouterLink>
      <button
        class="navbar-toggler"
        type="button"
        data-bs-toggle="collapse"
        data-bs-target="#navbarSupportedContent"
        aria-controls="navbarSupportedContent"
        aria-expanded="false"
        aria-label="Toggle navigation"
      >
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarSupportedContent">
        <ul class="navbar-nav me-auto mb-2 mb-lg-0 nav nav-pills">
          <template v-if="store.tournament">
            <PageNavbarIcon link="/problems" icon="boxes">Problems</PageNavbarIcon>
            <PageNavbarIcon link="/programs" icon="file-earmark-code">Programs</PageNavbarIcon>
            <PageNavbarIcon link="/schedule" icon="calendar-week">Schedule</PageNavbarIcon>
            <PageNavbarIcon link="/results" icon="bar-chart-line">Results</PageNavbarIcon>
          </template>
          <PageNavbarIcon v-if="store.team == 'admin'" link="/admin" icon="people"
            >Admin panel</PageNavbarIcon
          >
          <li class="nav-item mx-2">
            <a href="/docs/tutorial" class="nav-link align-middle"><i class="me-1 bi bi-book" />User Guide</a>
          </li>
        </ul>

        <div class="nav-item dropdown">
          <a
            class="nav-link dropdown-toggle text-white"
            href="#"
            role="button"
            data-bs-toggle="dropdown"
            data-bs-auto-close="outside"
            aria-expanded="false"
          >
            <i class="bi bi-person-circle me-2"></i> <strong>{{ displayName }}</strong>
          </a>
          <ul v-if="store.user" class="dropdown-menu" id="loggedInDropdown">
            <li><RouterLink class="dropdown-item" :to="{name: 'settings'}">Settings</RouterLink></li>
            <template v-if="store.user.teams.length >= (store.user.is_admin ? 1 : 2)">
              <li><hr class="dropdown-divider" /></li>
              <li class="dropdown-header">View as</li>
              <li v-for="team in store.user.teams">
                <button
                  class="dropdown-item"
                  :class="{ active: store.team != 'admin' && store.team?.id == team.id }"
                  @click="selectTeam(team)"
                >
                  {{ team.name }}
                </button>
              </li>
              <li v-if="store.user.is_admin">
                <button
                  class="dropdown-item"
                  :class="{ active: store.team == 'admin' }"
                  @click="selectTeam('admin')"
                >
                  Admin
                </button>
              </li>
            </template>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <button class="dropdown-item" @click="logout">Log out</button>
            </li>
          </ul>
          <LoginPane v-else />
        </div>
      </div>
    </div>
  </nav>

  <div class="container-xxl p-5">
    <RouterView />
  </div>
</template>
