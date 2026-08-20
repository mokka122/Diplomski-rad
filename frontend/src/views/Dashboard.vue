<script setup>
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
} from "vue";

import AppHeader from "../components/AppHeader.vue";
import MetricCard from "../components/dashboard/MetricCard.vue";
import TrafficStatusCard from "../components/dashboard/TrafficStatusCard.vue";
import VesselDetails from "../components/VesselDetails.vue";
import VesselMap from "../components/VesselMap.vue";

import {
  getCurrentTraffic,
  getCurrentVessels,
  getPredictionStatus,
  getVesselHistory,
} from "../services/api";


const vessels = ref([]);
const selectedVessel = ref(null);

const vesselHistory = ref([]);
const historyLoading = ref(false);
const historyError = ref("");

const traffic = ref(null);
const predictionStatus = ref(null);

const isLoading = ref(true);
const trafficLoading = ref(true);
const predictionLoading = ref(true);

const errorMessage = ref("");
const trafficError = ref("");

const lastUpdated = ref(null);

const vesselDetailsElement = ref(null);

let refreshTimer = null;


const vesselCount = computed(() => {
  return vessels.value.length;
});


const averageSpeed = computed(() => {
  const speeds = vessels.value
    .map((vessel) => Number(vessel.sog))
    .filter((value) => Number.isFinite(value));

  if (!speeds.length) {
    return "—";
  }

  const average =
    speeds.reduce(
      (sum, value) => sum + value,
      0,
    ) / speeds.length;

  return average.toFixed(1);
});


const trafficEvents = computed(() => {
  return traffic.value?.total_events ?? 0;
});


const arrivals = computed(() => {
  return traffic.value?.arrivals ?? 0;
});


const departures = computed(() => {
  return traffic.value?.departures ?? 0;
});


function formatTimestamp(timestamp) {
  if (!timestamp) {
    return "—";
  }

  return new Date(timestamp).toLocaleString(
    "en-GB",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  );
}


async function loadVessels() {
  try {
    errorMessage.value = "";

    const data = await getCurrentVessels();

    vessels.value = data.vessels ?? [];

    if (selectedVessel.value) {
      const updatedVessel =
        vessels.value.find(
          (vessel) =>
            vessel.mmsi ===
            selectedVessel.value.mmsi,
        );

      if (updatedVessel) {
        selectedVessel.value =
          updatedVessel;
      }
    }
  } catch (error) {
    errorMessage.value =
      error.message;
  } finally {
    isLoading.value = false;
  }
}


async function loadTraffic() {
  try {
    trafficError.value = "";

    traffic.value =
      await getCurrentTraffic();
  } catch (error) {
    trafficError.value =
      error.message;
  } finally {
    trafficLoading.value = false;
  }
}


async function loadPredictionStatus() {
  try {
    predictionStatus.value =
      await getPredictionStatus();
  } catch {
    predictionStatus.value = null;
  } finally {
    predictionLoading.value = false;
  }
}


async function refreshDashboard() {
  await Promise.allSettled([
    loadVessels(),
    loadTraffic(),
    loadPredictionStatus(),
  ]);

  lastUpdated.value = new Date();
}


async function selectVessel(vessel) {
  selectedVessel.value = vessel;

  await loadVesselHistory(vessel);

  await nextTick();

  if (
    window.matchMedia(
      "(max-width: 760px)",
    ).matches
  ) {
    vesselDetailsElement.value
      ?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
  }
}


async function loadVesselHistory(vessel) {
  if (!vessel?.mmsi) {
    vesselHistory.value = [];
    historyError.value = "";
    return;
  }

  historyLoading.value = true;
  historyError.value = "";
  vesselHistory.value = [];

  try {
    const data =
      await getVesselHistory(
        vessel.mmsi,
      );

    vesselHistory.value =
      data.positions ?? [];
  } catch (error) {
    historyError.value =
      error.message;
  } finally {
    historyLoading.value = false;
  }
}


function closeVesselDetails() {
  selectedVessel.value = null;
  vesselHistory.value = [];
  historyError.value = "";
}


