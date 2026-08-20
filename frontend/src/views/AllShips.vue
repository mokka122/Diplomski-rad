<script setup>
import {
  computed,
  onMounted,
  onUnmounted,
  ref,
} from "vue";

import AppHeader from "../components/AppHeader.vue";

import {
  getCurrentVessels,
} from "../services/api";


const vessels = ref([]);

const isLoading = ref(true);
const errorMessage = ref("");

const searchQuery = ref("");
const speedFilter = ref("all");

const sortBy = ref("updated");

const lastUpdated = ref(null);

let refreshTimer = null;


/* =========================================================
   FORMATTERS
   ========================================================= */

function vesselName(vessel) {
  return (
    vessel?.vessel_name ||
    "Unknown vessel"
  );
}


function formatNumber(
  value,
  decimals = 1,
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return number.toFixed(
    decimals,
  );
}


function formatTimestamp(timestamp) {
  if (!timestamp) {
    return "—";
  }

  return new Date(
    timestamp,
  ).toLocaleString(
    "en-GB",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  );
}


function formatRelativeTime(timestamp) {
  if (!timestamp) {
    return "Unknown";
  }

  const time =
    new Date(timestamp)
      .getTime();

  const now =
    Date.now();

  const difference =
    Math.max(
      0,
      now - time,
    );

  const seconds =
    Math.floor(
      difference / 1000,
    );

  if (seconds < 60) {
    return `${seconds}s ago`;
  }

  const minutes =
    Math.floor(
      seconds / 60,
    );

  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours =
    Math.floor(
      minutes / 60,
    );

  if (hours < 24) {
    return `${hours}h ago`;
  }

  return formatTimestamp(
    timestamp,
  );
}


/* =========================================================
   SPEED
   ========================================================= */

function speedCategory(vessel) {
  const speed =
    Number(
      vessel?.sog,
    );

  if (!Number.isFinite(speed)) {
    return "unknown";
  }

  if (speed >= 15) {
    return "fast";
  }

  if (speed >= 5) {
    return "moving";
  }

  return "slow";
}


function speedCategoryLabel(vessel) {
  const category =
    speedCategory(
      vessel,
    );

  if (category === "fast") {
    return "Fast";
  }

  if (category === "moving") {
    return "Under way";
  }

  if (category === "slow") {
    return "Slow";
  }

  return "Unknown";
}


/* =========================================================
   SIMPLE SHIP TYPE LABELS
   ========================================================= */

function shipTypeLabel(
  shipType,
) {
  const value =
    Number(
      shipType,
    );

  if (!Number.isFinite(value)) {
    return "Unknown";
  }

  if (value === 30) {
    return "Fishing";
  }

  if (
    value === 31 ||
    value === 32 ||
    value === 52
  ) {
    return "Tug";
  }

  if (
    value >= 60 &&
    value <= 69
  ) {
    return "Passenger";
  }

  if (
    value >= 70 &&
    value <= 79
  ) {
    return "Cargo";
  }

  if (
    value >= 80 &&
    value <= 89
  ) {
    return "Tanker";
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
    ].includes(value)
  ) {
    return "Auxiliary";
  }

  return `AIS ${value}`;
}


/* =========================================================
   SEARCH / FILTER / SORT
   ========================================================= */

const filteredVessels = computed(() => {
  const query =
    searchQuery.value
      .trim()
      .toLowerCase();

  let result =
    [...vessels.value];


  if (query) {
    result =
      result.filter(
        (vessel) => {
          const name =
            vesselName(
              vessel,
            )
              .toLowerCase();

          const mmsi =
            String(
              vessel?.mmsi ??
              "",
            ).toLowerCase();

          return (
            name.includes(
              query,
            ) ||
            mmsi.includes(
              query,
            )
          );
        },
      );
  }


  if (
    speedFilter.value !==
    "all"
  ) {
    result =
      result.filter(
        (vessel) =>
          speedCategory(
            vessel,
          ) ===
          speedFilter.value,
      );
  }


  result.sort(
    (
      first,
      second,
    ) => {
      if (
        sortBy.value ===
        "name"
      ) {
        return vesselName(
          first,
        ).localeCompare(
          vesselName(
            second,
          ),
        );
      }


      if (
        sortBy.value ===
        "speed"
      ) {
        const firstSpeed =
          Number(
            first?.sog,
          );

        const secondSpeed =
          Number(
            second?.sog,
          );

        return (
          (
            Number.isFinite(
              secondSpeed,
            )
              ? secondSpeed
              : -1
          ) -
          (
            Number.isFinite(
              firstSpeed,
            )
              ? firstSpeed
              : -1
          )
        );
      }


      const firstTimestamp =
        new Date(
          first?.timestamp ??
          0,
        ).getTime();

      const secondTimestamp =
        new Date(
          second?.timestamp ??
          0,
        ).getTime();

      return (
        secondTimestamp -
        firstTimestamp
      );
    },
  );


  return result;
});


