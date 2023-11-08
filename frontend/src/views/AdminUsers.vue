<script setup lang="ts">
import HoverBadgeVue from "@/components/HoverBadge.vue";
import Paginator from "@/components/Paginator.vue";
import { TournamentService, TeamService, UserService, type Team, type User, type Tournament } from "@client";
import { Modal } from "bootstrap";
import type { ModelDict } from "@/shared";
import { computed, onMounted, ref, toRaw, watch } from "vue";

const teams = ref<ModelDict<Team>>({});
const users = ref<ModelDict<User>>({});
const tournaments = ref<ModelDict<Tournament>>({});
const offset = ref(0);
const total = ref(0);
let modal: Modal;

const filterData = ref({
  name: "",
  email: "",
  isAdmin: undefined as boolean | undefined,
  tournament: "",
  team: "",
});
const isFiltered = computed(() => {
  return (
    filterData.value.name != "" ||
    filterData.value.email != "" ||
    filterData.value.isAdmin !== undefined ||
    filterData.value.tournament != "" ||
    filterData.value.team != ""
  );
});
onMounted(async () => {
  tournaments.value = await TournamentService.get({});
  modal = Modal.getOrCreateInstance("#userModal");
  search();
});
async function search(offset: number = 0) {
  const result = await UserService.searchUsers({
    name: filterData.value.name || undefined,
    tournament: filterData.value.tournament || undefined,
    offset: offset,
  });
  teams.value = result.teams;
  users.value = result.users;
  total.value = result.total;
}
async function clearSearch() {
  filterData.value = {
    name: "",
    email: "",
    isAdmin: undefined as boolean | undefined,
    tournament: "",
    team: "",
  };
  search();
}
watch(offset, search);

type UserTeams = Omit<User, "teams"> & { teams: Team[] };
const error = ref("");
const editData = ref<UserTeams>(emptyUser());
const teamSearchData = ref({
  name: "",
  tournament: "",
  result: [] as Team[],
});
const confirmDelete = ref(false);
function emptyUser(): UserTeams {
  return {
    id: "",
    name: "",
    email: "",
    is_admin: false,
    teams: [],
  };
}
function teamName(team: Team) {
  return `${team.name} (${team.tournament.name})`;
}

function openModal(user: User | undefined) {
  if (user) {
    editData.value = { ...user, teams: user.teams.map((id) => teams.value[id]) };
  } else {
    editData.value = emptyUser();
  }
  confirmDelete.value = false;
  error.value = "";
  teamSearchData.value = {
    name: "",
    tournament: "",
    result: [],
  };
  searchTeam();
  modal.show();
}
async function searchTeam() {
  const result = await TeamService.get({
    name: teamSearchData.value.name || undefined,
    tournament: teamSearchData.value.tournament || undefined,
  });
  teamSearchData.value.result = Object.values(result.teams)
    .filter((team) => !editData.value.teams.includes(team))
    .slice(0, 5);
}
async function sendData() {
  if (error.value) {
    return;
  }
  if (editData.value.id) {
    const oldTeams = users.value[editData.value.id].teams;
    const newTeams = editData.value.teams.filter((team) => !oldTeams.includes(team.id));
    const removedTeams = oldTeams.filter((id) => !editData.value.teams.map((t) => t.id).includes(id));
    try {
      users.value[editData.value.id] = await UserService.editUser({
        id: editData.value.id,
        requestBody: {
          name: editData.value.name,
          email: editData.value.email,
          is_admin: editData.value.is_admin,
          teams: Object.fromEntries(
            newTeams.map((team) => [team.id, "add"]).concat(removedTeams.map((id) => [id, "remove"]))
          ),
        },
      });
    } catch {
      error.value = "email";
    }
  } else {
    try {
      const newUser = await UserService.createUser({
        requestBody: {
          name: editData.value.name,
          email: editData.value.email,
          is_admin: editData.value.is_admin,
          teams: editData.value.teams.map((t) => t.id),
        },
      });
      users.value[newUser.id] = newUser;
    } catch {
      error.value = "email";
    }
  }
  modal.hide();
}
async function deleteUser() {
  if (!confirmDelete.value) {
    confirmDelete.value = true;
    return;
  } else {
    confirmDelete.value = false;
  }
  await UserService.deleteUser({ id: editData.value.id });
  delete users.value[editData.value.id];
  modal.hide();
}
async function checkEmail() {
  const result = await UserService.searchUsers({
    email: editData.value.email,
    exactSearch: true,
  });
  const userIds = Object.keys(result.teams);
  if (userIds.length != 0 && userIds[0] != editData.value.id) {
    console.log(editData.value);
    error.value = "email";
  } else {
    error.value = "";
  }
}
</script>

