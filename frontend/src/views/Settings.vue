<script setup lang="ts">
import { store } from "@/main";
import { UserService } from "@client";
import { ref } from "vue";

const userEdit = ref({
  email: store.user?.email,
});
const error = ref("");

async function saveEdit() {
  const newUser = await UserService.settings({
      email: userEdit.value.email,
  });
  store.user = newUser;
  error.value = "success";
}
</script>

<template>
  <div class="alert alert-success" role="alert" v-if="error == 'success'">Changes have been saved.</div>
  <h3>User settings</h3>
  <label class="form-label" for="emailInput">Email address</label>
  <input type="email" class="form-control  mb-2" id="emailInput" v-model="userEdit.email" />
  <button type="submit" class="btn btn-primary mt-4" @click="saveEdit">Save changes</button>
</template>