const vesselCount = computed(
  () =>
    vessels.value.length,
);


const visibleVesselCount =
  computed(
    () =>
      filteredVessels
        .value
        .length,
  );


const movingCount = computed(
  () =>
    vessels.value.filter(
      (vessel) =>
        speedCategory(
          vessel,
        ) ===
        "moving",
    ).length,
);


const fastCount = computed(
  () =>
    vessels.value.filter(
      (vessel) =>
        speedCategory(
          vessel,
        ) ===
        "fast",
    ).length,
);


/* =========================================================
   DATA
   ========================================================= */

async function loadVessels() {
  try {
    errorMessage.value = "";

    const data =
      await getCurrentVessels();

    vessels.value =
      data.vessels ?? [];

    lastUpdated.value =
      new Date();
  } catch (error) {
    errorMessage.value =
      error.message;
  } finally {
    isLoading.value = false;
  }
}


onMounted(async () => {
  await loadVessels();

  refreshTimer =
    setInterval(
      loadVessels,
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

    <div class="vessels-page">
      <!-- =====================================================
           PAGE HEADER
           ===================================================== -->

      <section class="vessels-intro">
        <div>
          <p class="eyebrow">
            LIVE AIS DIRECTORY
          </p>

          <h1>
            All vessels
          </h1>

          <p>
            Browse and inspect the latest
            vessel states received by OceanEye.
          </p>
        </div>

        <div class="vessels-live-state">
          <span class="dashboard-refresh-dot"></span>

          <div>
            <strong>
              {{ vesselCount }}
              active vessels
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
           SUMMARY
           ===================================================== -->

      <section class="vessels-summary">
        <article>
          <span>Total vessels</span>

          <strong>
            {{ vesselCount }}
          </strong>
        </article>

        <article>
          <span>Under way</span>

          <strong>
            {{ movingCount }}
          </strong>
        </article>

        <article>
          <span>Fast vessels</span>

          <strong>
            {{ fastCount }}
          </strong>
        </article>

        <article>
          <span>Visible results</span>

          <strong>
            {{ visibleVesselCount }}
          </strong>
        </article>
      </section>

      <!-- =====================================================
           DIRECTORY CARD
           ===================================================== -->

      <section class="vessel-directory">
        <div class="vessel-directory-toolbar">
          <div class="vessel-search">
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle
                cx="11"
                cy="11"
                r="6"
              />

              <path
                d="M16 16 L21 21"
              />
            </svg>

            <input
              v-model="searchQuery"
              type="search"
              placeholder="Search vessel name or MMSI..."
              aria-label="Search vessels"
            />
          </div>

          <div class="vessel-sort">
            <label for="vessel-sort">
              Sort
            </label>

            <select
              id="vessel-sort"
              v-model="sortBy"
            >
              <option value="updated">
                Latest update
              </option>

              <option value="name">
                Vessel name
              </option>

              <option value="speed">
                Highest speed
              </option>
            </select>
          </div>
        </div>

        <!-- ===================================================
             FILTERS
             =================================================== -->

        <div class="vessel-filters">
          <button
            type="button"
            :class="{
              active:
                speedFilter ===
                'all',
            }"
            @click="
              speedFilter = 'all'
            "
          >
            All
          </button>

          <button
            type="button"
            :class="{
              active:
                speedFilter ===
                'slow',
            }"
            @click="
              speedFilter = 'slow'
            "
          >
            Slow
          </button>

          <button
            type="button"
            :class="{
              active:
                speedFilter ===
                'moving',
            }"
            @click="
              speedFilter =
                'moving'
            "
          >
            Under way
          </button>

          <button
            type="button"
            :class="{
              active:
                speedFilter ===
                'fast',
            }"
            @click="
              speedFilter =
                'fast'
            "
          >
            Fast
          </button>
        </div>

        <!-- ===================================================
             STATES
             =================================================== -->

        <div
          v-if="isLoading"
          class="vessel-directory-state"
        >
          Loading vessel directory...
        </div>

        <div
          v-else-if="errorMessage"
          class="
            vessel-directory-state
            vessel-directory-state--error
          "
        >
          {{ errorMessage }}
        </div>

        <div
          v-else-if="
            filteredVessels.length === 0
          "
          class="vessel-directory-state"
        >
          No vessels match the current
          search and filters.
        </div>

        <template v-else>
          <!-- =================================================
               DESKTOP TABLE
               ================================================= -->

          <div class="vessels-table-wrapper">
            <table class="vessels-table">
              <thead>
                <tr>
                  <th>
                    Vessel
                  </th>

                  <th>
                    MMSI
                  </th>

                  <th>
                    Status
                  </th>

                  <th>
                    Speed
                  </th>

                  <th>
                    Type
                  </th>

                  <th>
                    Course
                  </th>

                  <th>
                    Position
                  </th>

                  <th>
                    Updated
                  </th>
                </tr>
              </thead>

              <tbody>
                <tr
                  v-for="
                    vessel in
                    filteredVessels
                  "
                  :key="vessel.mmsi"
                >
                  <td>
                    <div class="vessel-name-cell">
                      <div
                        class="table-vessel-marker"
                        :class="
                          `table-vessel-marker--${speedCategory(
                            vessel,
                          )}`
                        "
                      >
                        <svg
                          viewBox="0 0 24 28"
                          aria-hidden="true"
                        >
                          <path
                            d="
                              M12 2
                              L21 23
                              L12 19
                              L3 23
                              Z
                            "
                          />

                          <path
                            d="M12 7 V19"
                          />
                        </svg>
                      </div>

                      <div>
                        <strong>
                          {{
                            vesselName(
                              vessel,
                            )
                          }}
                        </strong>

                        <span>
                          {{
                            speedCategoryLabel(
                              vessel,
                            )
                          }}
                        </span>
                      </div>
                    </div>
                  </td>

                  <td class="monospace-value">
                    {{ vessel.mmsi }}
                  </td>

                  <td>
                    <span
                      class="speed-status"
                      :class="
                        `speed-status--${speedCategory(
                          vessel,
                        )}`
                      "
                    >
                      {{
                        speedCategoryLabel(
                          vessel,
                        )
                      }}
                    </span>
                  </td>

                  <td>
                    <strong>
                      {{
                        formatNumber(
                          vessel.sog,
                        )
                      }}
                    </strong>

                    <small>
                      kn
                    </small>
                  </td>

                  <td>
                    <span class="ship-type-label">
                      {{
                        shipTypeLabel(
                          vessel.ship_type,
                        )
                      }}
                    </span>
                  </td>

                  <td>
                    {{
                      formatNumber(
                        vessel.cog,
                      )
                    }}°
                  </td>

                  <td>
                    <div class="position-cell">
                      <span>
                        {{
                          formatNumber(
                            vessel.latitude,
                            4,
                          )
                        }}°
                      </span>

                      <span>
                        {{
                          formatNumber(
                            vessel.longitude,
                            4,
                          )
                        }}°
                      </span>
                    </div>
                  </td>

                  <td>
                    <span class="updated-time">
                      {{
                        formatRelativeTime(
                          vessel.timestamp,
                        )
                      }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- =================================================
               MOBILE CARDS
               ================================================= -->

          <div class="vessel-mobile-list">
            <article
              v-for="
                vessel in
                filteredVessels
              "
              :key="
                `mobile-${vessel.mmsi}`
              "
              class="vessel-mobile-card"
            >
              <div class="vessel-mobile-card-header">
                <div class="vessel-name-cell">
                  <div
                    class="table-vessel-marker"
                    :class="
                      `table-vessel-marker--${speedCategory(
                        vessel,
                      )}`
                    "
                  >
                    <svg
                      viewBox="0 0 24 28"
                      aria-hidden="true"
                    >
                      <path
                        d="
                          M12 2
                          L21 23
                          L12 19
                          L3 23
                          Z
                        "
                      />

                      <path
                        d="M12 7 V19"
                      />
                    </svg>
                  </div>

                  <div>
                    <strong>
                      {{
                        vesselName(
                          vessel,
                        )
                      }}
                    </strong>

                    <span>
                      MMSI
                      {{ vessel.mmsi }}
                    </span>
                  </div>
                </div>

                <span
                  class="speed-status"
                  :class="
                    `speed-status--${speedCategory(
                      vessel,
                    )}`
                  "
                >
                  {{
                    speedCategoryLabel(
                      vessel,
                    )
                  }}
                </span>
              </div>

              <div class="vessel-mobile-metrics">
                <div>
                  <span>
                    Speed
                  </span>

                  <strong>
                    {{
                      formatNumber(
                        vessel.sog,
                      )
                    }}
                    kn
                  </strong>
                </div>

                <div>
                  <span>
                    Type
                  </span>

                  <strong>
                    {{
                      shipTypeLabel(
                        vessel.ship_type,
                      )
                    }}
                  </strong>
                </div>

                <div>
                  <span>
                    Course
                  </span>

                  <strong>
                    {{
                      formatNumber(
                        vessel.cog,
                      )
                    }}°
                  </strong>
                </div>

                <div>
                  <span>
                    Updated
                  </span>

                  <strong>
                    {{
                      formatRelativeTime(
                        vessel.timestamp,
                      )
                    }}
                  </strong>
                </div>
              </div>

              <div class="vessel-mobile-position">
                <span>
                  {{
                    formatNumber(
                      vessel.latitude,
                      4,
                    )
                  }}°
                </span>

                <span>
                  {{
                    formatNumber(
                      vessel.longitude,
                      4,
                    )
                  }}°
                </span>
              </div>
            </article>
          </div>
        </template>
      </section>
    </div>
  </main>
</template>