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
let hasSetInitialBounds = false;
let isTouchDevice = false;
let trajectoryLayer = null;

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

function getMarkerColor(speed) {
  if (speed === null || speed === undefined) {
    return "#71818a";
  }

  if (Number(speed) >= 15) {
    return "#e9794b";
  }

  if (Number(speed) >= 5) {
    return "#16898b";
  }

  return "#3c9c68";
}

function formatValue(value, suffix = "") {
  if (value === null || value === undefined) {
    return "—";
  }

  return `${Number(value).toFixed(1)}${suffix}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function createInfoContent(vessel) {
  const vesselName = escapeHtml(vessel.vessel_name || "Unknown vessel");

  const shipType = escapeHtml(vessel.ship_type ?? "Unknown type");

  return `
    <div class="vessel-tooltip-content">
      <strong>${vesselName}</strong>

      <span>MMSI: ${escapeHtml(vessel.mmsi)}</span>

      <span>
        Speed: ${formatValue(vessel.sog, " kn")}
      </span>

      <span>
        Course: ${formatValue(vessel.cog, "°")}
      </span>

      <span>
        Heading: ${formatValue(vessel.heading, "°")}
      </span>

      <span>
        Type: ${shipType}
      </span>
    </div>
  `;
}

function createVesselIcon(vessel) {
  const color = getMarkerColor(vessel.sog);
  const direction = getDirection(vessel);

  return L.divIcon({
    className: "vessel-marker-wrapper",
    iconSize: [34, 42],
    iconAnchor: [17, 21],
    popupAnchor: [0, -22],

    html: `
      <div
        class="vessel-marker"
        style="
          --marker-color: ${color};
          transform: rotate(${direction}deg);
        "
      >
        <svg
          viewBox="0 0 34 42"
          aria-hidden="true"
        >
          <path
            d="
              M17 2
              C25 7 29 16 29 27
              L25 39
              H9
              L5 27
              C5 16 9 7 17 2
              Z
            "
            fill="var(--marker-color)"
            stroke="#ffffff"
            stroke-width="2"
            stroke-linejoin="round"
          />
          <path
            d="M11 16 H23 V27 H11 Z"
            fill="#ffffff"
            fill-opacity="0.88"
          />
          <path
            d="M17 5 V38"
            stroke="#ffffff"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-opacity="0.8"
          />
        </svg>
      </div>
    `,
  });
}

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
    color: "#16898b",
    weight: 4,
    opacity: 0.75,
    lineJoin: "round",
    lineCap: "round",
  });

  trajectory.addTo(trajectoryLayer);

  positions.forEach((position) => {
    const marker = L.circleMarker(
      [Number(position.latitude), Number(position.longitude)],
      {
        radius: 4,
        color: "#ffffff",
        weight: 1.5,
        fillColor: "#16898b",
        fillOpacity: 0.9,
      },
    );

    const timestamp = position.timestamp
      ? new Date(position.timestamp).toLocaleString("en-GB", {
          dateStyle: "medium",
          timeStyle: "medium",
        })
      : "—";

    const speed =
      position.sog === null || position.sog === undefined
        ? "—"
        : `${Number(position.sog).toFixed(1)} kn`;

    marker.bindTooltip(
      `
        <div class="trajectory-tooltip-content">
          <strong>Historical position</strong>
          <span>${timestamp}</span>
          <span>Speed: ${speed}</span>
        </div>
      `,
      {
        direction: "top",
        opacity: 1,
      },
    );

    marker.addTo(trajectoryLayer);
  });
}

function updateVesselMarkers() {
  if (!map || !vesselsLayer) {
    return;
  }

  vesselsLayer.clearLayers();

  const coordinates = [];

  for (const vessel of props.vessels) {
    const validLatitude = isValidCoordinate(vessel.latitude, -90, 90);

    const validLongitude = isValidCoordinate(vessel.longitude, -180, 180);

    if (!validLatitude || !validLongitude) {
      continue;
    }

    const latitude = Number(vessel.latitude);
    const longitude = Number(vessel.longitude);

    coordinates.push([latitude, longitude]);

    const marker = L.marker([latitude, longitude], {
      icon: createVesselIcon(vessel),
      title: vessel.vessel_name || vessel.mmsi,
    });

    if (isTouchDevice) {
      marker.bindPopup(createInfoContent(vessel)).on("click", () => {
        emit("vessel-selected", vessel);
      });
    } else {
      marker
        .bindTooltip(createInfoContent(vessel), {
          className: "vessel-tooltip",
          direction: "top",
          offset: [0, -16],
          opacity: 1,
        })
        .on("click", () => {
          emit("vessel-selected", vessel);
        });
    }
    marker.addTo(vesselsLayer);
  }

  if (coordinates.length > 0 && !hasSetInitialBounds) {
    map.fitBounds(L.latLngBounds(coordinates), {
      padding: [48, 48],
      maxZoom: 9,
    });

    hasSetInitialBounds = true;
  }
}

onMounted(() => {
  isTouchDevice = window.matchMedia("(hover: none), (pointer: coarse)").matches;

  map = L.map(mapElement.value, {
    zoomControl: true,
  }).setView([62, 7], 5);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  vesselsLayer = L.layerGroup().addTo(map);

  trajectoryLayer = L.layerGroup().addTo(map);

  updateVesselMarkers();
  updateTrajectory();

  setTimeout(() => {
    map.invalidateSize();
  }, 0);
});

watch(() => props.vessels, updateVesselMarkers);

watch(
  () => props.vesselHistory,
  updateTrajectory,
  {
    deep: true,
  },
)

onBeforeUnmount(() => {
  if (map) {
    map.remove();
  }
});
</script>

<template>
  <div ref="mapElement" class="vessel-map"></div>
</template>
