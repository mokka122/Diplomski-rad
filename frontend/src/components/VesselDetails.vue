<script setup>
const props = defineProps({
  vessel: {
    type: Object,
    default: null,
  },

  history: {
    type: Array,
    default: () => [],
  },

  historyLoading: {
    type: Boolean,
    default: false,
  },

  historyError: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["close"]);

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

function vesselName(vessel) {
  return vessel?.vessel_name || "Unknown vessel";
}

function averageSpeed(positions) {
  const speeds = positions
    .map((position) => Number(position.sog))
    .filter((speed) => Number.isFinite(speed));

  if (speeds.length === 0) {
    return "—";
  }

  const average = speeds.reduce((sum, speed) => sum + speed, 0) / speeds.length;

  return average.toFixed(1);
}

function formatDuration(positions) {
  if (positions.length < 2) {
    return "—";
  }

  const first = new Date(positions[0].timestamp);
  const last = new Date(positions[positions.length - 1].timestamp);

  const milliseconds = last - first;

  if (!Number.isFinite(milliseconds) || milliseconds < 0) {
    return "—";
  }

  const minutes = Math.round(milliseconds / (1000 * 60));

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (hours === 0) {
    return `${remainingMinutes} min`;
  }

  return `${hours} h ${remainingMinutes} min`;
}
</script>

<template>
  <section v-if="vessel" class="vessel-details-view">
    <div class="vessel-details-topbar">
      <button
        class="vessel-details-back"
        type="button"
        aria-label="Hide vessel details"
        @click="emit('close')"
      >
        <span aria-hidden="true">×</span>
        <span>Hide details</span>
      </button>
    </div>

    <div class="vessel-details-hero">
      <p class="section-label">VESSEL DETAILS</p>

      <h3>{{ vesselName(vessel) }}</h3>

      <p class="vessel-details-mmsi">MMSI {{ vessel.mmsi }}</p>
    </div>

    <div class="vessel-status-card">
      <span class="vessel-status-dot"></span>

      <div>
        <strong>Currently active</strong>
        <span>Live AIS position</span>
      </div>
    </div>

    <section class="details-group">
      <p class="details-group-label">MOVEMENT</p>

      <dl class="details-grid">
        <div class="detail-card">
          <dt>Speed</dt>
          <dd>
            {{ formatNumber(vessel.sog) }}
            <small>kn</small>
          </dd>
        </div>

        <div class="detail-card">
          <dt>Course</dt>
          <dd>
            {{ formatNumber(vessel.cog) }}
            <small>°</small>
          </dd>
        </div>

        <div class="detail-card">
          <dt>Heading</dt>
          <dd>
            {{ formatNumber(vessel.heading) }}
            <small>°</small>
          </dd>
        </div>

        <div class="detail-card">
          <dt>Ship type</dt>
          <dd class="text-value">
            {{ vessel.ship_type ?? "—" }}
          </dd>
        </div>
      </dl>
    </section>

    <section class="details-group">
      <p class="details-group-label">POSITION</p>

      <dl class="details-list">
        <div>
          <dt>Latitude</dt>
          <dd>{{ formatNumber(vessel.latitude, 5) }}°</dd>
        </div>

        <div>
          <dt>Longitude</dt>
          <dd>{{ formatNumber(vessel.longitude, 5) }}°</dd>
        </div>

        <div>
          <dt>Last AIS message</dt>
          <dd>
            {{ formatTimestamp(vessel.timestamp) }}
          </dd>
        </div>
      </dl>
    </section>

    <section class="details-group trajectory-details">
      <p class="details-group-label">TRAJECTORY</p>

      <div v-if="historyLoading" class="trajectory-state">
        Loading historical positions...
      </div>

      <div v-else-if="historyError" class="trajectory-state trajectory-error">
        {{ historyError }}
      </div>

      <div v-else-if="history.length < 2" class="trajectory-state">
        Not enough historical positions available yet.
      </div>

      <template v-else>
        <div class="trajectory-summary">
          <div>
            <span>Positions</span>
            <strong>{{ history.length }}</strong>
          </div>

          <div>
            <span>Duration</span>
            <strong>{{ formatDuration(history) }}</strong>
          </div>

          <div>
            <span>Avg. speed</span>
            <strong>
              {{ averageSpeed(history) }}
              <small>kn</small>
            </strong>
          </div>
        </div>

        <p class="trajectory-hint">
          Historical positions are displayed on the map. Hover over a point to
          inspect its timestamp and speed.
        </p>
      </template>
    </section>
  </section>

  <div v-else class="empty-selection">Select a vessel to view its details.</div>
</template>
