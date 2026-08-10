<script setup>
import { ref } from "vue";

const isMenuOpen = ref(false);

function closeMenu() {
  isMenuOpen.value = false;
}
</script>

<template>
  <header class="app-header">
    <RouterLink
      to="/"
      class="brand"
      aria-label="Go to OceanEye dashboard"
      @click="closeMenu"
    >
      <div class="logo-slot">
        <img
          src="/logo.png"
          alt="OceanEye logo"
        />
      </div>
    </RouterLink>

    <nav class="main-navigation">
      <RouterLink
        to="/"
        class="nav-link"
      >
        Dashboard
      </RouterLink>

      <RouterLink
        to="/all-ships"
        class="nav-link"
      >
        All ships
      </RouterLink>
    </nav>

    <div class="header-actions">
      <span class="live-status">
        <span class="live-dot"></span>
        Live data
      </span>

      <button
        class="menu-button"
        type="button"
        aria-label="Open navigation menu"
        :aria-expanded="isMenuOpen"
        @click="isMenuOpen = !isMenuOpen"
      >
        <span></span>
        <span></span>
        <span></span>
      </button>
    </div>

    <div
      v-if="isMenuOpen"
      class="mobile-navigation"
    >
      <RouterLink
        to="/"
        class="mobile-nav-link"
        @click="closeMenu"
      >
        Dashboard
      </RouterLink>

      <RouterLink
        to="/all-ships"
        class="mobile-nav-link"
        @click="closeMenu"
      >
        All ships
      </RouterLink>
    </div>
  </header>
</template>