<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";

import AppHeader from "../components/AppHeader.vue";
import VesselDetails from "../components/VesselDetails.vue";
import VesselMap from "../components/VesselMap.vue";
import { getCurrentVessels, getVesselHistory } from "../services/api";

const vessels = ref([]);
const selectedVessel = ref(null);

const vesselDetailsElement = ref(null);

const vesselHistory = ref([]);
const historyLoading = ref(false);
const historyError = ref("");

const isLoading = ref(true);
const errorMessage = ref("");
const lastUpdated = ref(null);

let refreshTimer = null;

const vesselCount = computed(() => vessels.value.length);

async function loadVessels() {
  try {
    errorMessage.value = "";

    const data = await getCurrentVessels();

    vessels.value = data.vessels;
    lastUpdated.value = new Date();

    if (selectedVessel.value) {
      const updatedSelectedVessel = vessels.value.find(
        (vessel) => vessel.mmsi === selectedVessel.value.mmsi,
      );

      if (updatedSelectedVessel) {
        selectedVessel.value = updatedSelectedVessel;
      }
    }
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isLoading.value = false;
  }
}

async function selectVessel(vessel) {
  selectedVessel.value = vessel;

  await loadVesselHistory(vessel);

  await nextTick();

  vesselDetailsElement.value?.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}

function hideVesselDetails() {
  selectedVessel.value = null;
  vesselHistory.value = [];
  historyError.value = "";
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
    const data = await getVesselHistory(vessel.mmsi);

    vesselHistory.value = data.positions ?? [];
  } catch (error) {
    historyError.value = error.message;
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
  await loadVessels();

  refreshTimer = setInterval(loadVessels, 15000);
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

    <div class="dashboard-content">
      <section class="map-panel">
        <div class="map-panel-header">
          <div>
            <h2>Live vessel positions</h2>

            <p>Norwegian maritime area · BarentsWatch AIS</p>
          </div>

          <div class="map-statistics">
            <strong>{{ vesselCount }}</strong>

            <span>active vessels</span>
          </div>
        </div>

        <p v-if="errorMessage" class="map-message error-message">
          {{ errorMessage }}
        </p>

        <p v-else-if="isLoading" class="map-message">
          Loading vessel positions...
        </p>

        <VesselMap
          v-else
          :vessels="vessels"
          :selected-vessel="selectedVessel"
          :vessel-history="vesselHistory"
          @vessel-selected="selectVessel"
        />

        <div
          v-if="selectedVessel"
          ref="vesselDetailsElement"
          class="dashboard-vessel-details"
        >
          <VesselDetails
            :vessel="selectedVessel"
            :history="vesselHistory"
            :history-loading="historyLoading"
            :history-error="historyError"
            @close="hideVesselDetails"
          />
        </div>
      </section>
    </div>
  </main>
</template>
