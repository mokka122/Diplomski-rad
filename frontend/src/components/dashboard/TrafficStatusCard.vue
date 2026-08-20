<script setup>
import { computed } from "vue";

const props = defineProps({
  predictionStatus: {
    type: Object,
    default: null,
  },

  loading: {
    type: Boolean,
    default: false,
  },
});


const statusLabel = computed(() => {
  if (props.loading) {
    return "Checking";
  }

  if (!props.predictionStatus) {
    return "Unavailable";
  }

  if (props.predictionStatus.ready_for_prediction) {
    return "Ready";
  }

  if (!props.predictionStatus.model_available) {
    return "Training pending";
  }

  if (!props.predictionStatus.live_history_ready) {
    return "Collecting history";
  }

  return "Unavailable";
});


const description = computed(() => {
  if (!props.predictionStatus) {
    return "Prediction service status is currently unavailable.";
  }

  if (props.predictionStatus.ready_for_prediction) {
    return "The live feature pipeline and trained model are ready.";
  }

  if (!props.predictionStatus.model_available) {
    return "The live ML pipeline is ready. Model training will be completed in the final project phase.";
  }

  if (!props.predictionStatus.live_history_ready) {
    return "OceanEye is collecting the hourly history required for live inference.";
  }

  return "Prediction requirements are not currently satisfied.";
});
</script>

<template>
  <article class="prediction-card">
    <div class="prediction-card-top">
      <div>
        <p class="metric-card-label">
          NEXT HOUR
        </p>

        <h3>
          Traffic prediction
        </h3>
      </div>

      <span
        class="prediction-status-pill"
        :class="{
          'prediction-status-pill--ready':
            predictionStatus?.ready_for_prediction,
        }"
      >
        {{ statusLabel }}
      </span>
    </div>

    <div class="prediction-card-main">
      <div class="prediction-placeholder-icon">
        <svg
          viewBox="0 0 48 48"
          aria-hidden="true"
        >
          <path
            d="M24 7 L38 36 L24 31 L10 36 Z"
            fill="currentColor"
          />

          <path
            d="M24 13 V31"
            stroke="white"
            stroke-width="2.2"
            stroke-linecap="round"
          />
        </svg>
      </div>

      <div>
        <strong class="prediction-primary">
          {{
            predictionStatus?.ready_for_prediction
              ? "Prediction ready"
              : "Prediction unavailable"
          }}
        </strong>

        <p>
          {{ description }}
        </p>
      </div>
    </div>

    <div
      v-if="predictionStatus"
      class="prediction-meta"
    >
      <span>
        Features
        <strong>
          {{ predictionStatus.feature_count ?? "—" }}
        </strong>
      </span>

      <span>
        Live history
        <strong>
          {{
            predictionStatus.live_history_ready
              ? "Ready"
              : "Pending"
          }}
        </strong>
      </span>
    </div>
  </article>
</template>