<template>
  <table class="table table-hover mb-2" id="users">
    <thead>
      <tr>
        <th scope="col">Name</th>
        <th scope="col">Email</th>
        <th scope="col">Teams</th>
        <th scope="col"></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="user in users" :class="{ 'table-info': user.id == '{{user.id}}' }">
        <td>
          {{ user.name }}
          <i
            v-if="user.is_admin"
            class="bi bi-patch-check-fill text-success ms-1"
            data-bs-toggle="tooltip"
            data-bs-placement="right"
            title="Admin"
          ></i>
        </td>
        <td>{{ user.email }}</td>
        <td>{{ user.teams.map((t) => teamName(teams[t])).join(", ") }}</td>
        <td class="text-end">
          <button
            type="button"
            class="btn btn-warning btn-sm"
            title="Edit user"
            @click="(e) => openModal(user)"
          >
            <i class="bi bi-pencil"></i>
          </button>
        </td>
      </tr>
    </tbody>
  </table>

  <div class="d-flex mb-3 pe-2">
    <button type="button" class="btn btn-primary btn-sm me-auto" @click="(e) => openModal(undefined)">
      Create new user
    </button>
    <button
      type="button"
      class="btn btn-primary btn-sm position-relative"
      data-bs-toggle="collapse"
      data-bs-target="#filters"
      aria-expanded="false"
      aria-controls="filters"
    >
      <i class="bi bi-funnel-fill"></i>
      <span
        class="position-absolute top-0 start-100 translate-middle p-2 bg-danger border border-light rounded-circle"
        v-if="isFiltered"
      >
        <span class="visually-hidden">Applied filters</span>
      </span>
    </button>
    <Paginator v-model="offset" :total="total" />
  </div>

  <div class="d-flex justify-content-end">
    <div class="collapse w-xs" id="filters" aria-labelledby="filterHeading">
      <div class="card card-body">
        <div class="row mb-3">
          <div class="col">
            <label for="nameFilter" class="form-label mb-1">Name</label>
            <input class="form-control" id="nameFilter" type="text" v-model="filterData.name" />
          </div>
          <div class="col">
            <label for="emailFilter" class="form-label mb-1">Email</label>
            <input class="form-control" id="emailFilter" type="text" v-model="filterData.email" />
          </div>
        </div>
        <div class="row mb-3">
          <div class="col">
            <label for="adminFilter" class="form-label mb-1">User type</label>
            <select
              class="form-select"
              id="adminFilter"
              aria-label="User type filter"
              v-model="filterData.isAdmin"
            >
              <option selected :value="null">Any</option>
              <option value="true">Admin</option>
              <option value="false">Non Admin</option>
            </select>
          </div>
          <div class="col"></div>
        </div>
        <div class="row mb-3">
          <div class="col">
            <label for="tournamentFilter" class="form-label mb-1">Tournament</label>
            <select class="form-select" id="tournamentFilter" v-model="filterData.tournament">
              <option :value="null"></option>
              <option v-for="(tournament, id) in tournaments" :value="id">{{ tournament.name }}</option>
            </select>
          </div>
          <div class="col">
            <label for="teamFilter" class="form-label mb-1">Team</label>
            <select class="form-select" id="teamFilter" v-model="filterData.team">
              <option :value="null"></option>
              <option v-for="(team, id) in teams" :value="id">{{ team.name }}</option>
            </select>
          </div>
        </div>
        <div class="row">
          <div class="col text-end align-self-end">
            <a v-if="isFiltered" class="btn btn-secondary me-2" @click="clearSearch" role="button">Clear</a>
            <a class="btn btn-primary" @click="(e) => search()" role="button">Apply</a>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div
    class="modal fade"
    id="userModal"
    tabindex="-1"
    aria-labelledby="modalLabel"
    aria-hidden="true"
    ref="user_modal"
  >
    <div class="modal-dialog modal-dialog-centered">
      <form class="modal-content" @submit.prevent="sendData">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="modalLabel">
            <span v-if="editData.id">Edit user</span>
            <span v-else>Create new user</span>
          </h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <label for="name" class="form-label">Name</label>
          <div class="input-group w-em mb-3">
            <input
              class="form-control"
              type="text"
              v-model="editData.name"
              required
              maxlength="32"
              id="name"
              autocomplete="off"
            />
            <input
              type="checkbox"
              class="btn-check"
              id="set-admin"
              name="is_admin"
              v-model="editData.is_admin"
            />
            <label
              class="btn btn-outline-success btn-sm"
              for="set-admin"
              data-bs-toggle="tooltip"
              title="Admin"
              ><i class="bi bi-patch-check"></i
            ></label>
          </div>
          <label for="email" class="form-label">Email</label>
          <input
            class="form-control"
            :class="{ 'is-invalid': error == 'email' }"
            id="email"
            type="email"
            maxlength="128"
            v-model="editData.email"
            autocomplete="off"
            @change="checkEmail"
            required
          />
          <div class="invalid-feedback">Email already in use by another user</div>
          <span class="form-label mt-3 mb-0 fake-label">Teams</span>
          <div class="d-flex flex-row flex-wrap mb-1">
            <HoverBadgeVue
              v-for="(team, i) in editData.teams"
              type="remove"
              @click="() => editData.teams.splice(i, 1)"
              >{{ teamName(team) }}</HoverBadgeVue
            >
          </div>
          <div class="card mt-2">
            <div class="card-body">
              <h6 class="card-subtitle mb-2">Add team</h6>
              <div class="row mb-2">
                <div class="col">
                  <label for="searchTournament" class="form-label">Tournament</label>
                  <select
                    class="form-select"
                    id="searchTournament"
                    v-model="teamSearchData.tournament"
                    @change="searchTeam"
                  >
                    <option value="" :selected="teamSearchData.tournament == ''">Any</option>
                    <option
                      v-for="(tournament, id) in tournaments"
                      :value="id"
                      :selected="id == teamSearchData.tournament"
                    >
                      {{ tournament.name }}
                    </option>
                  </select>
                </div>
                <div class="col">
                  <label for="searchName" class="form-label">Name</label>
                  <input
                    type="text"
                    class="form-control"
                    id="searchName"
                    v-model="teamSearchData.name"
                    autocomplete="off"
                    @input="searchTeam"
                  />
                </div>
              </div>
              <div class="d-flex flex-row flex-wrap">
                <HoverBadgeVue
                  v-for="team in teamSearchData.result"
                  type="add"
                  @click="() => editData.teams.push(team)"
                  >{{ team.name }}</HoverBadgeVue
                >
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button
            v-if="confirmDelete"
            type="button"
            class="btn btn-secondary"
            @click="(e) => (confirmDelete = false)"
          >
            Cancel
          </button>
          <button v-if="editData.id" type="button" class="btn btn-danger ms-2" @click="deleteUser">
            {{ confirmDelete ? "Confirm deletion" : "Delete user" }}
          </button>
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">{{ editData.id ? "Save" : "Create" }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<style>
.teams-box {
  min-height: 1.5rem;
}
fake-label {
  margin-bottom: 0.5rem;
}
</style>