onMounted(async () => {
  await refreshDashboard();

  refreshTimer = setInterval(
    refreshDashboard,
    15000,
  );
});


onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
});
</script>


<template>
  <main class="app-shell">
    <AppHeader />

    <div class="dashboard-page">
      <!-- =====================================================
           PAGE INTRO
           ===================================================== -->

      <section class="dashboard-intro">
        <div>
          <p class="eyebrow">
            LIVE MARITIME MONITORING
          </p>

          <h1>
            Ålesund Maritime Area
          </h1>

          <p class="dashboard-description">
            Real-time vessel monitoring and maritime
            traffic intelligence powered by
            BarentsWatch AIS.
          </p>
        </div>

        <div class="dashboard-refresh-status">
          <span class="dashboard-refresh-dot"></span>

          <div>
            <strong>Live system</strong>

            <span>
              Updated
              {{ formatTimestamp(lastUpdated) }}
            </span>
          </div>
        </div>
      </section>

      <!-- =====================================================
           METRICS
           ===================================================== -->

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
          helper="Ålesund geofence entries"
          variant="arrivals"
        />

        <MetricCard
          label="DEPARTURES THIS HOUR"
          :value="departures"
          helper="Ålesund geofence exits"
          variant="departures"
        />

        <MetricCard
          label="TRAFFIC EVENTS"
          :value="trafficEvents"
          helper="Combined hourly activity"
          variant="traffic"
        />
      </section>

      <p
        v-if="trafficError"
        class="dashboard-inline-error"
      >
        {{ trafficError }}
      </p>

      <!-- =====================================================
           MAIN WORKSPACE
           ===================================================== -->

      <section class="dashboard-workspace">
        <div class="dashboard-map-column">
          <div class="dashboard-panel map-card">
            <div class="dashboard-panel-header">
              <div>
                <p class="dashboard-panel-label">
                  LIVE MAP
                </p>

                <h2>
                  Vessel positions
                </h2>

                <p>
                  BarentsWatch AIS · refreshed every
                  15 seconds
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
                @vessel-selected="selectVessel"
              />
            </div>
          </div>
        </div>

        <!-- ===================================================
             RIGHT COLUMN
             =================================================== -->

        <aside class="dashboard-side-column">
          <TrafficStatusCard
            :prediction-status="predictionStatus"
            :loading="predictionLoading"
          />

          <article class="dashboard-panel traffic-detail-card">
            <div class="dashboard-panel-header compact">
              <div>
                <p class="dashboard-panel-label">
                  CURRENT HOUR
                </p>

                <h2>
                  Traffic composition
                </h2>
              </div>
            </div>

            <div class="traffic-composition-list">
              <div>
                <span>Passenger</span>

                <strong>
                  {{
                    traffic?.passenger_events ?? 0
                  }}
                </strong>
              </div>

              <div>
                <span>Cargo</span>

                <strong>
                  {{
                    traffic?.cargo_events ?? 0
                  }}
                </strong>
              </div>

              <div>
                <span>Fishing</span>

                <strong>
                  {{
                    traffic?.fishing_events ?? 0
                  }}
                </strong>
              </div>

              <div>
                <span>Tanker</span>

                <strong>
                  {{
                    traffic?.tanker_events ?? 0
                  }}
                </strong>
              </div>

              <div>
                <span>Auxiliary</span>

                <strong>
                  {{
                    traffic?.auxiliary_events ?? 0
                  }}
                </strong>
              </div>

              <div>
                <span>Tug</span>

                <strong>
                  {{
                    traffic?.tug_events ?? 0
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
                <small v-if="averageSpeed !== '—'">
                  kn
                </small>
              </strong>
            </div>
          </article>
        </aside>
      </section>

      <!-- =====================================================
           SELECTED VESSEL
           ===================================================== -->

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
            @click="closeVesselDetails"
          >
            Close details
          </button>
        </div>

        <VesselDetails
          :vessel="selectedVessel"
          :history="vesselHistory"
          :history-loading="historyLoading"
          :history-error="historyError"
          @close="closeVesselDetails"
        />
      </section>
    </div>
  </main>
</template>