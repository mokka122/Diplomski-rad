<script setup>
import {
  computed,
} from "vue";


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

  const number =
    Number(value);

  if (
    !Number.isFinite(number)
  ) {
    return "—";
  }

  return number.toFixed(
    decimals,
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


function vesselName(
  vessel,
) {
  return (
    vessel?.vessel_name ||
    "Unknown vessel"
  );
}


function averageSpeed(
  positions,
) {
  const speeds =
    positions
      .map(
        (position) =>
          Number(
            position.sog,
          ),
      )
      .filter(
        (speed) =>
          Number.isFinite(
            speed,
          ),
      );

  if (
    speeds.length === 0
  ) {
    return "—";
  }

  const average =
    speeds.reduce(
      (
        sum,
        speed,
      ) =>
        sum + speed,
      0,
    ) /
    speeds.length;

  return average.toFixed(1);
}


function formatDuration(
  positions,
) {
  if (
    positions.length < 2
  ) {
    return "—";
  }

  const timestamps =
    positions
      .map(
        (position) =>
          new Date(
            position.timestamp,
          ).getTime(),
      )
      .filter(
        (timestamp) =>
          Number.isFinite(
            timestamp,
          ),
      );

  if (
    timestamps.length < 2
  ) {
    return "—";
  }

  const first =
    Math.min(
      ...timestamps,
    );

  const last =
    Math.max(
      ...timestamps,
    );

  const milliseconds =
    last - first;

  const minutes =
    Math.round(
      milliseconds /
      (1000 * 60),
    );

  const hours =
    Math.floor(
      minutes / 60,
    );

  const remainingMinutes =
    minutes % 60;

  if (hours === 0) {
    return `${remainingMinutes} min`;
  }

  return (
    `${hours} h ${remainingMinutes} min`
  );
}


function shipTypeLabel(
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


const speedCategory =
  computed(
    () => {
      const speed =
        Number(
          props.vessel?.sog,
        );

      if (
        !Number.isFinite(
          speed,
        )
      ) {
        return "unknown";
      }

      if (
        speed >= 15
      ) {
        return "fast";
      }

      if (
        speed >= 5
      ) {
        return "moving";
      }

      return "slow";
    },
  );


const speedCategoryLabel =
  computed(
    () => {
      if (
        speedCategory.value ===
        "fast"
      ) {
        return "Fast";
      }

      if (
        speedCategory.value ===
        "moving"
      ) {
        return "Under way";
      }

      if (
        speedCategory.value ===
        "slow"
      ) {
        return "Slow";
      }

      return "Unknown speed";
    },
  );


const direction =
  computed(
    () => {
      const heading =
        Number(
          props.vessel
            ?.heading,
        );

      if (
        Number.isFinite(
          heading,
        ) &&
        heading >= 0 &&
        heading <= 360
      ) {
        return heading;
      }

      const course =
        Number(
          props.vessel
            ?.cog,
        );

      if (
        Number.isFinite(
          course,
        ) &&
        course >= 0 &&
        course <= 360
      ) {
        return course;
      }

      return 0;
    },
  );
</script>


<template>
  <section
    v-if="vessel"
    class="vessel-details-view"
  >
    <!-- =====================================================
         HERO
         ===================================================== -->

    <div class="vessel-details-main">
      <div class="vessel-details-identity">
        <div
          class="vessel-details-icon"
          :class="
            `vessel-details-icon--${speedCategory}`
          "
        >
          <svg
            viewBox="0 0 40 48"
            aria-hidden="true"
            :style="{
              transform:
                `rotate(${direction}deg)`,
            }"
          >
            <path
              d="
                M20 3
                L34 38
                L20 33
                L6 38
                Z
              "
            />

            <path
              d="M20 10 V34"
            />
          </svg>
        </div>

        <div>
          <div class="vessel-title-row">
            <h3>
              {{
                vesselName(
                  vessel,
                )
              }}
            </h3>

            <span
              class="vessel-details-speed-status"
              :class="
                `vessel-details-speed-status--${speedCategory}`
              "
            >
              {{
                speedCategoryLabel
              }}
            </span>
          </div>

          <div class="vessel-identity-meta">
            <span>
              MMSI
              <strong>
                {{ vessel.mmsi }}
              </strong>
            </span>

            <span>
              {{
                shipTypeLabel(
                  vessel.ship_type,
                )
              }}
            </span>

            <span class="vessel-live-label">
              <i></i>
              Live AIS
            </span>
          </div>
        </div>
      </div>

      <div class="vessel-last-message">
        <span>
          Last AIS message
        </span>

        <strong>
          {{
            formatTimestamp(
              vessel.timestamp,
            )
          }}
        </strong>
      </div>
    </div>

    <!-- =====================================================
         PRIMARY METRICS
         ===================================================== -->

    <div class="vessel-detail-metrics">
      <article>
        <span>
          Speed
        </span>

        <strong>
          {{
            formatNumber(
              vessel.sog,
            )
          }}

          <small>
            kn
          </small>
        </strong>
      </article>

      <article>
        <span>
          Course
        </span>

        <strong>
          {{
            formatNumber(
              vessel.cog,
            )
          }}

          <small>
            °
          </small>
        </strong>
      </article>

      <article>
        <span>
          Heading
        </span>

        <strong>
          {{
            formatNumber(
              vessel.heading,
            )
          }}

          <small>
            °
          </small>
        </strong>
      </article>

      <article>
        <span>
          Vessel type
        </span>

        <strong class="text-metric">
          {{
            shipTypeLabel(
              vessel.ship_type,
            )
          }}
        </strong>

        <small
          v-if="
            vessel.ship_type !==
            null &&
            vessel.ship_type !==
            undefined
          "
          class="metric-secondary"
        >
          AIS type
          {{ vessel.ship_type }}
        </small>
      </article>
    </div>

    <!-- =====================================================
         LOWER DETAILS
         ===================================================== -->

    <div class="vessel-details-lower">
      <!-- POSITION -->

      <section class="vessel-info-panel">
        <div class="vessel-info-heading">
          <p class="dashboard-panel-label">
            POSITION
          </p>

          <h4>
            Current position
          </h4>
        </div>

        <dl class="vessel-position-list">
          <div>
            <dt>
              Latitude
            </dt>

            <dd>
              {{
                formatNumber(
                  vessel.latitude,
                  5,
                )
              }}°
            </dd>
          </div>

          <div>
            <dt>
              Longitude
            </dt>

            <dd>
              {{
                formatNumber(
                  vessel.longitude,
                  5,
                )
              }}°
            </dd>
          </div>

          <div>
            <dt>
              Source
            </dt>

            <dd>
              {{
                vessel.source ||
                "BarentsWatch"
              }}
            </dd>
          </div>
        </dl>
      </section>

      <!-- TRAJECTORY -->

      <section class="vessel-info-panel">
        <div class="vessel-info-heading">
          <p class="dashboard-panel-label">
            TRAJECTORY
          </p>

          <h4>
            Recorded history
          </h4>
        </div>

        <div
          v-if="historyLoading"
          class="vessel-history-state"
        >
          Loading historical
          positions...
        </div>

        <div
          v-else-if="historyError"
          class="
            vessel-history-state
            vessel-history-state--error
          "
        >
          {{ historyError }}
        </div>

        <div
          v-else-if="
            history.length < 2
          "
          class="vessel-history-state"
        >
          Not enough historical
          positions are available yet.
        </div>

        <template v-else>
          <div class="vessel-history-summary">
            <article>
              <span>
                Positions
              </span>

              <strong>
                {{ history.length }}
              </strong>
            </article>

            <article>
              <span>
                Duration
              </span>

              <strong>
                {{
                  formatDuration(
                    history,
                  )
                }}
              </strong>
            </article>

            <article>
              <span>
                Avg. speed
              </span>

              <strong>
                {{
                  averageSpeed(
                    history,
                  )
                }}

                <small>
                  kn
                </small>
              </strong>
            </article>
          </div>

          <p class="vessel-history-hint">
            The recorded trajectory is
            displayed directly on the map.
            Hover over historical points to
            inspect timestamp and speed.
          </p>
        </template>
      </section>
    </div>
  </section>
</template>