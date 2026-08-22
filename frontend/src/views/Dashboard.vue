<script setup>
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from "vue";

import {
  useRoute,
  useRouter,
} from "vue-router";

import AppHeader from "../components/AppHeader.vue";
import MetricCard from "../components/dashboard/MetricCard.vue";
import TrafficStatusCard from "../components/dashboard/TrafficStatusCard.vue";
import VesselDetails from "../components/VesselDetails.vue";
import VesselMap from "../components/VesselMap.vue";

import {
  getCurrentTraffic,
  getCurrentVessels,
  getLivePrediction,
  getPredictionStatus,
  getVesselHistory,
} from "../services/api";


const route = useRoute();
const router = useRouter();


const vessels =
  ref([]);

const selectedVessel =
  ref(null);

const vesselHistory =
  ref([]);

const historyLoading =
  ref(false);

const historyError =
  ref("");

const traffic =
  ref(null);

const predictionStatus =
  ref(null);

const prediction =
  ref(null);

const isLoading =
  ref(true);

const trafficLoading =
  ref(true);

const predictionLoading =
  ref(true);

const errorMessage =
  ref("");

const trafficError =
  ref("");

const predictionError =
  ref("");

const lastUpdated =
  ref(null);

const vesselDetailsElement =
  ref(null);

let refreshTimer =
  null;


/* =========================================================
   BASIC METRICS
   ========================================================= */

const vesselCount =
  computed(
    () =>
      vessels.value.length,
  );


const averageSpeed =
  computed(() => {
    const speeds =
      vessels.value
        .map(
          (vessel) =>
            Number(
              vessel.sog,
            ),
        )
        .filter(
          (value) =>
            Number.isFinite(
              value,
            ),
        );

    if (
      !speeds.length
    ) {
      return "—";
    }

    const average =
      speeds.reduce(
        (
          sum,
          value,
        ) =>
          sum + value,
        0,
      ) /
      speeds.length;

    return average
      .toFixed(1);
  });


const trafficEvents =
  computed(
    () =>
      traffic.value
        ?.total_events ??
      0,
  );


const arrivals =
  computed(
    () =>
      traffic.value
        ?.arrivals ??
      0,
  );


const departures =
  computed(
    () =>
      traffic.value
        ?.departures ??
      0,
  );


/* =========================================================
   LIVE VESSEL COMPOSITION
   ========================================================= */

function vesselGroup(
  shipType,
) {
  const value =
    Number(
      shipType,
    );

  if (
    !Number.isFinite(
      value,
    )
  ) {
    return "other";
  }

  if (
    value === 30
  ) {
    return "fishing";
  }

  if (
    value === 31 ||
    value === 32 ||
    value === 52
  ) {
    return "tug";
  }

  if (
    value >= 60 &&
    value <= 69
  ) {
    return "passenger";
  }

  if (
    value >= 70 &&
    value <= 79
  ) {
    return "cargo";
  }

  if (
    value >= 80 &&
    value <= 89
  ) {
    return "tanker";
  }

  if (
    [
      33,
      34,
      35,
      50,
      51,
      53,
      54,
      55,
      58,
      59,
    ].includes(
      value,
    )
  ) {
    return "auxiliary";
  }

  return "other";
}


const vesselComposition =
  computed(() => {
    const result = {
      passenger:
        0,

      cargo:
        0,

      fishing:
        0,

      tanker:
        0,

      auxiliary:
        0,

      tug:
        0,

      other:
        0,
    };

    vessels.value
      .forEach(
        (vessel) => {
          const group =
            vesselGroup(
              vessel.ship_type,
            );

          result[group] +=
            1;
        },
      );

    return result;
  });


/* =========================================================
   FORMATTERS
   ========================================================= */

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
        "short",
    },
  );
}


/* =========================================================
   LOAD VESSELS
   ========================================================= */

async function loadVessels() {
  try {
    errorMessage.value =
      "";

    const data =
      await getCurrentVessels();

    vessels.value =
      data.vessels ??
      [];

    if (
      selectedVessel.value
    ) {
      const updated =
        vessels.value
          .find(
            (vessel) =>
              String(
                vessel.mmsi,
              ) ===
              String(
                selectedVessel
                  .value
                  .mmsi,
              ),
          );

      if (updated) {
        selectedVessel.value =
          updated;
      }
    }
  } catch (error) {
    errorMessage.value =
      error.message;
  } finally {
    isLoading.value =
      false;
  }
}


/* =========================================================
   TRAFFIC
   ========================================================= */

