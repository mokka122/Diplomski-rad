# OceanEye — development handover

**Last updated:** 10 August 2026  
**Project root:** `C:\Projects\OceanEye`  
**Current development phase:** live data pipeline is working; the frontend map dashboard is working; current work is a targeted frontend interaction and visual polish pass.

---

## 1. Project purpose

OceanEye is an interactive maritime traffic monitoring and prediction system for a final thesis titled:

> **Razvoj interaktivnog sustava za nadzor i predikciju pomorskog prometa luke Rijeka primjenom tehnologija u realnom vremenu**

The thesis context remains the Port of Rijeka. The live demonstrator currently uses Norwegian AIS data because the BarentsWatch stream is a reliable public real-time source.

The application currently focuses on one Norwegian maritime area, rather than multi-port management.

---

## 2. Scope decisions

### Explicitly excluded from the current version

- User accounts, login, JWT and roles.
- Admin panel and user management.
- Multi-port management.
- AISStream as an active data source.
- VesselAPI polling as an active data source.
- Raw AIS message storage unless it becomes necessary later.
- Kafka, Redis and Elasticsearch until the core system is complete and stable.

### Chosen architecture

```text
BarentsWatch AIS stream
        ↓
BarentsWatch provider
        ↓
Normalizer
        ↓
MongoDB Atlas
   ├── vessels              current state
   └── vessel_positions    historical positions
        ↓
FastAPI
        ↓
Vue + Leaflet frontend
```

---

## 3. Confirmed completed work

### Data source and backend

- BarentsWatch account, client credentials and access token were created.
- The BarentsWatch live AIS stream was tested successfully with real messages.
- The old AISStream and VesselAPI architecture was cleaned out and replaced with a BarentsWatch-oriented structure.
- `VesselPosition` is the shared internal model.
- Incoming BarentsWatch messages are normalised to the internal model.
- Timestamps are handled as timezone-aware UTC values.
- MongoDB Atlas stores:
  - the newest state of each vessel in `vessels`;
  - the full history in `vessel_positions`.
- MongoDB deduplication uses a unique `(mmsi, timestamp)` index for historical positions.
- Current-state updates reject an older incoming position.
- The stream ingestion runs continuously, reconnecting after errors.

### Backend API

The following endpoints were created and successfully tested in Swagger:

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Confirms FastAPI and MongoDB connectivity. |
| `POST /ingestion/start` | Starts BarentsWatch continuous ingestion. |
| `POST /ingestion/stop` | Requests ingestion shutdown. |
| `GET /ingestion/status` | Shows ingestion state and counters. |
| `GET /vessels/` | Returns current vessels from MongoDB. |
| `GET /vessels/{mmsi}` | Returns a specific vessel's current state. |
| `GET /vessels/{mmsi}/history` | Returns historical positions for one vessel. |
| `POST /testing/save-vessel` | MongoDB test endpoint. |
| `POST /testing/save-history` | Historical MongoDB test endpoint. |

The testing endpoints are intentionally retained for development, demonstrations and future thesis screenshots.

### Frontend

- A Vite + Vue frontend was created in `frontend`.
- Vite development proxy forwards `/api/*` calls to FastAPI on port `8000`.
- FastAPI CORS allows the local Vite frontend on port `5173`.
- The frontend retrieves live current-state data from `GET /vessels/`.
- The dashboard refreshes vessel data every 15 seconds.
- A light-mode UI was created.
- Leaflet and OpenStreetMap tiles were added.
- The map is the central desktop view.
- Desktop layout has a right sidebar with current vessel details and a vessel list.
- On screen widths under `900px`, the sidebar is hidden and opened with a hamburger button.
- The logo asset is stored at `frontend/public/logo.png` and is currently enabled.

---

## 4. Current project structure

Only relevant files are shown below.

