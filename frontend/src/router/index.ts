import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView
    },
    {
        path: "/settings",
        name: "settings",
        component: () => import("../views/Settings.vue")
    },
    {
      path: "/problems",
      name: "problems",
      component: () => import('../views/ProblemView.vue')
    },
    {
        path: "/problems/:contextName/:problemName",
        component: () => import("../views/ProblemDetail.vue"),
    },
    {
        path: "/problems/create",
        name: "problemCreate",
        component: () => import("../views/ProblemCreate.vue"),
    },
  ]
})

export default router
