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
  <div class="dropdown-menu" id="outer">
    <div v-if="msg == 'error'" class="alert alert-danger" role="alert">
      There was an error logging you in.
    </div>
    <div v-if="msg == 'email_sent'" class="alert alert-success" role="alert">
      A login email has been sent to the address if it is registered to a user.
    </div>
    <form @submit.prevent="login">
      <div class="mb-3">
        <label for="email" class="form-label">Email address</label>
        <input type="email" class="form-control " id="email" required v-model="email" />
      </div>
      <button type="submit" class="btn btn-primary">Login</button>
    </form>
  </div>
</template>

<style scoped>
.dropdown-menu {
  min-width: 340px;
  padding: 20px;
}

</style>
