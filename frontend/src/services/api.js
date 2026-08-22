const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "/api";


async function parseErrorResponse(
  response,
  fallbackMessage,
) {
  const data = await response
    .json()
    .catch(() => null);

  const detail =
    data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (
    detail &&
    typeof detail === "object"
  ) {
    return (
      detail.message ||
      fallbackMessage
    );
  }

  return fallbackMessage;
}


export async function getCurrentVessels() {
  const response = await fetch(
    `${API_BASE_URL}/vessels/`,
  );

  if (!response.ok) {
    throw new Error(
      await parseErrorResponse(
        response,
        `Unable to load vessels (${response.status})`,
      ),
    );
  }

  return response.json();
}


export async function getVesselHistory(
  mmsi,
  limit = 500,
) {
  const response = await fetch(
    `${API_BASE_URL}/vessels/${encodeURIComponent(
      mmsi,
    )}/history?limit=${limit}`,
  );

  if (!response.ok) {
    throw new Error(
      await parseErrorResponse(
        response,
        `Unable to load vessel history (${response.status})`,
      ),
    );
  }

  return response.json();
}


export async function getCurrentTraffic() {
  const response = await fetch(
    `${API_BASE_URL}/traffic/current`,
  );

  if (!response.ok) {
    throw new Error(
      await parseErrorResponse(
        response,
        `Unable to load current traffic (${response.status})`,
      ),
    );
  }

  return response.json();
}


export async function getPredictionStatus() {
  const response = await fetch(
    `${API_BASE_URL}/prediction/live/status`,
  );

  if (!response.ok) {
    throw new Error(
      await parseErrorResponse(
        response,
        `Unable to load prediction status (${response.status})`,
      ),
    );
  }

  return response.json();
}


export async function getLivePrediction() {
  const response = await fetch(
    `${API_BASE_URL}/prediction/live`,
  );

  if (
    response.status === 503
  ) {
    return null;
  }

  if (!response.ok) {
    throw new Error(
      await parseErrorResponse(
        response,
        `Unable to load live prediction (${response.status})`,
      ),
    );
  }

  return response.json();
}