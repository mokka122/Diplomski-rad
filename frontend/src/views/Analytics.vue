<script setup>
import {
  computed,
  onMounted,
  onUnmounted,
  ref,
} from "vue";

import {
  Bar,
  Doughnut,
  Line,
} from "vue-chartjs";

import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
} from "chart.js";

import AppHeader from "../components/AppHeader.vue";

import {
  getLiveAnalytics,
} from "../services/api";


ChartJS.register(
  ArcElement,
  BarElement,
  CategoryScale,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
);


const analytics = ref(null);

const isLoading = ref(true);

const errorMessage = ref("");

const lastUpdated = ref(null);

let refreshTimer = null;


/* =========================================================
   DATA HELPERS
   ========================================================= */

const hourlyTraffic = computed(() => {
  return (
    analytics.value
      ?.hourly_traffic ??
    []
  );
});


const summary = computed(() => {
  return (
    analytics.value
      ?.summary ??
    {}
  );
});


const coverage = computed(() => {
  return (
    analytics.value
      ?.coverage ??
    {}
  );
});


/* =========================================================
   FORMATTERS
   ========================================================= */

function formatHour(
  timestamp,
) {
  if (!timestamp) {
    return "—";
  }

  return new Date(
    timestamp,
  ).toLocaleTimeString(
    "en-GB",
    {
      hour: "2-digit",
      minute: "2-digit",
    },
  );
}


function formatTimestamp(
  timestamp,
) {
  if (!timestamp) {
    return "—";
  }

  return new Date(
    timestamp,
  ).toLocaleString(
    "en-GB",
    {
      dateStyle:
        "medium",

      timeStyle:
        "medium",
    },
  );
}


function formatPercent(
  value,
) {
  const number =
    Number(value);

  if (
    !Number.isFinite(number)
  ) {
    return "—";
  }

  return `${number.toFixed(1)}%`;
}


/* =========================================================
   CHART LABELS
   ========================================================= */

const hourLabels = computed(() => {
  return hourlyTraffic.value.map(
    (hour) =>
      formatHour(
        hour.timestamp_utc,
      ),
  );
});


/* =========================================================
   ENTRIES VS EXITS
   ========================================================= */

const trafficActivityData = computed(() => {
  return {
    labels:
      hourLabels.value,

    datasets: [
      {
        label:
          "Entries",

        data:
          hourlyTraffic.value.map(
            (hour) =>
              hour.data_available
                ? hour.entries
                : null,
          ),

        borderColor:
          "#1b7f69",

        backgroundColor:
          "rgba(27, 127, 105, 0.12)",

        borderWidth:
          2,

        pointRadius:
          3,

        pointHoverRadius:
          5,

        tension:
          0.3,

        spanGaps:
          false,
      },

      {
        label:
          "Exits",

        data:
          hourlyTraffic.value.map(
            (hour) =>
              hour.data_available
                ? hour.exits
                : null,
          ),

        borderColor:
          "#dd8a3d",

        backgroundColor:
          "rgba(221, 138, 61, 0.10)",

        borderWidth:
          2,

        pointRadius:
          3,

        pointHoverRadius:
          5,

        tension:
          0.3,

        spanGaps:
          false,
      },
    ],
  };
});


/* =========================================================
   HOURLY TRAFFIC
   ========================================================= */

const hourlyVolumeData = computed(() => {
  return {
    labels:
      hourLabels.value,

    datasets: [
      {
        label:
          "Traffic events",

        data:
          hourlyTraffic.value.map(
            (hour) =>
              hour.data_available
                ? hour.total_events
                : null,
          ),

        backgroundColor:
          "rgba(27, 127, 105, 0.72)",

        borderRadius:
          6,

        maxBarThickness:
          24,
      },
    ],
  };
});


/* =========================================================
   VESSEL TYPES
   ========================================================= */