```text
OceanEye/
├── backend/
│   ├── .env                         # local only; never commit
│   ├── requirements.txt
│   ├── test_barentswatch.py          # standalone connection proof; keep
│   └── app/
│       ├── main.py
│       ├── api/
│       │   ├── ingestion.py
│       │   ├── testing.py
│       │   └── vessels.py
│       ├── db/
│       │   ├── database.py
│       │   └── startup.py
│       ├── models/
│       │   └── vessel.py
│       ├── repositories/
│       │   └── vessel_repository.py
│       └── services/
│           ├── normalizer.py
│           ├── data_providers/
│           │   ├── base.py
│           │   └── barentswatch.py
│           └── ingestion/
│               └── barentswatch_ingestion.py
├── frontend/
│   ├── public/
│   │   └── logo.png
│   ├── src/
│   │   ├── App.vue
│   │   ├── style.css
│   │   ├── services/api.js
│   │   └── components/VesselMap.vue
│   └── vite.config.js
└── docs/
    └── development-handover.md
```

---

## 5. Current frontend behaviour

The current frontend implementation has these confirmed characteristics:

- Header displays the supplied logo and also still contains the text `LIVE AIS MONITORING` and `OceanEye` next to it.
- The central Leaflet map shows vessel markers.
- The right sidebar displays:
  - active vessel count;
  - latest refresh time;
  - selected vessel data;
  - a compact vessel list.
- The sidebar is permanently visible on desktop and is a slide-out panel under `900px`.
- Hovering a desktop marker shows a Leaflet tooltip.
- Clicking a touch-device marker opens a Leaflet popup.

### Known issues found during the latest review

1. **The current vessel icon does not use the intended per-speed colours.**
   - `VesselMap.vue` currently uses one external PNG icon URL.
   - Its CSS applies a fixed teal `filter`, so every icon receives the same appearance.
   - `getMarkerColor()` exists but is not used by the marker icon creation code.

2. **On smaller screens, hovering a vessel can open the hidden sidebar.**
   - `App.vue` currently calls `isSidebarOpen = true` from `selectVessel()` when the viewport is below `900px`.
   - The map emits `vessel-selected` on marker hover for non-touch interaction, which indirectly opens the sidebar.
   - Required behaviour: only the hamburger button may open a hidden sidebar. Marker hover/click must only show vessel-specific map information.

3. **The logo header needs simplification.**
   - The logo should be wider.
   - The adjacent `LIVE AIS MONITORING` and `OceanEye` text should be removed because the supplied logo already conveys the brand.

---

## 6. Exact current stopping point

### Status

The backend and frontend are both connected and live data is visible on the frontend.

The project is currently stopped at the following UI refinement task:

> Replace the current external PNG vessel marker with a custom inline SVG vessel icon that rotates by heading/course and uses the existing speed-based colour logic. Prevent map interactions from opening the mobile sidebar. Make the logo wider and remove duplicate brand text next to it.

### Important distinction

The instructions for this refinement were provided, but their application has **not yet been confirmed**. The state inspected immediately before this handover still contains the old external PNG marker and the old sidebar-opening behaviour.

---

## 7. Next step: apply the pending UI refinement

### 7.1 Prevent the map from opening the hidden sidebar

File: `frontend/src/App.vue`

Replace this function:

```javascript
function selectVessel(vessel) {
  selectedVessel.value = vessel

  if (window.matchMedia('(max-width: 900px)').matches) {
    isSidebarOpen.value = true
  }
}
```

with:

```javascript
function selectVessel(vessel) {
  selectedVessel.value = vessel
}
```

Result:

- Marker hover on desktop updates sidebar data and shows the map tooltip.
- Marker click on touch devices shows the map popup only.
- The hidden sidebar opens only from the hamburger menu.

### 7.2 Replace the marker icon and restore different colours

File: `frontend/src/components/VesselMap.vue`

Delete the current `CARGO_SHIP_ICON_URL` constant. Then replace the current `createVesselIcon()` function with:

```javascript
function createVesselIcon(vessel) {
  const color = getMarkerColor(vessel.sog)
  const direction = getDirection(vessel)

  return L.divIcon({
    className: 'vessel-marker-wrapper',
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
  })
}
```

File: `frontend/src/style.css`

Delete the current `.cargo-ship-marker-wrapper` and `.cargo-ship-marker` blocks. Add:

```css
.vessel-marker-wrapper {
  border: 0 !important;
  background: transparent !important;
}

.vessel-marker {
  width: 34px;
  height: 42px;
  transform-origin: center;
  filter: drop-shadow(0 2px 2px rgb(13 48 55 / 30%));
}

.vessel-marker svg {
  display: block;
  width: 100%;
  height: 100%;
}
```

