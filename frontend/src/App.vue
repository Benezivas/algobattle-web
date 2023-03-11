<script setup lang="ts">
import { RouterView, useRouter } from 'vue-router'
import PageNavbarIcon from './components/HomeNavbarIcon.vue';
import { store, userApi } from "./main"
import LoginView from './views/LoginView.vue';
import { useCookies } from "vue3-cookies"
import { onMounted } from 'vue';
import type { UserWithSettings } from 'typescript_client';

const router = useRouter()
const { cookies } = useCookies()

onMounted(async () => { 
  try {
    store.user = await userApi.getSelf()
  } catch {}
  
  const route = router.currentRoute.value
  let login_token = route.query.login_token
  if (login_token instanceof Array) {
    login_token = login_token[0]
  }
  if (login_token) {
    const data = await userApi.getToken({loginToken: login_token})
    cookies.set("user_token", data.token, data.expires)
    store.user = await userApi.getSelf()
    router.replace({path: route.path})
  }
})

async function logout() {
  cookies.remove("user_token")
  store.user = {} as UserWithSettings
}

</script>

<template>
  <nav class="navbar navbar-expand-md sticky-top bg-primary-subtle" data-bs-theme="dark">
    <div class="container-xxl">
      <RouterLink to="/" class="navbar-brand">
        <span class="fs-4">Algobattle</span>
      </RouterLink>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarSupportedContent">
        <ul v-if="store.user.id" class="navbar-nav me-auto mb-2 mb-lg-0 nav nav-pills">
          <PageNavbarIcon link="/problems" icon="boxes">Problems</PageNavbarIcon>
          <PageNavbarIcon link="/programs" icon="file-earmark-code">Programs</PageNavbarIcon>
          <PageNavbarIcon link="/schedule" icon="calendar-week">Schedule</PageNavbarIcon>
          <PageNavbarIcon link="/results" icon="bar-chart-line">Results</PageNavbarIcon>
          <PageNavbarIcon v-if="store.user.isAdmin" link="/admin/users" icon="people">Admin panel</PageNavbarIcon>
        </ul>

        <div v-if="store.user.id" class="nav-item dropdown">
          <a class="nav-link dropdown-toggle text-white" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
            <i class="bi bi-person-circle me-2"></i> <strong>{{store.user.name}}</strong>
          </a>
          <ul class="dropdown-menu">
            <li v-if="store.user.teams"><RouterLink class="dropdown-item" to="/team">Team</RouterLink></li>
            <li><RouterLink class="dropdown-item" to="/user">User</RouterLink></li>
            <li><hr class="dropdown-divider"></li>
            <li>
              <button class="dropdown-item" @click="logout">Log out</button>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </nav>

  <div class="container-xxl p-5">
    <RouterView v-if="store.user.id" />
    <LoginView v-else />
  </div>
</template>