const vesselTypeData = computed(() => {
  const distribution =
    analytics.value
      ?.vessel_type_distribution ??
    {};

  return {
    labels: [
      "Cargo",
      "Passenger",
      "Fishing",
      "Tanker",
      "Auxiliary",
      "Tug",
    ],

    datasets: [
      {
        data: [
          distribution.cargo ??
            0,

          distribution.passenger ??
            0,

          distribution.fishing ??
            0,

          distribution.tanker ??
            0,

          distribution.auxiliary ??
            0,

          distribution.tug ??
            0,
        ],

        backgroundColor: [
          "#1b7f69",
          "#4aa38f",
          "#87b7a9",
          "#d7a15a",
          "#72868b",
          "#344d55",
        ],

        borderColor:
          "#ffffff",

        borderWidth:
          3,

        hoverOffset:
          6,
      },
    ],
  };
});


/* =========================================================
   CHART OPTIONS
   ========================================================= */

const commonChartOptions = {
  responsive:
    true,

  maintainAspectRatio:
    false,

  interaction: {
    intersect:
      false,

    mode:
      "index",
  },

  plugins: {
    legend: {
      position:
        "top",

      align:
        "start",

      labels: {
        usePointStyle:
          true,

        boxWidth:
          8,

        boxHeight:
          8,

        padding:
          18,

        color:
          "#63757a",

        font: {
          size:
            12,
        },
      },
    },

    tooltip: {
      backgroundColor:
        "#14272d",

      padding:
        12,

      cornerRadius:
        8,

      displayColors:
        true,
    },
  },

  scales: {
    x: {
      grid: {
        display:
          false,
      },

      ticks: {
        color:
          "#8b999d",

        maxRotation:
          0,

        autoSkip:
          true,

        maxTicksLimit:
          12,
      },

      border: {
        display:
          false,
      },
    },

    y: {
      beginAtZero:
        true,

      ticks: {
        precision:
          0,

        color:
          "#8b999d",
      },

      grid: {
        color:
          "rgba(221, 230, 227, 0.7)",
      },

      border: {
        display:
          false,
      },
    },
  },
};


const doughnutOptions = {
  responsive:
    true,

  maintainAspectRatio:
    false,

  cutout:
    "68%",

  plugins: {
    legend: {
      position:
        "right",

      labels: {
        usePointStyle:
          true,

        boxWidth:
          8,

        boxHeight:
          8,

        padding:
          16,

        color:
          "#63757a",
      },
    },

    tooltip: {
      backgroundColor:
        "#14272d",

      padding:
        12,

      cornerRadius:
        8,
    },
  },
};


/* =========================================================
   DATA
   ========================================================= */

async function loadAnalytics() {
  try {
    errorMessage.value =
      "";

    const data =
      await getLiveAnalytics(
        24,
      );

    analytics.value =
      data;

    lastUpdated.value =
      new Date();
  } catch (error) {
    errorMessage.value =
      error.message;
  } finally {
    isLoading.value =
      false;
  }
}


onMounted(async () => {
  await loadAnalytics();

  refreshTimer =
    setInterval(
      loadAnalytics,
      15000,
    );
});


onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(
      refreshTimer,
    );
  }
});
</script>


