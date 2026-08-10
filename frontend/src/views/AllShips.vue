<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import AppHeader from "../components/AppHeader.vue";
import { getCurrentVessels } from "../services/api";

const vessels = ref([]);
const isLoading = ref(true);
const errorMessage = ref("");
const lastUpdated = ref(null);

let refreshTimer = null;

function vesselName(vessel) {
  return vessel?.vessel_name || "Unknown vessel";
}

function formatNumber(value, decimals = 1) {
  if (value === null || value === undefined) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return number.toFixed(decimals);
}

function formatTimestamp(timestamp) {
  if (!timestamp) {
    return "—";
  }

  return new Date(timestamp).toLocaleString("en-GB", {
    dateStyle: "medium",
    timeStyle: "medium",
  });
}

async function loadVessels() {
  try {
    errorMessage.value = "";

    const data = await getCurrentVessels();

    vessels.value = data.vessels;
    lastUpdated.value = new Date();
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isLoading.value = false;
  }
}

onMounted(async () => {
  await loadVessels();

  refreshTimer = setInterval(loadVessels, 15000);
});

onUnmounted(() => {
  clearInterval(refreshTimer);
});
</script>

<template>
  <main class="all-ships-page">
  <AppHeader />

  <section class="all-ships-content">
    <header class="all-ships-intro">
      <div>
        <p class="sidebar-label">OCEANEYE</p>

        <h1>All ships</h1>

        <p>
          Current vessels received from the live AIS data stream.
        </p>
      </div>

      <div class="all-ships-actions">
        <span>
          {{ vessels.length }} active vessels
        </span>

        <span>
          Last refresh:
          {{ formatTimestamp(lastUpdated) }}
        </span>
      </div>
    </header>

    <p
      v-if="errorMessage"
      class="map-message error-message"
    >
      {{ errorMessage }}
    </p>

    <p
      v-else-if="isLoading"
      class="map-message"
    >
      Loading vessel positions...
    </p>

    <div
      v-else
      class="all-ships-table-wrapper"
    >
      <table class="all-ships-table">
        <thead>
          <tr>
            <th>Vessel</th>
            <th>MMSI</th>
            <th>Speed</th>
            <th>Course</th>
            <th>Heading</th>
            <th>Ship type</th>
            <th>Latitude</th>
            <th>Longitude</th>
            <th>Last message</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="vessel in vessels"
            :key="vessel.mmsi"
          >
            <td>
              <strong>{{ vesselName(vessel) }}</strong>
            </td>

            <td>
              {{ vessel.mmsi }}
            </td>

            <td>
              {{ formatNumber(vessel.sog) }} kn
            </td>

            <td>
              {{ formatNumber(vessel.cog) }}°
            </td>

            <td>
              {{ formatNumber(vessel.heading) }}°
            </td>

            <td>
              {{ vessel.ship_type ?? "—" }}
            </td>

            <td>
              {{ formatNumber(vessel.latitude, 4) }}°
            </td>

            <td>
              {{ formatNumber(vessel.longitude, 4) }}°
            </td>

            <td>
              {{ formatTimestamp(vessel.timestamp) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</main>
</template>