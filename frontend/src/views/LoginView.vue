<script setup lang="ts">
import { UserService } from "@client";
import { ref } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
var email = ref("");
var msg = ref("");

async function login() {
  try {
    await UserService.login({ requestBody: { email: email.value, target_url: route.fullPath } });
    msg.value = "email_sent";
  } catch {
    msg.value = "error";
  }
}
</script>

<template>
  <h1>Login</h1>
  <div v-if="msg == 'error'" class="alert alert-danger" role="alert">
    There was an error logging you in.
    <button type="button" class="btn-close float-end" data-bs-dismiss="alert" aria-label="Close"></button>
  </div>
  <div v-if="msg == 'email_sent'" class="alert alert-success" role="alert">
    We've sent you an email, click the link in it to login.
  </div>
  <form @submit.prevent="login">
    <div class="mb-3">
      <label for="email" class="form-label">Email address</label>
      <input type="email" class="form-control w-em" id="email" required v-model="email" />
    </div>
    <button type="submit" class="btn btn-primary">Login</button>
  </form>
</template>
