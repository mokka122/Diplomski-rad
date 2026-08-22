<script setup>
import {
  computed,
} from "vue";


const props = defineProps({
  predictionStatus: {
    type: Object,
    default: null,
  },

  prediction: {
    type: Object,
    default: null,
  },

  loading: {
    type: Boolean,
    default: false,
  },

  error: {
    type: String,
    default: "",
  },
});


const statusLabel = computed(() => {
  if (props.loading) {
    return "Checking";
  }

  if (props.error) {
    return "Unavailable";
  }

  if (!props.predictionStatus) {
    return "Unavailable";
  }

  if (
    props.predictionStatus
      .ready_for_prediction &&
    props.prediction
  ) {
    return "Live prediction";
  }

  if (
    !props.predictionStatus
      .model_available
  ) {
    return "Model unavailable";
  }

  if (
    !props.predictionStatus
      .live_history_ready
  ) {
    return "Collecting history";
  }

  return "Preparing";
});


const statusVariant = computed(() => {
  if (
    props.predictionStatus
      ?.ready_for_prediction &&
    props.prediction
  ) {
    return "ready";
  }

  if (props.error) {
    return "error";
  }

  return "pending";
});


const historyAvailable = computed(() => {
  return (
    props.predictionStatus
      ?.history
      ?.available_required_hours ??
    0
  );
});


const historyRequired = computed(() => {
  return (
    props.predictionStatus
      ?.history
      ?.required_hours ??
    25
  );
});


const historyProgress = computed(() => {
  if (
    historyRequired.value <= 0
  ) {
    return 0;
  }

  return Math.min(
    100,
    Math.round(
      (
        historyAvailable.value /
        historyRequired.value
      ) * 100,
    ),
  );
});


const trafficLevel = computed(() => {
  return (
    props.prediction
      ?.traffic_level ??
    null
  );
});


const confidence = computed(() => {
  const value =
    Number(
      props.prediction
        ?.confidence,
    );

  if (
    !Number.isFinite(value)
  ) {
    return null;
  }

  return (
    value * 100
  ).toFixed(1);
});


const probabilities = computed(() => {
  const source =
    props.prediction
      ?.probabilities ??
    {};

  return [
    {
      label: "LOW",
      value:
        Number(
          source.LOW ?? 0,
        ) * 100,
    },

    {
      label: "MEDIUM",
      value:
        Number(
          source.MEDIUM ?? 0,
        ) * 100,
    },

    {
      label: "HIGH",
      value:
        Number(
          source.HIGH ?? 0,
        ) * 100,
    },
  ];
});


const predictionDescription =
  computed(() => {
    if (props.error) {
      return (
        "The prediction service " +
        "is currently unavailable."
      );
    }

    if (
      props.predictionStatus
        ?.ready_for_prediction &&
      props.prediction
    ) {
      return (
        "Predicted maritime traffic " +
        "level for the next hour."
      );
    }

    if (
      !props.predictionStatus
    ) {
      return (
        "Prediction service status " +
        "is currently unavailable."
      );
    }

    if (
      !props.predictionStatus
        .model_available
    ) {
      return (
        "The trained prediction " +
        "model is not available."
      );
    }

    if (
      !props.predictionStatus
        .live_history_ready
    ) {
      return (
        "OceanEye is collecting " +
        "25 consecutive completed " +
        "hours required for live inference."
      );
    }

    return (
      "The prediction pipeline " +
      "is preparing the required inputs."
    );
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
        :class="
          `prediction-status-pill--${statusVariant}`
        "
      >
        {{ statusLabel }}
      </span>
    </div>

    <!-- =========================================
         READY PREDICTION
         ========================================= -->

    <template
      v-if="
        predictionStatus
          ?.ready_for_prediction &&
        prediction
      "
    >
      <div class="prediction-result">
        <div
          class="prediction-level"
          :class="
            `prediction-level--${trafficLevel?.toLowerCase()}`
          "
        >
          {{ trafficLevel }}
        </div>

        <div>
          <span class="prediction-result-label">
            Predicted traffic level
          </span>

          <strong class="prediction-confidence">
            {{ confidence ?? "—" }}%
            confidence
          </strong>
        </div>
      </div>

      <p class="prediction-description">
        {{ predictionDescription }}
      </p>

      <div class="prediction-probabilities">
        <div
          v-for="item in probabilities"
          :key="item.label"
          class="prediction-probability-row"
        >
          <div class="prediction-probability-heading">
            <span>
              {{ item.label }}
            </span>

            <strong>
              {{ item.value.toFixed(1) }}%
            </strong>
          </div>

          <div class="prediction-probability-track">
            <span
              :style="{
                width:
                  `${Math.min(
                    100,
                    item.value,
                  )}%`,
              }"
            ></span>
          </div>
        </div>
      </div>

      <div class="prediction-meta prediction-meta--extended">
        <span>
          Model
          <strong>
            {{
              prediction.model_name ??
              predictionStatus
                ?.selected_model ??
              "—"
            }}
          </strong>
        </span>

        <span>
          Horizon
          <strong>
            {{
              prediction
                .prediction_horizon_hours ??
              1
            }}
            hour
          </strong>
        </span>

        <span>
          Features
          <strong>
            {{
              predictionStatus
                ?.feature_count ??
              "—"
            }}
          </strong>
        </span>

        <span>
          Area
          <strong>
            Ålesund
          </strong>
        </span>
      </div>
    </template>

    <!-- =========================================
         COLLECTING HISTORY
         ========================================= -->

    <template v-else>
      <div class="prediction-card-main">
        <div class="prediction-placeholder-icon">
          <svg
            viewBox="0 0 48 48"
            aria-hidden="true"
          >
            <path
              d="
                M24 7
                L38 36
                L24 31
                L10 36
                Z
              "
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
              loading
                ? "Checking prediction service"
                : (
                  predictionStatus
                    ?.live_history_ready
                    ? "Preparing prediction"
                    : "Collecting traffic history"
                )
            }}
          </strong>

          <p>
            {{ predictionDescription }}
          </p>
        </div>
      </div>

      <div
        v-if="
          predictionStatus &&
          !predictionStatus
            .live_history_ready
        "
        class="prediction-history-progress"
      >
        <div class="prediction-history-heading">
          <span>
            Historical coverage
          </span>

          <strong>
            {{ historyAvailable }}
            /
            {{ historyRequired }}
            hours
          </strong>
        </div>

        <div class="prediction-history-track">
          <span
            :style="{
              width:
                `${historyProgress}%`,
            }"
          ></span>
        </div>

        <small>
          {{ historyProgress }}%
          complete
        </small>
      </div>

      <div
        v-if="predictionStatus"
        class="prediction-meta"
      >
        <span>
          Features
          <strong>
            {{
              predictionStatus
                .feature_count ??
              "—"
            }}
          </strong>
        </span>

        <span>
          Model
          <strong>
            {{
              predictionStatus
                .selected_model ??
              "—"
            }}
          </strong>
        </span>
      </div>
    </template>
  </article>
</template>