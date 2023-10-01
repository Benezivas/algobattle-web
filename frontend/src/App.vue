<script setup lang="ts">
import { RouterView, useRouter } from "vue-router";
import PageNavbarIcon from "./components/HomeNavbarIcon.vue";
import { store } from "./main";
import { UserService, type Team } from "../typescript_client";
import LoginPane from "./components/LoginPane.vue";
import { useCookies } from "vue3-cookies";
import { computed, onMounted, reactive } from "vue";

const router = useRouter();
const { cookies } = useCookies();

onMounted(async () => {
  try {
    const response = await UserService.getLogin();
    if (response) {
      store.user = response.user;
      store.settings = response.settings;
      store.logged_in = response.logged_in as any;
    } else {
      store.user = null;
      store.settings = null;
      store.logged_in = null;
    }
  } catch {}

  const route = router.currentRoute.value;
  let login_token = route.query.login_token;
  if (login_token instanceof Array) {
    login_token = login_token[0];
  }
  if (login_token) {
    const data = await UserService.getToken({ loginToken: login_token });
    cookies.set("algobattle_user_token", data.token, data.expires);
    const response = await UserService.getLogin();
    if (response) {
      store.user = response.user;
      store.settings = response.settings;
      store.logged_in = response.logged_in as any;
    } else {
      store.user = null;
      store.settings = null;
      store.logged_in = null;
    }
    router.replace({ path: route.path });
  }
});

async function logout() {
  cookies.remove("algobattle_user_token");
  store.user = null;
  store.settings = null;
  store.logged_in = null;
}

async function selectTeam(team: Team | "admin") {
  if (team == "admin" && !store.user?.is_admin) {
    return
  }
  UserService.settings({
    requestBody: {
      team: team == "admin" ? null : team.id,
    }
  })
}

const displayName = computed(() => {
  if (store.logged_in == "admin") {
    return "Admin"
  } else if (store.logged_in) {
    return store.logged_in.name
  } else {
    return "Log in"
  }
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
          <template v-if="store.user">
            <PageNavbarIcon link="/problems" icon="boxes">Problems</PageNavbarIcon>
            <PageNavbarIcon link="/programs" icon="file-earmark-code">Programs</PageNavbarIcon>
            <PageNavbarIcon link="/schedule" icon="calendar-week">Schedule</PageNavbarIcon>
            <PageNavbarIcon link="/results" icon="bar-chart-line">Results</PageNavbarIcon>
            <PageNavbarIcon v-if="store.logged_in == 'admin'" link="/admin" icon="people">Admin panel</PageNavbarIcon>
          </template>
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
          <ul v-if="store.logged_in" class="dropdown-menu">
            <li><RouterLink class="dropdown-item" to="settings">Settings</RouterLink></li>
            <template v-if="store.user.is_admin || store.user.teams.length >= 2">
              <li><hr class="dropdown-divider" /></li>
              <li class="dropdown-header">Select team</li>
              <li class="dropdown-item" v-for="team in store.user.teams" @click="selectTeam(team)">{{ team.name }}</li>
              <li class="dropdown-item" v-if="store.user.is_admin" @click="selectTeam('admin')">Admin</li>
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
