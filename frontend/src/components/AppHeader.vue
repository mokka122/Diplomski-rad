<script setup>
import { computed, onMounted, ref } from "vue";

import { RouterLink, useRouter } from "vue-router";

import { getCurrentUser, logout } from "../services/auth";

const router = useRouter();

const isMenuOpen = ref(false);

const user = ref(null);

const userInitial = computed(() => {
  const name = user.value?.name || user.value?.email || "O";

  return name.charAt(0).toUpperCase();
});

const isUserMenuOpen = ref(false);

function toggleUserMenu() {
  isUserMenuOpen.value = !isUserMenuOpen.value;
}

function closeUserMenu() {
  isUserMenuOpen.value = false;
}

function toggleMenu() {
  isMenuOpen.value = !isMenuOpen.value;
}

function closeMenu() {
  isMenuOpen.value = false;
}

async function signOut() {
  await logout();
  closeUserMenu();

  closeMenu();

  await router.replace("/login");
}

onMounted(async () => {
  user.value = await getCurrentUser();
});
</script>
<template>
  <header class="app-header">
    <div class="app-header-inner">
      <RouterLink
        class="app-brand"
        to="/"
        aria-label="OceanEye dashboard"
        @click="closeMenu"
      >
        <img class="app-brand-logo" src="/logo.png" alt="OceanEye" />
      </RouterLink>

      <nav class="desktop-navigation" aria-label="Primary navigation">
        <RouterLink class="nav-link" to="/"> Dashboard </RouterLink>

        <RouterLink class="nav-link" to="/all-ships"> All vessels </RouterLink>
      </nav>

      <div class="app-header-actions">
        <div class="live-indicator">
          <span class="live-indicator-dot"></span>

          <span>Live AIS</span>
        </div>
        <div v-if="user" class="user-account">
          <button
            class="user-menu-trigger"
            type="button"
            :aria-expanded="isUserMenuOpen"
            @click="toggleUserMenu"
          >
            <img
              v-if="user.picture"
              class="user-avatar-image"
              :src="user.picture"
              alt=""
              referrerpolicy="no-referrer"
            />

            <div v-else class="user-avatar">
              {{ userInitial }}
            </div>

            <div class="user-chip-copy">
              <strong>
                {{ user.name || "OceanEye user" }}
              </strong>

              <span>
                {{ user.email }}
              </span>
            </div>

            <svg
              class="user-menu-chevron"
              viewBox="0 0 20 20"
              aria-hidden="true"
            >
              <path d="M6 8 L10 12 L14 8" />
            </svg>
          </button>

          <Transition name="user-menu">
            <div v-if="isUserMenuOpen" class="user-menu-dropdown">
              <div class="user-menu-info">
                <span> Signed in as </span>

                <strong>
                  {{ user.email }}
                </strong>
              </div>

              <button type="button" @click="signOut">Sign out</button>
            </div>
          </Transition>
        </div>

        <button
          class="mobile-menu-button"
          type="button"
          aria-label="Toggle navigation"
          :aria-expanded="isMenuOpen"
          @click="toggleMenu"
        >
          <span></span>
          <span></span>
          <span></span>
        </button>
      </div>
    </div>

    <Transition name="mobile-nav">
      <nav
        v-if="isMenuOpen"
        class="mobile-navigation"
        aria-label="Mobile navigation"
      >
        <RouterLink class="mobile-nav-link" to="/" @click="closeMenu">
          Dashboard
        </RouterLink>

        <RouterLink class="mobile-nav-link" to="/all-ships" @click="closeMenu">
          All vessels
        </RouterLink>
        <button
          class="mobile-nav-link mobile-signout-button"
          type="button"
          @click="signOut"
        >
          Sign out
        </button>
      </nav>
    </Transition>
  </header>
</template>
