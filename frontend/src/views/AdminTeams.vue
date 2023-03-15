<script setup lang="ts">
import HoverBadgeVue from '@/components/HoverBadge.vue';
import { contextApi, teamApi, userApi, type ModelDict } from '@/main';
import { Modal } from 'bootstrap';
import type { AlgobattleWebModelsTeamSchema, Context, User } from 'typescript_client';
import { computed, onMounted, ref } from 'vue';


const teams = ref<ModelDict<AlgobattleWebModelsTeamSchema>>({})
const users = ref<ModelDict<User>>({})
const contexts = ref<ModelDict<Context>>({})
const currPage = ref(1)
const maxPage = ref(1)

const searchData = ref({
  name: "",
  context: "",
  limit: 25,
})
const isFiltered = computed(() => {
  return searchData.value.name != "" || searchData.value.context != "" || searchData.value.limit != 25
})
let modal: Modal
onMounted(async () => {
  contexts.value = await contextApi.allContexts()
  modal = Modal.getOrCreateInstance("#teamModal")
  search()
})

async function search(page: number = 1) {
  const result = await teamApi.searchTeam({
    name: searchData.value.name || undefined,
    context: searchData.value.context || undefined,
    limit: searchData.value.limit,
    page: page,
  })
  teams.value = result.teams
  users.value = result.users
  currPage.value = result.page
  maxPage.value = result.maxPage
}
async function clearSearch() {
  searchData.value = {
    name: "",
    context: "",
    limit: 25,
  }
  search()
}

const error = ref("")
const editData = ref<AlgobattleWebModelsTeamSchema>(emptyTeam())
const userSearchData = ref({
  name: "",
  email: "",
  result: [] as User[],
})
const confirmDelete = ref(false)

function emptyTeam(): AlgobattleWebModelsTeamSchema {
  return {
    id: "",
    name: "",
    context: "",
    members: [],
  }
}
function openModal(team: AlgobattleWebModelsTeamSchema | undefined) {
  editData.value = team || emptyTeam()
  confirmDelete.value = false
  error.value = ""
  userSearchData.value = {
    name: "",
    email: "",
    result: [],
  }
  userSearch()
  modal.show()
}
async function userSearch() {
  const result = await userApi.searchUsers({
    name: userSearchData.value.name || undefined,
    email: userSearchData.value.email || undefined,
    limit: editData.value.members.length + 5,
    page: 1,
  })
  userSearchData.value.result = Object.values(result.users).filter(u => !editData.value.members.includes(u.id)).slice(0, 5)
}
async function sendData() {
  if (error.value) {
    return
  }
  try {
    if (editData.value.id) {
      const oldMembers = teams.value[editData.value.id].members
      const newMembers = editData.value.members.filter(id => !oldMembers.includes(id))
      const deletedMembers = oldMembers.filter(id => !editData.value.members.includes(id))
      teams.value[editData.value.id] = await teamApi.editTeam({
        id: editData.value.id,
        editTeam: {
          name: editData.value.name,
          context: editData.value.context,
          members: Object.fromEntries(newMembers.map(id => [id, "add"]).concat(deletedMembers.map(id => [id, "remove"])))
        }
      })
    } else {
      const newTeam = await teamApi.createTeam({
        createTeam: {
          name: editData.value.name,
          context: editData.value.context,
          members: editData.value.members,
        }
      })
      teams.value[newTeam.id] = newTeam
    }
    modal.hide()
  } catch {
    error.value = "name"
  }
}
async function deleteTeam() {
  if (!confirmDelete.value) {
    confirmDelete.value = true
    return
  } else {
    confirmDelete.value = false
  }
  await teamApi.deleteTeam({id: editData.value.id})
  delete teams.value[editData.value.id]
  modal.hide()
}
async function checkName() {
  const result = await teamApi.searchTeam({
    name: editData.value.name,
    context: editData.value.context,
    limit: 1,
    exactName: true,
  })
  const teamIds = Object.keys(result.teams)
  if (teamIds.length != 0 && teamIds[0] != editData.value.id ) {
    error.value = "name"
  } else {
    error.value = ""
  }
}
</script>