<template>
  <main class="app-shell">
    <AppHeader />

    <div class="analytics-page">
      <!-- =====================================================
           PAGE INTRO
           ===================================================== -->

      <section class="analytics-intro">
        <div>
          <p class="eyebrow">
            LIVE TRAFFIC INTELLIGENCE
          </p>

          <h1>
            Maritime analytics
          </h1>

          <p class="analytics-description">
            Live operational insights based on real-time AIS traffic events and maritime activity.
          </p>
        </div>

        <div class="analytics-live-state">
          <span class="dashboard-refresh-dot"></span>

          <div>
            <strong>
              Live analytics
            </strong>

            <span>
              Updated
              {{
                formatTimestamp(
                  lastUpdated,
                )
              }}
            </span>
          </div>
        </div>
      </section>


      <!-- =====================================================
           ERROR
           ===================================================== -->

      <p
        v-if="errorMessage"
        class="dashboard-inline-error"
      >
        {{ errorMessage }}
      </p>


      <!-- =====================================================
           LOADING
           ===================================================== -->

      <section
        v-if="isLoading"
        class="analytics-loading"
      >
        Loading maritime analytics...
      </section>


      <template v-else-if="analytics">
        <!-- =====================================================
             KPI CARDS
             ===================================================== -->

        <section class="analytics-metrics">
          <article class="analytics-metric-card">
            <span>
              VESSELS INSIDE AREA
            </span>

            <strong>
              {{
                summary
                  .vessels_inside_area ??
                0
              }}
            </strong>

            <small>
              Current geofence state
            </small>
          </article>


          <article class="analytics-metric-card">
            <span>
              ENTRIES TODAY
            </span>

            <strong>
              {{
                summary
                  .entries_today ??
                0
              }}
            </strong>

            <small>
              Arrival-like proxy events
            </small>
          </article>


          <article class="analytics-metric-card">
            <span>
              EXITS TODAY
            </span>

            <strong>
              {{
                summary
                  .exits_today ??
                0
              }}
            </strong>

            <small>
              Departure-like proxy events
            </small>
          </article>


          <article class="analytics-metric-card">
            <span>
              DATA COVERAGE
            </span>

            <strong>
              {{
                formatPercent(
                  coverage
                    .coverage_percent,
                )
              }}
            </strong>

            <small>
              {{
                coverage
                  .observed_hours ??
                0
              }}
              /
              {{
                coverage
                  .requested_hours ??
                24
              }}
              observed hours
            </small>
          </article>
        </section>


        <!-- =====================================================
             COVERAGE NOTICE
             ===================================================== -->

        <section
          v-if="
            Number(
              coverage.coverage_percent,
            ) < 100
          "
          class="analytics-coverage-notice"
        >
          <div>
            <strong>
              Partial historical coverage
            </strong>

            <p>
              {{
                coverage
                  .missing_hours ??
                0
              }}
              hour(s) in the selected 24-hour
              window have no recorded Redis
              observation and are shown as gaps,
              not zero traffic.
            </p>
          </div>

          <span>
            {{
              formatPercent(
                coverage
                  .coverage_percent,
              )
            }}
          </span>
        </section>


        <!-- =====================================================
             MAIN CHART GRID
             ===================================================== -->

        <section class="analytics-grid">
          <article
            class="
              analytics-panel
              analytics-panel--wide
            "
          >
            <div class="analytics-panel-header">
              <div>
                <p class="dashboard-panel-label">
                  TRAFFIC ACTIVITY
                </p>

                <h2>
                  Entries vs exits
                </h2>

                <p>
                  Hourly geofence crossing
                  activity during the last
                  24 hours.
                </p>
              </div>

              <div class="analytics-panel-stat">
                <strong>
                  {{
                    summary
                      .window_total_events ??
                    0
                  }}
                </strong>

                <span>
                  events
                </span>
              </div>
            </div>

            <div class="analytics-chart analytics-chart--line">
              <Line
                :data="trafficActivityData"
                :options="commonChartOptions"
              />
            </div>
          </article>


          <article class="analytics-panel">
            <div class="analytics-panel-header">
              <div>
                <p class="dashboard-panel-label">
                  EVENT DISTRIBUTION
                </p>

                <h2>
                  Vessel types
                </h2>

                <p>
                  Distribution of classified
                  traffic events during the
                  observed window.
                </p>
              </div>
            </div>

            <div class="analytics-chart analytics-chart--doughnut">
              <Doughnut
                :data="vesselTypeData"
                :options="doughnutOptions"
              />
            </div>
          </article>


          <article class="analytics-panel">
            <div class="analytics-panel-header">
              <div>
                <p class="dashboard-panel-label">
                  HOURLY VOLUME
                </p>

                <h2>
                  Traffic events
                </h2>

                <p>
                  Combined ENTRY and EXIT
                  proxy events by hour.
                </p>
              </div>
            </div>

            <div class="analytics-chart analytics-chart--bar">
              <Bar
                :data="hourlyVolumeData"
                :options="commonChartOptions"
              />
            </div>
          </article>
        </section>
      </template>
    </div>
  </main>
</template>