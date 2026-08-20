import { createRouter, createWebHistory } from "vue-router";

import Dashboard from "../views/Dashboard.vue";
import AllShips from "../views/AllShips.vue";
import Login from "../views/Login.vue";
import { getCurrentUser } from "../services/auth";

const router = createRouter({
  history: createWebHistory(),

  routes: [
    {
      path: "/login",
      name: "login",
      component: Login,
      meta: {
        public: true,
      },
    },

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

    {
      path: "/:pathMatch(.*)*",
      redirect: "/",
    },
  ],
});

router.beforeEach(async (to) => {
  /*
   * Login itself is public.
   *
   * If the user already has a valid session,
   * there is no reason to show Login again.
   */

  if (to.name === "login") {
    try {
      const user = await getCurrentUser();

      if (user) {
        return {
          name: "dashboard",
        };
      }
    } catch {
      /*
       * If session verification fails,
       * allow Login to render.
       */
    }

    return true;
  }

  /*
   * Every other OceanEye page requires
   * an authenticated user.
   */

  try {
    const user = await getCurrentUser();

    if (!user) {
      return {
        name: "login",

        query: {
          redirect: to.fullPath,
        },
      };
    }

    return true;
  } catch {
    return {
      name: "login",

      query: {
        redirect: to.fullPath,
      },
    };
  }
});

router.afterEach((to) => {
  const titles = {
    login:
      "Sign in · OceanEye",

    dashboard:
      "Dashboard · OceanEye",

    "all-ships":
      "All vessels · OceanEye",
  };


  document.title =
    titles[to.name] ??
    "OceanEye · Maritime Monitoring";
});

export default router;
