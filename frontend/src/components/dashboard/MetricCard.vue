<script setup>
defineProps({
  label: {
    type: String,
    required: true,
  },

  value: {
    type: [String, Number],
    default: "—",
  },

  helper: {
    type: String,
    default: "",
  },

  variant: {
    type: String,
    default: "default",
  },
});
</script>

<template>
  <article
    class="metric-card"
    :class="`metric-card--${variant}`"
  >
    <div class="metric-card-header">
      <span class="metric-card-label">
        {{ label }}
      </span>

      <span class="metric-card-indicator"></span>
    </div>

    <strong class="metric-card-value">
      {{ value }}
    </strong>

    <p
      v-if="helper"
      class="metric-card-helper"
    >
      {{ helper }}
    </p>
  </article>
</template>