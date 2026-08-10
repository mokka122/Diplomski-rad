import { createRouter, createWebHistory } from "vue-router";

import Dashboard from "../views/Dashboard.vue";
import AllShips from "../views/AllShips.vue";

const router = createRouter({
  history: createWebHistory(),

  routes: [
    {
      path: "/",
      name: "dashboard",
      component: Dashboard,
    },

    {
      path: "/all-ships",
      name: "all-ships",
      component: AllShips,
    },
  ],
});

export default router;