async function loadTraffic() {
  try {
    trafficError.value =
      "";

    traffic.value =
      await getCurrentTraffic();
  } catch (error) {
    trafficError.value =
      error.message;
  } finally {
    trafficLoading.value =
      false;
  }
}


/* =========================================================
   PREDICTION
   ========================================================= */

async function loadPrediction() {
  predictionLoading.value =
    true;

  predictionError.value =
    "";

  try {
    predictionStatus.value =
      await getPredictionStatus();

    if (
      predictionStatus
        .value
        ?.ready_for_prediction
    ) {
      prediction.value =
        await getLivePrediction();
    } else {
      prediction.value =
        null;
    }
  } catch (error) {
    predictionError.value =
      error.message;

    prediction.value =
      null;
  } finally {
    predictionLoading.value =
      false;
  }
}


/* =========================================================
   VESSEL HISTORY
   ========================================================= */

async function loadVesselHistory(
  vessel,
) {
  if (
    !vessel?.mmsi
  ) {
    vesselHistory.value =
      [];

    historyError.value =
      "";

    return;
  }

  historyLoading.value =
    true;

  historyError.value =
    "";

  vesselHistory.value =
    [];

  try {
    const data =
      await getVesselHistory(
        vessel.mmsi,
      );

    vesselHistory.value =
      data.positions ??
      [];
  } catch (error) {
    historyError.value =
      error.message;
  } finally {
    historyLoading.value =
      false;
  }
}


/* =========================================================
   SELECT VESSEL
   ========================================================= */

async function selectVessel(
  vessel,
  updateRoute = true,
) {
  selectedVessel.value =
    vessel;

  if (
    updateRoute
  ) {
    await router.replace({
      name:
        "dashboard",

      query: {
        vessel:
          String(
            vessel.mmsi,
          ),
      },
    });
  }

  await loadVesselHistory(
    vessel,
  );

  await nextTick();

  if (
    window.matchMedia(
      "(max-width: 760px)",
    ).matches
  ) {
    vesselDetailsElement
      .value
      ?.scrollIntoView({
        behavior:
          "smooth",

        block:
          "start",
      });
  }
}


async function selectVesselFromRoute() {
  const requestedMmsi =
    route.query.vessel;

  if (
    !requestedMmsi
  ) {
    return;
  }

  const vessel =
    vessels.value
      .find(
        (item) =>
          String(
            item.mmsi,
          ) ===
          String(
            requestedMmsi,
          ),
      );

  if (!vessel) {
    return;
  }

  if (
    selectedVessel
      .value
      ?.mmsi ===
    vessel.mmsi
  ) {
    return;
  }

  await selectVessel(
    vessel,
    false,
  );
}


async function closeVesselDetails() {
  selectedVessel.value =
    null;

  vesselHistory.value =
    [];

  historyError.value =
    "";

  await router.replace({
    name:
      "dashboard",
  });
}


/* =========================================================
   REFRESH
   ========================================================= */

async function refreshDashboard() {
  await Promise.allSettled(
    [
      loadVessels(),
      loadTraffic(),
      loadPrediction(),
    ],
  );

  await selectVesselFromRoute();

  lastUpdated.value =
    new Date();
}


onMounted(async () => {
  await refreshDashboard();

  refreshTimer =
    setInterval(
      refreshDashboard,
      15000,
    );
});


watch(
  () =>
    route.query.vessel,

  async () => {
    await selectVesselFromRoute();
  },
);


onUnmounted(() => {
  if (
    refreshTimer
  ) {
    clearInterval(
      refreshTimer,
    );
  }
});
</script>


