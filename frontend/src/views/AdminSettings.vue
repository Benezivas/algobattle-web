<script setup lang="ts">
import { type AdminServerSettings, SettingsService } from "@client";
import { onMounted, ref, watch } from "vue";

const settings = ref<AdminServerSettings>();
const state = ref<"plain" | "success" | "error">("plain");

watch(settings, () => state.value = "plain", {deep: true});

onMounted(async () => {
  settings.value = (await SettingsService.getServer()) as AdminServerSettings;
  state.value = "plain";
});

async function saveEdit() {
  if (settings.value) {
    try {
      await SettingsService.editServer({ requestBody: settings.value });
      state.value = "success";
    } catch {
      state.value = "error";
    }
  }
}
</script>

<template>
  <template v-if="settings">
    <h4 class="mt-3">General</h4>
    <div class="form-check form-switch mt-3">
      <input
        class="form-check-input"
        type="checkbox"
        role="switch"
        id="userEditEmail"
        v-model="settings.user_change_email"
      />
      <label class="form-check-label" for="userEditEmail">Let users edit their own email address</label>
    </div>
    <div class="form-check form-switch">
      <input
        class="form-check-input"
        type="checkbox"
        role="switch"
        id="teamEditName"
        v-model="settings.team_change_name"
      />
      <label class="form-check-label" for="teamEditName">Let teams edit their own name</label>
    </div>
    <h4 class="mt-5">Server email</h4>
    <span>Configuration for the email account used to send things like login links.</span>
    <div class="mt-2 row justify-content-start">
      <div class="col-md-12 mb-3">
        <label for="serverEmail" class="form-label">Email address</label>
        <input
          type="email"
          class="form-control mb-0"
          id="serverEmail"
          aria-describedby="serverEmailHelp"
          autocomplete="off"
          v-model="settings.email_config.address"
        />
        <div id="serverEmailHelp" class="form-text">Address used to send the emails</div>
      </div>
      <div class="col-md-3 mb-3">
        <label for="mailServerUrl" class="form-label">Mail server url</label>
        <input
          type="url"
          class="form-control"
          id="mailServerUrl"
          autocomplete="off"
          v-model="settings.email_config.server"
        />
      </div>
      <div class="col-md-9 mb-3">
        <label for="mailServerPort" class="form-label">Port</label>
        <input
          type="number"
          min="0"
          max="65535"
          step="1"
          class="form-control"
          id="mailServerPort"
          autocomplete="off"
          v-model="settings.email_config.port"
        />
      </div>
      <div class="col-md-3 mb-3">
        <label for="mailServerUsername" class="form-label">Username</label>
        <input
          type="text"
          class="form-control mb-0"
          id="mailServerUsername"
          aria-describedby="mailServerUsernameHelp"
          autocomplete="off"
          v-model="settings.email_config.username"
        />
        <div id="mailServerUsernameHelp" class="form-text">Username used to login to the mail server</div>
      </div>
      <div class="col-md-9 mb-3">
        <label for="mailServerPW" class="form-label">Password</label>
        <input
          type="password"
          class="form-control mb-0"
          id="mailServerPW"
          aria-describedby="mailServerPWHelp"
          autocomplete="off"
          v-model="settings.email_config.password"
        />
        <div id="mailServerPWHelp" class="form-text">Used for authentication at the mail server</div>
      </div>
    </div>
    <div id="saveBox">
      <button type="submit" class="btn btn-primary" id="saveButton" @click="saveEdit">Save changes</button>
      <span v-if="state === 'success'" class="text-success notif">
        <i class="bi bi-check-lg"></i> Successfully saved settings
      </span>
      <div v-else-if="state !== 'plain'" class="text-danger notif">
        <i class="bi bi-x-lg"></i> Couldn't save changes
      </div>
    </div>
  </template>
  <div v-else class="d-flex justify-content-center pt-3">
    <div class="spinner-border text-primary" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
  </div>
</template>

<style>
#saveBox {
  margin-top: 1.5rem;
  height: 3rem + 2px;
  align-items: center;
  display: block flex;
  flex-direction: row;
}

.notif {
  margin-left: 1rem;
}
</style>