<template>
  <table class="table">
    <thead>
      <tr>
        <th scope="col">Name</th>
        <th scope="col">Context</th>
        <th scope="col">Members</th>
        <th scope="col"></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(team, id) in teams" :team="team" :key="id">
        <td>{{ team.name }}</td>
        <td>{{ contexts[team.context].name }}</td>
        <td>{{ team.members.map(u => users[u].name).join(", ") }}</td>
        <td class="text-end">
          <button type="button" class="btn btn-sm btn-warning" title="Edit team" @click="e => openModal(team)"><i class="bi bi-pencil"></i></button>
        </td>
      </tr>
    </tbody>
  </table>

  <div class="d-flex mb-3 pe-2">
    <button type="button" class="btn btn-primary btn-sm me-auto" @click="e => openModal(undefined)">Create new team</button>
    <button type="button" class="btn btn-primary btn-sm position-relative" data-bs-toggle="collapse" data-bs-target="#filters" aria-expanded="false" aria-controls="filters">
      <i class="bi bi-funnel-fill"></i>
      <span class="position-absolute top-0 start-100 translate-middle p-2 bg-danger border border-light rounded-circle" v-if="isFiltered">
        <span class="visually-hidden">Applied filters</span>
      </span>
    </button>
    <nav v-if="maxPage != 1" aria-label="Table pagination">
      <ul class="pagination pagination-sm justify-content-end mb-0 ms-2">
        <li class="page-item"><a class="page-link" :class="{disabled: currPage <= 1}" @click="e => search(1)"><i class="bi bi-chevron-double-left"></i></a></li>
        <li class="page-item"><a class="page-link" :class="{disabled: currPage <= 1}" @click="e => search(currPage - 1)"><i class="bi bi-chevron-compact-left"></i></a></li>
        <li class="page-item"><a class="page-link" href="#">{{ currPage }} / maxPage</a></li>
        <li class="page-item"><a class="page-link" :class="{disabled: currPage >= maxPage}" @click="e => search(currPage + 1)"><i class="bi bi-chevron-compact-right"></i></a></li>
        <li class="page-item"><a class="page-link" :class="{disabled: currPage >= maxPage}" @click="e => search(maxPage)"><i class="bi bi-chevron-double-right"></i></a></li>
      </ul>
    </nav>
  </div>

  <div class="d-flex justify-content-end">
    <div class="collapse w-xs" id="filters" aria-labelledby="filterHeading">
      <div class="card card-body">
        <div class="row mb-3">
          <div class="col">
            <label for="nameFilter" class="form-label mb-1">Name</label>
            <input class="form-control w-em" id="nameFilter" type="text" v-model="searchData.name">
          </div>
          <div class="col">
            <label for="contextFilter" class="form-label mb-1">Context</label>
            <select class="form-select w-em" id="contextFilter" v-model="searchData.context">
              <option value=""></option>
              <option v-for="(context, id) in contexts" :value="id">{{ context.name }}</option>
            </select>
          </div>
        </div>
        <div class="row">
          <div class="col">
            <label for="limitFilter" class="form-label mb-1">Limit</label>
            <input class="form-control w-em" id="limitFilter" type="number" min="1" max="200" step="1" v-model="searchData.limit">
          </div>
          <div class="col text-end align-self-end">
            <button v-if="isFiltered" class="btn btn-secondary me-2" @click="clearSearch">Clear</button>
            <button class="btn btn-primary" @click="e => search()">Apply</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="modal fade" id="teamModal" tabindex="-1" aria-labelledby="modalLabel" aria-hidden="true" ref="user_modal">
    <div class="modal-dialog modal-dialog-centered">
      <form class="modal-content" @submit.prevent="sendData">
        <div class="modal-header">
          <h1 class="modal-title fs-5" id="modalLabel">
          <span v-if="editData.id">Edit team</span>
          <span v-else>Create new team</span>
          </h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <label for="name" class="form-label">Name</label>
          <input class="form-control w-em" type="text" v-model="editData.name" required :class="{'is-invalid': error == 'name'}" @change="checkName">
          <div class="invalid-feedback">
            Another team with the same name already exists in this context
          </div>
          <label for="context" class="form-label">Context</label>
          <select class="form-select w-em mb-3" name="context" v-model="editData.context" :required="editData.id != ''" @change="checkName">
            <option v-for="(context, id) in contexts" :value="id" :selected="id == editData.context">{{ context.name }}</option>
          </select>
          <label for="members" class="form-label mb-0">Members</label>
          <div class="d-flex flex-row mb-1 members-box">
            <HoverBadgeVue v-for="(id, i) in editData.members" type="remove" @click="() => editData.members.splice(i, 1)">{{ users[id].name }}</HoverBadgeVue>
          </div>
          <div class="card mt-2">
            <div class="card-body">
              <h6 class="card-subtitle mb-2">Add user</h6>
              <div class="row mb-2">
                <div class="col">
                  <label for="searchName" class="form-label">Name</label>
                  <input type="text" class="form-control form-control-sm" id="searchName" v-model="userSearchData.name" @input="userSearch">
                </div>
                <div class="col">
                  <label for="searchEmail" class="form-label">Email</label>
                  <input type="text" class="form-control form-control-sm" id="searchEmail" v-model="userSearchData.email" @input="userSearch">
                </div>
              </div>
              <div class="d-flex flex-row members-box">
                <HoverBadgeVue v-for="user in userSearchData.result" type="add" @click="() => editData.members.push(user.id)">{{ user.name }}</HoverBadgeVue>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button v-if="confirmDelete" type="button" class="btn btn-secondary" @click="(e) => confirmDelete = false">Cancel</button>
          <button v-if="editData.id" type="button" class="btn btn-danger ms-2" @click="deleteTeam">
            {{confirmDelete ? "Confirm deletion" : "Delete context"}}
          </button>
          <button type="button" class="btn btn-secondary ms-auto" data-bs-dismiss="modal">Discard</button>
          <button type="submit" class="btn btn-primary">{{ editData.id ? "Save" : "Create" }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<style>
.members-box {
  min-height: 1.5rem;
}
</style>
