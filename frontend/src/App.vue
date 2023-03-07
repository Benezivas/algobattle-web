<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import PageNavbarIcon from './components/PageNavbarIcon.vue';
import { store } from "./main"
</script>

<template>
  <nav class="navbar navbar-expand-md sticky-top bg-primary-subtle" data-bs-theme="dark">
    <div class="container-xxl">
      <a href="/" class="navbar-brand">
        <span class="fs-4">Algobattle</span>
      </a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarSupportedContent">
        <ul class="navbar-nav me-auto mb-2 mb-lg-0 nav nav-pills">
          <PageNavbarIcon link="/problems" icon="boxes">Problems</PageNavbarIcon>
          <PageNavbarIcon link="/programs" icon="file-earmark-code">Programs</PageNavbarIcon>
          <PageNavbarIcon link="/schedule" icon="calendar-week">Schedule</PageNavbarIcon>
          <PageNavbarIcon link="/results" icon="bar-chart-line">Results</PageNavbarIcon>
          <PageNavbarIcon v-if="store.user.is_admin" link="/admin/users" icon="people">Admin panel</PageNavbarIcon>
        </ul>

        <div class="nav-item dropdown">
          <a class="nav-link dropdown-toggle text-white" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
            <i class="bi bi-person-circle me-2"></i> <strong>{{store.user.name}}</strong>
          </a>
          <ul class="dropdown-menu">
            {% if user.teams %}
            <li><a class="dropdown-item" href="/team">Team</a></li>
            {% endif %}
            <li><a class="dropdown-item" href="/user">User</a></li>
            <li><hr class="dropdown-divider"></li>
            <li>
              <form action="/logout" method="post">
                <button class="dropdown-item" type="submit" name="LogoutButton" value="test">Log out</button>
              </form>
            </li>
          </ul>
        </div>
      
      </div>
    </div>
  </nav>

  <div class="container-xxl p-5">
    <RouterView />
  </div>
</template>