The existing colour function will then work as intended:

| Speed | Colour |
| --- | --- |
| Under 5 kn | Green |
| 5–15 kn | Teal |
| 15 kn and above | Orange |
| No speed data | Grey |

### 7.3 Simplify and widen the logo

File: `frontend/src/App.vue`

Replace the entire current `<div class="brand">...</div>` header brand block with:

```vue
<div class="brand">
  <div class="logo-slot">
    <img
      v-if="logoAvailable"
      src="/logo.png"
      alt="OceanEye logo"
    >

    <span v-else>OE</span>
  </div>
</div>
```

File: `frontend/src/style.css`

Replace the current `.brand` and `.logo-slot` rules with:

```css
.brand {
  display: flex;
  align-items: center;
}

.logo-slot {
  display: flex;
  width: 190px;
  height: 52px;
  align-items: center;
  justify-content: flex-start;
  overflow: hidden;
  background: transparent;
}

.logo-slot img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: left center;
}
```

Inside the `@media (max-width: 560px)` block, replace the old `.logo-slot` rule with:

```css
.logo-slot {
  width: 132px;
  height: 40px;
}
```

---

## 8. How to run and test the project

### Backend terminal

```powershell
cd C:\Projects\OceanEye\backend
venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Backend URLs:

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

Before testing the frontend, start ingestion in Swagger with `POST /ingestion/start`.

### Frontend terminal

```powershell
cd C:\Projects\OceanEye\frontend
npm run dev
```

Open the Vite URL, normally:

```text
http://localhost:5173
```

### UI refinement verification checklist

- Desktop: no sidebar animation/opening occurs on vessel hover.
- Desktop: hovering a vessel opens only the small map tooltip.
- Tablet/mobile: tapping a marker opens only the marker popup.
- Tablet/mobile: only the hamburger button opens the hidden sidebar.
- Vessel icons rotate according to heading/course.
- Different vessel speeds visibly produce green, teal, orange and grey icons.
- The header contains the wider logo only, without duplicate brand text.

---

## 9. Planned work after the current UI refinement

Work should continue in this order:

1. Add a dedicated vessel-details view or modal from the sidebar list.
2. Add trajectory display using `GET /vessels/{mmsi}/history`.
3. Add historical time-range selection and a trajectory polyline on the map.
4. Add basic dashboard traffic metrics, such as vessel count, average speed and ship-type distribution.
5. Locate and evaluate a large historical AIS dataset for machine learning.
6. Prepare traffic-density features and train a `LOW` / `MEDIUM` / `HIGH` traffic classification model.
7. Evaluate the model with accuracy, precision, recall, F1-score and a confusion matrix.
8. Expose traffic-classification results through FastAPI and display them in the frontend.
9. Only after the core system works: assess whether Redis, Elasticsearch or Kafka provide a demonstrable and justified benefit.

---

## 10. Important operational notes

- Never commit `.env`, BarentsWatch credentials or MongoDB credentials.
- Keep `test_barentswatch.py`; it documents the successful live-stream proof.
- Keep testing endpoints for Swagger demonstrations and thesis screenshots.
- MongoDB Atlas may occasionally fail with a TLS handshake error because of network, VPN, firewall or Atlas access-list conditions. This is an environment/connection issue, not an ingestion-code issue.
- If Atlas fails, first check cluster status, Atlas Network Access, VPN state and outbound port `27017` before changing application logic.
- Avoid introducing Kafka, Redis or Elasticsearch merely for complexity. The working live pipeline, frontend map and ML classification have priority.

---

## 11. One-sentence continuation prompt

Use this prompt in a future conversation:

> OceanEye uses a working BarentsWatch → FastAPI → MongoDB Atlas → Vue/Leaflet pipeline. Read `docs/development-handover.md`, inspect the current project files, and continue from the pending frontend UI refinement: replace the fixed-colour external vessel PNG with the documented coloured rotating inline SVG vessel icon, prevent map interaction from opening the mobile sidebar, and simplify the logo header. Give manual copy/paste instructions only; do not edit files yourself.
