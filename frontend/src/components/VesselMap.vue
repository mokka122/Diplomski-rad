<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

import L from "leaflet";
import "leaflet/dist/leaflet.css";

const props = defineProps({
  vessels: {
    type: Array,
    default: () => [],
  },

  selectedVessel: {
    type: Object,
    default: null,
  },

  vesselHistory: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["vessel-selected"]);

const mapElement = ref(null);

let map = null;

let vesselsLayer = null;
let trajectoryLayer = null;
let geofenceLayer = null;

let isTouchDevice = false;

let hasFocusedAlesund = false;

/* =========================================================
   ÅLESUND STUDY AREA
   ========================================================= */

const ALESUND_BOUNDS = [
  [62.43, 6.05],
  [62.52, 6.27],
];

const ALESUND_CENTER = [62.475, 6.16];

/* =========================================================
   BASIC HELPERS
   ========================================================= */

function isValidCoordinate(value, min, max) {
  const number = Number(value);

  return Number.isFinite(number) && number >= min && number <= max;
}

function getDirection(vessel) {
  const heading = Number(vessel.heading);

  if (Number.isFinite(heading) && heading >= 0 && heading <= 360) {
    return heading;
  }

  const course = Number(vessel.cog);

  if (Number.isFinite(course) && course >= 0 && course <= 360) {
    return course;
  }

  return 0;
}

/* =========================================================
   SPEED CLASSIFICATION
   ========================================================= */

function getMarkerColor(speed) {
  if (speed === null || speed === undefined) {
    return "#71818a";
  }

  const value = Number(speed);

  if (!Number.isFinite(value)) {
    return "#71818a";
  }

  if (value >= 15) {
    return "#d9843e";
  }

  if (value >= 5) {
    return "#168b79";
  }

  return "#3b966c";
}

function getSpeedCategory(speed) {
  if (speed === null || speed === undefined) {
    return "Unknown speed";
  }

  const value = Number(speed);

  if (!Number.isFinite(value)) {
    return "Unknown speed";
  }

  if (value >= 15) {
    return "Fast";
  }

  if (value >= 5) {
    return "Under way";
  }

  return "Slow";
}

/* =========================================================
   FORMATTERS
   ========================================================= */

function formatValue(value, suffix = "") {
  if (value === null || value === undefined) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return `${number.toFixed(1)}${suffix}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/* =========================================================
   TOOLTIP / POPUP
   ========================================================= */

function createInfoContent(vessel) {
  const vesselName = escapeHtml(vessel.vessel_name || "Unknown vessel");

  const shipType = escapeHtml(vessel.ship_type ?? "Unknown type");

  const speedCategory = getSpeedCategory(vessel.sog);

  return `
    <div class="vessel-tooltip-content">
      <div class="vessel-tooltip-heading">
        <strong>
          ${vesselName}
        </strong>

        <span>
          ${escapeHtml(speedCategory)}
        </span>
      </div>

      <div class="vessel-tooltip-grid">
        <div>
          <small>MMSI</small>
          <span>
            ${escapeHtml(vessel.mmsi)}
          </span>
        </div>

        <div>
          <small>Type</small>
          <span>
            ${shipType}
          </span>
        </div>

        <div>
          <small>Speed</small>
          <span>
            ${formatValue(vessel.sog, " kn")}
          </span>
        </div>

        <div>
          <small>Course</small>
          <span>
            ${formatValue(vessel.cog, "°")}
          </span>
        </div>
      </div>
    </div>
  `;
}

/* =========================================================
   CUSTOM VESSEL ICON
   ========================================================= */

function createVesselIcon(vessel) {
  const color = getMarkerColor(vessel.sog);

  const direction = getDirection(vessel);

  const isSelected = props.selectedVessel?.mmsi === vessel.mmsi;

  return L.divIcon({
    className: "vessel-marker-wrapper",

    iconSize: [38, 44],

    iconAnchor: [19, 22],

    popupAnchor: [0, -25],

    tooltipAnchor: [0, -23],

    html: `
      <div
        class="
          oceaneye-vessel-marker
          ${isSelected ? "oceaneye-vessel-marker--selected" : ""}
        "
        style="
          --vessel-color: ${color};
          --vessel-direction: ${direction}deg;
        "
      >
        <div
          class="oceaneye-vessel-marker-ring"
        ></div>

        <svg
          viewBox="0 0 40 48"
          aria-hidden="true"
        >
          <path
            class="oceaneye-vessel-hull"
            d="
              M20 3
              L34 38
              L20 33
              L6 38
              Z
            "
          />

          <path
            class="oceaneye-vessel-centerline"
            d="M20 10 V34"
          />

          <path
            class="oceaneye-vessel-crossline"
            d="M12 32 L20 28 L28 32"
          />
        </svg>
      </div>
    `,
  });
}

/* =========================================================
   GEOFENCE
   ========================================================= */

function createGeofence() {
  if (!map) {
    return;
  }

  if (geofenceLayer) {
    geofenceLayer.remove();
  }

  geofenceLayer = L.rectangle(ALESUND_BOUNDS, {
    color: "#168b79",

    weight: 1.5,

    opacity: 0.85,

    fillColor: "#168b79",

    fillOpacity: 0.055,

    dashArray: "7 7",

    interactive: false,
  });

  geofenceLayer.addTo(map);
}

/* =========================================================
   TRAJECTORY
   ========================================================= */

function clearTrajectory() {
  if (!trajectoryLayer) {
    return;
  }

  trajectoryLayer.clearLayers();
}

function updateTrajectory() {
  if (!map || !trajectoryLayer) {
    return;
  }

  clearTrajectory();

  const positions = props.vesselHistory.filter((position) => {
    return (
      isValidCoordinate(position.latitude, -90, 90) &&
      isValidCoordinate(position.longitude, -180, 180)
    );
  });

  if (positions.length < 2) {
    return;
  }

  const latLngs = positions.map((position) => [
    Number(position.latitude),
    Number(position.longitude),
  ]);

  const trajectory = L.polyline(latLngs, {
    color: "#168b79",

    weight: 3,

    opacity: 0.72,

    lineJoin: "round",

    lineCap: "round",
  });

  trajectory.addTo(trajectoryLayer);

  positions.forEach((position, index) => {
    const isLast = index === positions.length - 1;

    const marker = L.circleMarker(
      [Number(position.latitude), Number(position.longitude)],
      {
        radius: isLast ? 4.5 : 3,

        color: "#ffffff",

        weight: 1.5,

        fillColor: "#168b79",

        fillOpacity: isLast ? 1 : 0.72,
      },
    );

    const timestamp = position.timestamp
      ? new Date(position.timestamp).toLocaleString("en-GB", {
          dateStyle: "medium",

          timeStyle: "medium",
        })
      : "—";

    marker.bindTooltip(
      `
          <div
            class="trajectory-tooltip-content"
          >
            <strong>
              Historical position
            </strong>

            <span>
              ${timestamp}
            </span>

            <span>
              Speed:
              ${formatValue(position.sog, " kn")}
            </span>
          </div>
        `,
      {
        direction: "top",

        opacity: 1,

        className: "trajectory-tooltip",
      },
    );

    marker.addTo(trajectoryLayer);
  });
}

/* =========================================================
   VESSEL MARKERS
   ========================================================= */

function updateVesselMarkers() {
  if (!map || !vesselsLayer) {
    return;
  }

  vesselsLayer.clearLayers();

  for (const vessel of props.vessels) {
    const validLatitude = isValidCoordinate(vessel.latitude, -90, 90);

    const validLongitude = isValidCoordinate(vessel.longitude, -180, 180);

    if (!validLatitude || !validLongitude) {
      continue;
    }

    const latitude = Number(vessel.latitude);

    const longitude = Number(vessel.longitude);

    const marker = L.marker([latitude, longitude], {
      icon: createVesselIcon(vessel),

      title: vessel.vessel_name || vessel.mmsi,
    });

    if (isTouchDevice) {
      marker
        .bindPopup(createInfoContent(vessel), {
          className: "oceaneye-vessel-popup",
        })
        .on("click", () => {
          emit("vessel-selected", vessel);
        });
    } else {
      marker
        .bindTooltip(createInfoContent(vessel), {
          className: "vessel-tooltip",

          direction: "top",

          offset: [0, -18],

          opacity: 1,
        })
        .on("click", () => {
          emit("vessel-selected", vessel);
        });
    }

    marker.addTo(vesselsLayer);
  }
}

function focusAlesund() {
  if (!map) {
    return;
  }

  map.fitBounds(ALESUND_BOUNDS, {
    padding: [42, 42],

    maxZoom: 11,
  });
}

/* =========================================================
   SELECTED VESSEL FOCUS
   ========================================================= */

function focusSelectedVessel() {
  if (!map || !props.selectedVessel) {
    return;
  }

  const latitude = Number(props.selectedVessel.latitude);

  const longitude = Number(props.selectedVessel.longitude);

  if (
    !isValidCoordinate(latitude, -90, 90) ||
    !isValidCoordinate(longitude, -180, 180)
  ) {
    return;
  }

  map.flyTo([latitude, longitude], Math.max(map.getZoom(), 11), {
    duration: 0.7,
  });
}

/* =========================================================
   MAP INITIALIZATION
   ========================================================= */

onMounted(() => {
  isTouchDevice = window.matchMedia("(hover: none), (pointer: coarse)").matches;

  map = L.map(mapElement.value, {
    zoomControl: false,

    attributionControl: true,

    preferCanvas: true,
  }).setView(ALESUND_CENTER, 10);

  L.control
    .zoom({
      position: "topright",
    })
    .addTo(map);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,

    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  geofenceLayer = L.layerGroup().addTo(map);

  trajectoryLayer = L.layerGroup().addTo(map);

  vesselsLayer = L.layerGroup().addTo(map);

  createGeofence();

  updateVesselMarkers();

  updateTrajectory();

  if (!hasFocusedAlesund) {
    map.fitBounds(ALESUND_BOUNDS, {
      padding: [42, 42],

      maxZoom: 11,
    });

    hasFocusedAlesund = true;
  }

  setTimeout(() => {
    map?.invalidateSize();
  }, 0);
});

/* =========================================================
   WATCHERS
   ========================================================= */

watch(
  () => props.vessels,
  () => {
    updateVesselMarkers();
  },
  {
    deep: true,
  },
);

watch(
  () => props.vesselHistory,
  () => {
    updateTrajectory();
  },
  {
    deep: true,
  },
);
watch(
  () =>
    props.selectedVessel?.mmsi,

  (
    currentMmsi,
    previousMmsi,
  ) => {
    updateVesselMarkers();

    if (
      currentMmsi &&
      currentMmsi !==
      previousMmsi
    ) {
      focusSelectedVessel();
    }
  },
);

/* =========================================================
   CLEANUP
   ========================================================= */

onBeforeUnmount(() => {
  if (map) {
    map.remove();
    map = null;
  }
});
</script>

<template>
  <div class="vessel-map-shell">
    <div
      ref="mapElement"
      class="vessel-map"
    ></div>

    <!-- ==============================================
         MAP RESET
         ============================================== -->

    <button
      class="map-area-reset"
      type="button"
      title="Return map to Ålesund study area"
      @click="focusAlesund"
    >
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          d="
            M12 3
            C8.7 3 6 5.7 6 9
            C6 13.6 12 20 12 20
            C12 20 18 13.6 18 9
            C18 5.7 15.3 3 12 3
            Z
          "
        />

        <circle
          cx="12"
          cy="9"
          r="2.2"
        />
      </svg>

      <span>
        Back to Ålesund
      </span>
    </button>

    <!-- ==============================================
         MAP LEGEND
         ============================================== -->

    <div class="map-legend">
      <div class="map-legend-title">
        Map legend
      </div>

      <div class="map-legend-items">
        <div>
          <span
            class="
              map-legend-dot
              map-legend-dot--slow
            "
          ></span>

          <span>
            Slow
          </span>
        </div>

        <div>
          <span
            class="
              map-legend-dot
              map-legend-dot--moving
            "
          ></span>

          <span>
            Under way
          </span>
        </div>

        <div>
          <span
            class="
              map-legend-dot
              map-legend-dot--fast
            "
          ></span>

          <span>
            Fast
          </span>
        </div>

        <div>
          <span
            class="
              map-legend-dot
              map-legend-dot--unknown
            "
          ></span>

          <span>
            Unknown
          </span>
        </div>

        <div>
          <span
            class="map-legend-geofence"
          ></span>

          <span>
            Study area
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