<template>
  <main class="app-shell">
    <AppHeader />

    <div class="dashboard-page">
      <section class="dashboard-intro">
        <div>
          <p class="eyebrow">
            LIVE MARITIME MONITORING
          </p>

          <h1>
            Ålesund Maritime Area
          </h1>

          <p class="dashboard-description">
            Real-time vessel monitoring and
            maritime traffic intelligence
            powered by BarentsWatch AIS.
          </p>
        </div>

        <div class="dashboard-refresh-status">
          <span
            class="dashboard-refresh-dot"
          ></span>

          <div>
            <strong>
              Live system
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

      <section class="dashboard-metrics">
        <MetricCard
          label="ACTIVE VESSELS"
          :value="vesselCount"
          helper="Current AIS vessel states"
          variant="vessels"
        />

        <MetricCard
          label="ARRIVALS THIS HOUR"
          :value="arrivals"
          helper="Study-area geofence entries"
          variant="arrivals"
        />

        <MetricCard
          label="DEPARTURES THIS HOUR"
          :value="departures"
          helper="Study-area geofence exits"
          variant="departures"
        />

        <MetricCard
          label="TRAFFIC EVENTS"
          :value="trafficEvents"
          helper="Combined hourly geofence activity"
          variant="traffic"
        />
      </section>

      <p
        v-if="trafficError"
        class="dashboard-inline-error"
      >
        {{ trafficError }}
      </p>

      <section class="dashboard-workspace">
        <div class="dashboard-map-column">
          <div
            class="
              dashboard-panel
              map-card
            "
          >
            <div class="dashboard-panel-header">
              <div>
                <p class="dashboard-panel-label">
                  LIVE MAP
                </p>

                <h2>
                  Vessel positions
                </h2>

                <p>
                  BarentsWatch AIS · refreshed
                  every 15 seconds
                </p>
              </div>

              <div class="map-summary">
                <strong>
                  {{ vesselCount }}
                </strong>

                <span>
                  vessels
                </span>
              </div>
            </div>

            <div class="dashboard-map-wrapper">
              <div
                v-if="isLoading"
                class="dashboard-map-state"
              >
                Loading live AIS positions...
              </div>

              <div
                v-else-if="errorMessage"
                class="
                  dashboard-map-state
                  dashboard-map-state--error
                "
              >
                {{ errorMessage }}
              </div>

              <VesselMap
                v-else
                :vessels="vessels"
                :selected-vessel="selectedVessel"
                :vessel-history="vesselHistory"
                @vessel-selected="
                  selectVessel
                "
              />
            </div>
          </div>
        </div>

        <aside class="dashboard-side-column">
          <TrafficStatusCard
            :prediction-status="
              predictionStatus
            "
            :prediction="
              prediction
            "
            :loading="
              predictionLoading
            "
            :error="
              predictionError
            "
          />

          <article
            class="
              dashboard-panel
              traffic-detail-card
            "
          >
            <div
              class="
                dashboard-panel-header
                compact
              "
            >
              <div>
                <p class="dashboard-panel-label">
                  LIVE AIS
                </p>

                <h2>
                  Active vessel composition
                </h2>
              </div>
            </div>

            <div class="traffic-composition-list">
              <div>
                <span>
                  Passenger
                </span>

                <strong>
                  {{
                    vesselComposition
                      .passenger
                  }}
                </strong>
              </div>

              <div>
                <span>
                  Cargo
                </span>

                <strong>
                  {{
                    vesselComposition
                      .cargo
                  }}
                </strong>
              </div>

              <div>
                <span>
                  Fishing
                </span>

                <strong>
                  {{
                    vesselComposition
                      .fishing
                  }}
                </strong>
              </div>

              <div>
                <span>
                  Tanker
                </span>

                <strong>
                  {{
                    vesselComposition
                      .tanker
                  }}
                </strong>
              </div>

              <div>
                <span>
                  Auxiliary
                </span>

                <strong>
                  {{
                    vesselComposition
                      .auxiliary
                  }}
                </strong>
              </div>

              <div>
                <span>
                  Tug
                </span>

                <strong>
                  {{
                    vesselComposition
                      .tug
                  }}
                </strong>
              </div>

              <div>
                <span>
                  Other / unknown
                </span>

                <strong>
                  {{
                    vesselComposition
                      .other
                  }}
                </strong>
              </div>
            </div>

            <div class="traffic-average-speed">
              <span>
                Average vessel speed
              </span>

              <strong>
                {{ averageSpeed }}

                <small
                  v-if="
                    averageSpeed !==
                    '—'
                  "
                >
                  kn
                </small>
              </strong>
            </div>
          </article>
        </aside>
      </section>

      <section
        v-if="selectedVessel"
        ref="vesselDetailsElement"
        class="selected-vessel-section"
      >
        <div class="selected-vessel-heading">
          <div>
            <p class="eyebrow">
              VESSEL CONTEXT
            </p>

            <h2>
              Selected vessel
            </h2>
          </div>

          <button
            class="secondary-button"
            type="button"
            @click="
              closeVesselDetails
            "
          >
            Close details
          </button>
        </div>

        <VesselDetails
          :vessel="
            selectedVessel
          "
          :history="
            vesselHistory
          "
          :history-loading="
            historyLoading
          "
          :history-error="
            historyError
          "
        />
      </section>
    </div>
  </main>
</template>